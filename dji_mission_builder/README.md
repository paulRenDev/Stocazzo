# DJI Mapping Mission Builder

A tool to create, edit, validate, and export DJI-compatible `.kmz` waypoint
and mapping missions for the **DJI Mini 5 Pro + DJI RC 2**, with both manual
and AI-assisted configuration.

Core principle: **the AI decides what the user means; a deterministic
mission engine computes and generates the actual flight plan.** The AI
never writes KMZ/XML directly.

## Status: Phase 0 in progress

This project deliberately did not start with a UI or a guessed WPML
implementation. One real DJI Fly export (Mini 5 Pro + RC 2) has been
reverse-engineered — see `docs/WPML_FINDINGS.md` — and a structured
parser, generator, and validator exist, with a passing identity
round-trip test against that real file (`tests/test_generator.py`).

**Still needed to move Phase 0 forward:** a second `.kmz` — the same
mission re-exported after changing one setting (start with altitude) in
DJI Fly — to confirm which fields are actually safe to edit, plus a real
DJI-Fly-generated *mapping*-grid mission to inform Phase 2. Drop new
samples into `examples/`; see `examples/README.md`.

Implemented and tested so far: mission naming/versioning
(`mission/naming.py`), a generic KMZ inspector plus the real WPML 1.0.2
parser (`mission/parser.py`), the KMZ generator (`mission/generator.py`),
and structural validation (`mission/validator.py`).

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
├── mission/        naming.py, parser.py, generator.py, validator.py
│                   implemented and tested; mapping.py stubbed (Phase 2)
├── wpml/           empty — see build spec sec. 2 on whether it's needed
├── tests/
└── examples/       drop real DJI .kmz files here
```

## Running tests

```bash
cd dji_mission_builder
python -m pytest tests/
```
