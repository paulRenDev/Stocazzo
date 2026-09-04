"""Encodes the Phase 0 single-parameter-change finding (build spec sec. 7,
docs/WPML_FINDINGS.md "Confirmed via second sample"): a real DJI Fly
re-export where only one waypoint's height/position changed. This is the
evidence that editing a single waypoint's `executeHeight`/coordinates does
not disturb any other waypoint, the action groups/IDs attached to it, or
the mission config — if a future parser/generator change breaks that
isolation, this test should catch it.
"""
from pathlib import Path

from mission.parser import parse_mission

BASE_KMZ = Path(__file__).parent.parent / "examples" / "original_dji_mission.kmz"
EDITED_KMZ = Path(__file__).parent.parent / "examples" / "original_dji_mission_wp2_edited.kmz"


def test_mission_config_unchanged_across_the_edit():
    base = parse_mission(str(BASE_KMZ))
    edited = parse_mission(str(EDITED_KMZ))
    assert base.mission_config == edited.mission_config
    assert base.author == edited.author


def test_export_timestamps_differ():
    # Confirms createTime/updateTime are refreshed on every real DJI Fly
    # export/save, not stable mission content -- see WPML_FINDINGS.md.
    base = parse_mission(str(BASE_KMZ))
    edited = parse_mission(str(EDITED_KMZ))
    assert base.create_time != edited.create_time
    assert base.update_time != edited.update_time


def test_only_waypoint_two_changed():
    base = parse_mission(str(BASE_KMZ))
    edited = parse_mission(str(EDITED_KMZ))

    base_wps = base.folders[0].waypoints
    edited_wps = edited.folders[0].waypoints
    assert len(base_wps) == len(edited_wps) == 3

    # Waypoints 0 and 1 are byte-for-byte identical, including their
    # action groups and action IDs.
    assert base_wps[0] == edited_wps[0]
    assert base_wps[1] == edited_wps[1]

    # Waypoint 2: height and position changed, everything else about it
    # (speed, heading, turn params, action group/action IDs) did not.
    base_wp2, edited_wp2 = base_wps[2], edited_wps[2]
    assert base_wp2.execute_height == 50
    assert edited_wp2.execute_height == 201
    assert (base_wp2.longitude, base_wp2.latitude) != (edited_wp2.longitude, edited_wp2.latitude)

    assert base_wp2.speed == edited_wp2.speed
    assert base_wp2.heading == edited_wp2.heading
    assert base_wp2.turn == edited_wp2.turn
    assert base_wp2.use_straight_line == edited_wp2.use_straight_line
    assert base_wp2.action_groups == edited_wp2.action_groups
    assert base_wp2.gimbal_heading == edited_wp2.gimbal_heading


def test_distance_and_duration_still_not_recomputed():
    # Neither file has these auto-filled despite the height/position edit
    # -- confirms the WPML_FINDINGS.md hypothesis that these fields aren't
    # computed by whatever produced these exports.
    base = parse_mission(str(BASE_KMZ))
    edited = parse_mission(str(EDITED_KMZ))
    assert base.folders[0].distance == edited.folders[0].distance == 0
    assert base.folders[0].duration == edited.folders[0].duration == 0
