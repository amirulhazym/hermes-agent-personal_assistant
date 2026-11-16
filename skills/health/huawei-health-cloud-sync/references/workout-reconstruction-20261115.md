# Workout reconstruction — 2026-11-15 investigation log

Account: MY HUAWEI ID · Watch Fit 4 Pro (HarmonyOS 6.1.0.117 SP20C00M05patch01) ·
Honor 600 Pro 5G · cloud host `sportdata-dra.things.dbankcloud.com`.
Session: indoor cycling finished ~19:00; first question was "why is the workout missing?".

## What each endpoint actually returned (day 20261115)

| Probe | Result |
|---|---|
| `getSportsStat` (with and without `device_code=<deviceCode>`) | **1 row only**, `sportType: 0`, `calorie: 431549` (431.5 kcal), `duration: 102`, `totalMidHighIntensity: 114` |
| `getSportsDimenStat` (`sports_daily`) | 2 rows: `sportType 2` (3 min, 4.5 kcal), `sportType 5` (99 min, 78.4 kcal) → sum 82.9 kcal, i.e. **348.6 kcal unattributed** |
| `getSportsDataByTime`, types `(1,2,3,4,6,7,8,9,10,13,14)` | 3 records, all `sportType 2`, 1 minute each |
| `dataSource` 0 / 1 / 2 / 999 on the same call | empty in all four |
| epoch-**ms** window instead of `YYYYMMDD` | `resultCode 1001` (endpoint wants day ints) |
| guessed paths `getSportRecord`, `getWorkoutRecord`, `getSportRecords`, `getWorkoutData`, `getSportStatDetail` | `404 {"message":"Not Found"}` |
| `getSyncVersions` (documented in `READ_PATHS`, no wrapper) | endpoint exists (`1001`), rejects every body tried: `{startTime,endTime}`, `+dataSource`, string dates, `{versions: []}` |

Conclusion at that point looked like "workout never uploaded". It was wrong — the search had only covered
`/dataQuery/sport/*` and `getHealthStat`.

## What `getHealthData` held

| type | verified content |
|---|---|
| 12 `EXERCISE_INTENSITY` | 114 minute-samples for the day; blocks `00:03–00:33` (24 samples) and `17:18–18:48` (89 samples) |
| 7 `DATA_POINT_DYNAMIC_HEARTRATE` | 618 samples/day, ~10-min cadence normally, **1-min inside the workout**; 92 samples inside the block → avg 109.4, max 129, min 56 |
| 8 `WEIGHT_BODYFAT_BROAD` | `{"age":<n>,"bodyWeight":<kg>,"gender":<0|1>,"height":<cm>}` on `deviceCode <id>` |
| 16 `BLOOD_OXYGEN_SATURATION` | 8 daytime samples, `avgSaturation` values averaging **96.9 %** (first sample 99.0 %) |

`getHealthStat.heartRateBasic.maxHeartRate` said **123**; the type-7 series said **129**. The stat endpoint samples
routine minutes, so the true workout peak only exists in the series.

## Reconstructed workout (delivered payload)

```
17:18–18:49 · 89 min · avg 109.4 bpm · max 129 · min 56 · 93 HR samples
workout_kcal_gap = 349.9 kcal   (431.5 − 78.4 − 4.5, recomputed at 21:16)
body_weight_kg   = 59.0
spo2_pct         = 96.9   (mean of 8 samples)
```

Second block `00:03–00:34` (24 min, avg 107.5, max 123) was reported as *unidentified*, not labelled a workout.

## Cross-AI claims that were checked (not accepted)

| Claim | Verdict |
|---|---|
| Workout calories = total − walk − climb (348.6 kcal) | **true** |
| Type 12 + type 7 reconstruct duration and HR | **true** (avg 109.9 vs measured 109.4, max 129 exact) |
| `getSportsStat` returns one row per sport type | **false** — one row, `sportType 0` — so the ID cannot be discovered that way |
| Indoor cycling uses sportType `265`/`137` | **untestable** — server rejects those IDs with `1001` |
| SpO2 = 99.0 % | **misleading** — single sample; mean of 8 is 96.9 % |
| `getSportsDataByTime` stores only GPS/steps sample points | plausible (consistent with the empty result) but **unproven** |

## Lesson

Before saying a metric does not exist: (1) enumerate the series endpoint's type IDs, (2) check whether the
daily aggregate contains an unattributed remainder, (3) only then call it a vendor-side gap. The gap between
`total` and the per-activity breakdown is the cheapest tell that a missing record is hiding somewhere.
