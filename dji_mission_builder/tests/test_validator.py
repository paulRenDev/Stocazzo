import copy
from pathlib import Path

from mission.parser import parse_mission
from mission.validator import Severity, has_errors, validate_mission

EXAMPLE_KMZ = Path(__file__).parent.parent / "examples" / "original_dji_mission.kmz"


def test_real_mission_validates_clean():
    mission = parse_mission(str(EXAMPLE_KMZ))
    issues = validate_mission(mission)
    assert not has_errors(issues)


def test_unknown_drone_enum_warns():
    mission = parse_mission(str(EXAMPLE_KMZ))
    mission = copy.deepcopy(mission)
    mission.mission_config.drone_info.drone_enum_value = 999
    issues = validate_mission(mission)
    assert any(i.severity is Severity.WARNING and "droneEnumValue" in i.message for i in issues)
    assert not has_errors(issues)  # unknown drone is a warning, not a hard error


def test_empty_mission_errors():
    mission = parse_mission(str(EXAMPLE_KMZ))
    mission = copy.deepcopy(mission)
    mission.folders = []
    issues = validate_mission(mission)
    assert has_errors(issues)


def test_invalid_latitude_errors():
    mission = parse_mission(str(EXAMPLE_KMZ))
    mission = copy.deepcopy(mission)
    mission.folders[0].waypoints[0].latitude = 999.0
    issues = validate_mission(mission)
    assert has_errors(issues)


def test_duplicate_index_errors():
    mission = parse_mission(str(EXAMPLE_KMZ))
    mission = copy.deepcopy(mission)
    mission.folders[0].waypoints[1].index = 0
    issues = validate_mission(mission)
    assert has_errors(issues)


def test_non_positive_height_errors():
    mission = parse_mission(str(EXAMPLE_KMZ))
    mission = copy.deepcopy(mission)
    mission.folders[0].waypoints[0].execute_height = 0
    issues = validate_mission(mission)
    assert has_errors(issues)
