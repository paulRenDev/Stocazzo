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
pass identity round-trip tests against all six, plus diff-based tests
confirming: `executeHeight` is safely, independently per-waypoint
editable; `takePhoto`/`startRecord`/`stopRecord` actions and their exact
parameter shapes; that `actionGroupId` marks single-point-trigger (1) vs.
transition (2) action groups; that `actionId` is a global, no-duplicates
counter that is **not** stable across edits; and that first/last-waypoint
markers (`waypointTurnMode`, `waypointHeadingAngleEnable`, whether a
transition action group exists) are recomputed by DJI Fly on every save
based on current route position, not fixed per waypoint.

**Phase 2 is now considered unblocked**, not waiting on a real
mapping-grid sample: cross-referencing DJI's official WPML spec and
independent third-party sources (see `docs/WPML_FINDINGS.md`,
"Cross-reference") strongly indicates (a) DJI Fly on the Mini 5 Pro has
no native mapping/grid mode at all — third-party tools compute the grid
externally and hand DJI Fly a plain waypoint mission, exactly this
project's own architecture — and (b) WPML's interval/distance camera
auto-trigger (`multipleTiming`/`multipleDistance`) isn't supported on
this aircraft anyway, consistent with all six real samples using only
one-shot `reachPoint` triggers. So Phase 2 doesn't need a DJI-generated
mapping export to build against: it needs to compute the grid itself
(pure geometry, brief §3) and emit it through the already-confirmed
plain-waypoint-mission structure, one `takePhoto` per grid point. This
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

## 1. Why Phase 0 came first

DJI's Wayline Mission format (WPML, wrapped in a `.kmz`) is not fully public
spec — DJI publishes a *partial* schema for its Cloud API, but what DJI Fly
actually writes for a given aircraft/RC combination (field names present,
namespaces, default values, which tags are aircraft-specific) varies by
firmware and app version and is only reliably known by inspecting a real
file. Guessing at the schema and shipping a generator against the guess is
exactly the "op goed geluk XML aanpassen" failure mode the brief explicitly
rules out (brief §11, §18).

So: `mission/generator.py`, `mission/mapping.py` (the KMZ-facing parts),
and `wpml/schemas/*` don't get implemented against assumptions. They get
built against real exported missions.

**What we have:** six real exports, from `examples/original_dji_mission.kmz`
(3 waypoints, `droneEnumValue=68`/`droneSubEnumValue=0`) through a
20-waypoint multi-photo route. See `docs/WPML_FINDINGS.md` for the full
field-by-field breakdown, including two diff-confirmed edits and a
cross-reference against DJI's official (enterprise-oriented) WPML spec.

**What's still open, but no longer blocking:** no sample is an actual
mapping/lawnmower-grid mission — but per `docs/WPML_FINDINGS.md`,
"Cross-reference", that's very likely because DJI Fly has no native
mapping mode on the Mini 5 Pro at all, so there may never be one to
capture. Phase 2 can proceed on the plain-waypoint-mission structure
already confirmed (§3 Phase 2, below) rather than waiting on it.

## 2. Current implementation status

| Module | Brief section | Status |
|---|---|---|
| `mission/naming.py` | §6 (filename standard), §7 (versioning), §8 (mission ID + metadata) | **Implemented + tested** |
| `mission/parser.py` | §18 (generic inspector) + real WPML 1.0.2 structured parser | **Implemented + tested** against all six real samples |
| `mission/generator.py` | §2, §11 | **Implemented + tested** — identity round-trip against every real sample passes (structural equivalence; DJI Fly re-import still needs manual confirmation, see §7) |
| `mission/validator.py` | §12 | **Implemented + tested** — structural/range checks only; aircraft-specific numeric limits (max altitude/speed) intentionally NOT hardcoded, see the module docstring |
| `mission/mapping.py` | §3 | **Implemented + tested** — polygon → lawnmower grid → `WpmlMission`, one `takePhoto` per waypoint; camera model sourced from Mini 5 Pro manufacturer specs (unverified against a real mapping export, see the module docstring) |
| `wpml/schemas/*`, `wpml/templates/*` | §11 | **Empty** — the parser/generator currently model the WPML structure directly as dataclasses rather than a separate schema layer; revisit once a second/third real sample either confirms this generalizes or shows it needs to be split out |
| `app/*` (map UI, mission editor) | §9, §14, §15 | **First version implemented** — a local Flask app with a Leaflet map: draw a polygon, set mapping parameters, preview the computed grid + stats, export a versioned `.kmz`. See §3 Phase 4 below for what's not covered yet |

## 3. Phase plan

### Phase 0 — Reverse-engineering (well underway)

Done across the six samples analyzed: archive layout, namespace/version,
mission-config fields, waypoint fields, action groups, camera actions,
dynamic first/last-waypoint markers, compound action groups — all
documented in `docs/WPML_FINDINGS.md`, backed by `mission/parser.py`'s
structured parser and a battery of tests.

Still open (see `docs/WPML_FINDINGS.md`, "Next steps") but none of these
block Phase 2 any more:

1. A sample isolating a coordinates-only edit, and one changing a
   mission-level field (e.g. `finishAction`) — would move a few more rows
   from "likely editable" to "confirmed" in the editable-field table.
2. Manual DJI Fly import of a round-trip-regenerated file (produced by
   `mission.generator.export_mission` with zero intentional changes) to
   confirm DJI Fly actually accepts it, not just that it re-parses
   identically.
3. Decide whether `wpml/schemas/*` and `wpml/templates/*` need to exist
   as a separate layer, or whether the dataclass-based parser/generator
   already serve that role well enough — leaning toward the latter given
   how cleanly six structurally different samples have fit the same
   dataclasses so far.

### Phase 1 — MVP v0.1 (brief §17)

Import → parse → display-as-data → adjust a few scalar params (altitude,
speed, gimbal, photo action) → re-validate → re-export. The identity
round-trip (parse → re-export with no changes → re-parse → compare) is
implemented and passing (`tests/test_generator.py`); the "change one
field" round-trip against a live DJI Fly still needs step (1) above before
the UI can honestly claim any given field is safe to edit. No map UI
required yet — a CLI or a plain data dump is enough to satisfy v0.1.

### Phase 2 — v0.2: mapping engine (brief §3, §17) — **implemented**

`mission/mapping.py`: polygon in → boustrophedon flight-grid generation
(front/side overlap → line spacing/photo spacing via a Mini-5-Pro camera
model, compass-bearing direction, first/last-waypoint turn/heading
markers recomputed per the confirmed dynamic-marker behavior) →
`WpmlMission` → the same `mission.generator`/`mission.validator`/export
path as Phase 1. Pure geometry, no AI involved, matching the brief's
architecture diagram (§16).

**This did not need a new WPML shape**, confirming the Phase 0 research:
DJI's official WPML spec defines a `templateType=mapping2d/mapping3d`
mechanism with its own `overlap`/`direction`/`shootType`/`Polygon`
fields, but that spec's "Product Support" only ever lists enterprise Dock
aircraft, and independent sources indicate DJI Fly has no such native
mode on the Mini 5 Pro at all (see `docs/WPML_FINDINGS.md`,
"Cross-reference"). So `mission/mapping.py` owns the grid math itself
(brief §3 says this outright anyway) and emits it through the
already-confirmed plain-waypoint-mission structure — a `WaylineFolder`
with many `Waypoint`s, one `takePhoto` (`reachPoint`) action per grid
point, mirroring `examples/original_dji_mission_20wp_multi_photo.kmz`.
No interval/distance trigger used or needed.

Two things in `mission/mapping.py` are explicitly flagged in its
docstring as *not* reverse-engineered facts, since no real DJI-Fly
mapping-grid export exists to check them against: the Mini 5 Pro camera
model (sensor resolution/FOV, sourced from manufacturer spec pages, used
to compute footprint/GSD/spacing) and the across-track/along-track axis
mapping (which photo dimension governs line spacing vs. photo spacing).
Revisit both if a real mapping export or camera calibration ever
surfaces. Fixed alongside this: `mission/generator.py` had a latent
precision bug (`:g` formatting silently truncates to 6 significant
figures) that every real sample's round numbers happened not to trigger,
but a computed mapping altitude/speed could — see
`tests/test_generator.py::test_high_precision_values_survive_round_trip`.

Not yet done within Phase 2: the polygon-clipping is single-interval per
scan line (correct for convex/simple shapes, documented limitation for
strongly concave polygons — see `generate_lawnmower_grid`'s docstring).

### Phase 3 — v0.3: AI assistant (brief §4, §17) — not started

A chat surface that turns natural language into the structured parameter
JSON shown in brief §4 — and stops there. The mission engine from Phase 2
consumes that JSON exactly as if a human had typed it into the Quick
Mission form (brief §14). The AI never sees or touches XML.

### Phase 4: UI (brief §9, §14, §15) — first version implemented

`app/server.py` (Flask) + `app/templates/index.html` +
`app/static/main.js`: a three-pane layout matching brief §9 (settings
left, Leaflet map middle, mission-info right). Draw a polygon with
Leaflet.draw, set the Phase 2 mapping parameters, **Preview** computes
the grid via `mission.mapping` and validates via `mission.validator`
(errors block export, warnings don't), **Exporteer .kmz** downloads a
correctly-named, auto-versioned file via `mission.naming`/`generator`.
Runs locally via `run.sh`/`run.bat` — no install beyond Python + Flask,
no data leaves the user's machine. Leaflet/Leaflet.draw are vendored in
`app/static/vendor/` rather than CDN-loaded, so only real map tile
imagery needs internet at runtime.

Verified with a real headless-browser run (draw polygon → preview →
export → downloaded file re-parses cleanly through `mission.parser`),
not just the Flask-test-client tests in `tests/test_app.py`.

Not yet covered by this first UI pass, still open for a later Phase 4
iteration:

- Importing an existing `.kmz` to view/edit (brief §2, §13) — this UI
  only creates new mapping missions.
- Quick Mission mode vs. Expert Mode as distinct UI states (brief §14-15)
  — currently one form with every Phase-2 parameter exposed.
- The AI chat surface (Phase 3) feeding into this same form/preview flow.
- WP3D/WPINS/WPVID mission types — `mission/mapping.py` only builds
  WP2D so far.

## 4. Directory layout

```
dji_mission_builder/
├── AGENTS.md              # instructions for agents working in this project
├── README.md
├── docs/
│   ├── PROJECT_BRIEF.md   # original brief, verbatim
│   ├── BUILD_SPEC.md      # this file
│   └── WPML_FINDINGS.md   # created in Phase 0, once a real KMZ exists
├── run.sh / run.bat       # start the web UI
├── app/                   # Flask app (Phase 4, first version)
│   ├── server.py
│   ├── static/            # main.js, style.css, vendor/ (Leaflet, vendored)
│   └── templates/         # index.html
├── mission/
│   ├── parser.py          # implemented (Phase 0 inspector + WPML parser)
│   ├── generator.py       # implemented
│   ├── mapping.py         # implemented (Phase 2 grid engine)
│   ├── validator.py       # implemented
│   └── naming.py          # implemented
├── wpml/
│   ├── schemas/           # empty -- parser/generator dataclasses serve this role
│   └── templates/         # empty -- see above
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
