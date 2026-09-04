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
  mission: 14 waypoints in a freeform loop (not a mapping grid — no
  `startRecord`/`takePhoto` actions anywhere). Useful for confirming
  which per-sample patterns above generalize beyond 3 waypoints.

Three samples, still all plain waypoint/gimbal missions — no mapping-grid
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
recording was presumably started manually in DJI Fly rather than via a
mission action, or a start action exists under a mechanism not
represented in this file. **Still an open question** — the 14-waypoint
sample (below) has no camera actions at all either, so neither sample
resolves how a real mapping mission expresses photo/video triggers.

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

**Confirmed editable:** `executeHeight` (per waypoint, diff-confirmed
above).

**Likely editable, not yet isolated by a diff:** `waypointSpeed`,
coordinates, `waypointHeadingParam`, `waypointTurnParam`, gimbal-related
actions, `autoFlightSpeed`, `finishAction`, `flyToWaylineMode`,
`exitOnRCLost`/`executeRCLostAction`. Confirm each with its own
single-field-changed sample before the UI marks it "safe to edit" per
brief §11/§15.

**Do not modify without further evidence:**
`droneInfo` (aircraft identity — changing this on a Mini-5-Pro-only tool
makes no sense anyway), `author` (metadata, not flight data), the WPML
namespace/version string. `actionId` (confirmed: a single global,
gapless-except-for-actionless-waypoints counter across the whole mission
— see "Confirmed at n=14") and `actionGroupId` (confirmed: reused by role,
not unique — same caveat) are understood well enough to *generate*
correctly for a newly-built mission, but a generator that edits an
*existing* real mission should still preserve the original file's IDs
verbatim rather than renumbering, since it's not yet confirmed DJI Fly
tolerates a renumbered scheme on re-import.

**Refreshed on every export, not user-editable content:** `createTime`
(set once, preserve), `updateTime` (bump on every save/export).

## Next steps to de-risk further

1. ~~Get a second real export...~~ **Done** — see "Confirmed via diff"
   above. Still worth getting a sample that changes *only* coordinates
   (no height change) to isolate that field cleanly, and one that changes
   a mission-level field (e.g. `finishAction`) rather than a per-waypoint
   one.
2. **Still the main gap**: a real DJI-Fly-generated **mapping** mission
   (grid/lawnmower pattern, many waypoints, `startRecord`/`takePhoto`
   actions) to inform Phase 2 (`mission/mapping.py`). All three samples
   so far are plain waypoint routes (freeform or a short line), not a
   mapping grid, and none has a photo/video action anywhere — how DJI Fly
   expresses "take a photo/start recording at this waypoint" is still
   completely unconfirmed.
3. Manually re-import the round-trip-regenerated file
   (`mission.generator.export_mission` output, unchanged from parse) into
   DJI Fly and confirm it's accepted and flies identically to the
   original, per `docs/BUILD_SPEC.md` sec. 7. The automated test in
   `tests/test_generator.py` only proves structural/semantic equivalence
   after parsing — it cannot prove DJI Fly itself accepts the file.
