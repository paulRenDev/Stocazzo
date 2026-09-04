"""Area -> flight-grid -> waypoints mapping engine (brief sec. 3).

Phase 2 work: given a drawn polygon and front/side overlap + altitude +
camera parameters, compute flight lines, waypoint spacing, and camera
actions, then hand the result to `mission.generator` to produce the
`WpmlMission` structure.

Not started. This needs:

- The Mini 5 Pro's actual camera field-of-view / sensor parameters (for
  ground-sampling-distance and overlap-driven line/photo spacing), which
  DJI Fly likely does not encode in the KMZ itself — these come from
  DJI's own published Mini 5 Pro specs, not from reverse-engineering the
  mission file.
- A confirmed understanding, from a real multi-line DJI-Fly-generated
  mapping mission, of how DJI Fly itself expresses "the same photo
  actions repeated per waypoint" as multiple wayline templates/folders —
  the one sample analyzed so far (see docs/WPML_FINDINGS.md) is a plain
  3-waypoint route, not a mapping grid, so the multi-line case is
  unverified.

Do not implement this against assumptions; see docs/BUILD_SPEC.md sec. 3
(Phase 2) before starting.
"""
