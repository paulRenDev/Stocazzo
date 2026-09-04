from datetime import date

import pytest

from mission.naming import (
    MISSION_TYPES,
    build_filename,
    generate_mission_id,
    next_available_version,
    sanitize_name,
    validate_mission_type,
)


def test_sanitize_name_removes_spaces_and_specials():
    assert sanitize_name("Boerderij Jos") == "BoerderijJos"
    assert sanitize_name('a/b\\c:d*e?f"g<h>i|j') == "abcdefghij"


def test_sanitize_name_truncates():
    assert len(sanitize_name("x" * 100, max_len=40)) == 40


def test_sanitize_name_rejects_empty():
    with pytest.raises(ValueError):
        sanitize_name("   ")
    with pytest.raises(ValueError):
        sanitize_name("///***")


def test_validate_mission_type():
    for mtype in MISSION_TYPES:
        assert validate_mission_type(mtype) == mtype
    with pytest.raises(ValueError):
        validate_mission_type("NOPE")


def test_build_filename_without_version():
    result = build_filename(date(2026, 9, 2), "WP2D", "Boerderij Jos")
    assert result == "20260902_WP2D_BoerderijJos.kmz"


def test_build_filename_with_version():
    result = build_filename(date(2026, 9, 2), "WP2D", "Boerderij Jos", version=1)
    assert result == "20260902_WP2D_BoerderijJos_v01.kmz"


def test_next_available_version(tmp_path):
    assert next_available_version(tmp_path, date(2026, 9, 2), "WP2D", "Boerderij Jos") == 1

    (tmp_path / "20260902_WP2D_BoerderijJos_v01.kmz").touch()
    (tmp_path / "20260902_WP2D_BoerderijJos_v02.kmz").touch()
    (tmp_path / "20260902_WP2D_OtherPlace_v05.kmz").touch()

    assert next_available_version(tmp_path, date(2026, 9, 2), "WP2D", "Boerderij Jos") == 3


def test_generate_mission_id():
    mission_id = generate_mission_id(date(2026, 9, 2), "WP2D", "Boerderij Jos", 1)
    assert mission_id == "20260902-WP2D-BoerderijJos-01"
