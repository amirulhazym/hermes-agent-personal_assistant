# Phase 5 — attribution fix, CLI modes, settling flag (2026-11-16)

Owner SOP executed `/xcute` after a trust break: three consecutive answers quoted 367.3 → 375.0 →
380.8 kcal for the same indoor-cycling session, the app said 325 active, and "indoor bike" was
presented as sensor data. Owner: *"Apa yg kau mengarut? Banyak mistake tu."*

## Root causes (all confirmed live)

| # | Failure | Cause |
|---|---|---|
| P1 | `data/latest.json` frozen at 19:05:49 (367.3 kcal) while probes returned 375.0 → 380.8 | answering from ad-hoc Python stdout instead of running `sync_huawei.py`; no `--date` historical sync; no previous-day finalisation |
| P2 | Numbers moved between messages | no settling detection for a `type=12` block that ended < 30 min earlier |
| P3 | Workout active under-attributed | `dimenDailyActivity.walkCalories` absorbs stationary cadence: raw `total − walk − climb` = 268.6 vs app's 325 |
| P4 | Modality invented | reconstructed block has no sport label; prose said "indoor bike" |
| P5 | Multi-revision prose | no canonical report contract per turn |

## Fixes shipped

- `workout_reconstructor.workout_active_pool()` — caps walk kcal at `steps × 0.035 × weight/60`
  when an unlogged block exists; returns `walk_capped`, `raw_walk_kcal`, `effective_walk_kcal`,
  `max_step_kcal`, `workout_active_kcal`.
- `estimated_gross_kcal = active_kcal + duration_min × (1449/1440)`.
- `modality` / `modality_source` on every workout; sidecar `data/workout_annotations.json`,
  key `YYYY-MM-DD_HH:MM`, written by `sync_huawei.py --annotate DATE HH:MM "Label"`.
- CLI: `--date YYYYMMDD`, `--finalize-yesterday`, `--annotate`. Historical runs write
  `data/YYYY-MM-DD.json` only and never touch `latest.json`.
- `sync_settling` + `sync_settling_reason` in every payload (last block ended < 30 min ago).
- Wrapper: 09:30 MYT tick runs `--finalize-yesterday` first; failure prints one warning line,
  success stays silent (stdout-is-the-message).
- `schema_validator.py` now fails on missing `estimated_gross_kcal`, invalid `modality_source`,
  `sync_settling` not bool, or a `user_confirmed` label that is still `unclassified_workout`.

## Verified parity (canonical sync, schema 1.1.0)

| Day | active kcal | steps | workout pool | mode | TDEE cand | settling |
|---|---|---|---|---|---|---|
| 14 Nov | 176.7 | 1,677 | 138.7 (no block) | — | 1666.3 | false |
| 15 Nov | 439.4 | 2,696 | 351.3 (89 min, gross 440.9) | unclassified / reconstructed | 1888.4 | false |
| 16 Nov | 380.8 | 1,671 | **322.2** (70 min, gross 392.6) | Indoor cycle / user_confirmed | 1829.8 | false |

16 Nov cap: walk raw 111.1 → 57.5 (`1,671 × 0.035 × 59/60`), climb 1.1 → pool 322.2 vs app 325
= **0.86 %** (raw subtraction would have been 268.6, a 56 kcal / 17 % miss).
RSS on the four runs: 30,320 / 31,420 / 31,672 / 31,036 KB — all under the 40 MB gate.

## Tests

`tests/huawei/test_workout_attribution.py` — 13 pure-function tests: cap formula (real 16 Nov and
15 Nov payloads), uncapped cases, never-negative, blank annotation is not confirmed, block filter
drops single-sample noise. `tests/guard` 127 passed for regression.

## Notes that cost time

- Repo `skills/health/huawei-health-cloud-sync/SKILL.md` was a stale 6-section version; the full
  15 Nov rewrite had never been captured, so the Phase-5 PR carries ~250 lines of documentation
  drift. Disclose that in the receipt instead of pretending the diff is all new work.
- `sports_detail` rejects sport-type batches containing unknown IDs with `1001` — enumerate in
  small accepted sets (`1,2,3,4,6,7,8,9,10,13,14`) or the whole call fails and returns nothing.
- A no-workout day still produces a non-zero pool (14 Nov: 138.7) — the pool exists but no block
  claims it. That is not a bug; do not force a workout entry to consume it.
