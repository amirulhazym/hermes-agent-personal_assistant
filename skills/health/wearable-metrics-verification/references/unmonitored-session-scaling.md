# Unmonitored Session Scaling — Worked Run (2026-11-10)

Session where the owner did the same indoor bike but **wore no tracker**, so the number had to be
modeled from his own last measured session. Kept here because the arithmetic, the cue choice and
the deficit hand-off are all reusable.

## Inputs

| Item | Value | Source |
|---|---|---|
| Today's session | indoor cycling, Brand Zero bike, 70 min, ended ~18:48 | owner report, no device |
| Anchor session | 2026-11-08, 76.15 min, device 481 kcal, avg HR 131 | Redmi Watch 5 Active |
| Weight | 62.8 kg (2026-11-02) | IPR clinical vitals slip (`weight_history`) |
| Owner self-report | "intensity sama lebih kurang dgn 8/11… peluh banyak awal then tak sangat, nafas controllable, boleh nyanyi santai² sikit²" | chat |

`profile.latest_weight_kg` read `62.0` while `weight_history` read `62.8` — history wins; summary
field was corrected to 62.8 with a note recording why.

## Step 1 — anchor rate

```
481 / 76.15            = 6.316 kcal/min (gross)
implied gross MET      = 6.316 * 60 / 62.8 = 6.03
```

Device total is treated as **gross** (see the skill's Test 2).

## Step 2 — scale, then bound

| MET | gross @ 70 min | net (minus 1.09 kcal/min × 70 = 76) |
|---|---|---|
| 5.0 | 366 | 290 |
| 5.5 | 403 | 327 |
| 6.0 (= anchor) | 440 | 363 |

Plain scaling gave 442 gross / 366 net. The talk test (can sing → below ventilatory threshold)
overrode the anchor's implied 6.0 MET, so **327 net** was used, band 290–366, and the reply said
why plus offered to re-raise to 363 if the effort felt harder.

## Step 3 — deficit hand-off

```
BMR      = 10*62.8 + 6.25*157 - 5*27 + 5 = 1,479
TDEE     = 1,479 * 1.20                 = 1,775
+ cycling net 327                       = 2,102 burn
intake   = 424 (284 logged + 2 eggs projected for sahur)
deficit  = 1,678   band 1,641–1,714
conservative (no cycling added, PAL 1.175, intake 424) = 1,314
```

Always hand over **both** the with-workout and conservative-deficit figures — the earlier 11-08
record had quietly omitted the session from TDEE, so stating both keeps the comparison honest.

## Notes that mattered

- `resting_kcal` subtraction is not optional: 76 kcal here, ~17% of the naive figure.
- Owner's sweat narrative was reported as ambiguous (acclimatisation vs lower effort), not resolved.
- Protein coverage was flagged alongside the deficit (34.8 g = 0.55 g/kg on Dexamethasone 5 mg) —
a big deficit plus low protein is the finding, not the calorie number alone.
