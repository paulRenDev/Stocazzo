import copy
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


def test_high_precision_values_survive_round_trip(tmp_path):
    """Regression test: `:g` formatting (the original implementation)
    silently truncates to 6 significant figures. Every real sample so far
    only has round numbers (2.5, 50, 8.1, ...) so this bug was latent
    until Phase 2 started generating computed altitudes/speeds with more
    precision. Uses a real sample as a base and mutates one waypoint's
    numeric fields to exercise the fix broadly across the format.
    """
    mission = parse_mission(str(EXAMPLE_KMZ))
    mission = copy.deepcopy(mission)

    wp = mission.folders[0].waypoints[0]
    wp.execute_height = 123.456789
    wp.speed = 3.141592653589793
    wp.heading.angle = 12.3456789
    wp.turn.damping_dist = 0.987654321
    wp.gimbal_heading.pitch_angle = -89.123456
    mission.mission_config.global_transitional_speed = 4.56789012
    mission.folders[0].auto_flight_speed = 7.891234567

    output_path = tmp_path / "high_precision.kmz"
    export_mission(mission, str(output_path))
    reparsed = parse_mission(str(output_path))

    assert reparsed == mission
