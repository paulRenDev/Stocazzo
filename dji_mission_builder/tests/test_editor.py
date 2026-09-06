from pathlib import Path

import pytest

from mission.editor import apply_edits
from mission.generator import export_mission
from mission.parser import parse_mission
from mission.validator import has_errors, validate_mission

EXAMPLE_KMZ = Path(__file__).parent.parent / "examples" / "original_dji_mission_14wp_loop.kmz"


def test_apply_edits_does_not_mutate_original():
    original = parse_mission(str(EXAMPLE_KMZ))
    original_height = original.folders[0].waypoints[0].execute_height

    apply_edits(original, altitude_m=123)

    assert original.folders[0].waypoints[0].execute_height == original_height


def test_apply_edits_sets_altitude_on_every_waypoint():
    mission = parse_mission(str(EXAMPLE_KMZ))
    edited = apply_edits(mission, altitude_m=75)

    for folder in edited.folders:
        for wp in folder.waypoints:
            assert wp.execute_height == 75


def test_apply_edits_sets_speed_on_every_waypoint_and_folder():
    mission = parse_mission(str(EXAMPLE_KMZ))
    edited = apply_edits(mission, speed_ms=6.5)

    for folder in edited.folders:
        assert folder.auto_flight_speed == 6.5
        for wp in folder.waypoints:
            assert wp.speed == 6.5


def test_apply_edits_bumps_update_time_but_preserves_create_time():
    mission = parse_mission(str(EXAMPLE_KMZ))
    edited = apply_edits(mission, altitude_m=75)

    assert edited.create_time == mission.create_time
    assert edited.update_time != mission.update_time


def test_apply_edits_with_no_args_is_a_no_op_copy():
    mission = parse_mission(str(EXAMPLE_KMZ))
    edited = apply_edits(mission)

    assert edited == mission
    assert edited is not mission


def test_apply_edits_rejects_non_positive_values():
    mission = parse_mission(str(EXAMPLE_KMZ))
    with pytest.raises(ValueError):
        apply_edits(mission, altitude_m=0)
    with pytest.raises(ValueError):
        apply_edits(mission, speed_ms=-1)


def test_edited_mission_validates_and_round_trips(tmp_path):
    mission = parse_mission(str(EXAMPLE_KMZ))
    edited = apply_edits(mission, altitude_m=60, speed_ms=4.0)

    issues = validate_mission(edited)
    assert not has_errors(issues)

    output_path = tmp_path / "edited.kmz"
    export_mission(edited, str(output_path))
    reparsed = parse_mission(str(output_path))
    assert reparsed == edited
