"""Filename, mission-ID, and versioning logic (brief secs. 6-8).

Pure string/logic module — no dependency on the DJI WPML/KMZ format, so it
does not need a real sample file to be correct.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date as _date
from pathlib import Path

MISSION_TYPES = ("WP2D", "WP3D", "WPINS", "WPVID", "WPGEN")

_INVALID_CHARS = re.compile(r'[/\\:*?"<>|]')
_WHITESPACE = re.compile(r"\s+")
_NON_ALNUM = re.compile(r"[^A-Za-z0-9]")

DEFAULT_MAX_NAME_LEN = 40


def sanitize_name(raw: str, max_len: int = DEFAULT_MAX_NAME_LEN) -> str:
    """Turn free-text like "Boerderij Jos" into a safe filename fragment.

    Removes the characters Windows/DJI Fly can't handle in a filename,
    collapses whitespace, then strips everything that isn't alphanumeric
    (matching the brief's example: "Boerderij Jos" -> "BoerderijJos").
    """
    if not raw or not raw.strip():
        raise ValueError("name must not be empty")
    cleaned = _INVALID_CHARS.sub("", raw)
    cleaned = _WHITESPACE.sub(" ", cleaned).strip()
    cleaned = _NON_ALNUM.sub("", cleaned)
    if not cleaned:
        raise ValueError(f"name {raw!r} has no usable characters after sanitizing")
    return cleaned[:max_len]


def validate_mission_type(mission_type: str) -> str:
    if mission_type not in MISSION_TYPES:
        raise ValueError(
            f"unknown mission type {mission_type!r}; must be one of {MISSION_TYPES}"
        )
    return mission_type


def build_filename(
    mission_date: _date,
    mission_type: str,
    name: str,
    version: int | None = None,
    max_name_len: int = DEFAULT_MAX_NAME_LEN,
) -> str:
    """Build "YYYYMMDD_TYPE_NAME.kmz" or "..._vNN.kmz" (brief secs. 6-7)."""
    validate_mission_type(mission_type)
    safe_name = sanitize_name(name, max_name_len)
    stamp = mission_date.strftime("%Y%m%d")
    base = f"{stamp}_{mission_type}_{safe_name}"
    if version is not None:
        if version < 1:
            raise ValueError("version must be >= 1")
        base += f"_v{version:02d}"
    return f"{base}.kmz"


_VERSION_RE_TEMPLATE = r"^{stamp}_{mtype}_{name}_v(\d+)\.kmz$"


def next_available_version(
    directory: Path,
    mission_date: _date,
    mission_type: str,
    name: str,
    max_name_len: int = DEFAULT_MAX_NAME_LEN,
) -> int:
    """Scan `directory` for existing exports of this mission and return the
    next free version number (brief sec. 7): never overwrite an existing
    export, including the originally imported KMZ.
    """
    validate_mission_type(mission_type)
    safe_name = sanitize_name(name, max_name_len)
    stamp = mission_date.strftime("%Y%m%d")
    pattern = re.compile(
        _VERSION_RE_TEMPLATE.format(
            stamp=re.escape(stamp),
            mtype=re.escape(mission_type),
            name=re.escape(safe_name),
        )
    )
    highest = 0
    if directory.exists():
        for entry in directory.iterdir():
            match = pattern.match(entry.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return highest + 1


def generate_mission_id(
    mission_date: _date,
    mission_type: str,
    name: str,
    version: int,
    max_name_len: int = DEFAULT_MAX_NAME_LEN,
) -> str:
    """Build the internal mission ID, e.g. "20260902-WP2D-BoerderijJos-01"
    (brief sec. 8). Deliberately hyphenated rather than underscored so it
    is visibly distinct from the exported filename.
    """
    validate_mission_type(mission_type)
    safe_name = sanitize_name(name, max_name_len)
    stamp = mission_date.strftime("%Y%m%d")
    return f"{stamp}-{mission_type}-{safe_name}-{version:02d}"


@dataclass
class MissionMetadata:
    """Metadata tracked per mission (brief sec. 8)."""

    mission_id: str
    created: str
    modified: str
    mission_type: str
    name: str
    drone: str
    altitude_m: float | None = None
    front_overlap: float | None = None
    side_overlap: float | None = None
    speed_ms: float | None = None
    version: int = 1
    source_kmz: str | None = None
