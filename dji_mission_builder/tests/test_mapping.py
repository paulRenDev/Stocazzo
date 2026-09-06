import math

import pytest

from mission.generator import export_mission
from mission.mapping import (
    MINI_5_PRO_CAMERA,
    MappingMissionParams,
    build_mapping_mission,
    generate_lawnmower_grid,
    ground_footprint_m,
    ground_sample_distance_cm,
    line_spacing_m,
    photo_spacing_m,
)
from mission.parser import parse_mission
from mission.validator import has_errors, validate_mission

# Lennik, Belgium area, matching the real samples' location -- arbitrary
# but keeps test coordinates realistic.
ORIGIN_LON, ORIGIN_LAT = 4.197, 50.826
_METERS_PER_DEG_LAT = 111320.0


def _offset(lon: float, lat: float, east_m: float, north_m: float) -> tuple[float, float]:
    """Simple local-planar offset, independent of mapping.py's own
    projection helpers, so the test doesn't validate the implementation
    against itself.
    """
    dlat = north_m / _METERS_PER_DEG_LAT
    dlon = east_m / (_METERS_PER_DEG_LAT * math.cos(math.radians(lat)))
    return lon + dlon, lat + dlat


def _rectangle(east_m: float, north_m: float) -> list[tuple[float, float]]:
    return [
        _offset(ORIGIN_LON, ORIGIN_LAT, 0, 0),
        _offset(ORIGIN_LON, ORIGIN_LAT, east_m, 0),
        _offset(ORIGIN_LON, ORIGIN_LAT, east_m, north_m),
        _offset(ORIGIN_LON, ORIGIN_LAT, 0, north_m),
    ]


def test_camera_fov_consistent_with_diagonal_spec():
    camera = MINI_5_PRO_CAMERA
    h, v = camera.horizontal_fov_deg, camera.vertical_fov_deg
    # Re-derive the diagonal FOV from the computed H/V FOV and confirm it
    # matches the spec input (84 deg) -- proves the derivation is
    # self-consistent, not that it's confirmed correct for the real lens.
    diag = 2 * math.degrees(
        math.atan(math.sqrt(math.tan(math.radians(h / 2)) ** 2 + math.tan(math.radians(v / 2)) ** 2))
    )
    assert diag == pytest.approx(84.0, abs=0.01)
    assert h == pytest.approx(71.5, abs=0.5)
    assert v == pytest.approx(56.8, abs=0.5)


def test_ground_sample_distance_matches_public_reference():
    # Independent sources report ~0.9 cm/px GSD at 50 m for this camera.
    assert ground_sample_distance_cm(50) == pytest.approx(0.9, abs=0.05)


def test_ground_footprint_scales_linearly_with_altitude():
    across_50, along_50 = ground_footprint_m(50)
    across_100, along_100 = ground_footprint_m(100)
    assert across_100 == pytest.approx(across_50 * 2)
    assert along_100 == pytest.approx(along_50 * 2)


def test_spacing_decreases_as_overlap_increases():
    assert line_spacing_m(50, 0.8) < line_spacing_m(50, 0.5)
    assert photo_spacing_m(50, 0.8) < photo_spacing_m(50, 0.5)


def test_spacing_rejects_invalid_overlap():
    with pytest.raises(ValueError):
        line_spacing_m(50, 1.0)
    with pytest.raises(ValueError):
        line_spacing_m(50, -0.1)
    with pytest.raises(ValueError):
        photo_spacing_m(50, 1.0)


def test_footprint_rejects_non_positive_altitude():
    with pytest.raises(ValueError):
        ground_footprint_m(0)
    with pytest.raises(ValueError):
        ground_footprint_m(-10)


def test_generate_lawnmower_grid_is_deterministic():
    polygon = _rectangle(200, 150)
    grid1 = generate_lawnmower_grid(polygon, altitude_m=50, front_overlap=0.7, side_overlap=0.7)
    grid2 = generate_lawnmower_grid(polygon, altitude_m=50, front_overlap=0.7, side_overlap=0.7)
    assert grid1 == grid2
    assert len(grid1) > 2


def test_generate_lawnmower_grid_stays_within_polygon_bounds():
    polygon = _rectangle(200, 150)
    grid = generate_lawnmower_grid(polygon, altitude_m=50, front_overlap=0.7, side_overlap=0.7)

    min_lon = min(p[0] for p in polygon)
    max_lon = max(p[0] for p in polygon)
    min_lat = min(p[1] for p in polygon)
    max_lat = max(p[1] for p in polygon)

    # Half a line-spacing of slack: scan lines are centered within
    # [min_u, max_u], so the outermost line can sit slightly inside the
    # boundary rather than exactly on it.
    tolerance_deg = 0.001
    for lon, lat in grid:
        assert min_lon - tolerance_deg <= lon <= max_lon + tolerance_deg
        assert min_lat - tolerance_deg <= lat <= max_lat + tolerance_deg


def test_generate_lawnmower_grid_rejects_degenerate_polygon():
    with pytest.raises(ValueError):
        generate_lawnmower_grid([(0, 0), (1, 1)], altitude_m=50, front_overlap=0.7, side_overlap=0.7)


def test_build_mapping_mission_validates_clean():
    params = MappingMissionParams(
        polygon=_rectangle(100, 80),
        altitude_m=50,
        front_overlap=0.7,
        side_overlap=0.7,
    )
    mission = build_mapping_mission(params)
    issues = validate_mission(mission)
    assert not has_errors(issues)


def test_build_mapping_mission_first_and_last_waypoint_markers():
    params = MappingMissionParams(
        polygon=_rectangle(100, 80),
        altitude_m=50,
        front_overlap=0.7,
        side_overlap=0.7,
    )
    mission = build_mapping_mission(params)
    waypoints = mission.folders[0].waypoints
    assert len(waypoints) > 2

    assert waypoints[0].turn.mode == "toPointAndStopWithContinuityCurvature"
    assert waypoints[0].heading.angle_enable is True
    assert waypoints[-1].turn.mode == "toPointAndStopWithContinuityCurvature"
    assert waypoints[-1].heading.angle_enable is True

    for wp in waypoints[1:-1]:
        assert wp.turn.mode == "toPointAndPassWithContinuityCurvature"
        assert wp.heading.angle_enable is False


def test_build_mapping_mission_actions():
    params = MappingMissionParams(
        polygon=_rectangle(100, 80),
        altitude_m=50,
        front_overlap=0.7,
        side_overlap=0.7,
        gimbal_pitch_deg=-90,
    )
    mission = build_mapping_mission(params)
    waypoints = mission.folders[0].waypoints

    first_funcs = [a.actuator_func for g in waypoints[0].action_groups for a in g.actions]
    assert first_funcs == ["gimbalRotate", "takePhoto"]

    for wp in waypoints[1:]:
        funcs = [a.actuator_func for g in wp.action_groups for a in g.actions]
        assert funcs == ["takePhoto"]

    all_action_ids = [
        a.action_id for wp in waypoints for g in wp.action_groups for a in g.actions
    ]
    assert len(all_action_ids) == len(set(all_action_ids))
    assert all_action_ids == list(range(1, len(all_action_ids) + 1))


def test_build_mapping_mission_indices_sequential():
    params = MappingMissionParams(
        polygon=_rectangle(100, 80),
        altitude_m=50,
        front_overlap=0.7,
        side_overlap=0.7,
    )
    mission = build_mapping_mission(params)
    indices = [wp.index for wp in mission.folders[0].waypoints]
    assert indices == list(range(len(indices)))


def test_build_mapping_mission_round_trips(tmp_path):
    params = MappingMissionParams(
        polygon=_rectangle(120, 90),
        altitude_m=47.5,
        front_overlap=0.65,
        side_overlap=0.6,
        direction_deg=35.0,
        speed_ms=4.2,
        gimbal_pitch_deg=-90,
    )
    mission = build_mapping_mission(params)

    output_path = tmp_path / "mapping_mission.kmz"
    export_mission(mission, str(output_path))
    reparsed = parse_mission(str(output_path))

    assert reparsed == mission

    issues = validate_mission(reparsed)
    assert not has_errors(issues)
