# Implementation Plan: Diet EOD Report Upgrade

**Date:** 2026-11-03
**Feature:** `diet-report-template-upgrade`

## Tasks
1. **Red Test**:
   - Add unit tests in `tests/diet/test_diet_report.py` testing the new 5 structured blocks and dynamic BMR calculation.
   - Run `pytest tests/diet/test_diet_report.py` -> confirm failure on new assertions.
2. **Green Implementation**:
   - Update `scripts/diet_report.py` with dynamic BMR/TDEE calculation and the revamped `format_eod_report()`.
   - Run `pytest tests/diet/test_diet_report.py` -> confirm 100% green.
3. **Live Verification**:
   - Run `python3 scripts/diet_report.py --date 2026-11-03` to generate real output for Amirulhazym's review.
4. **Publication & Deployment Gate**:
   - Execute secret scan and PII review.
   - Commit, push PR to GitHub SSOT, merge.
   - Deploy to `~/.hermes/scripts/diet_report.py`.
