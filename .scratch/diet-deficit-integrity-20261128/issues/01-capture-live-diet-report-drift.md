# 01 — Capture live diet_report.py drift into SSOT

Blocked by: none

## Why
`~/.hermes/scripts/diet_report.py` (683 lines) diverges from
`scripts/diet_report.py` (617 lines). Live carries owner-visible fixes:
BMR profile 157 cm / 27 y and `_resolved_band_burn` for nested
`workout_met_band`. Deploying SSOT as-is would regress both.

## Slice
1. Diff live vs SSOT; extract only intentional hunks.
2. Apply to SSOT `scripts/diet_report.py`.
3. Add unit tests for BMR at 59.0 kg (= 1441) and for the three historical
   `workout_met_band` shapes.
4. Assert repo/live parity after deploy, not before.

## Done
- `pytest tests/diet/test_diet_report_drift.py` green.
- `diff scripts/diet_report.py ~/.hermes/scripts/diet_report.py` empty after
  manifest deploy.
