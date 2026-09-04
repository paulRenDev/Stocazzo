# WPML findings — DJI Mini 5 Pro + RC 2

Sources, all real exports for the DJI Mini 5 Pro + RC 2, provided by the
user:

- `examples/original_dji_mission.kmz` — the base sample, 3 waypoints.
- `examples/original_dji_mission_wp2_edited.kmz` — the same mission,
  pulled directly from the RC 2's own storage
  (`Internal shared storage/Android/data/dji.go.v5/files/waypoint/`)
  after the third waypoint's height/position was edited in DJI Fly and
  re-saved.
- `examples/original_dji_mission_14wp_loop.kmz` — a different, larger
  mission: 14 waypoints in a freeform loop (originally no
  `startRecord`/`takePhoto` actions anywhere). Useful for confirming
  which per-sample patterns above generalize beyond 3 waypoints.
- `examples/original_dji_mission_14wp_with_camera_actions.kmz` — the
  *same* 14-waypoint loop, re-edited in DJI Fly: waypoints 3, 5, 9, 11, 13
  repositioned slightly, waypoint 3's speed changed to 8.1 m/s, and
  `takePhoto` / `startRecord` / `stopRecord` actions added. This is what
  finally shows how DJI Fly expresses a camera trigger.
- `examples/original_dji_mission_15wp_with_camera_actions.kmz` — the same
  mission again, edited further: a new waypoint 14 appended at a new
  location, a second `takePhoto` added at waypoint 1 (with a small
  position/speed edit alongside it), and waypoint 12's speed changed.
  This is what shows the first/last-waypoint markers are recomputed on
  every save, not a fixed property of a given waypoint.
- `examples/original_dji_mission_20wp_multi_photo.kmz` — a different,
  larger route: 20 waypoints, 8 `takePhoto` actions, uniform 1.4 m/s
  waypoint speed. Not a lawnmower grid (waypoints aren't evenly spaced
  parallel lines), but the richest multi-photo sample so far.

Six samples, still all plain waypoint routes — no mapping/lawnmower-grid
export yet (see "Next steps"). Treat anything below not explicitly marked
"confirmed via diff" or "confirmed at n=14" as observed-in-these-files,
not a general DJI spec. Re-run `mission.parser.inspect_kmz` against any
new sample before assuming it generalizes.

## Archive layout

```
original_dji_mission.kmz
└── wpmz/
    ├── template.kml
    └── waylines.wpml
```

No `res/` folder, no thumbnail, no extra resource files. Note this is
*leaner* than some publicly documented DJI WPML examples (which often show
a `res/` folder and template.kml carrying its own `Folder`/`Placemark`
data) — do not assume a `res/` folder is required until a sample that
needs one turns up.

## Namespaces

```xml
xmlns="http://www.opengis.net/kml/2.2"
xmlns:wpml="http://www.uav.com/wpmz/1.0.2"
```

WPML version **1.0.2** (per the xmlns URL). Both files declare the same
namespaces.

## `wpmz/template.kml`

Minimal — no `Folder`/`Placemark` data at all in this sample:

```xml
<kml ...>
  <Document>
    <wpml:author>fly</wpml:author>
    <wpml:createTime>1788344651962</wpml:createTime>
    <wpml:updateTime>1788344651962</wpml:updateTime>
    <wpml:missionConfig>...</wpml:missionConfig>
  </Document>
</kml>
```

- `author` = `"fly"` (i.e. DJI Fly).
- `createTime`/`updateTime` are millisecond Unix timestamps.
- `missionConfig` is byte-for-byte duplicated in `waylines.wpml` (see
  below) in this sample.

## `wpmz/waylines.wpml`

### `wpml:missionConfig` (duplicated from template.kml)

| Field | Value observed | Notes |
|---|---|---|
| `flyToWaylineMode` | `safely` | |
| `finishAction` | `goHome` | |
| `exitOnRCLost` | `executeLostAction` | |
| `executeRCLostAction` | `goBack` | |
| `globalTransitionalSpeed` | `2.5` | m/s, matches per-waypoint speed in this sample |
| `droneInfo.droneEnumValue` | `68` | **Believed** to identify the Mini 5 Pro in DJI's internal drone-type enum, based on this being a real Mini 5 Pro + RC 2 export — DJI's own enum table has not been independently confirmed, so treat `68` as "the value this specific aircraft/app combo produces," not a verified spec constant. |
| `droneInfo.droneSubEnumValue` | `0` | |

### `Folder` (one wayline template)

| Field | Value | Notes |
|---|---|---|
| `templateId` | `0` | |
| `executeHeightMode` | `relativeToStartPoint` | i.e. AGL relative to the takeoff point, not absolute/relative-to-ground-per-point |
| `waylineId` | `0` | |
| `distance` | `0` | Not computed by whatever produced this file — likely filled in by DJI Fly itself on real missions, or simply unused for this mission type. Do not assume the generator must always fill a real value here until confirmed. |
| `duration` | `0` | same caveat as `distance` |
| `autoFlightSpeed` | `2.5` | |

### Waypoints (3 `Placemark` elements, index 0-2)

All three share: `executeHeight = 50` (relativeToStartPoint => 50 m AGL),
`waypointSpeed = 2.5` m/s, `useStraightLine = 0`.

Coordinates (lon, lat — note KML's lon,lat order):

| index | lon | lat |
|---|---|---|
| 0 | 4.19765158540255 | 50.8260738260504 |
| 1 | 4.19785543328268 | 50.8261009346566 |
| 2 | 4.19808073883513 | 50.8261050009369 |

(Lennik, Belgium area — consistent with the user's home location.)

`waypointHeadingParam`: mode `followWayline` in all three; `angleEnable`
is `1` on waypoint 0 and 2 (first and last), `0` on waypoint 1 (middle).
**Confirmed at n=14** (see below): this is exactly the pattern in the
14-waypoint sample too — `1` only on the first and last waypoint of the
route, `0` on every waypoint in between.

`waypointTurnParam`: waypoint 0 and 2 use
`toPointAndStopWithContinuityCurvature`; waypoint 1 (the middle one) uses
`toPointAndPassWithContinuityCurvature`. **Confirmed at n=14**: "stop" at
the first and last waypoint of the route, "pass" through every waypoint
in between, holds exactly for the 14-waypoint sample as well.

### Action groups / actions

- Waypoint 0: two action groups —
  - group 1 (`actionGroupMode=parallel`, trigger `reachPoint`): one action,
    `gimbalRotate` (absolute angle, pitch=0, roll=0, yaw disabled).
  - group 2: one action, `gimbalEvenlyRotate` (pitch=0, roll=0).
- Waypoint 1: one action group, one action, `gimbalEvenlyRotate`.
- Waypoint 2: one action group, one action, `stopRecord`.

No `startRecord`/`takePhoto` action appears anywhere in this sample —
**resolved below**, see "Confirmed: camera/recording actions".

`waypointGimbalHeadingParam` on every waypoint is `pitch=0, yaw=0` —
redundant with the per-waypoint `gimbalRotate`/`gimbalEvenlyRotate`
actions above; relationship between the two not yet understood.

## Confirmed at n=14 (third sample, `original_dji_mission_14wp_loop.kmz`)

A structurally different mission (14 waypoints, freeform loop, no
recording actions) lets several patterns above be checked beyond n=3.
Parses cleanly and round-trips correctly (`tests/test_generator.py`
covers this file too) — including the case of a waypoint with **no**
`actionGroup` element at all (waypoint 13, the last one), which the
parser already handles since it treats `action_groups` as "however many
`<wpml:actionGroup>` elements are present, possibly zero."

- **First/last-waypoint pattern confirmed**: `waypointTurnMode` is
  `toPointAndStopWithContinuityCurvature` only on waypoint 0 and waypoint
  13 (the last), `toPointAndPassWithContinuityCurvature` on all 12 in
  between. `waypointHeadingAngleEnable` is `1` only on waypoint 0 and 13,
  `0` on all of the rest. Both generalize cleanly from the 3-waypoint
  sample.
- **`actionGroupId` is reused, not globally unique**: waypoint 0 has
  groups `1` (its `gimbalRotate`) and `2` (its `gimbalEvenlyRotate`);
  every one of waypoints 1-12 has exactly one group, and *all twelve use
  `actionGroupId=2`* again. This overturns the earlier "uniqueness
  unclear" note below — group IDs plainly repeat across waypoints and
  seem to identify a *role* (`1` = the initial gimbal-rotate step, `2` =
  a per-transition gimbal-evenly-rotate step) rather than being a unique
  instance ID. Waypoint 13 has no action group at all.
- **`actionId` is a single global counter across the whole mission,
  incrementing once per individual `<wpml:action>` regardless of which
  group it's in**: 1, 2 (waypoint 0's two actions), then 3, 4, 5, ... 14
  (one per waypoint 1 through 12), then nothing for waypoint 13 (it has
  no actions to number). No resets, no gaps except where a waypoint has
  zero actions.
- This also resolves the "out of numeric order" oddity noted in the
  3-waypoint sample (actionIds 1, 2, 4, 3): that mission's middle
  waypoint (id 4) and last waypoint (id 3) simply reflect the same
  global counter *combined with* the last waypoint's action having been
  added to the mission before the middle waypoint's, not a bug or a
  meaningful ordering signal.

## Confirmed: camera/recording actions (4th sample)

`examples/original_dji_mission_14wp_with_camera_actions.kmz` is the
14-waypoint loop, re-edited to add camera actions. This finally answers
the open question above:

- **`takePhoto`**: a single-point action (its `actionGroup`'s
  `actionGroupStartIndex == actionGroupEndIndex`), in its own group with
  `actionGroupId=1` — the same group ID role as `gimbalRotate` at
  waypoint 0 (see below). Params: `payloadPositionIndex` and a **new
  field, `useGlobalPayloadLensIndex`** (value `0` in this single-lens
  Mini 5 Pro sample — presumably relevant for multi-lens aircraft).
- **`startRecord`**: same shape as `takePhoto`, same two params
  (`payloadPositionIndex`, `useGlobalPayloadLensIndex`).
- **`stopRecord`**: same shape, but only `payloadPositionIndex` — no
  `useGlobalPayloadLensIndex` (makes sense: stopping doesn't need to
  select a lens).
- All three use `actionTriggerType=reachPoint` — the same trigger type as
  every other action seen so far. No interval- or distance-based trigger
  has been observed yet, so **continuous photo capture during a mapping
  run (the classic photogrammetry "every N meters" behavior) is still
  unconfirmed** — everything seen so far is a one-shot trigger at a
  specific waypoint.
- **`actionGroupId` role, refined**: it's not "gimbal vs. camera" as
  first guessed — it's "single-point trigger" (id `1`: `gimbalRotate`,
  `takePhoto`, `startRecord`, `stopRecord` all use it, whichever waypoint
  they're on) vs. "spans-two-waypoints transition" (id `2`:
  `gimbalEvenlyRotate`, always `startIndex+1 == endIndex`).
- **Correction to the earlier `actionId` claim**: the 3-waypoint sample's
  "single global gapless counter" was only verified within one static
  snapshot. Comparing this edited file to its pre-edit version
  (`original_dji_mission_14wp_loop.kmz`) shows existing actions' IDs are
  **not stable across edits**: e.g. waypoint 4's `gimbalEvenlyRotate` was
  id `6` before this edit and is id `7` after it, purely because new
  camera actions were inserted elsewhere in the mission. `actionId`
  remains a single global namespace with no duplicates in either
  snapshot, but do not assume a given action keeps its ID once further
  edits happen anywhere else in the mission — and do not assume the
  numbering follows waypoint/document order (it doesn't: e.g. the new
  `takePhoto` at waypoint 5 got id `6`, lower than waypoint 4's
  transition action at id `7`, despite waypoint 4 coming first in the
  file).

## Confirmed: first/last-waypoint markers are recomputed, not fixed (5th sample)

`examples/original_dji_mission_15wp_with_camera_actions.kmz` takes the
4th sample and appends a brand-new waypoint 14 at a new location, plus
adds a second `takePhoto` at waypoint 1 (with a small position/speed edit
alongside it) and changes waypoint 12's speed. Diffing against the 4th
sample:

- **Former waypoint 13** (previously the route's last waypoint: `turnMode
  = toPointAndStopWithContinuityCurvature`, `headingAngleEnable = 1`, one
  action group) **reverted to a normal middle waypoint**: `turnMode`
  became `toPointAndPassWithContinuityCurvature`, `headingAngleEnable`
  became `0`, and it **gained a new `gimbalEvenlyRotate` transition
  action group** (`actionGroupId=2`) it didn't have before — because it
  now needs to transition onward to the new waypoint 14. Its existing
  `stopRecord` action group (`actionGroupId=1`) was untouched.
- **New waypoint 14** is the new last waypoint: `turnMode = ...Stop...`,
  `headingAngleEnable = 1`, no action groups — exactly the pattern the
  *original* last waypoint had before this edit.
- This **confirms the first/last-waypoint markers found in the earlier
  samples are recomputed by DJI Fly on every save based on current route
  position**, not a fixed attribute attached to a specific waypoint. A
  generator that supports real editing (inserting/appending waypoints)
  must recompute `turnMode`/`headingAngleEnable` for whichever waypoints
  are currently first/last, and must add/remove the transition action
  group accordingly — this is real, confirmed generator logic, not
  speculation, though not yet implemented since Phase 1 has no edit
  workflow built yet.
- A second `takePhoto` coexists fine with the first one, confirming
  multiple photo triggers in one mission are unremarkable. It was added
  to a waypoint (1) that previously had no single-point action group,
  alongside a small coordinate shift and a speed change (2.5 → 15.0 m/s)
  — consistent with the earlier finding that editing one waypoint doesn't
  disturb others. Waypoint 12's speed also changed (2.5 → 15.0 m/s) with
  no other edit to it, reinforcing `waypointSpeed` as independently
  per-waypoint editable (still "likely", not yet isolated by its own
  single-field diff — see below).
- `actionId` renumbering happened again here too, consistent with the
  correction above.

## Confirmed: compound action groups & independent speed fields (6th sample)

`examples/original_dji_mission_20wp_multi_photo.kmz`: a 20-waypoint route
with 8 `takePhoto` actions scattered across it.

- **A single-point `actionGroupId=1` group can hold more than one
  action**: waypoint 0's group 1 has *both* `takePhoto` and
  `gimbalRotate` (in that order), not just one. So "single-point trigger
  group" means "one or more actions executed together at this point," not
  strictly one.
- **`waypointSpeed` and `globalTransitionalSpeed` are independent**: every
  waypoint in this route uses `waypointSpeed=1.4`, while
  `missionConfig.globalTransitionalSpeed` stayed `2.5` (its usual value
  in every sample so far). Confirms these are two separate speed knobs —
  presumably per-wayline speed vs. the speed used for
  non-wayline/transitional flight (e.g. flying to the first waypoint).
- Still **only `reachPoint` triggers** — 27 action triggers in this file,
  all `reachPoint`. Discrete point-triggered photos (as many as needed,
  scattered anywhere along a route) is therefore a confirmed, viable
  fallback for Phase 2 even if an interval/distance trigger is never
  found: a lawnmower-grid mission could in principle be generated as one
  `takePhoto` action per grid waypoint rather than needing a continuous
  trigger mode. Whether DJI Fly's own mapping mode actually does that or
  uses something else is still unconfirmed.

## Confirmed via diff (second sample)

`examples/original_dji_mission_wp2_edited.kmz` is the same mission as the
base sample, with waypoint index 2's height edited from 50 m to 201 m in
DJI Fly and re-saved. Diffing the two parsed missions
(`tests/test_diff_findings.py` encodes this as a regression test):

- **Only waypoint 2 changed** — `executeHeight` (50 → 201) and its
  coordinates shifted slightly (likely an incidental drag alongside the
  height edit, not proof coordinates alone are independently editable,
  but proof editing them doesn't break anything else). Waypoints 0 and 1
  are byte-for-byte identical across both files, action groups and
  `actionId`s included.
- **`wpml:missionConfig` is completely unchanged**, including `droneInfo` —
  confirms mission-level config and per-waypoint content are edited
  independently.
- **`createTime`/`updateTime` both changed** on the re-export (different
  millisecond timestamps) — these are refreshed by DJI Fly on every
  save, not stable mission identity. A generator that later supports real
  edits should set `update_time` to the current time on export while
  preserving the original `create_time`, mirroring this; not done yet
  since Phase 1 has no edit workflow built yet, only identity round-trip.
- **`distance`/`duration` stayed `0`** in both files despite the edit —
  confirms these aren't recomputed by whatever last touched the file, so
  the generator doesn't need to compute them either (at least not to stay
  consistent with what DJI Fly itself produces here).
- **`actionId` numbering was untouched** by an edit to the waypoint that
  owns one of the actions (`stopRecord`, `actionId=3`) — the ID scheme
  isn't renumbered by unrelated edits.

This confirms `executeHeight` is safely, independently per-waypoint
editable. It does **not** yet isolate a coordinates-only edit, and it's
still only one aircraft/app version combination.

## Editable vs do-not-modify

**Confirmed editable:** `executeHeight` (per waypoint, diff-confirmed via
2nd sample). `takePhoto`/`startRecord`/`stopRecord` actions can be added
to any waypoint independently (4th/5th samples). Waypoints can be
appended, which correctly recomputes first/last-waypoint markers on the
next save (5th sample) — confirmed as an *output* behavior of DJI Fly;
our own generator doesn't implement waypoint insertion yet (Phase 2).

**Likely editable, not yet isolated by a single-field diff:**
`waypointSpeed` (changed twice across samples, always alongside other
edits, never in isolation), coordinates, `waypointHeadingParam`,
`waypointTurnParam`, gimbal-related actions, `autoFlightSpeed`,
`finishAction`, `flyToWaylineMode`, `exitOnRCLost`/`executeRCLostAction`.
Confirm each with its own single-field-changed sample before the UI marks
it "safe to edit" per brief §11/§15.

**Do not modify without further evidence:**
`droneInfo` (aircraft identity — changing this on a Mini-5-Pro-only tool
makes no sense anyway), `author` (metadata, not flight data), the WPML
namespace/version string. `actionId` and `actionGroupId`: understood well
enough to *generate* correctly for a newly-built mission (`actionGroupId`
1 = single-point trigger, 2 = transition; `actionId` a single global,
no-duplicates counter), but **do not assume actionId is stable across
edits** (confirmed false — see "Confirmed: camera/recording actions") or
that it follows waypoint/document order (also confirmed false). A
generator that edits an *existing* real mission should preserve the
original file's IDs verbatim for anything it doesn't touch, and mint new
IDs by taking `max(existing) + 1` for new actions — simple and always
valid, even though it won't match DJI Fly's own (still not fully
understood) renumbering behavior exactly.

**Refreshed on every export, not user-editable content:** `createTime`
(set once, preserve), `updateTime` (bump on every save/export).

**Dynamically recomputed on every save, not fixed per-waypoint:**
`waypointTurnMode` and `waypointHeadingAngleEnable`'s "first/last
waypoint" values, and whether a waypoint has a transition
(`gimbalEvenlyRotate`) action group at all — see "Confirmed: first/last
waypoint markers" above. A generator must compute these from the
waypoint's current position in the route, never copy them from a
previous version of the same waypoint.

## Next steps to de-risk further

1. ~~Get a second real export...~~ **Done** — see "Confirmed via diff"
   above. Still worth getting a sample that changes *only* coordinates
   (no height change) to isolate that field cleanly, and one that changes
   a mission-level field (e.g. `finishAction`) rather than a per-waypoint
   one.
2. ~~Get a real DJI-Fly export with camera actions...~~ **Done** — see
   "Confirmed: camera/recording actions" above. **Still the main gap**: a
   real DJI-Fly-generated **mapping** mission (grid/lawnmower pattern,
   many waypoints) to inform Phase 2 (`mission/mapping.py`), and
   specifically whether photogrammetry-style continuous capture uses an
   interval/distance trigger rather than the one-shot `reachPoint`
   trigger seen in every sample so far.
3. Manually re-import the round-trip-regenerated file
   (`mission.generator.export_mission` output, unchanged from parse) into
   DJI Fly and confirm it's accepted and flies identically to the
   original, per `docs/BUILD_SPEC.md` sec. 7. The automated test in
   `tests/test_generator.py` only proves structural/semantic equivalence
   after parsing — it cannot prove DJI Fly itself accepts the file.
