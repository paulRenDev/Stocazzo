"""Area -> flight-grid -> waypoints mapping engine (brief sec. 3, Phase 2).

Per docs/BUILD_SPEC.md and docs/WPML_FINDINGS.md ("Cross-reference: DJI's
official WPML spec"), this does not need a DJI-generated mapping-mode
sample to build against: DJI Fly appears to have no native mapping/grid
mode on the Mini 5 Pro, and third-party grid-mapping tools for this
aircraft already compute the grid externally and hand DJI Fly a plain
waypoint mission. So this module owns the geometry itself and emits it
through the plain-waypoint-mission structure already confirmed in
`mission.parser`/`mission.generator`: one `takePhoto` (`reachPoint`)
action per grid waypoint, mirroring
`examples/original_dji_mission_20wp_multi_photo.kmz`.

Two things here are NOT reverse-engineered facts, and are flagged as such
inline: the Mini 5 Pro camera model (sourced from manufacturer spec pages,
not a calibration report) used for footprint/GSD math, and the choice to
mint fresh, simple monotonic action IDs for a newly-generated mission
(WPML_FINDINGS.md's own conclusion, since DJI Fly's real ID-renumbering
behavior on edits is itself unconfirmed).
"""
from __future__ import annotations

import math
import time
from dataclasses import dataclass, field

from mission.parser import (
    Action,
    ActionGroup,
    DroneInfo,
    GimbalHeadingParam,
    HeadingParam,
    MissionConfig,
    TurnParam,
    Waypoint,
    WaylineFolder,
    WpmlMission,
)

# Confirmed via docs/WPML_FINDINGS.md across all real samples.
MINI_5_PRO_DRONE_ENUM = 68
MINI_5_PRO_DRONE_SUB_ENUM = 0

_EARTH_RADIUS_M = 6378137.0


def _num(value: float) -> str:
    if value == int(value):
        return str(int(value))
    return repr(value)


@dataclass(frozen=True)
class CameraModel:
    """A simple rectilinear-lens camera model, enough for footprint/GSD
    planning math. Not a full lens-distortion model.
    """

    photo_width_px: int
    photo_height_px: int
    diagonal_fov_deg: float

    @property
    def diagonal_px(self) -> float:
        return math.hypot(self.photo_width_px, self.photo_height_px)

    @property
    def focal_length_px(self) -> float:
        return (self.diagonal_px / 2) / math.tan(math.radians(self.diagonal_fov_deg / 2))

    @property
    def horizontal_fov_deg(self) -> float:
        return 2 * math.degrees(math.atan((self.photo_width_px / 2) / self.focal_length_px))

    @property
    def vertical_fov_deg(self) -> float:
        return 2 * math.degrees(math.atan((self.photo_height_px / 2) / self.focal_length_px))


# DJI Mini 5 Pro: 1" CMOS, 50MP stills at 8192x6144, 24mm full-frame-
# equivalent focal length, 84 deg diagonal FOV. Sourced from manufacturer
# spec pages, not an independent calibration -- if GSD/overlap output
# ever looks off, check this first. Horizontal/vertical FOV are derived
# from the diagonal FOV + resolution assuming a single rectilinear focal
# length (the same approach mapping-planning tools like Pix4D/DroneDeploy
# use), not independently confirmed for this specific lens.
MINI_5_PRO_CAMERA = CameraModel(photo_width_px=8192, photo_height_px=6144, diagonal_fov_deg=84.0)


def ground_footprint_m(altitude_m: float, camera: CameraModel = MINI_5_PRO_CAMERA) -> tuple[float, float]:
    """Return (across_track_m, along_track_m): the ground footprint of one
    nadir photo at `altitude_m` AGL over flat terrain.

    Modeling choice: "across-track" (perpendicular to flight direction,
    governs line spacing / side overlap) is mapped to the photo's *width*
    axis, and "along-track" (parallel to flight direction, governs photo
    spacing / front overlap) to its *height* axis -- the conventional
    landscape-mounted-camera mapping-survey setup. Not confirmed against
    a real DJI Fly Mini-5-Pro mapping export (see module docstring).
    """
    if altitude_m <= 0:
        raise ValueError("altitude_m must be positive")
    across = 2 * altitude_m * math.tan(math.radians(camera.horizontal_fov_deg / 2))
    along = 2 * altitude_m * math.tan(math.radians(camera.vertical_fov_deg / 2))
    return across, along


def ground_sample_distance_cm(altitude_m: float, camera: CameraModel = MINI_5_PRO_CAMERA) -> float:
    """Ground sample distance in cm/pixel (across-track), at nadir."""
    across_m, _ = ground_footprint_m(altitude_m, camera)
    return (across_m * 100) / camera.photo_width_px


def line_spacing_m(altitude_m: float, side_overlap: float, camera: CameraModel = MINI_5_PRO_CAMERA) -> float:
    """Distance between adjacent flight lines for a given side overlap."""
    if not 0 <= side_overlap < 1:
        raise ValueError("side_overlap must be in [0, 1)")
    across_m, _ = ground_footprint_m(altitude_m, camera)
    return across_m * (1 - side_overlap)


def photo_spacing_m(altitude_m: float, front_overlap: float, camera: CameraModel = MINI_5_PRO_CAMERA) -> float:
    """Distance between consecutive photos along one flight line for a
    given front overlap.
    """
    if not 0 <= front_overlap < 1:
        raise ValueError("front_overlap must be in [0, 1)")
    _, along_m = ground_footprint_m(altitude_m, camera)
    return along_m * (1 - front_overlap)


def _to_local_xy(lon: float, lat: float, origin_lon: float, origin_lat: float) -> tuple[float, float]:
    """Equirectangular projection centered at `origin`, in meters, (east, north)."""
    x = math.radians(lon - origin_lon) * _EARTH_RADIUS_M * math.cos(math.radians(origin_lat))
    y = math.radians(lat - origin_lat) * _EARTH_RADIUS_M
    return x, y


def _to_lon_lat(x: float, y: float, origin_lon: float, origin_lat: float) -> tuple[float, float]:
    lon = origin_lon + math.degrees(x / (_EARTH_RADIUS_M * math.cos(math.radians(origin_lat))))
    lat = origin_lat + math.degrees(y / _EARTH_RADIUS_M)
    return lon, lat


def generate_lawnmower_grid(
    polygon: list[tuple[float, float]],
    altitude_m: float,
    front_overlap: float,
    side_overlap: float,
    direction_deg: float = 0.0,
    camera: CameraModel = MINI_5_PRO_CAMERA,
) -> list[tuple[float, float]]:
    """Compute a boustrophedon ("lawnmower") grid of (lon, lat) waypoints
    covering `polygon`, spaced per the overlap settings, with a `takePhoto`
    waypoint at the target photo spacing along each line (see module
    docstring: this project generates one discrete photo trigger per
    waypoint rather than relying on an interval/distance trigger, since
    that's confirmed unsupported on this aircraft).

    `polygon` is a simple ring `[(lon, lat), ...]`, not closed (first point
    not repeated at the end). `direction_deg` is the flight-line compass
    bearing (0 = north-south lines, 90 = east-west lines), matching brief
    sec. 3's "vliegrichting".

    Limitation: for each scan line, only the outermost entry/exit points
    with the polygon boundary are used. This is correct for convex
    polygons and most simple field shapes; a strongly concave polygon (a
    "C" or "U" shape) may get extra coverage across the concave gap rather
    than being split into separate segments. Good enough for a first
    implementation; revisit with proper multi-interval clipping if a real
    survey area needs it.
    """
    if len(polygon) < 3:
        raise ValueError("polygon needs at least 3 points")

    spacing = line_spacing_m(altitude_m, side_overlap, camera)
    photo_gap = photo_spacing_m(altitude_m, front_overlap, camera)

    origin_lon = sum(p[0] for p in polygon) / len(polygon)
    origin_lat = sum(p[1] for p in polygon) / len(polygon)
    local = [_to_local_xy(lon, lat, origin_lon, origin_lat) for lon, lat in polygon]

    # Rotate (east, north) into (u, v) where v runs along the flight
    # direction and u is the perpendicular scan axis, per compass bearing
    # `direction_deg` (0 = north, 90 = east, clockwise).
    theta = math.radians(direction_deg)
    cos_t, sin_t = math.cos(theta), math.sin(theta)

    def to_uv(x: float, y: float) -> tuple[float, float]:
        return x * cos_t - y * sin_t, x * sin_t + y * cos_t

    def from_uv(u: float, v: float) -> tuple[float, float]:
        return u * cos_t + v * sin_t, -u * sin_t + v * cos_t

    rotated = [to_uv(x, y) for x, y in local]
    n = len(rotated)
    us = [p[0] for p in rotated]
    min_u, max_u = min(us), max(us)

    lines: list[tuple[float, float, float]] = []  # (u, v_start, v_end)
    u = min_u + spacing / 2
    while u <= max_u:
        crossings = []
        for i in range(n):
            u1, v1 = rotated[i]
            u2, v2 = rotated[(i + 1) % n]
            if u1 == u2:
                continue
            if (u1 <= u < u2) or (u2 <= u < u1):
                t = (u - u1) / (u2 - u1)
                crossings.append(v1 + t * (v2 - v1))
        if len(crossings) >= 2:
            lines.append((u, min(crossings), max(crossings)))
        u += spacing

    if not lines:
        raise ValueError(
            "no flight lines intersect the polygon -- check altitude/overlap/direction/polygon"
        )

    grid_uv: list[tuple[float, float]] = []
    for i, (u, v_start, v_end) in enumerate(lines):
        length = v_end - v_start
        n_points = max(2, math.ceil(length / photo_gap) + 1)
        vs = [v_start + length * k / (n_points - 1) for k in range(n_points)]
        if i % 2 == 1:
            vs.reverse()
        grid_uv.extend((u, v) for v in vs)

    grid_local = [from_uv(u, v) for u, v in grid_uv]
    return [_to_lon_lat(x, y, origin_lon, origin_lat) for x, y in grid_local]


@dataclass
class MappingMissionParams:
    """Structured parameters for a 2D mapping mission (brief sec. 3-4)."""

    polygon: list[tuple[float, float]]
    altitude_m: float
    front_overlap: float
    side_overlap: float
    direction_deg: float = 0.0
    speed_ms: float = 2.5
    gimbal_pitch_deg: float = -90.0
    author: str = "dji_mission_builder"
    camera: CameraModel = field(default=MINI_5_PRO_CAMERA)


def build_mapping_mission(params: MappingMissionParams) -> WpmlMission:
    """Compute the grid and build a `WpmlMission` ready for
    `mission.generator.export_mission` (after `mission.validator`).
    """
    points = generate_lawnmower_grid(
        params.polygon,
        params.altitude_m,
        params.front_overlap,
        params.side_overlap,
        params.direction_deg,
        params.camera,
    )
    if len(points) < 2:
        raise ValueError("grid produced fewer than 2 waypoints; check polygon/altitude/overlap")

    last_index = len(points) - 1
    waypoints: list[Waypoint] = []
    next_action_id = 1

    for i, (lon, lat) in enumerate(points):
        is_endpoint = i == 0 or i == last_index

        heading = HeadingParam(
            mode="followWayline",
            angle=0.0,
            poi_point="0.000000,0.000000,0.000000",
            angle_enable=is_endpoint,
            path_mode="followBadArc",
            poi_index=0,
        )
        turn = TurnParam(
            mode=(
                "toPointAndStopWithContinuityCurvature"
                if is_endpoint
                else "toPointAndPassWithContinuityCurvature"
            ),
            damping_dist=0.0,
        )
        gimbal_heading = GimbalHeadingParam(pitch_angle=0.0, yaw_angle=0.0)

        actions: list[Action] = []
        if i == 0:
            actions.append(
                Action(
                    action_id=next_action_id,
                    actuator_func="gimbalRotate",
                    params={
                        "gimbalHeadingYawBase": "aircraft",
                        "gimbalRotateMode": "absoluteAngle",
                        "gimbalPitchRotateEnable": "1",
                        "gimbalPitchRotateAngle": _num(params.gimbal_pitch_deg),
                        "gimbalRollRotateEnable": "1",
                        "gimbalRollRotateAngle": "0",
                        "gimbalYawRotateEnable": "0",
                        "gimbalYawRotateAngle": "0",
                        "gimbalRotateTimeEnable": "0",
                        "gimbalRotateTime": "0",
                        "payloadPositionIndex": "0",
                    },
                )
            )
            next_action_id += 1
        actions.append(
            Action(
                action_id=next_action_id,
                actuator_func="takePhoto",
                params={"payloadPositionIndex": "0", "useGlobalPayloadLensIndex": "0"},
            )
        )
        next_action_id += 1

        action_group = ActionGroup(
            action_group_id=1,
            start_index=i,
            end_index=i,
            mode="parallel",
            trigger_type="reachPoint",
            actions=actions,
        )

        waypoints.append(
            Waypoint(
                index=i,
                longitude=lon,
                latitude=lat,
                execute_height=params.altitude_m,
                speed=params.speed_ms,
                heading=heading,
                turn=turn,
                use_straight_line=False,
                action_groups=[action_group],
                gimbal_heading=gimbal_heading,
            )
        )

    folder = WaylineFolder(
        template_id=0,
        execute_height_mode="relativeToStartPoint",
        wayline_id=0,
        distance=0.0,
        duration=0.0,
        auto_flight_speed=params.speed_ms,
        waypoints=waypoints,
    )

    mission_config = MissionConfig(
        fly_to_wayline_mode="safely",
        finish_action="goHome",
        exit_on_rc_lost="executeLostAction",
        execute_rc_lost_action="goBack",
        global_transitional_speed=2.5,
        drone_info=DroneInfo(
            drone_enum_value=MINI_5_PRO_DRONE_ENUM,
            drone_sub_enum_value=MINI_5_PRO_DRONE_SUB_ENUM,
        ),
    )

    now_ms = int(time.time() * 1000)
    return WpmlMission(
        author=params.author,
        create_time=now_ms,
        update_time=now_ms,
        mission_config=mission_config,
        folders=[folder],
    )
