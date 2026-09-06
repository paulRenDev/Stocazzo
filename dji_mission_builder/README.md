# DJI Mapping Mission Builder

A tool to create, edit, validate, and export DJI-compatible `.kmz` waypoint
and mapping missions for the **DJI Mini 5 Pro + DJI RC 2**, with both manual
and AI-assisted configuration.

Core principle: **the AI decides what the user means; a deterministic
mission engine computes and generates the actual flight plan.** The AI
never writes KMZ/XML directly.

## Quick start (just want to use it?)

1. Install [Python 3](https://www.python.org/downloads/) if you don't have it.
2. Double-click `run.bat` (Windows) or run `./run.sh` (Mac/Linux) from
   this folder.
3. Your browser opens to a map. Draw an area, set your mission settings,
   click **Preview**, then **Export .kmz**.

No Python knowledge needed — the scripts install the one dependency
(Flask) and start the app for you. See "Web UI" below for what's built.

## Status: Phase 0 well underway, Phase 2 + a first Phase 4 UI implemented

This project deliberately did not start with a UI or a guessed WPML
implementation. Six real DJI Fly exports (Mini 5 Pro + RC 2) have been
reverse-engineered — see `docs/WPML_FINDINGS.md` — informing a structured
parser, generator, and validator, all passing identity round-trip tests
against every real sample.

Research (DJI's official WPML spec, plus independent sources — see
`docs/WPML_FINDINGS.md`, "Cross-reference") indicates DJI Fly has no
native mapping/grid mode on the Mini 5 Pro at all, and that WPML's
interval/distance photo trigger isn't supported on this aircraft either.
That unblocked Phase 2 without needing a real mapping-grid export: the
grid engine (`mission/mapping.py`) computes the lawnmower grid itself and
emits it through the already-confirmed plain-waypoint structure, one
`takePhoto` per waypoint.

**Still useful to add** (not blocking): a `.kmz` isolating a
coordinates-only edit or a mission-level field change (moves more fields
from "likely editable" to "confirmed" in `docs/WPML_FINDINGS.md`), and a
real DJI-Fly mapping-grid export or camera calibration if one ever
surfaces, to check `mission/mapping.py`'s camera-model assumptions. Drop
new samples into `examples/`; see `examples/README.md`.

Implemented and tested: mission naming/versioning (`mission/naming.py`),
a generic KMZ inspector plus the real WPML 1.0.2 parser
(`mission/parser.py`), the KMZ generator (`mission/generator.py`),
structural validation (`mission/validator.py`), and the mapping-grid
engine (`mission/mapping.py`).

## Web UI

A local Flask app (`app/server.py`) with a Leaflet map (brief sec. 9), all
user-facing text in English using DJI's own terminology. Two tabs:

- **New Mapping Mission**: draw a polygon, set altitude/overlap/
  direction/speed/gimbal pitch, hit **Preview** to see the computed
  flight grid and stats (waypoints, distance, photo count, estimated
  flight time) plus any validator warnings/errors, then **Export .kmz**
  to download a correctly-named, auto-versioned mission file.
- **Import Existing Mission** (brief sec. 2, sec. 13): upload a real DJI
  Fly `.kmz`, see its waypoints on the map and its settings (drone,
  altitude, speed, finish action, distance, photos), optionally set a new
  uniform altitude and/or speed, then **Export Edited Version**. The
  uploaded file is never modified or stored — every export is a new,
  separately versioned file (`mission/editor.py`).

Runs entirely on your own machine — nothing is uploaded anywhere except
to your own local server. Only real map tile imagery needs internet; the
map/drawing library itself is vendored in `app/static/vendor/` (see its
`NOTICE.md`), not loaded from a CDN.

Not built yet: Quick Mission mode vs. Expert Mode as distinct UI states
(brief sec. 14-15), the AI chat assistant (brief sec. 4, Phase 3), and
gimbal/photo-action edits on imported missions (brief sec. 17 items 8-9)
— only altitude and speed are exposed so far.

## Read first

- [`docs/PROJECT_BRIEF.md`](docs/PROJECT_BRIEF.md) — the original project
  brief (Dutch).
- [`docs/BUILD_SPEC.md`](docs/BUILD_SPEC.md) — the phased technical spec
  derived from it, with the AI/engine contract and the round-trip test
  plan.
- [`AGENTS.md`](AGENTS.md) — guardrails for any agent (or human) working in
  this directory.

## Layout

```
dji_mission_builder/
├── AGENTS.md
├── README.md
├── run.sh / run.bat    start the web UI (installs Flask, opens browser)
├── docs/
├── app/                server.py (Flask) + static/ (JS/CSS, vendored
│                       Leaflet/Leaflet.draw) + templates/ (index.html)
├── mission/            naming.py, parser.py, generator.py, validator.py,
│                       mapping.py — all implemented and tested
├── wpml/               empty — parser/generator dataclasses serve this role
├── tests/
└── examples/           drop real DJI .kmz files here
```

## Running tests

```bash
cd dji_mission_builder
pip install -r requirements.txt
python -m pytest tests/
```
