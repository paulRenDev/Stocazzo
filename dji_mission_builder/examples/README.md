# Examples

Real DJI Fly exports for the Mini 5 Pro + RC 2, used to ground the
parser/generator/validator in actual DJI output instead of assumptions
(see `docs/BUILD_SPEC.md` sec. 1).

- `original_dji_mission.kmz` — the first real sample. A plain 3-waypoint
  route (not a mapping grid).
- `original_dji_mission_wp2_edited.kmz` — the same mission, re-saved from
  the RC 2 after editing waypoint 2's height (50m → 201m). This is what
  confirmed `executeHeight` is safely, independently per-waypoint
  editable (see `docs/WPML_FINDINGS.md`, "Confirmed via diff").

Findings from both are documented in `docs/WPML_FINDINGS.md`, and the diff
between them is encoded as a regression test in
`tests/test_diff_findings.py`.

## What's still useful to add here

1. A sample that changes *only* coordinates (no height change), to
   isolate that field the way the height edit above was isolated.
2. A sample that changes a mission-level field (e.g. `finishAction`)
   rather than a per-waypoint one.
3. A real DJI-Fly-generated *mapping* mission (grid pattern, many
   waypoints, photo/video actions) — needed before `mission/mapping.py`
   (Phase 2) can be built on evidence.

Never overwrite an existing file here — each real export is a reference
data point; add new ones alongside, don't replace.
