"""KMZ/WPML import.

Two layers:

1. `inspect_kmz` — a generic, format-agnostic archive inspector. Unzips any
   `.kmz`/`.kml` and dumps its contents for manual review. This is the
   Phase 0 tool: run it against a new real-world sample before assuming
   anything about its structure.

2. `parse_mission` — a structured parser for the specific WPML 1.0.2
   layout observed in `examples/original_dji_mission.kmz` (a real Mini 5
   Pro + RC 2 / DJI Fly export): a `wpmz/` folder containing exactly
   `template.kml` and `waylines.wpml`, no resource files. Only fields
   actually seen in that file are modeled. If a second real sample shows a
   different layout (a `res/` folder, multiple wayline templates, fields
   not seen here), extend this module against that evidence rather than
   assuming it generalizes.
"""
from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from xml.etree import ElementTree as ET

KML_NS = "http://www.opengis.net/kml/2.2"
WPML_NS = "http://www.uav.com/wpmz/1.0.2"
NS = {"kml": KML_NS, "wpml": WPML_NS}

TEMPLATE_ENTRY = "wpmz/template.kml"
WAYLINES_ENTRY = "wpmz/waylines.wpml"


# --- Layer 1: generic inspector -------------------------------------------------


@dataclass
class ArchiveEntry:
    name: str
    size: int
    text: str | None  # decoded text if it looked like text, else None


@dataclass
class InspectionReport:
    source: str
    entries: list[ArchiveEntry]

    def summary(self) -> str:
        lines = [f"{self.source}:"]
        for entry in self.entries:
            lines.append(f"  {entry.name} ({entry.size} bytes)")
        return "\n".join(lines)


def inspect_kmz(path: str) -> InspectionReport:
    """Unzip `path` and return every entry's name, size, and text content
    (best-effort UTF-8 decode) without assuming any particular internal
    layout. Use this first against any new real-world sample.
    """
    entries: list[ArchiveEntry] = []
    with zipfile.ZipFile(path) as archive:
        for info in archive.infolist():
            raw = archive.read(info.filename)
            text: str | None
            try:
                text = raw.decode("utf-8")
            except UnicodeDecodeError:
                text = None
            entries.append(ArchiveEntry(name=info.filename, size=info.file_size, text=text))
    return InspectionReport(source=path, entries=entries)


# --- Layer 2: structured WPML parser (grounded in the real sample) --------------


@dataclass
class DroneInfo:
    drone_enum_value: int
    drone_sub_enum_value: int


@dataclass
class MissionConfig:
    fly_to_wayline_mode: str
    finish_action: str
    exit_on_rc_lost: str
    execute_rc_lost_action: str
    global_transitional_speed: float
    drone_info: DroneInfo


@dataclass
class Action:
    action_id: int
    actuator_func: str
    # Kept as an ordered dict of raw tag->text pairs rather than a fixed
    # schema: the params differ per actuator function (gimbalRotate,
    # gimbalEvenlyRotate, stopRecord, ...) and only a few have been seen
    # in the one real sample so far.
    params: dict[str, str] = field(default_factory=dict)


@dataclass
class ActionGroup:
    action_group_id: int
    start_index: int
    end_index: int
    mode: str
    trigger_type: str
    actions: list[Action] = field(default_factory=list)


@dataclass
class HeadingParam:
    mode: str
    angle: float
    poi_point: str
    angle_enable: bool
    path_mode: str
    poi_index: int


@dataclass
class TurnParam:
    mode: str
    damping_dist: float


@dataclass
class GimbalHeadingParam:
    pitch_angle: float
    yaw_angle: float


@dataclass
class Waypoint:
    index: int
    longitude: float
    latitude: float
    execute_height: float
    speed: float
    heading: HeadingParam
    turn: TurnParam
    use_straight_line: bool
    action_groups: list[ActionGroup]
    gimbal_heading: GimbalHeadingParam


@dataclass
class WaylineFolder:
    template_id: int
    execute_height_mode: str
    wayline_id: int
    distance: float
    duration: float
    auto_flight_speed: float
    waypoints: list[Waypoint] = field(default_factory=list)


@dataclass
class WpmlMission:
    author: str
    create_time: int
    update_time: int
    mission_config: MissionConfig
    folders: list[WaylineFolder] = field(default_factory=list)


def _text(el: ET.Element, path: str, ns: dict = NS) -> str:
    found = el.find(path, ns)
    if found is None or found.text is None:
        raise ValueError(f"missing required element {path!r}")
    return found.text.strip()


def _opt_text(el: ET.Element, path: str, ns: dict = NS) -> str | None:
    found = el.find(path, ns)
    return found.text.strip() if found is not None and found.text is not None else None


def _parse_mission_config(doc: ET.Element) -> MissionConfig:
    cfg = doc.find("wpml:missionConfig", NS)
    if cfg is None:
        raise ValueError("missing wpml:missionConfig")
    drone_info_el = cfg.find("wpml:droneInfo", NS)
    if drone_info_el is None:
        raise ValueError("missing wpml:droneInfo")
    return MissionConfig(
        fly_to_wayline_mode=_text(cfg, "wpml:flyToWaylineMode"),
        finish_action=_text(cfg, "wpml:finishAction"),
        exit_on_rc_lost=_text(cfg, "wpml:exitOnRCLost"),
        execute_rc_lost_action=_text(cfg, "wpml:executeRCLostAction"),
        global_transitional_speed=float(_text(cfg, "wpml:globalTransitionalSpeed")),
        drone_info=DroneInfo(
            drone_enum_value=int(_text(drone_info_el, "wpml:droneEnumValue")),
            drone_sub_enum_value=int(_text(drone_info_el, "wpml:droneSubEnumValue")),
        ),
    )


def _parse_action(action_el: ET.Element) -> Action:
    params: dict[str, str] = {}
    param_el = action_el.find("wpml:actionActuatorFuncParam", NS)
    if param_el is not None:
        for child in param_el:
            tag = child.tag.split("}")[-1]
            params[tag] = (child.text or "").strip()
    return Action(
        action_id=int(_text(action_el, "wpml:actionId")),
        actuator_func=_text(action_el, "wpml:actionActuatorFunc"),
        params=params,
    )


def _parse_action_group(group_el: ET.Element) -> ActionGroup:
    trigger_el = group_el.find("wpml:actionTrigger", NS)
    if trigger_el is None:
        raise ValueError("missing wpml:actionTrigger")
    return ActionGroup(
        action_group_id=int(_text(group_el, "wpml:actionGroupId")),
        start_index=int(_text(group_el, "wpml:actionGroupStartIndex")),
        end_index=int(_text(group_el, "wpml:actionGroupEndIndex")),
        mode=_text(group_el, "wpml:actionGroupMode"),
        trigger_type=_text(trigger_el, "wpml:actionTriggerType"),
        actions=[_parse_action(a) for a in group_el.findall("wpml:action", NS)],
    )


def _parse_waypoint(placemark: ET.Element) -> Waypoint:
    coords_text = _text(placemark, "kml:Point/kml:coordinates")
    lon_str, lat_str, *_rest = coords_text.split(",")

    heading_el = placemark.find("wpml:waypointHeadingParam", NS)
    if heading_el is None:
        raise ValueError("missing wpml:waypointHeadingParam")
    heading = HeadingParam(
        mode=_text(heading_el, "wpml:waypointHeadingMode"),
        angle=float(_text(heading_el, "wpml:waypointHeadingAngle")),
        poi_point=_text(heading_el, "wpml:waypointPoiPoint"),
        angle_enable=_text(heading_el, "wpml:waypointHeadingAngleEnable") == "1",
        path_mode=_text(heading_el, "wpml:waypointHeadingPathMode"),
        poi_index=int(_text(heading_el, "wpml:waypointHeadingPoiIndex")),
    )

    turn_el = placemark.find("wpml:waypointTurnParam", NS)
    if turn_el is None:
        raise ValueError("missing wpml:waypointTurnParam")
    turn = TurnParam(
        mode=_text(turn_el, "wpml:waypointTurnMode"),
        damping_dist=float(_text(turn_el, "wpml:waypointTurnDampingDist")),
    )

    gimbal_el = placemark.find("wpml:waypointGimbalHeadingParam", NS)
    if gimbal_el is None:
        raise ValueError("missing wpml:waypointGimbalHeadingParam")
    gimbal = GimbalHeadingParam(
        pitch_angle=float(_text(gimbal_el, "wpml:waypointGimbalPitchAngle")),
        yaw_angle=float(_text(gimbal_el, "wpml:waypointGimbalYawAngle")),
    )

    action_groups = [_parse_action_group(g) for g in placemark.findall("wpml:actionGroup", NS)]

    return Waypoint(
        index=int(_text(placemark, "wpml:index")),
        longitude=float(lon_str),
        latitude=float(lat_str),
        execute_height=float(_text(placemark, "wpml:executeHeight")),
        speed=float(_text(placemark, "wpml:waypointSpeed")),
        heading=heading,
        turn=turn,
        use_straight_line=_text(placemark, "wpml:useStraightLine") == "1",
        action_groups=action_groups,
        gimbal_heading=gimbal,
    )


def _parse_folder(folder_el: ET.Element) -> WaylineFolder:
    return WaylineFolder(
        template_id=int(_text(folder_el, "wpml:templateId")),
        execute_height_mode=_text(folder_el, "wpml:executeHeightMode"),
        wayline_id=int(_text(folder_el, "wpml:waylineId")),
        distance=float(_text(folder_el, "wpml:distance")),
        duration=float(_text(folder_el, "wpml:duration")),
        auto_flight_speed=float(_text(folder_el, "wpml:autoFlightSpeed")),
        waypoints=[_parse_waypoint(p) for p in folder_el.findall("kml:Placemark", NS)],
    )


def parse_mission(path: str) -> WpmlMission:
    """Parse a `.kmz` matching the layout of `examples/original_dji_mission.kmz`
    (`wpmz/template.kml` + `wpmz/waylines.wpml`, WPML namespace 1.0.2).

    Raises `KeyError` if either expected entry is missing, or `ValueError`
    if a required field is missing from the XML — surface these to the
    caller rather than silently guessing a default, per the project's
    "never guess at the mission" rule.
    """
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        if TEMPLATE_ENTRY not in names:
            raise KeyError(f"{path} has no {TEMPLATE_ENTRY} entry")
        if WAYLINES_ENTRY not in names:
            raise KeyError(f"{path} has no {WAYLINES_ENTRY} entry")
        template_xml = archive.read(TEMPLATE_ENTRY)
        waylines_xml = archive.read(WAYLINES_ENTRY)

    template_root = ET.fromstring(template_xml)
    template_doc = template_root.find("kml:Document", NS)
    if template_doc is None:
        raise ValueError(f"{TEMPLATE_ENTRY}: missing kml:Document")

    waylines_root = ET.fromstring(waylines_xml)
    waylines_doc = waylines_root.find("kml:Document", NS)
    if waylines_doc is None:
        raise ValueError(f"{WAYLINES_ENTRY}: missing kml:Document")

    mission_config = _parse_mission_config(waylines_doc)
    folders = [_parse_folder(f) for f in waylines_doc.findall("kml:Folder", NS)]

    return WpmlMission(
        author=_text(template_doc, "wpml:author"),
        create_time=int(_text(template_doc, "wpml:createTime")),
        update_time=int(_text(template_doc, "wpml:updateTime")),
        mission_config=mission_config,
        folders=folders,
    )
