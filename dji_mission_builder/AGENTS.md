# Agent instructions — DJI Mapping Mission Builder

Read `docs/PROJECT_BRIEF.md` (the original spec, in Dutch) and
`docs/BUILD_SPEC.md` (the sequenced technical spec derived from it) before
doing anything else in this directory. This file is the short version /
guardrails; those two are the source of truth.

## Current status

**Phase 0 is well underway, not complete.** Six real DJI Mini 5 Pro + RC 2
exports have been reverse-engineered (`examples/original_dji_mission*.kmz`,
findings in `docs/WPML_FINDINGS.md`), and `mission/parser.py`,
`mission/generator.py`, and `mission/validator.py` are implemented and
tested against all of them, including passing identity round-trips
(`tests/test_generator.py` and others). Confirmed so far: `executeHeight`
is safely per-waypoint editable; `takePhoto`/`startRecord`/`stopRecord`
action shapes; `actionGroupId` marks single-point-trigger (1) vs.
transition (2) groups; `actionId` is a global, no-duplicates counter that
is **not** stable across edits; first/last-waypoint markers
(`waypointTurnMode`, `waypointHeadingAngleEnable`, whether a transition
action group exists) are recomputed on every save, not fixed per
waypoint. Read `docs/WPML_FINDINGS.md` before touching any of the three
modules above — it lists exactly what's confirmed vs still a hypothesis,
and corrects at least one of its own earlier claims once evidence
disproved it (that's expected — update it the same way when new evidence
does that again).

**`mission/mapping.py` is implemented** (polygon → lawnmower grid →
`WpmlMission`, one `takePhoto` per waypoint, no interval/distance
trigger — see `docs/BUILD_SPEC.md` Phase 2 for why that's fine). Two
things in it are explicitly NOT reverse-engineered facts and are flagged
as such in its docstring: the Mini 5 Pro camera model used for
footprint/GSD math (sourced from manufacturer spec pages) and the
across-track/along-track axis mapping. Revisit both if a real
DJI-Fly-generated mapping export or camera calibration ever surfaces. Do
NOT reach for DJI's official `templateType=mapping2d`/`overlap`/
`multipleDistance` fields (from `dji-sdk/Cloud-API-Doc`) instead of this
module's approach — that spec is enterprise/Dock-only (its own "Product
Support" tables never list the Mini series) and two of its details
already contradict our real Mini 5 Pro samples (namespace URI,
transition-group trigger type).

**`wpml/schemas/*` and `wpml/templates/*` stay empty** — the dataclass
parser/generator already serve that role across six structurally
different samples; revisit only if that stops holding up.

**Do not mark any field "confirmed editable" beyond what
`docs/WPML_FINDINGS.md`'s "Editable vs do-not-modify" section already
lists as confirmed.** Several fields remain "likely editable, not yet
isolated by a diff" even after six samples — see that section.

## Hard rules (non-negotiable, carried from the brief)

1. The AI assistant (chat/NL layer) only ever produces the structured
   parameter JSON described in `docs/BUILD_SPEC.md` §5. It never generates
   or edits WPML/KMZ/XML directly. All XML I/O goes through the
   deterministic `mission/` engine.
2. Never overwrite a user's originally imported `.kmz`. Every edit produces
   a new versioned file (see `mission/naming.py`).
3. This tool never talks to the drone or pushes a mission to the aircraft.
   Its only output is a `.kmz` file on disk. The user loads it into DJI Fly
   themselves.
4. Every export goes through CREATE → CALCULATE → PREVIEW → VALIDATE →
   EXPORT. No code path skips VALIDATE.
5. Keep "editable" vs "do-not-modify" DJI fields explicitly distinguished
   in code and in the UI (once there is a UI) — never silently drop or
   rewrite a field you haven't confirmed is safe to touch (see the
   round-trip test plan, build spec §7).

## What's already built and safe to extend

- `mission/naming.py` — filename/mission-ID/versioning logic (brief §6–8).
- `mission/parser.py` — generic inspector (`inspect_kmz`) plus the real
  WPML 1.0.2 structured parser (`parse_mission`), grounded in all six
  samples in `examples/`.
- `mission/generator.py` — rebuilds a `.kmz` from the parsed structure;
  identity round-trip confirmed by test against every sample.
- `mission/validator.py` — structural/range checks; deliberately has no
  hardcoded aircraft-specific limits yet (see its docstring).
- `mission/mapping.py` — Phase 2 grid engine: `CameraModel`/footprint/GSD
  math, `generate_lawnmower_grid`, `build_mapping_mission`.
- Tests for all of the above, run against the real samples
  (`tests/test_parser.py`, `test_generator.py`, `test_validator.py`,
  `test_diff_findings.py`, `test_structural_patterns.py`,
  `test_camera_actions.py`, `test_multi_photo_route.py`,
  `test_mapping.py`).

Extending the parser/generator to cover fields from a *new* real sample is
in scope any time — that's exactly how Phase 0 is meant to grow. Guessing
fields that no sample has shown is not.

## What still needs more real `.kmz` samples

Confirming the "editable vs do-not-modify" hypothesis in
`docs/WPML_FINDINGS.md` (needs a same-mission-one-field-changed pair for
the fields still marked "likely" rather than "confirmed"); validating
`mission/mapping.py`'s camera model and axis-mapping assumptions against
a real mapping-grid export if one ever surfaces; and the map/mission-editor
UI (needs the engine to be further along first, per brief §18). See build
spec §1–3 for the full phase breakdown.

## Style

- Python for `mission/` and `wpml/`. Keep modules small and testable;
  the mission engine must be usable headlessly (no UI dependency) since
  Phase 1's acceptance test is a round-trip, not a UI interaction.
- No speculative abstractions ahead of Phase 0 data. It's fine for
  `generator.py` etc. to stay a documented stub with a `NotImplementedError`
  until real findings exist.
