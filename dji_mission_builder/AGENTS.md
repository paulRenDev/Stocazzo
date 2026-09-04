# Agent instructions — DJI Mapping Mission Builder

Read `docs/PROJECT_BRIEF.md` (the original spec, in Dutch) and
`docs/BUILD_SPEC.md` (the sequenced technical spec derived from it) before
doing anything else in this directory. This file is the short version /
guardrails; those two are the source of truth.

## Current status

**Phase 0 is in progress, not complete.** One real DJI Mini 5 Pro + RC 2
export has been reverse-engineered (`examples/original_dji_mission.kmz`,
findings in `docs/WPML_FINDINGS.md`), and `mission/parser.py`,
`mission/generator.py`, and `mission/validator.py` are implemented and
tested against it, including a passing identity round-trip
(`tests/test_generator.py`). Read `docs/WPML_FINDINGS.md` before touching
any of those three modules — it lists exactly what's confirmed vs still a
hypothesis.

**Do not write `mission/mapping.py`, `wpml/schemas/*`, or `wpml/templates/*`
against guessed DJI XML structure or assumed mapping-grid behavior.** Only
one real sample exists so far and it's a plain 3-waypoint route, not a
mapping mission — Phase 2 (the grid/overlap engine) needs a real
DJI-Fly-generated mapping mission before it can be built on evidence
rather than assumption. If you're tempted to fill this in from DJI's
public partial docs anyway, stop and re-read `docs/BUILD_SPEC.md` §1 —
that's the exact mistake this project is structured to avoid.

**Do not mark any field "confirmed editable" beyond what
`docs/WPML_FINDINGS.md` already lists as confirmed.** The "editable vs
do-not-modify" table there is still a hypothesis pending a second sample
(same mission, one field changed, re-exported) — see that doc's "Next
steps" section.

## Hard rules (non-negotiable, carried from the brief)

1. The AI assistant (chat/NL layer) only ever produces the structured
   parameter JSON described in `docs/BUILD_SPEC.md` §5. It never generates
   or edits WPML/KMZ/XML directly. All XML I/O goes through the
   deterministic `mission/` engine.
2. Never overwrite a user's originally imported `.kmz`. Every edit produces
   a new versioned file (see `mission/naming.py`).
3. This tool never talks to the drone or pushes a mission to the aircraft.
   Its only output is a `.kmz` file on disk. The user loads it into DJI Fly
   themselves.
4. Every export goes through CREATE → CALCULATE → PREVIEW → VALIDATE →
   EXPORT. No code path skips VALIDATE.
5. Keep "editable" vs "do-not-modify" DJI fields explicitly distinguished
   in code and in the UI (once there is a UI) — never silently drop or
   rewrite a field you haven't confirmed is safe to touch (see the
   round-trip test plan, build spec §7).

## What's already built and safe to extend

- `mission/naming.py` — filename/mission-ID/versioning logic (brief §6–8).
- `mission/parser.py` — generic inspector (`inspect_kmz`) plus the real
  WPML 1.0.2 structured parser (`parse_mission`), grounded in
  `examples/original_dji_mission.kmz`.
- `mission/generator.py` — rebuilds a `.kmz` from the parsed structure;
  identity round-trip confirmed by test.
- `mission/validator.py` — structural/range checks; deliberately has no
  hardcoded aircraft-specific limits yet (see its docstring).
- Tests for all of the above, run against the real sample.

Extending the parser/generator to cover fields from a *new* real sample is
in scope any time — that's exactly how Phase 0 is meant to grow. Guessing
fields that no sample has shown is not.

## What still needs more real `.kmz` samples

`mission/mapping.py` (Phase 2 grid engine — needs a real mapping-grid
export), confirming the "editable vs do-not-modify" hypothesis in
`docs/WPML_FINDINGS.md` (needs a same-mission-one-field-changed pair), and
the map/mission-editor UI (needs the engine to be further along first, per
brief §18). See build spec §1–3 for the full phase breakdown.

## Style

- Python for `mission/` and `wpml/`. Keep modules small and testable;
  the mission engine must be usable headlessly (no UI dependency) since
  Phase 1's acceptance test is a round-trip, not a UI interaction.
- No speculative abstractions ahead of Phase 0 data. It's fine for
  `generator.py` etc. to stay a documented stub with a `NotImplementedError`
  until real findings exist.
