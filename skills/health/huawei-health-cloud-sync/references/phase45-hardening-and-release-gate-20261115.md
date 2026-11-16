# Phase 4.5 hardening + release-gate record (2026-11-15)

Owner-issued hardening pass after Gate 4 closed. All numbers below are from live runs on the VPS.

## Owner-locked decisions

- Workout filter: block **≥ 30 min** AND attributed gap **≥ 100 kcal**; blocks failing either are not workouts
  (00:03–00:34 = awake movement, explicitly excluded by owner).
- Reconstruction runs on **all three** ticks (09:30 / 15:00 / 22:30 MYT), not end-of-day only.
- Weight: today's `type=8` value, else 14-day lookback returning `body_weight_kg` + `measured_date`.
- SpO2: ship `spo2_avg` (mean) **and** `spo2_latest` (last sample).
- Lean schema: no top-level `devices` array in `data/*.json`; validator fails if it returns.
- RSS gate raised 30 000 → **40 000 KB**, with `RSS_KB=` logged every run.
- TDEE formula unchanged: `1449 + max(217.35, device_active_kcal)`, legacy PAL-1.20 kept for 7-day calibration.

## Verification actually observed

```
OK kcal=434.3 steps=2497 stale=62min
RSS_KB=30712                (gate 40000 → PASS)
wrapper stdout = 0 bytes    (silent normal path)
validator → PASS (exit 0)
HAS_DEVICES: False
WORKOUTS_COUNT: 1  → 17:18–18:49 · 89 min · 349.9 kcal · avg 109.4 · max 129 · hr_samples 93
body_weight_kg: 59.0 (measured 20261115)     spo2_avg: 96.9  spo2_latest: 96.0
14-day lookback: body_weight(20261116) → (59.0, '20261115')
```

`workout_excluded_blocks` stays in the payload as a `reason` list so a filtered block is visible, not silent.

## Bugs hit while hardening (both mine)

1. **`UnboundLocalError: annotated`** — `del stat, rows, …, annotated, eligible` ran *before* the return dict
   built `excluded_blocks` from them. Sync exited 3, wrapper alerted "sync gagal". Fix: compute `excluded`
   first, then `del`, then `gc.collect()`.
2. **Validator exit code hidden by a pipe** — `python3 validator.py … | tail` reports `tail`'s status. Check the
   code with the file redirected (`> /tmp/val.txt; echo $?`), not through a pipe.

## Secret/PII gate before staging

- `scripts/guard/secret-scan.sh --staged` → `SECRET-SCAN PASS: scope=staged`.
- The naive `git diff --cached | grep -Ei "(access_token|refresh_token|…)"` matches *field names in vendored
  source* every time — treat those as benign and scan for **values**: token strings, serials, `uniqueId`,
  `devId`, MAC. Device ids (`f2ea16c7…`, `4SPBB2671…`) had to be redacted from the evidence markdown before
  staging; the marketing model code (`VKP-NX9`) is not a serial and was kept.

## Release-approval conflict (repo policy vs plan)

The repository's `AGENTS.md` requires `APPROVE RELEASE <full-sha>` for `main` promotion; the relayed execution
plan asked for `APPROVE PUSH`. Both were surfaced to the owner at the HITL gate rather than silently choosing:
latest explicit owner instruction wins, but the agent must state that the conflict exists and which token it is
honouring. Never commit/tag/push before that reply.
