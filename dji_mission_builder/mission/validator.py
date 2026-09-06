"""Pre-export validation (brief sec. 12).

Only checks that are actually verifiable from the WPML structure and
general flight-safety sense (non-empty route, valid coordinates, unique
sequential indices, non-negative numeric fields, recognized enum values)
are implemented here. Aircraft-specific numeric limits (max altitude, max
speed the Mini 5 Pro / DJI Fly itself enforces) are deliberately NOT
hardcoded: only one real sample has been analyzed so far (50 m AGL,
2.5 m/s) and guessing DJI's actual limits would violate this project's
core rule of never acting on assumptions about the aircraft. Fill in
`KNOWN_DRONE_ENUM_VALUES` and add range checks once those limits are
confirmed (DJI Fly's own UI, or official docs) — see docs/WPML_FINDINGS.md.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from mission.parser import WpmlMission

# (droneEnumValue, droneSubEnumValue) pairs seen in real, confirmed exports.
KNOWN_DRONE_ENUM_VALUES: set[tuple[int, int]] = {
    (68, 0),  # DJI Mini 5 Pro + RC 2 (examples/original_dji_mission.kmz)
}

KNOWN_ACTUATOR_FUNCS: set[str] = {
    "gimbalRotate",
    "gimbalEvenlyRotate",
    "stopRecord",
    "startRecord",
    "takePhoto",
}

# Commonly reported across DJI Fly / DJI GS Pro waypoint missions (99 per
# mission, auto-split into segments beyond that) -- not independently
# confirmed for the Mini 5 Pro specifically, so this is a WARNING, not a
# hard cap, per this project's rule against acting on unconfirmed limits.
COMMONLY_REPORTED_MAX_WAYPOINTS = 99


class Severity(str, Enum):
    ERROR = "ERROR"
    WARNING = "WARNING"


@dataclass
class ValidationIssue:
    severity: Severity
    message: str


def validate_mission(mission: WpmlMission) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    all_waypoints = [wp for folder in mission.folders for wp in folder.waypoints]

    if not mission.folders:
        issues.append(ValidationIssue(Severity.ERROR, "Mission has no wayline folders"))
    if not all_waypoints:
        issues.append(ValidationIssue(Severity.ERROR, "Mission has no waypoints"))
    elif len(all_waypoints) > COMMONLY_REPORTED_MAX_WAYPOINTS:
        issues.append(
            ValidationIssue(
                Severity.WARNING,
                f"Mission has {len(all_waypoints)} waypoints; DJI Fly waypoint missions are "
                f"commonly reported to cap out around {COMMONLY_REPORTED_MAX_WAYPOINTS} (not "
                "independently confirmed for the Mini 5 Pro) — verify DJI Fly accepts this "
                "many, or reduce overlap/area, before flying",
            )
        )

    di = mission.mission_config.drone_info
    drone_key = (di.drone_enum_value, di.drone_sub_enum_value)
    if drone_key not in KNOWN_DRONE_ENUM_VALUES:
        issues.append(
            ValidationIssue(
                Severity.WARNING,
                f"droneEnumValue/droneSubEnumValue {drone_key} not confirmed against a real "
                "Mini 5 Pro + RC 2 export; compatibility cannot be verified",
            )
        )

    for folder in mission.folders:
        indices = [wp.index for wp in folder.waypoints]
        if len(set(indices)) != len(indices):
            issues.append(
                ValidationIssue(Severity.ERROR, f"Folder {folder.template_id}: duplicate waypoint indices")
            )
        if indices and sorted(indices) != list(range(min(indices), max(indices) + 1)):
            issues.append(
                ValidationIssue(
                    Severity.ERROR,
                    f"Folder {folder.template_id}: waypoint indices are not a contiguous sequence "
                    "(route continuity check, brief sec. 12)",
                )
            )

        for wp in folder.waypoints:
            if not (-90.0 <= wp.latitude <= 90.0):
                issues.append(
                    ValidationIssue(Severity.ERROR, f"Waypoint {wp.index}: invalid latitude {wp.latitude}")
                )
            if not (-180.0 <= wp.longitude <= 180.0):
                issues.append(
                    ValidationIssue(Severity.ERROR, f"Waypoint {wp.index}: invalid longitude {wp.longitude}")
                )
            if wp.execute_height <= 0:
                issues.append(
                    ValidationIssue(
                        Severity.ERROR, f"Waypoint {wp.index}: executeHeight must be positive, got {wp.execute_height}"
                    )
                )
            if wp.speed <= 0:
                issues.append(
                    ValidationIssue(
                        Severity.ERROR, f"Waypoint {wp.index}: waypointSpeed must be positive, got {wp.speed}"
                    )
                )
            for group in wp.action_groups:
                for action in group.actions:
                    if action.actuator_func not in KNOWN_ACTUATOR_FUNCS:
                        issues.append(
                            ValidationIssue(
                                Severity.WARNING,
                                f"Waypoint {wp.index}: unrecognized actionActuatorFunc "
                                f"{action.actuator_func!r} — not verified against a real export",
                            )
                        )

    return issues


def has_errors(issues: list[ValidationIssue]) -> bool:
    return any(issue.severity is Severity.ERROR for issue in issues)
