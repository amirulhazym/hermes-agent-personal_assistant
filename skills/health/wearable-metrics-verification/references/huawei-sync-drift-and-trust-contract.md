# Huawei sync drift → trust contract (2026-11-16)

Owner verdict that started it: *"Apa yg kau mengarut? Banyak mistake tu"*, after three consecutive
answers quoted three different calorie totals for the same indoor-cycling session.

## What actually happened

| read | route | active kcal | steps |
|---|---|---|---|
| 19:05:49 | canonical `sync_huawei.py` (cron-shaped run) | 367.3 | 1,359 |
| 19:07–19:11 | ad-hoc `python3 - <<EOF` probes against the cloud | 375.0 | 1,560 |
| 20:13:54 | canonical `sync_huawei.py` after fixes | **380.8** | 1,671 |

The app's own Active calories for that session: **325**. Raw subtraction `total − walk − climb`
gave 268.6 (walk 111.1 booked against a stationary session); the capped pool gave **322.2**.

Two separate defects, one impression of fabrication:

1. **Answering from the probe, not the persisted sync.** The numbers were each true at read time;
   presenting a moving figure as the answer is what he reads as invention.
2. **Quoting a day-level pool as a session measurement**, with no MODALITY provenance — the cloud
   had no `/sport/` record at all (`sports_detail` sportTypes 1–10,13,14 → only auto walk/climb;
   11,12,15+ rejected `1001 parameter invalid`). "Indoor bike" was prose, not telemetry.

## Contract now enforced in code (`hermes-huawei-sync`)

```
python3 sync_huawei.py                                  # today -> daily + latest.json
python3 sync_huawei.py --date 20261114                  # historical -> daily only
python3 sync_huawei.py --finalize-yesterday             # re-close yesterday (09:30 cron does this)
python3 sync_huawei.py --annotate 2026-11-16 17:33 "Indoor cycle"
```

Output additions (schema 1.1.0):

- `sync_settling` / `sync_settling_reason` — true when a `type=12` block ended < 30 min ago.
- `workout_active_pool` — `total_active_kcal`, `raw_walk_kcal`, `climb_kcal`, `max_step_kcal`,
  `effective_walk_kcal`, `workout_active_kcal`, `walk_capped`.
- per workout: `active_kcal`, `estimated_gross_kcal` (= active + minutes × 1449/1440),
  `modality`, `modality_source` (`user_confirmed` | `reconstructed_intensity_hr`).

Verified run 2026-11-16 20:13 MYT: 380.8 kcal / 1,671 steps, pool 322.2, gross 392.6,
`walk_capped: true`, TDEE 1829.8, RSS 30,320 KB. Backfills 14 Nov (176.7 / 1,677) and
15 Nov (439.4 / 2,696, pool 351.3) also PASS the schema gate.

## Rules for the next session

1. Run the canonical sync **before** answering any live health number; quote `fetched_at`.
2. If you probe live anyway, say "probe, not the persisted file" and never let a second probe
   silently replace the first number in a later message.
3. Treat a task-shaped question ("what did you ask me to check") as an attribution question first —
   automated reports deliver asks too; read `~/.hermes/cron/output/<job_id>/` before answering.
4. "Banyak mistake" without specifics → stop re-deriving. Ask for one value off his screen
   (kcal or duration) and lock to it.
