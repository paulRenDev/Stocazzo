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
- `original_dji_mission_14wp_loop.kmz` — a different, larger mission: 14
  waypoints in a freeform loop, no camera actions at all. Used to confirm
  several structural patterns (turn mode and heading-angle-enable at the
  route's start/end, `actionGroupId` reuse, `actionId` as one global
  counter) generalize beyond the 3-waypoint sample. See
  `docs/WPML_FINDINGS.md`, "Confirmed at n=14".

Findings from all three are documented in `docs/WPML_FINDINGS.md`, and the
diffs/patterns are encoded as regression tests in
`tests/test_diff_findings.py` and `tests/test_structural_patterns.py`.

## What's still useful to add here

1. A sample that changes *only* coordinates (no height change), to
   isolate that field the way the height edit above was isolated.
2. A sample that changes a mission-level field (e.g. `finishAction`)
   rather than a per-waypoint one.
3. **The main remaining gap**: a real DJI-Fly-generated *mapping* mission
   (grid/lawnmower pattern, many waypoints, photo/video actions) — needed
   before `mission/mapping.py` (Phase 2) can be built on evidence. None of
   the three samples so far has a `startRecord`/`takePhoto` action, so how
   DJI Fly triggers photos/video in a mission is still completely open.

Never overwrite an existing file here — each real export is a reference
data point; add new ones alongside, don't replace.
