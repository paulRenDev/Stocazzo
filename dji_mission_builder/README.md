# DJI Mapping Mission Builder

A tool to create, edit, validate, and export DJI-compatible `.kmz` waypoint
and mapping missions for the **DJI Mini 5 Pro + DJI RC 2**, with both manual
and AI-assisted configuration.

Core principle: **the AI decides what the user means; a deterministic
mission engine computes and generates the actual flight plan.** The AI
never writes KMZ/XML directly.

## Status: Phase 0 well underway, Phase 2 implemented

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
├── docs/
├── app/            (not started — UI follows the engine)
├── mission/        naming.py, parser.py, generator.py, validator.py,
│                   mapping.py — all implemented and tested
├── wpml/           empty — parser/generator dataclasses serve this role
├── tests/
└── examples/       drop real DJI .kmz files here
```

## Running tests

```bash
cd dji_mission_builder
python -m pytest tests/
```
