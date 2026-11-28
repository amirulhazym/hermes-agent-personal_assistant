# Plan — diet deficit integrity (2026-11-28)

Spec: `.scratch/diet-deficit-integrity-20261128/spec.md`
Tickets: `.scratch/diet-deficit-integrity-20261128/issues/01..05`

Owner-locked values (2026-11-28): target deficit 1100 kcal/day,
est_loss_per_week_kg 1.0, no clamp, no intake floor in arithmetic,
protein floor 1.2 g/kg + optimum 1.6 g/kg, weight always with measured_date.

## Task 1 — capture live drift (ticket 01)
1. Write `tests/diet/test_diet_report_drift.py` asserting BMR(59.0) == 1441 and
   band resolution for 3 schema shapes. Run -> FAIL (SSOT lacks the functions).
2. Apply the live hunks to `scripts/diet_report.py`. Run -> PASS.

## Task 2 — profile reconcile (ticket 02)
1. Backup diet-log.json, write the two fields, read back.
2. Add consistency assertion test on a synthetic profile. Run -> PASS.

## Task 3 — weight provenance (ticket 03)
1. Failing test: render_weight returns date in parens.
2. Implement helper, swap all call sites. Run -> PASS.

## Task 4 — protein dual floor (ticket 04)
1. Failing tests: 67.3 -> "BELUM capai (gap 3.5 g)", 71.0 -> reached.
2. Implement threshold wording. Run -> PASS.

## Task 5 — advisory only (ticket 05)
1. Failing test: deficit(1657.2, 66.0) == 1591.2 and != 750.
2. Add warning text, assert arithmetic untouched. Run -> PASS.

## Task 6 — regression + live render
1. `pytest tests/diet -q` all green.
2. Render 2026-11-28 in compact + eod, diff against expected fixture.

## Task 7 — publication (hermes-git-pr-flow)
guard secret-scan, pii-review, manifest recompute/validate, contract tests,
feat/ branch, PR, CI poll, squash merge, branch delete, main sync.
