from pathlib import Path

from mission.parser import inspect_kmz, parse_mission

EXAMPLE_KMZ = Path(__file__).parent.parent / "examples" / "original_dji_mission.kmz"


def test_inspect_kmz_lists_real_archive_layout():
    report = inspect_kmz(str(EXAMPLE_KMZ))
    names = {entry.name for entry in report.entries}
    assert names == {"wpmz/template.kml", "wpmz/waylines.wpml"}
    for entry in report.entries:
        assert entry.text is not None  # both entries are plain-text XML


def test_parse_mission_reads_mission_config():
    mission = parse_mission(str(EXAMPLE_KMZ))
    assert mission.author == "fly"
    assert mission.mission_config.fly_to_wayline_mode == "safely"
    assert mission.mission_config.finish_action == "goHome"
    assert mission.mission_config.exit_on_rc_lost == "executeLostAction"
    assert mission.mission_config.execute_rc_lost_action == "goBack"
    assert mission.mission_config.global_transitional_speed == 2.5
    assert mission.mission_config.drone_info.drone_enum_value == 68
    assert mission.mission_config.drone_info.drone_sub_enum_value == 0


def test_parse_mission_reads_waypoints():
    mission = parse_mission(str(EXAMPLE_KMZ))
    assert len(mission.folders) == 1
    folder = mission.folders[0]
    assert folder.execute_height_mode == "relativeToStartPoint"
    assert len(folder.waypoints) == 3

    indices = [wp.index for wp in folder.waypoints]
    assert indices == [0, 1, 2]

    for wp in folder.waypoints:
        assert wp.execute_height == 50
        assert wp.speed == 2.5

    first = folder.waypoints[0]
    assert first.longitude == 4.19765158540255
    assert first.latitude == 50.8260738260504


def test_parse_mission_reads_actions():
    mission = parse_mission(str(EXAMPLE_KMZ))
    folder = mission.folders[0]

    first_wp = folder.waypoints[0]
    actuator_funcs = [
        action.actuator_func
        for group in first_wp.action_groups
        for action in group.actions
    ]
    assert "gimbalRotate" in actuator_funcs
    assert "gimbalEvenlyRotate" in actuator_funcs

    last_wp = folder.waypoints[-1]
    last_actuator_funcs = [
        action.actuator_func
        for group in last_wp.action_groups
        for action in group.actions
    ]
    assert "stopRecord" in last_actuator_funcs
