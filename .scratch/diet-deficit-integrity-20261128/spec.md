# Spec — Diet deficit integrity (2026-11-28)

## Problem Statement
Four integrity defects produced a diet report the owner could not trust:

1. `diet-log.json` profile holds two mutually exclusive deficit targets:
   `daily_deficit_target_kcal = 1400` (= 1.27 kg/wk) and
   `est_loss_per_week_kg = 0.45` (= 495 kcal/day). A report can cite either.
2. `deficit_uniform` is pure subtraction (`tdee - intake`) with no advisory
   layer, so a day with 66 kcal logged reports a 1,591 kcal deficit and gets
   graded "pass" against a target that is arithmetically impossible on a
   1,657 kcal TDEE day (1400 deficit => 257 kcal intake).
3. Weight is printed without its measurement date. `latest_weight_kg = 59.0`
   comes from a `2026-11-15` type-8 sample (13 days stale at print time), yet
   prose said "berat terkini kekal 59.0 kg".
4. A protein line claimed "mencapai lantai 70.8 g" at 67.3 g (3.5 g short) and
   quoted only the 1.2 g/kg floor while the log already stored 1.6 g/kg.

Additionally the live report script had drifted from SSOT:
`~/.hermes/scripts/diet_report.py` is 683 lines, `scripts/diet_report.py` is
617 lines, and the live copy carries unmanaged fixes (BMR profile corrected to
157 cm / 27 y, `_resolved_band_burn`, nested `workout_met_band` schema).

## Solution
- Reconcile SSOT with the live script first (no loss of the 11 Nov fixes).
- Replace the contradictory profile fields with one consistent pair, in BOTH
  fields (`daily_deficit_target_kcal` and `deficit_target_kcal`).
- Never alter deficit arithmetic. Advisory warnings are additive text only.
- Print both protein floors (1.2 g/kg minimum, 1.6 g/kg optimum) and never
  label a sub-floor day as "reached".
- Every weight print carries `measured_date`.

## User Stories
1. As the owner, I want one deficit target in the profile, so that two
   reports can never grade the same day differently.
2. As the owner, I want the reported deficit to stay `TDEE - intake`, so that
   no clamp can hide what I actually ate.
3. As the owner, I want a warning when protein is under the floor, so that I
   see the gap without the arithmetic being rewritten.
4. As the owner, I want every weight to show its measurement date, so that a
   13-day-old sample is never presented as current.

## Implementation Decisions
- Profile (private runtime state, not public Git):
  `daily_deficit_target_kcal: 1400 -> 1100`,
  `deficit_target_kcal: 1400 -> 1100`,
  `est_loss_per_week_kg: 0.45 -> 1.0` (1100*7/7700 = 1.0 kg/wk, consistent).
- `diet_report.py`: no clamp, no intake floor, no rewrite of `deficit`.
  `reported_deficit(tdee, intake)` is the single formula.
- Advisory line format: `⚠️ Protein X g < lantai 70.8 g`.
- Weight string format: `59.0 kg (timbang 2026-11-15)`; a missing date renders
  `(tarikh tiada — jangan anggap semasa)` instead of a bare number.
- Degenerate deficit ranges collapse to one figure instead of `X hingga X`.
- SSOT sync must preserve the live 11 Nov fixes; deployment via manifest.

## Testing Decisions
- Unit tests: deficit == tdee - intake for synthetic low/high intake days.
- Unit test: 66 kcal day reports 1591.2, NOT 750.
- Unit test: protein 28.55 g renders warning and never "mencapai lantai".
- Unit test: protein 71.0 g renders reached.
- Unit test: weight line contains ISO measured_date; missing date -> explicit
  marker.
- Unit test: inconsistent profile (1400 / 0.45) is flagged, consistent
  (1100 / 1.0) is silent.
- Regression: full `tests/diet` suite, including eod/compact render.

## Out of Scope
- Changing BMR/TDEE formula (7-day lock).
- Any change to `deficit_uniform` computation or `--sync-diet-log`.
- Clamping or falsifying deficit values (explicitly rejected by owner).
- Making `diet_report.py` consume `burn.tdee_kcal` from the Huawei payload
  (separate open item; eod still uses sedentary estimate).
