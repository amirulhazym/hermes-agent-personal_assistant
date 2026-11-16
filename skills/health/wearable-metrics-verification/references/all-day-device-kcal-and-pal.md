# All-day device kcal vs PAL — worked case (2026-11-14)

Raw device report, verbatim: *"kalau ikut jam aku cuma show 88kcal harini, and 1621steps"* —
Huawei Watch Fit 4 Pro, first day of use, no workout that day (lightning, cycling skipped).

## Inputs

| Field | Value | Source |
|---|---|---|
| Weight | 59.8 kg | home scale, single source |
| BMR (Mifflin) | 1449 kcal | 10(59.8) + 6.25(157) - 5(27) + 5 |
| PAL used | 1.2 | existing `deficit_uniform` rule |
| TDEE | 1739 kcal | 1449 × 1.2 |
| Intake | 801.5 kcal | full day, 2 windows |
| Device | 1621 steps / 88 kcal | watch display, unlabelled metric |

## The decision

```
pal_overhead = 1449 * 0.2 = 290 kcal   # already credited by PAL 1.2
290 > 88  ->  device figure is a SUBSET of the PAL allowance
=> add 0 kcal; deficit stays 1739 - 801.5 = 938 kcal
```

Inference for the label: 88 kcal < BMR 1449 kcal, so it cannot be a total-day burn → active-only.
Not verified against the watch's own field name; the reply flagged that caveat and offered correction.

## What was written to `~/.hermes/diet-log.json`

```json
"device_activity": {
  "device": "Huawei Watch Fit 4 Pro",
  "steps": 1621,
  "device_kcal_shown": 88,
  "kcal_type_inferred": "active (88 < BMR 1449, so cannot be whole-day total)",
  "recorded_in_deficit": false,
  "provenance": "single source, not cross-validated"
}
```

## Cross-checks worth reusing

- 1,621 steps ≈ 1.2–1.3 km — a desk day; the correct conclusion is "PAL 1.2 is right", not "lower PAL".
- Deficit target was >1400 kcal. With intake 801.5 and no session, the gap is 462 kcal, which at
  59.8 kg needs ~110 min of MET 5.0 riding (4.19 kcal/min net). Saying "cannot reach target tonight"
  beat rounding the gap away.
