import copy
import math
from pathlib import Path

from mission.mapping import MappingMissionParams, build_mapping_mission
from mission.parser import parse_mission
from mission.validator import COMMONLY_REPORTED_MAX_WAYPOINTS, Severity, has_errors, validate_mission

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


def _offset(lon, lat, east_m, north_m):
    dlat = north_m / 111320.0
    dlon = east_m / (111320.0 * math.cos(math.radians(lat)))
    return lon + dlon, lat + dlat


def test_large_grid_warns_about_commonly_reported_waypoint_limit():
    # A large-enough area at high overlap easily exceeds 99 waypoints;
    # this should warn, not error -- the limit isn't confirmed for the
    # Mini 5 Pro, only commonly reported for DJI Fly generally.
    polygon = [
        _offset(4.197, 50.826, 0, 0),
        _offset(4.197, 50.826, 500, 0),
        _offset(4.197, 50.826, 500, 400),
        _offset(4.197, 50.826, 0, 400),
    ]
    params = MappingMissionParams(
        polygon=polygon, altitude_m=50, front_overlap=0.85, side_overlap=0.85
    )
    mission = build_mapping_mission(params)
    all_waypoints = mission.folders[0].waypoints
    assert len(all_waypoints) > COMMONLY_REPORTED_MAX_WAYPOINTS

    issues = validate_mission(mission)
    assert any(
        i.severity is Severity.WARNING and "commonly reported" in i.message for i in issues
    )
    assert not has_errors(issues)
