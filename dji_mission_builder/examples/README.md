# Examples

Real DJI Fly exports for the Mini 5 Pro + RC 2, used to ground the
parser/generator/validator in actual DJI output instead of assumptions
(see `docs/BUILD_SPEC.md` sec. 1).

- `original_dji_mission.kmz` — the first real sample. A plain 3-waypoint
  route (not a mapping grid). Findings documented in
  `docs/WPML_FINDINGS.md`.

## What's still useful to add here

1. The same mission as `original_dji_mission.kmz`, re-exported from DJI
   Fly after changing exactly one setting (start with altitude). Name it
   something like `original_dji_mission_altitude_changed.kmz`. This is
   what turns the "editable vs do-not-modify" table in
   `docs/WPML_FINDINGS.md` from a hypothesis into a confirmed fact.
2. A real DJI-Fly-generated *mapping* mission (grid pattern, many
   waypoints, photo/video actions) — needed before `mission/mapping.py`
   (Phase 2) can be built on evidence.

Never overwrite an existing file here — each real export is a reference
data point; add new ones alongside, don't replace.
