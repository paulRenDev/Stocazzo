# WPML findings — DJI Mini 5 Pro + RC 2

Source: `examples/original_dji_mission.kmz`, provided by the user, a real
export for the DJI Mini 5 Pro + RC 2. This is the **only** real sample
analyzed so far (one file, no altered-parameter comparison sample yet) —
treat everything below as confirmed-for-this-one-file, not as a general
DJI spec. Re-run `mission.parser.inspect_kmz` against any new sample
before assuming it generalizes.

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
toggles 1/0/1 across the three waypoints with no other visible effect in
this sample — meaning unconfirmed.

`waypointTurnParam`: waypoint 0 and 2 use
`toPointAndStopWithContinuityCurvature`; waypoint 1 (the middle one) uses
`toPointAndPassWithContinuityCurvature` — consistent with "stop at start
and end, pass through the middle point," a plausible general DJI Fly
pattern but confirmed only for this one route shape.

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
represented in this file. **Open question**, not resolved by this sample.
`actionId` values are globally incrementing across the whole mission
(1, 2, 4, 3 — note 3 and 4 appear out of numeric order relative to
position), not reset per waypoint.

`waypointGimbalHeadingParam` on every waypoint is `pitch=0, yaw=0` —
redundant with the per-waypoint `gimbalRotate`/`gimbalEvenlyRotate`
actions above; relationship between the two not yet understood.

## Editable vs do-not-modify (preliminary — needs the round-trip test to confirm)

This is a **hypothesis**, not yet validated by the single-parameter
round-trip test in `docs/BUILD_SPEC.md` sec. 7 (that needs a second sample:
same mission, one field changed in DJI Fly, re-exported).

**Likely editable** (per-waypoint mission content):
`executeHeight`, `waypointSpeed`, coordinates, `waypointHeadingParam`,
`waypointTurnParam`, gimbal-related actions, `autoFlightSpeed`,
`finishAction`, `flyToWaylineMode`, `exitOnRCLost`/`executeRCLostAction`.

**Do not modify without further evidence:**
`droneInfo` (aircraft identity — changing this on a Mini-5-Pro-only tool
makes no sense anyway), `author`/`createTime` (metadata, not flight
data), the WPML namespace/version string, `actionId` numbering scheme
(unclear whether DJI Fly requires strict monotonic IDs or just uniqueness).

## Next steps to de-risk further

1. Get a second real export: same physical mission, one parameter changed
   in DJI Fly (start with altitude), re-exported. Diff the two files
   field-by-field to confirm which fields actually change and whether
   anything else changes as a side effect.
2. Get a real DJI-Fly-generated **mapping** mission (grid pattern, many
   waypoints, `startRecord`/`takePhoto` actions) to inform Phase 2
   (`mission/mapping.py`) — this sample is a plain 3-point route, not a
   mapping grid.
3. Manually re-import the round-trip-regenerated file
   (`mission.generator.export_mission` output, unchanged from parse) into
   DJI Fly and confirm it's accepted and flies identically to the
   original, per `docs/BUILD_SPEC.md` sec. 7. The automated test in
   `tests/test_generator.py` only proves structural/semantic equivalence
   after parsing — it cannot prove DJI Fly itself accepts the file.
