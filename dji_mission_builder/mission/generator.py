"""KMZ/WPML export.

Rebuilds `wpmz/template.kml` and `wpmz/waylines.wpml` from a
`mission.parser.WpmlMission` and zips them into a `.kmz`, mirroring the tag
layout observed in `examples/original_dji_mission.kmz` exactly (see
`docs/WPML_FINDINGS.md`).

This only covers what Phase 0 has confirmed: the mission-config block and
single-wayline-template waypoints seen in the one real sample so far. It
deliberately does not attempt the grid/overlap generation from brief sec.
3 (mapping.py, Phase 2) — that needs its own geometry engine, not just a
WPML writer.
"""
from __future__ import annotations

import zipfile
from pathlib import Path

from mission.parser import Action, ActionGroup, Waypoint, WaylineFolder, WpmlMission

_XML_HEADER = '<?xml version="1.0" encoding="UTF-8"?>\n'
_KML_OPEN = '<kml xmlns="http://www.opengis.net/kml/2.2" xmlns:wpml="http://www.uav.com/wpmz/1.0.2">\n'
_KML_CLOSE = "</kml>\n"


def _mission_config_xml(mission: WpmlMission, indent: str) -> str:
    cfg = mission.mission_config
    di = cfg.drone_info
    return (
        f"{indent}<wpml:missionConfig>\n"
        f"{indent}  <wpml:flyToWaylineMode>{cfg.fly_to_wayline_mode}</wpml:flyToWaylineMode>\n"
        f"{indent}  <wpml:finishAction>{cfg.finish_action}</wpml:finishAction>\n"
        f"{indent}  <wpml:exitOnRCLost>{cfg.exit_on_rc_lost}</wpml:exitOnRCLost>\n"
        f"{indent}  <wpml:executeRCLostAction>{cfg.execute_rc_lost_action}</wpml:executeRCLostAction>\n"
        f"{indent}  <wpml:globalTransitionalSpeed>{cfg.global_transitional_speed:g}</wpml:globalTransitionalSpeed>\n"
        f"{indent}  <wpml:droneInfo>\n"
        f"{indent}    <wpml:droneEnumValue>{di.drone_enum_value}</wpml:droneEnumValue>\n"
        f"{indent}    <wpml:droneSubEnumValue>{di.drone_sub_enum_value}</wpml:droneSubEnumValue>\n"
        f"{indent}  </wpml:droneInfo>\n"
        f"{indent}</wpml:missionConfig>\n"
    )


def render_template_kml(mission: WpmlMission) -> str:
    body = (
        f"  <Document>\n"
        f"    <wpml:author>{mission.author}</wpml:author>\n"
        f"    <wpml:createTime>{mission.create_time}</wpml:createTime>\n"
        f"    <wpml:updateTime>{mission.update_time}</wpml:updateTime>\n"
        f"{_mission_config_xml(mission, '    ')}"
        f"  </Document>\n"
    )
    return _XML_HEADER + _KML_OPEN + body + _KML_CLOSE


def _action_xml(action: Action, indent: str) -> str:
    params = "".join(
        f"{indent}    <wpml:{tag}>{value}</wpml:{tag}>\n" for tag, value in action.params.items()
    )
    return (
        f"{indent}<wpml:action>\n"
        f"{indent}  <wpml:actionId>{action.action_id}</wpml:actionId>\n"
        f"{indent}  <wpml:actionActuatorFunc>{action.actuator_func}</wpml:actionActuatorFunc>\n"
        f"{indent}  <wpml:actionActuatorFuncParam>\n"
        f"{params}"
        f"{indent}  </wpml:actionActuatorFuncParam>\n"
        f"{indent}</wpml:action>\n"
    )


def _action_group_xml(group: ActionGroup, indent: str) -> str:
    actions_xml = "".join(_action_xml(a, indent + "  ") for a in group.actions)
    return (
        f"{indent}<wpml:actionGroup>\n"
        f"{indent}  <wpml:actionGroupId>{group.action_group_id}</wpml:actionGroupId>\n"
        f"{indent}  <wpml:actionGroupStartIndex>{group.start_index}</wpml:actionGroupStartIndex>\n"
        f"{indent}  <wpml:actionGroupEndIndex>{group.end_index}</wpml:actionGroupEndIndex>\n"
        f"{indent}  <wpml:actionGroupMode>{group.mode}</wpml:actionGroupMode>\n"
        f"{indent}  <wpml:actionTrigger>\n"
        f"{indent}    <wpml:actionTriggerType>{group.trigger_type}</wpml:actionTriggerType>\n"
        f"{indent}  </wpml:actionTrigger>\n"
        f"{actions_xml}"
        f"{indent}</wpml:actionGroup>\n"
    )


def _waypoint_xml(wp: Waypoint, indent: str) -> str:
    heading = wp.heading
    turn = wp.turn
    gimbal = wp.gimbal_heading
    groups_xml = "".join(_action_group_xml(g, indent + "  ") for g in wp.action_groups)
    return (
        f"{indent}<Placemark>\n"
        f"{indent}  <Point>\n"
        f"{indent}    <coordinates>\n"
        f"{indent}      {wp.longitude},{wp.latitude}\n"
        f"{indent}    </coordinates>\n"
        f"{indent}  </Point>\n"
        f"{indent}  <wpml:index>{wp.index}</wpml:index>\n"
        f"{indent}  <wpml:executeHeight>{wp.execute_height:g}</wpml:executeHeight>\n"
        f"{indent}  <wpml:waypointSpeed>{wp.speed:g}</wpml:waypointSpeed>\n"
        f"{indent}  <wpml:waypointHeadingParam>\n"
        f"{indent}    <wpml:waypointHeadingMode>{heading.mode}</wpml:waypointHeadingMode>\n"
        f"{indent}    <wpml:waypointHeadingAngle>{heading.angle:g}</wpml:waypointHeadingAngle>\n"
        f"{indent}    <wpml:waypointPoiPoint>{heading.poi_point}</wpml:waypointPoiPoint>\n"
        f"{indent}    <wpml:waypointHeadingAngleEnable>{int(heading.angle_enable)}</wpml:waypointHeadingAngleEnable>\n"
        f"{indent}    <wpml:waypointHeadingPathMode>{heading.path_mode}</wpml:waypointHeadingPathMode>\n"
        f"{indent}    <wpml:waypointHeadingPoiIndex>{heading.poi_index}</wpml:waypointHeadingPoiIndex>\n"
        f"{indent}  </wpml:waypointHeadingParam>\n"
        f"{indent}  <wpml:waypointTurnParam>\n"
        f"{indent}    <wpml:waypointTurnMode>{turn.mode}</wpml:waypointTurnMode>\n"
        f"{indent}    <wpml:waypointTurnDampingDist>{turn.damping_dist:g}</wpml:waypointTurnDampingDist>\n"
        f"{indent}  </wpml:waypointTurnParam>\n"
        f"{indent}  <wpml:useStraightLine>{int(wp.use_straight_line)}</wpml:useStraightLine>\n"
        f"{groups_xml}"
        f"{indent}  <wpml:waypointGimbalHeadingParam>\n"
        f"{indent}    <wpml:waypointGimbalPitchAngle>{gimbal.pitch_angle:g}</wpml:waypointGimbalPitchAngle>\n"
        f"{indent}    <wpml:waypointGimbalYawAngle>{gimbal.yaw_angle:g}</wpml:waypointGimbalYawAngle>\n"
        f"{indent}  </wpml:waypointGimbalHeadingParam>\n"
        f"{indent}</Placemark>\n"
    )


def _folder_xml(folder: WaylineFolder, indent: str) -> str:
    waypoints_xml = "".join(_waypoint_xml(wp, indent + "  ") for wp in folder.waypoints)
    return (
        f"{indent}<Folder>\n"
        f"{indent}  <wpml:templateId>{folder.template_id}</wpml:templateId>\n"
        f"{indent}  <wpml:executeHeightMode>{folder.execute_height_mode}</wpml:executeHeightMode>\n"
        f"{indent}  <wpml:waylineId>{folder.wayline_id}</wpml:waylineId>\n"
        f"{indent}  <wpml:distance>{folder.distance:g}</wpml:distance>\n"
        f"{indent}  <wpml:duration>{folder.duration:g}</wpml:duration>\n"
        f"{indent}  <wpml:autoFlightSpeed>{folder.auto_flight_speed:g}</wpml:autoFlightSpeed>\n"
        f"{waypoints_xml}"
        f"{indent}</Folder>\n"
    )


def render_waylines_wpml(mission: WpmlMission) -> str:
    folders_xml = "".join(_folder_xml(f, "    ") for f in mission.folders)
    body = f"  <Document>\n{_mission_config_xml(mission, '    ')}{folders_xml}  </Document>\n"
    return _XML_HEADER + _KML_OPEN + body + _KML_CLOSE


def export_mission(mission: WpmlMission, output_path: str) -> None:
    """Write `mission` out as a `.kmz` at `output_path`.

    Python's default float-to-str conversion (used throughout this module)
    already matches DJI Fly's plain decimal notation for the coordinate
    magnitudes seen so far; correctness is confirmed by the round-trip
    test comparing parsed structures, not raw text.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("wpmz/template.kml", render_template_kml(mission))
        archive.writestr("wpmz/waylines.wpml", render_waylines_wpml(mission))
