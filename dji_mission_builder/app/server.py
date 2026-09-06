"""Local web UI for the DJI Mapping Mission Builder (brief sec. 9, Phase 4).

Runs entirely on the user's own machine -- no data leaves localhost. This
is a thin HTTP layer only: every mission-building decision (grid geometry,
WPML structure, validation rules) lives in `mission/`, imported here
unchanged. This file must never build or validate a mission itself.

Start with `python app/server.py` from the project root (or use
`run.sh`/`run.bat`), then open http://127.0.0.1:5000 in a browser.
"""
from __future__ import annotations

import math
import sys
import tempfile
import threading
import webbrowser
import zipfile
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from flask import Flask, jsonify, render_template, request, send_file  # noqa: E402

from mission.editor import apply_edits  # noqa: E402
from mission.generator import export_mission  # noqa: E402
from mission.mapping import MappingMissionParams, build_mapping_mission  # noqa: E402
from mission.naming import MISSION_TYPES, build_filename, next_available_version, sanitize_name  # noqa: E402
from mission.parser import parse_mission  # noqa: E402
from mission.validator import Severity, has_errors, validate_mission  # noqa: E402

EXPORTS_DIR = PROJECT_ROOT / "exports"
MISSION_TYPE = "WP2D"  # the only type mission/mapping.py currently builds

app = Flask(__name__, static_folder="static", template_folder="templates")


def _haversine_m(lon1: float, lat1: float, lon2: float, lat2: float) -> float:
    """Great-circle distance in meters -- used only for the UI's distance/
    flight-time estimate, not for mission generation itself.
    """
    r = 6378137.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _parse_params(payload: dict) -> MappingMissionParams:
    polygon = [(float(lon), float(lat)) for lon, lat in payload["polygon"]]
    return MappingMissionParams(
        polygon=polygon,
        altitude_m=float(payload["altitude_m"]),
        front_overlap=float(payload["front_overlap"]),
        side_overlap=float(payload["side_overlap"]),
        direction_deg=float(payload.get("direction_deg", 0.0)),
        speed_ms=float(payload.get("speed_ms", 2.5)),
        gimbal_pitch_deg=float(payload.get("gimbal_pitch_deg", -90.0)),
    )


def _mission_stats(mission) -> dict:
    waypoints = [wp for folder in mission.folders for wp in folder.waypoints]
    distance_m = sum(
        _haversine_m(a.longitude, a.latitude, b.longitude, b.latitude)
        for a, b in zip(waypoints, waypoints[1:])
    )
    speed = waypoints[0].speed if waypoints else 0
    estimated_seconds = distance_m / speed if speed else 0
    photo_count = sum(
        1
        for wp in waypoints
        for group in wp.action_groups
        for action in group.actions
        if action.actuator_func == "takePhoto"
    )
    return {
        "waypoint_count": len(waypoints),
        "distance_m": round(distance_m, 1),
        "estimated_seconds": round(estimated_seconds),
        "photo_count": photo_count,
        "waypoints": [[wp.longitude, wp.latitude] for wp in waypoints],
    }


def _issues_json(issues) -> list[dict]:
    return [{"severity": issue.severity.value, "message": issue.message} for issue in issues]


def _range_or_value(values: list[float]) -> dict:
    lo, hi = min(values), max(values)
    return {"min": lo, "max": hi, "uniform": lo == hi}


def _import_summary(mission) -> dict:
    """Stats + mission-config summary for an imported mission -- unlike a
    freshly-generated mapping mission, an imported one may have varying
    per-waypoint altitude/speed, so report a range rather than assuming
    one value.
    """
    summary = _mission_stats(mission)
    waypoints = [wp for folder in mission.folders for wp in folder.waypoints]
    summary["altitude_m"] = _range_or_value([wp.execute_height for wp in waypoints]) if waypoints else None
    summary["speed_ms"] = _range_or_value([wp.speed for wp in waypoints]) if waypoints else None
    cfg = mission.mission_config
    summary["mission_config"] = {
        "fly_to_wayline_mode": cfg.fly_to_wayline_mode,
        "finish_action": cfg.finish_action,
        "exit_on_rc_lost": cfg.exit_on_rc_lost,
        "execute_rc_lost_action": cfg.execute_rc_lost_action,
        "drone_enum_value": cfg.drone_info.drone_enum_value,
        "drone_sub_enum_value": cfg.drone_info.drone_sub_enum_value,
    }
    summary["author"] = mission.author
    return summary


def _save_upload_to_tempfile(file_storage) -> Path:
    suffix = Path(file_storage.filename or "upload.kmz").suffix or ".kmz"
    fd, tmp_path = tempfile.mkstemp(suffix=suffix)
    with open(fd, "wb") as f:
        file_storage.save(f)
    return Path(tmp_path)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/preview", methods=["POST"])
def api_preview():
    payload = request.get_json(force=True)
    try:
        params = _parse_params(payload)
        mission = build_mapping_mission(params)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    issues = validate_mission(mission)
    stats = _mission_stats(mission)
    stats["issues"] = _issues_json(issues)
    stats["has_errors"] = has_errors(issues)
    return jsonify(stats)


@app.route("/api/export", methods=["POST"])
def api_export():
    payload = request.get_json(force=True)
    try:
        params = _parse_params(payload)
        mission = build_mapping_mission(params)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    issues = validate_mission(mission)
    if has_errors(issues):
        return jsonify({"error": "validation failed", "issues": _issues_json(issues)}), 400

    raw_name = payload.get("name") or "Mission"
    try:
        sanitize_name(raw_name)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    version = next_available_version(EXPORTS_DIR, today, MISSION_TYPE, raw_name)
    filename = build_filename(today, MISSION_TYPE, raw_name, version=version)
    output_path = EXPORTS_DIR / filename

    export_mission(mission, str(output_path))

    return send_file(
        output_path,
        mimetype="application/vnd.google-earth.kmz",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/api/import", methods=["POST"])
def api_import():
    """Parse an uploaded .kmz and return its structure for display --
    read-only, writes nothing (brief sec. 2: "de originele file moet
    altijd onaangeroerd blijven").
    """
    if "file" not in request.files:
        return jsonify({"error": "No file received."}), 400
    upload = request.files["file"]
    tmp_path = _save_upload_to_tempfile(upload)
    try:
        mission = parse_mission(str(tmp_path))
    except (KeyError, ValueError, zipfile.BadZipFile) as exc:
        return jsonify({"error": f"Could not read the file: {exc}"}), 400
    finally:
        tmp_path.unlink(missing_ok=True)

    issues = validate_mission(mission)
    summary = _import_summary(mission)
    summary["issues"] = _issues_json(issues)
    summary["has_errors"] = has_errors(issues)
    summary["source_filename"] = upload.filename
    return jsonify(summary)


@app.route("/api/import/export", methods=["POST"])
def api_import_export():
    """Re-parse the same uploaded file fresh (never trust client-side
    state for what was originally in it), apply the requested edits via
    `mission.editor`, validate, and export a new versioned file. The
    originally uploaded file itself is never written to.
    """
    if "file" not in request.files:
        return jsonify({"error": "No file received."}), 400
    upload = request.files["file"]
    tmp_path = _save_upload_to_tempfile(upload)
    try:
        mission = parse_mission(str(tmp_path))
    except (KeyError, ValueError, zipfile.BadZipFile) as exc:
        return jsonify({"error": f"Could not read the file: {exc}"}), 400
    finally:
        tmp_path.unlink(missing_ok=True)

    altitude_raw = request.form.get("altitude_m", "").strip()
    speed_raw = request.form.get("speed_ms", "").strip()
    try:
        altitude_m = float(altitude_raw) if altitude_raw else None
        speed_ms = float(speed_raw) if speed_raw else None
        edited = apply_edits(mission, altitude_m=altitude_m, speed_ms=speed_ms)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    issues = validate_mission(edited)
    if has_errors(issues):
        return jsonify({"error": "validation failed", "issues": _issues_json(issues)}), 400

    raw_name = request.form.get("name") or "Mission"
    mission_type = request.form.get("mission_type") or "WPGEN"
    try:
        sanitize_name(raw_name)
        if mission_type not in MISSION_TYPES:
            raise ValueError(f"unknown mission type {mission_type!r}")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today()
    version = next_available_version(EXPORTS_DIR, today, mission_type, raw_name)
    filename = build_filename(today, mission_type, raw_name, version=version)
    output_path = EXPORTS_DIR / filename

    export_mission(edited, str(output_path))

    return send_file(
        output_path,
        mimetype="application/vnd.google-earth.kmz",
        as_attachment=True,
        download_name=filename,
    )


@app.route("/api/mission-types")
def api_mission_types():
    return jsonify({"mission_types": list(MISSION_TYPES), "active": MISSION_TYPE})


def _open_browser():
    webbrowser.open("http://127.0.0.1:5000")


if __name__ == "__main__":
    threading.Timer(1.0, _open_browser).start()
    app.run(host="127.0.0.1", port=5000, debug=False)
