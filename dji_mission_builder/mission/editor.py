"""Editing an already-parsed mission (brief sec. 2, sec. 13; MVP v0.1
items 6-7 in brief sec. 17: altitude and speed edits).

Only fields `docs/WPML_FINDINGS.md` marks as confirmed (or at minimum
"likely") independently editable are exposed here. Gimbal and photo-action
edits (brief sec. 17 items 8-9) are not implemented yet -- extend this
module when they are, rather than special-casing edits in the UI/app
layer. `app/server.py` must call into this module rather than mutating a
`WpmlMission` itself.
"""
from __future__ import annotations

import copy
import time

from mission.parser import WpmlMission


def apply_edits(
    mission: WpmlMission,
    altitude_m: float | None = None,
    speed_ms: float | None = None,
) -> WpmlMission:
    """Return a new `WpmlMission` with `altitude_m`/`speed_ms` applied
    uniformly to every waypoint (and `speed_ms` to each folder's
    `autoFlightSpeed`), leaving fields not passed untouched. Never
    mutates `mission` itself -- always returns a copy.

    Bumps `update_time` to now when any edit is applied, while preserving
    `create_time` -- matching the real DJI Fly behavior confirmed in
    docs/WPML_FINDINGS.md ("Confirmed via diff": createTime is set once,
    updateTime refreshes on every save).
    """
    edited = copy.deepcopy(mission)
    changed = False

    if altitude_m is not None:
        if altitude_m <= 0:
            raise ValueError("altitude_m must be positive")
        for folder in edited.folders:
            for wp in folder.waypoints:
                wp.execute_height = altitude_m
        changed = True

    if speed_ms is not None:
        if speed_ms <= 0:
            raise ValueError("speed_ms must be positive")
        for folder in edited.folders:
            folder.auto_flight_speed = speed_ms
            for wp in folder.waypoints:
                wp.speed = speed_ms
        changed = True

    if changed:
        edited.update_time = int(time.time() * 1000)

    return edited
