# Build Spec — DJI Mapping Mission Builder

Status: **Phase 0 well underway** — six real DJI Mini 5 Pro + RC 2
exports have been analyzed: `examples/original_dji_mission.kmz` (3
waypoints), `examples/original_dji_mission_wp2_edited.kmz` (one
waypoint's height edited), `examples/original_dji_mission_14wp_loop.kmz`
(a structurally different 14-waypoint freeform loop), two further edits
of that loop adding camera actions and an appended waypoint
(`..._14wp_with_camera_actions.kmz`, `..._15wp_with_camera_actions.kmz`),
and a 20-waypoint route with 8 `takePhoto` actions
(`..._20wp_multi_photo.kmz`).
Findings are in `docs/WPML_FINDINGS.md`; the parser/generator/validator
pass identity round-trip tests against all five, plus diff-based tests
confirming: `executeHeight` is safely, independently per-waypoint
editable; `takePhoto`/`startRecord`/`stopRecord` actions and their exact
parameter shapes; that `actionGroupId` marks single-point-trigger (1) vs.
transition (2) action groups; that `actionId` is a global, no-duplicates
counter that is **not** stable across edits; and that first/last-waypoint
markers (`waypointTurnMode`, `waypointHeadingAngleEnable`, whether a
transition action group exists) are recomputed by DJI Fly on every save
based on current route position, not fixed per waypoint. Phase 0 is not
*complete*: the main remaining gap is that no sample so far is an actual
mapping-grid mission, and it's still unconfirmed whether continuous
photo capture uses an interval/distance trigger rather than the one-shot
`reachPoint` trigger seen everywhere so far — both needed before Phase 2
(see `docs/WPML_FINDINGS.md`, "Next steps"). This
document turns the original Dutch project brief (`docs/PROJECT_BRIEF.md`)
into a sequenced, buildable spec. It exists so that any agent (Opus,
Sonnet, or a human) can pick up a phase and know exactly what "done" looks
like, without re-deriving the reasoning below.

## 0. Governing principle

> The AI decides *what the user means*. The mission engine computes the
> actual flight plan deterministically. The AI never writes WPML/KMZ.

Nothing in this codebase should let a language model hand-write or
hand-edit mission XML. The AI assistant's only output is a structured
parameter object (see §5); everything from there to the `.kmz` on disk is
deterministic code, covered by tests.

## 1. Why Phase 0 blocks everything else

DJI's Wayline Mission format (WPML, wrapped in a `.kmz`) is not fully public
spec — DJI publishes a *partial* schema for its Cloud API, but what DJI Fly
actually writes for a given aircraft/RC combination (field names present,
namespaces, default values, which tags are aircraft-specific) varies by
firmware and app version and is only reliably known by inspecting a real
file. Guessing at the schema and shipping a generator against the guess is
exactly the "op goed geluk XML aanpassen" failure mode the brief explicitly
rules out (brief §11, §18).

So: no `mission/generator.py`, `mission/mapping.py` (the KMZ-facing parts),
or `wpml/schemas/*` gets implemented against assumptions. They get built
against a real exported mission.

**What we have:** one real export, `examples/original_dji_mission.kmz` — a
plain 3-waypoint route, `droneEnumValue=68`/`droneSubEnumValue=0`. See
`docs/WPML_FINDINGS.md` for the full field-by-field breakdown.

**What we still need from the user:** at least one more `.kmz`, ideally
two: (a) the *same* mission re-exported after changing exactly one
parameter (start with altitude) in DJI Fly, to confirm what "editable"
actually means field-by-field (§7); (b) a real DJI-Fly-generated
*mapping*-grid mission (many waypoints, `startRecord`/`takePhoto`
actions) — the current sample is a plain route, not a mapping mission, so
it doesn't yet inform Phase 2 (§3 mapping.py).

## 2. Current implementation status

| Module | Brief section | Status |
|---|---|---|
| `mission/naming.py` | §6 (filename standard), §7 (versioning), §8 (mission ID + metadata) | **Implemented + tested** |
| `mission/parser.py` | §18 (generic inspector) + real WPML 1.0.2 structured parser | **Implemented + tested** against `examples/original_dji_mission.kmz` |
| `mission/generator.py` | §2, §11 | **Implemented + tested** — identity round-trip against the real sample passes (structural equivalence; DJI Fly re-import still needs manual confirmation, see §7) |
| `mission/validator.py` | §12 | **Implemented + tested** — structural/range checks only; aircraft-specific numeric limits (max altitude/speed) intentionally NOT hardcoded, see the module docstring |
| `mission/mapping.py` | §3 | **Stubbed** — needs a real mapping-grid sample, see §1 |
| `wpml/schemas/*`, `wpml/templates/*` | §11 | **Empty** — the parser/generator currently model the WPML structure directly as dataclasses rather than a separate schema layer; revisit once a second/third real sample either confirms this generalizes or shows it needs to be split out |
| `app/*` (map UI, mission editor) | §9, §14, §15 | **Not started** — UI work should follow the engine, not precede it (see brief §18, and the advisor thread the user forwarded: build the engine core first) |

## 3. Phase plan

### Phase 0 — Reverse-engineering (in progress)

Done for the one sample analyzed: archive layout, namespace/version,
mission-config fields, waypoint fields, action groups — all documented in
`docs/WPML_FINDINGS.md`, backed by `mission/parser.py`'s structured parser
and its tests.

Still open (see `docs/WPML_FINDINGS.md`, "Next steps"):

1. A second real sample — same mission, one field changed in DJI Fly,
   re-exported — to confirm which fields are safe to edit vs which
   silently break DJI Fly's acceptance of the file, and to move the
   "editable vs do-not-modify" table there from hypothesis to confirmed.
2. A real DJI-Fly-generated mapping-grid mission, needed before Phase 2
   can start on solid ground.
3. Manual DJI Fly import of the round-trip-regenerated file (produced by
   `mission.generator.export_mission` with zero intentional changes) to
   confirm DJI Fly actually accepts it, not just that it re-parses
   identically.
4. Once (1)-(3) are in hand: decide whether `wpml/schemas/*` and
   `wpml/templates/*` need to exist as a separate layer, or whether the
   dataclass-based parser/generator already serve that role well enough.

### Phase 1 — MVP v0.1 (brief §17)

Import → parse → display-as-data → adjust a few scalar params (altitude,
speed, gimbal, photo action) → re-validate → re-export. The identity
round-trip (parse → re-export with no changes → re-parse → compare) is
implemented and passing (`tests/test_generator.py`); the "change one
field" round-trip against a live DJI Fly still needs step (1) above before
the UI can honestly claim any given field is safe to edit. No map UI
required yet — a CLI or a plain data dump is enough to satisfy v0.1.

### Phase 2 — v0.2: mapping engine (brief §3, §17)

Polygon in → flight-grid generation (front/side overlap, line spacing,
photo spacing, direction, start/end point, turn mode) → waypoints + camera
actions → through the same generator/validator/export path as Phase 1.
This is pure geometry + the deterministic engine in the brief's
architecture diagram (§16); still no AI involved.

### Phase 3 — v0.3: AI assistant (brief §4, §17)

A chat surface that turns natural language into the structured parameter
JSON shown in brief §4 — and stops there. The mission engine from Phase 2
consumes that JSON exactly as if a human had typed it into the Quick
Mission form (brief §14). The AI never sees or touches XML.

### Phase 4: UI polish (brief §9, §15)

Map view, expert mode, quick mission mode. Deliberately last: every prior
phase is independently testable headlessly.

## 4. Directory layout

```
dji_mission_builder/
├── AGENTS.md              # instructions for agents working in this project
├── README.md
├── docs/
│   ├── PROJECT_BRIEF.md   # original brief, verbatim
│   ├── BUILD_SPEC.md      # this file
│   └── WPML_FINDINGS.md   # created in Phase 0, once a real KMZ exists
├── app/
│   ├── ui/
│   ├── map/
│   └── mission_editor/
├── mission/
│   ├── parser.py          # Phase 0 inspector now; WPML parser after Phase 0
│   ├── generator.py       # stub until Phase 0 findings exist
│   ├── mapping.py         # stub until Phase 2
│   ├── validator.py       # stub until Phase 0 findings exist
│   └── naming.py          # implemented
├── wpml/
│   ├── schemas/           # empty until Phase 0
│   └── templates/         # empty until Phase 0
├── tests/
└── examples/
    └── (drop real .kmz files here — see examples/README.md)
```

## 5. AI → engine contract (brief §4, §16)

The AI assistant's entire output surface is one JSON object, e.g.:

```json
{
  "mission_type": "mapping_2d",
  "name": "Boerderij Jos",
  "altitude_m": 100,
  "front_overlap": 0.80,
  "side_overlap": 0.70,
  "speed_ms": 5,
  "gimbal_pitch": -90,
  "camera_action": "photo",
  "flight_direction": "long_axis"
}
```

The mission engine (Phase 2) validates and fills in the rest
deterministically. If a required field is missing or a value is out of
range, the engine returns a structured error/warning list (brief §10) — the
AI can use that to ask a clarifying follow-up, but it still cannot patch
the mission itself.

## 6. Mission-type registry (brief §5)

Kept as a single source of truth once code exists (e.g.
`mission/naming.py::MISSION_TYPES` or similar) rather than duplicated
across modules:

- `WP2D` — 2D mapping
- `WP3D` — 3D mapping
- `WPINS` — inspection
- `WPVID` — video
- `WPGEN` — generic waypoint mission

## 7. Round-trip test plan (once real KMZ(s) exist)

1. **Identity round-trip**: import a real `.kmz` → parse → re-export with
   zero intentional changes → the regenerated file must be accepted by DJI
   Fly and fly identically. Where byte-identical isn't achievable (e.g.
   zip metadata, ordering), the test asserts semantic equivalence of every
   parsed field, and a human confirms the DJI-Fly-import step manually.
2. **Single-parameter round-trip**: change exactly one supported field
   (start with altitude) → export → confirm DJI Fly accepts it and the
   change is the *only* observed difference against sample 1.
3. Repeat per field the team wants to mark "editable" before trusting it in
   the UI. Fields that fail this test move to "do not modify" (brief §11)
   or "experimental, not recommended" (brief §15) until understood.

Automate what can be automated (archive structure, XML schema/field
diffing) in `tests/`; the actual DJI Fly import/flight check is manual and
should be logged in `docs/WPML_FINDINGS.md`.

## 8. Non-goals / hard rules (carried over from the brief)

- Never let the AI generate or directly edit KMZ/XML (§1, §4, §16).
- Never overwrite the user's originally imported `.kmz` (§2, §7).
- Never start the drone or push a mission to the aircraft — this tool only
  ever produces a `.kmz` file (§12).
- Every export goes through CREATE → CALCULATE → PREVIEW → VALIDATE →
  EXPORT (§10); no shortcut path to a `.kmz`.
