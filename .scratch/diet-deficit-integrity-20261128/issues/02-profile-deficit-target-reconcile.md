# 02 — Reconcile profile deficit target

Blocked by: none

## Why
`daily_deficit_target_kcal = 1400` and `est_loss_per_week_kg = 0.45` contradict
each other (1400/day = 1.27 kg/wk; 0.45 kg/wk = 495 kcal/day). Owner decision
2026-11-28: target 1,100 kcal/day, `est_loss_per_week_kg = 1.0`.

## Slice
1. Backup `~/.hermes/diet-log.json` to `diet-log.json.bak-<ts>`.
2. Set `daily_deficit_target_kcal = 1100`, `est_loss_per_week_kg = 1.0`.
3. Read back and print both fields + derived kg/wk (1100*7/7700 = 1.0).
4. Add consistency check to report script: if |target_kcal - est_loss*7700/7|
   > 25, print a profile-inconsistency warning.

## Done
- Read-back shows 1100 / 1.0, warning absent.
- Private runtime state only; no secrets or medical values in Git.
