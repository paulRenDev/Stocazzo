from pathlib import Path

from mission.generator import export_mission
from mission.parser import parse_mission

EXAMPLE_KMZ = Path(__file__).parent.parent / "examples" / "original_dji_mission.kmz"


def test_identity_round_trip(tmp_path):
    """Phase 1 acceptance gate (build spec sec. 7): parse a real DJI export,
    re-export it with no intentional changes, and confirm the regenerated
    file parses back to an identical structure. This does not by itself
    prove DJI Fly accepts the regenerated file — that still needs a manual
    DJI Fly import check per docs/BUILD_SPEC.md sec. 7.
    """
    original = parse_mission(str(EXAMPLE_KMZ))

    output_path = tmp_path / "roundtrip.kmz"
    export_mission(original, str(output_path))

    reparsed = parse_mission(str(output_path))

    assert reparsed == original


def test_round_trip_preserves_waypoint_count_and_order(tmp_path):
    original = parse_mission(str(EXAMPLE_KMZ))
    output_path = tmp_path / "roundtrip.kmz"
    export_mission(original, str(output_path))
    reparsed = parse_mission(str(output_path))

    original_indices = [wp.index for f in original.folders for wp in f.waypoints]
    reparsed_indices = [wp.index for f in reparsed.folders for wp in f.waypoints]
    assert original_indices == reparsed_indices
