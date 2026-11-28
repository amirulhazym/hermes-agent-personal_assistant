# 05 — Advisory warning only; deficit arithmetic untouched

Blocked by: none

## Why
The first proposal added `deficit = min(deficit, 750)` and an intake floor of
BMR. Owner rejected it correctly: that hides the real number. Advisory text is
allowed; arithmetic rewriting is not.

## Slice
1. Add `⚠️` advisory when protein < floor (and when intake < BMR, text only).
2. Hard test: for any (tdee, intake), `reported_deficit == tdee - intake`.
3. Test with the 2026-11-28 fixture: intake 66.0 -> deficit 1591.2, never 750.

## Done
- Anti-clamp test green.
- No code path can mutate a computed deficit value.
