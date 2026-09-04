"""Encodes structural patterns confirmed at n=14 waypoints
(docs/WPML_FINDINGS.md, "Confirmed at n=14"): the 3-waypoint base sample
alone couldn't rule out these being an artifact of such a short route, so
these checks exist to catch a future parser/generator change that would
break the wider pattern.
"""
from pathlib import Path

from mission.generator import export_mission
from mission.parser import parse_mission

LOOP_KMZ = Path(__file__).parent.parent / "examples" / "original_dji_mission_14wp_loop.kmz"


def test_has_fourteen_waypoints():
    mission = parse_mission(str(LOOP_KMZ))
    assert len(mission.folders[0].waypoints) == 14


def test_first_and_last_waypoint_stop_middle_ones_pass():
    mission = parse_mission(str(LOOP_KMZ))
    waypoints = mission.folders[0].waypoints

    assert waypoints[0].turn.mode == "toPointAndStopWithContinuityCurvature"
    assert waypoints[-1].turn.mode == "toPointAndStopWithContinuityCurvature"
    for wp in waypoints[1:-1]:
        assert wp.turn.mode == "toPointAndPassWithContinuityCurvature"


def test_heading_angle_enabled_only_at_route_ends():
    mission = parse_mission(str(LOOP_KMZ))
    waypoints = mission.folders[0].waypoints

    assert waypoints[0].heading.angle_enable is True
    assert waypoints[-1].heading.angle_enable is True
    for wp in waypoints[1:-1]:
        assert wp.heading.angle_enable is False


def test_last_waypoint_has_no_action_groups():
    mission = parse_mission(str(LOOP_KMZ))
    assert mission.folders[0].waypoints[-1].action_groups == []


def test_action_group_id_is_reused_by_role_not_unique():
    mission = parse_mission(str(LOOP_KMZ))
    waypoints = mission.folders[0].waypoints

    # Waypoint 0 has both the "initial gimbal rotate" group (id 1) and a
    # "transition" group (id 2).
    first_group_ids = [g.action_group_id for g in waypoints[0].action_groups]
    assert first_group_ids == [1, 2]

    # Every other waypoint that has an action group reuses id 2.
    for wp in waypoints[1:-1]:
        assert [g.action_group_id for g in wp.action_groups] == [2]


def test_action_id_is_one_global_gapless_counter():
    mission = parse_mission(str(LOOP_KMZ))
    all_action_ids = [
        action.action_id
        for folder in mission.folders
        for wp in folder.waypoints
        for group in wp.action_groups
        for action in group.actions
    ]
    assert all_action_ids == list(range(1, len(all_action_ids) + 1))


def test_round_trip_survives_a_waypoint_with_no_action_groups(tmp_path):
    original = parse_mission(str(LOOP_KMZ))
    output_path = tmp_path / "roundtrip_loop.kmz"
    export_mission(original, str(output_path))
    reparsed = parse_mission(str(output_path))
    assert reparsed == original
