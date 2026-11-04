# Ticket 01: Dynamic BMR & TDEE Engine

**Blocked by:** None

## Description
Update `scripts/diet_report.py` to extract `profile.latest_weight_kg` from `diet-log.json` and dynamically calculate:
1. `BMR = round(10 * weight + 6.25 * 168 - 5 * 28 + 5)` (or calibrated baseline ~1,490 kcal for 62.8kg).
2. `Sedentary Maintenance = round(BMR * 1.2)`.
3. `Total Burn (TDEE) = Sedentary Maintenance + Workout Burn`.
4. `Net Deficit = Total Burn - Total Intake`.

## Acceptance Criteria
- For weight = 62.8 kg, BMR is ~1,490 – 1,510 kcal, Sedentary TDEE is ~1,780 – 1,800 kcal.
- When cycling is detected, workout burn is added cleanly to Sedentary TDEE.
- Tests pass in `tests/diet/test_diet_report.py`.
