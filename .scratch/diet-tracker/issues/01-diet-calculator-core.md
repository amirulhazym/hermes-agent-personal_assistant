# Ticket 01: Core Diet Data Parser and Calculator Logic

## Description
Implement the calculation and data parsing layer for `diet_report.py`. It must load `~/.hermes/diet-log.json`, handle missing dates gracefully, calculate total calories, macro sums (protein, carbs, fat), BMR/active burn totals, net deficit, and fasting hours.

## Acceptance Criteria
- [ ] Loads valid day entry from specified or current date.
- [ ] Returns default/empty schema if date not found without throwing unhandled exceptions.
- [ ] Accurately computes intake sum and net deficit.
- [ ] Unit tests pass under `tests/diet/test_diet_report.py`.

## Blocked by: None
