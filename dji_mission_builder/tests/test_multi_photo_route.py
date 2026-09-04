"""Encodes findings from docs/WPML_FINDINGS.md, "Confirmed: compound
action groups & independent speed fields".
"""
from pathlib import Path

from mission.generator import export_mission
from mission.parser import parse_mission

MULTI_PHOTO_KMZ = Path(__file__).parent.parent / "examples" / "original_dji_mission_20wp_multi_photo.kmz"


def test_first_waypoint_bundles_takephoto_and_gimbal_rotate_in_one_group():
    mission = parse_mission(str(MULTI_PHOTO_KMZ))
    first_wp = mission.folders[0].waypoints[0]

    single_point_groups = [g for g in first_wp.action_groups if g.start_index == g.end_index]
    assert len(single_point_groups) == 1
    group = single_point_groups[0]
    assert group.action_group_id == 1
    assert [a.actuator_func for a in group.actions] == ["takePhoto", "gimbalRotate"]


def test_waypoint_speed_independent_of_global_transitional_speed():
    mission = parse_mission(str(MULTI_PHOTO_KMZ))
    assert mission.mission_config.global_transitional_speed == 2.5
    for wp in mission.folders[0].waypoints:
        assert wp.speed == 1.4


def test_eight_take_photo_actions_all_reach_point_triggered():
    mission = parse_mission(str(MULTI_PHOTO_KMZ))
    take_photos = [
        (wp.index, group.trigger_type)
        for wp in mission.folders[0].waypoints
        for group in wp.action_groups
        for action in group.actions
        if action.actuator_func == "takePhoto"
    ]
    assert len(take_photos) == 8
    assert all(trigger == "reachPoint" for _, trigger in take_photos)


def test_round_trip(tmp_path):
    original = parse_mission(str(MULTI_PHOTO_KMZ))
    output_path = tmp_path / "roundtrip_multi_photo.kmz"
    export_mission(original, str(output_path))
    reparsed = parse_mission(str(output_path))
    assert reparsed == original
