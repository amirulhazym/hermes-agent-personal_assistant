# Taper Data Validation (2026-07-05)

Validation script for `~/.hermes/dexa_taper.json` to catch arithmetic mismatches
before they propagate to patient dosing.

## Why This Exists

The 2026-07-05 adversarial review found 10 out of 21 phases in `dexa_taper.json`
had `total_mg` that didn't match the sum of `dose_morning + dose_midday + dose_afternoon`:

- **Phase 1** (6/5–19/5, TDS): declared 18mg, sum = 6+6+0 = 12mg → 33% underdose
- **Phase 2** (20/5–2/6, TDS): declared 17mg, sum = 5+6+0 = 11mg → 35% underdose
- **Phase 3** (3/6–16/6, TDS): declared 16mg, sum = 6+6+0 = 12mg → 25% underdose
- **Phase 10** (9/9–22/9, BD): declared 10mg, sum = 6+0+0 = 6mg → 40% underdose
- **Phase 11** (23/9–6/10, BD): declared 9mg, sum = 5+0+0 = 5mg → 44% underdose
- **Phase 12** (7/10–20/10, BD): declared 8mg, sum = 4+0+0 = 4mg → 50% underdose
- **Phase 13** (21/10–3/11, BD): declared 7mg, sum = 4+0+0 = 4mg → 43% underdose
- **Phase 14** (4/11–17/11, BD): declared 6mg, sum = 3+0+0 = 3mg → 50% underdose
- **Phase 15** (18/11–1/12, BD): declared 5mg, sum = 3+0+0 = 3mg → 40% underdose
- **Phase 16** (2/12–15/12, BD): declared 4mg, sum = 2+0+0 = 2mg → 50% underdose

Historical phases (1-9) are less urgent — patient has already lived through them.
Future phases (10-16, all BD) are CRITICAL — patient will be UNDERDOSED.

## The Script

Run this before adding/editing any phase:

```bash
cd /home/ubuntu/.hermes/scripts && python3 -c "
import json
taper = json.load(open('/home/ubuntu/.hermes/dexa_taper.json'))
errors = 0
for p in taper['phases']:
    pid = p['id']
    freq = p.get('freq')
    tot = p.get('total_mg', 0)
    m = p.get('dose_morning', 0)
    mid = p.get('dose_midday', 0)
    aft = p.get('dose_afternoon', 0) or p.get('dose_evening', 0)
    actual = m + mid + aft
    if actual != tot:
        print(f'❌ Phase {pid} ({p.get(\"start\")}–{p.get(\"end\")}): {freq} declared={tot}mg, sum={m}+{mid}+{aft}={actual}mg ({tot - actual:+d}mg gap)')
        errors += 1
    else:
        print(f'✅ Phase {pid} ({p.get(\"start\")}–{p.get(\"end\")}): {freq} {tot}mg = {m}+{mid}+{aft} OK')
print()
print(f'TOTAL ERRORS: {errors}')
exit(0 if errors == 0 else 1)
"
```

Exit code 0 = clean, 1 = at least one phase has arithmetic mismatch.

## Expected Output (After Fix)

```
✅ Phase 1: TDS 18mg = 6+6+6 OK
✅ Phase 2: TDS 17mg = 5+6+6 OK
...
✅ Phase 10: BD 10mg = 6+4 OK (after adding dose_2pm or fixing total_mg)
```

## What Each Mismatch Means

| Pattern | Likely Fix |
|---------|------------|
| TDS with `dose_afternoon=0` and total > morning+midday | Set `dose_afternoon` to make sum match total (probably 6/6/6 pattern in phase 1, 5/6/6 in phase 2) |
| BD with `dose_afternoon=0` and total > morning | Add `dose_2pm` field (or fix total_mg to match morning only if 2pm dose is genuinely not taken) |

## The BD 2pm Dose Problem (Structural)

The med-schedule.json has slots A-E only. The med-tracker system has no slot
for a 2pm BD dose. So `dose_afternoon` (which maps to slot D = 4pm) is wrong
for BD phases. Two options:

### Option A: Add `dose_2pm` field (recommended)

```json
{
  "id": 10,
  "freq": "BD",
  "dose_morning": 6,
  "dose_2pm": 4,
  "dose_afternoon": 0,
  "times": ["08:00", "14:00"],
  "total_mg": 10
}
```

Then update `chain_calc.py`, `taper_alert.py`, `chain_calc.py --taper-display`
to read `dose_2pm` for BD phases. Add `active_slots_by_freq["BD_2pm"]` logic.

### Option B: Just fix `total_mg` to match morning-only

Acknowledges that the 2pm dose is tracked externally (manual log, separate
medication card). Set total_mg = dose_morning + 0 (or = 2 × morning if 2pm = morning).

**WARNING: Option B lies about the actual dose patient takes. Only use if IPR
prescriber confirms the BD 2pm dose is genuinely 0mg, not "missing from JSON".**

## History of Mismatches

| Date | Found by | Method |
|------|----------|--------|
| 2026-07-05 | Adversarial review of med system v3 | Live `python3 -c` against chain_calc.py |

This is the first time the taper data has been independently validated
end-to-end. The data was generated in a single session (2026-07-05) from IPR
schedule images. No arithmetic check was run at the time.
