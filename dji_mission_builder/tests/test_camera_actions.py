"""Encodes the camera-action and dynamic-first/last-marker findings in
docs/WPML_FINDINGS.md ("Confirmed: camera/recording actions" and
"Confirmed: first/last-waypoint markers are recomputed, not fixed").
"""
from pathlib import Path

from mission.generator import export_mission
from mission.parser import parse_mission

LOOP_NO_ACTIONS = Path(__file__).parent.parent / "examples" / "original_dji_mission_14wp_loop.kmz"
LOOP_14WP_CAMERA = (
    Path(__file__).parent.parent / "examples" / "original_dji_mission_14wp_with_camera_actions.kmz"
)
LOOP_15WP_CAMERA = (
    Path(__file__).parent.parent / "examples" / "original_dji_mission_15wp_with_camera_actions.kmz"
)


def _actions(waypoint):
    return [
        (group.action_group_id, action.action_id, action.actuator_func)
        for group in waypoint.action_groups
        for action in group.actions
    ]


def test_camera_actions_parse_with_expected_params():
    mission = parse_mission(str(LOOP_14WP_CAMERA))
    waypoints = mission.folders[0].waypoints

    take_photo = next(
        a for wp in waypoints for g in wp.action_groups for a in g.actions if a.actuator_func == "takePhoto"
    )
    assert take_photo.params == {"payloadPositionIndex": "0", "useGlobalPayloadLensIndex": "0"}

    start_record = next(
        a for wp in waypoints for g in wp.action_groups for a in g.actions if a.actuator_func == "startRecord"
    )
    assert start_record.params == {"payloadPositionIndex": "0", "useGlobalPayloadLensIndex": "0"}

    stop_records = [
        a for wp in waypoints for g in wp.action_groups for a in g.actions if a.actuator_func == "stopRecord"
    ]
    assert len(stop_records) == 2
    for stop_record in stop_records:
        # No useGlobalPayloadLensIndex -- stopping doesn't need a lens choice.
        assert stop_record.params == {"payloadPositionIndex": "0"}


def test_action_group_id_marks_single_point_vs_transition():
    mission = parse_mission(str(LOOP_14WP_CAMERA))
    for wp in mission.folders[0].waypoints:
        for group in wp.action_groups:
            if group.start_index == group.end_index:
                assert group.action_group_id == 1
            else:
                assert group.end_index == group.start_index + 1
                assert group.action_group_id == 2


def test_action_ids_have_no_duplicates_within_one_file():
    for kmz in (LOOP_14WP_CAMERA, LOOP_15WP_CAMERA):
        mission = parse_mission(str(kmz))
        all_ids = [
            a.action_id for wp in mission.folders[0].waypoints for g in wp.action_groups for a in g.actions
        ]
        assert len(all_ids) == len(set(all_ids))


def test_action_id_is_not_stable_across_edits():
    # Waypoint 4's transition action shifts from id 6 (pre-camera-edit) to
    # id 7 (post-edit) purely because new actions were inserted elsewhere
    # in the mission -- actionId is a global counter, not a per-action
    # identity that survives edits.
    before = parse_mission(str(LOOP_NO_ACTIONS))
    after = parse_mission(str(LOOP_14WP_CAMERA))

    before_wp4_action = _actions(before.folders[0].waypoints[4])[0]
    after_wp4_action = _actions(after.folders[0].waypoints[4])[0]

    assert before_wp4_action[2] == after_wp4_action[2] == "gimbalEvenlyRotate"
    assert before_wp4_action[1] != after_wp4_action[1]


def test_appending_a_waypoint_demotes_the_old_last_waypoint():
    mission_14 = parse_mission(str(LOOP_14WP_CAMERA))
    mission_15 = parse_mission(str(LOOP_15WP_CAMERA))

    old_last = mission_14.folders[0].waypoints[13]
    assert old_last.turn.mode == "toPointAndStopWithContinuityCurvature"
    assert old_last.heading.angle_enable is True
    assert len(old_last.action_groups) == 1  # only its stopRecord group

    now_middle = mission_15.folders[0].waypoints[13]
    assert now_middle.turn.mode == "toPointAndPassWithContinuityCurvature"
    assert now_middle.heading.angle_enable is False
    # Gained a transition action group it didn't have before, but its
    # original stopRecord action itself is untouched in content -- only
    # its actionId shifted (17 -> 18), consistent with actionId not being
    # stable across edits (see test_action_id_is_not_stable_across_edits).
    assert len(now_middle.action_groups) == 2
    stop_records = [a for g in now_middle.action_groups for a in g.actions if a.actuator_func == "stopRecord"]
    assert len(stop_records) == 1
    assert stop_records[0].params == old_last.action_groups[0].actions[0].params

    new_last = mission_15.folders[0].waypoints[14]
    assert new_last.turn.mode == "toPointAndStopWithContinuityCurvature"
    assert new_last.heading.angle_enable is True
    assert new_last.action_groups == []


def test_round_trip_camera_action_samples(tmp_path):
    for kmz in (LOOP_14WP_CAMERA, LOOP_15WP_CAMERA):
        original = parse_mission(str(kmz))
        output_path = tmp_path / f"roundtrip_{kmz.name}"
        export_mission(original, str(output_path))
        reparsed = parse_mission(str(output_path))
        assert reparsed == original
