"""Tests for the local web UI's HTTP layer (app/server.py).

These exercise the Flask routes with Flask's test client -- no real
browser, no real Leaflet map. The point is to prove the HTTP layer wires
requests through correctly to `mission/`'s already-tested engine, not to
re-test the engine itself.
"""
import io
import math
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.server import EXPORTS_DIR, app as flask_app  # noqa: E402
from mission.parser import parse_mission  # noqa: E402

EXAMPLE_KMZ = PROJECT_ROOT / "examples" / "original_dji_mission_14wp_loop.kmz"


def _offset(lon, lat, east_m, north_m):
    dlat = north_m / 111320.0
    dlon = east_m / (111320.0 * math.cos(math.radians(lat)))
    return [lon + dlon, lat + dlat]


SMALL_POLYGON = [
    _offset(4.197, 50.826, 0, 0),
    _offset(4.197, 50.826, 100, 0),
    _offset(4.197, 50.826, 100, 80),
    _offset(4.197, 50.826, 0, 80),
]


@pytest.fixture
def client():
    flask_app.config.update(TESTING=True)
    return flask_app.test_client()


@pytest.fixture(autouse=True)
def _clean_exports_dir():
    yield
    if EXPORTS_DIR.exists():
        for f in EXPORTS_DIR.glob("*.kmz"):
            f.unlink()


def _preview_payload(**overrides):
    payload = {
        "polygon": SMALL_POLYGON,
        "altitude_m": 50,
        "front_overlap": 0.7,
        "side_overlap": 0.7,
        "direction_deg": 0,
        "speed_ms": 5,
        "gimbal_pitch_deg": -90,
    }
    payload.update(overrides)
    return payload


def test_index_serves_html(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"DJI Mapping Mission Builder" in response.data


def test_preview_returns_waypoints_and_stats(client):
    response = client.post("/api/preview", json=_preview_payload())
    assert response.status_code == 200
    data = response.get_json()
    assert data["waypoint_count"] > 0
    assert len(data["waypoints"]) == data["waypoint_count"]
    assert data["photo_count"] == data["waypoint_count"]
    assert data["distance_m"] > 0
    assert data["estimated_seconds"] > 0
    assert data["has_errors"] is False


def test_preview_rejects_degenerate_polygon(client):
    response = client.post("/api/preview", json=_preview_payload(polygon=[[0, 0], [1, 1]]))
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_preview_warns_on_huge_grid(client):
    big_polygon = [
        _offset(4.197, 50.826, 0, 0),
        _offset(4.197, 50.826, 500, 0),
        _offset(4.197, 50.826, 500, 400),
        _offset(4.197, 50.826, 0, 400),
    ]
    response = client.post(
        "/api/preview",
        json=_preview_payload(polygon=big_polygon, front_overlap=0.85, side_overlap=0.85),
    )
    assert response.status_code == 200
    data = response.get_json()
    assert any("commonly reported" in issue["message"] for issue in data["issues"])
    assert data["has_errors"] is False  # a warning, not a hard error


def test_export_writes_versioned_file_and_serves_download(client):
    payload = _preview_payload(name="Test Veld")

    first = client.post("/api/export", json=payload)
    assert first.status_code == 200
    assert first.headers["Content-Disposition"].endswith('.kmz"') or "TestVeld" in first.headers[
        "Content-Disposition"
    ]
    assert "_v01.kmz" in first.headers["Content-Disposition"]

    second = client.post("/api/export", json=payload)
    assert second.status_code == 200
    assert "_v02.kmz" in second.headers["Content-Disposition"]

    saved = sorted(EXPORTS_DIR.glob("*TestVeld*.kmz"))
    assert len(saved) == 2


def test_export_blocked_by_validation_errors(client):
    # An empty polygon is rejected before a mission can even be built, but
    # a mission with a validator ERROR should also be blocked -- exercise
    # that path by asking for an absurdly steep gimbal pitch is fine (not
    # an error), so instead directly hit the invalid-overlap ValueError
    # path via the mapping engine's own guard.
    response = client.post("/api/export", json=_preview_payload(front_overlap=1.0))
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_mission_types_endpoint(client):
    response = client.get("/api/mission-types")
    assert response.status_code == 200
    data = response.get_json()
    assert "WP2D" in data["mission_types"]
    assert data["active"] == "WP2D"


def _upload(client, route, extra_form=None):
    with open(EXAMPLE_KMZ, "rb") as f:
        data = {"file": (f, "original_dji_mission_14wp_loop.kmz")}
        data.update(extra_form or {})
        return client.post(route, data=data, content_type="multipart/form-data")


def test_import_returns_summary_without_writing_files(client):
    response = _upload(client, "/api/import")
    assert response.status_code == 200
    data = response.get_json()

    assert data["waypoint_count"] == 14
    assert data["altitude_m"]["uniform"] is True
    assert data["altitude_m"]["min"] == 50
    assert data["mission_config"]["drone_enum_value"] == 68
    assert data["has_errors"] is False
    assert data["source_filename"] == "original_dji_mission_14wp_loop.kmz"

    assert not EXPORTS_DIR.exists() or not list(EXPORTS_DIR.glob("*.kmz"))


def test_import_rejects_non_kmz_file(client):
    response = client.post(
        "/api/import",
        data={"file": (io.BytesIO(b"not a kmz"), "not_a_mission.kmz")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_import_export_applies_altitude_edit(client):
    response = _upload(
        client,
        "/api/import/export",
        {"name": "Geimporteerd", "mission_type": "WPGEN", "altitude_m": "65"},
    )
    assert response.status_code == 200
    assert "_v01.kmz" in response.headers["Content-Disposition"]
    assert "WPGEN" in response.headers["Content-Disposition"]

    saved = sorted(EXPORTS_DIR.glob("*Geimporteerd*.kmz"))
    assert len(saved) == 1
    reparsed = parse_mission(str(saved[0]))
    for folder in reparsed.folders:
        for wp in folder.waypoints:
            assert wp.execute_height == 65


def test_import_export_without_edits_preserves_original_values(client):
    response = _upload(client, "/api/import/export", {"name": "Onveranderd", "mission_type": "WPGEN"})
    assert response.status_code == 200

    saved = sorted(EXPORTS_DIR.glob("*Onveranderd*.kmz"))
    original = parse_mission(str(EXAMPLE_KMZ))
    reparsed = parse_mission(str(saved[0]))

    assert [wp.execute_height for f in reparsed.folders for wp in f.waypoints] == [
        wp.execute_height for f in original.folders for wp in f.waypoints
    ]


def test_import_export_rejects_bad_mission_type(client):
    response = _upload(client, "/api/import/export", {"name": "Test", "mission_type": "NOTATYPE"})
    assert response.status_code == 400
    assert "error" in response.get_json()


def test_original_upload_never_overwritten(client):
    before = EXAMPLE_KMZ.read_bytes()
    _upload(client, "/api/import/export", {"name": "Test", "mission_type": "WPGEN", "altitude_m": "99"})
    after = EXAMPLE_KMZ.read_bytes()
    assert before == after
