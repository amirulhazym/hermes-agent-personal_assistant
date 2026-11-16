# Watch cross-check — worked examples

Source sessions: 2026-11-08 (indoor cycling) and 2026-11-09 (badminton).
Weight used: 62 kg. `kcal_per_MET_min = 3.5 * 62 / 200 = 1.085`.

---

## A. Indoor cycling, 2026-11-08

**Device data:** Redmi Watch 5 Active, "cycling indoor", 01:16:09 = 75.93 min,
481 kcal, HR panel showed 131 BPM (after stop; not confirmed average vs final).
Zero-brand bike: no power meter, no GPS.

**Arithmetic**

| quantity | value |
|---|---|
| resting over session (1 MET) | 82 kcal |
| MET 3.5 | gross 288 / net 206 |
| MET 4.25 | gross 350 / net 268 |
| MET 5.0 | gross 412 / net 330 |
| MET 5.5 | gross 454 / net 372 |
| implied MET from 481 | 5.8 |

**Reasoning:** HR 131 = 68-69% of HRmax (Tanaka 189 / 220-age 193). That maps to
roughly MET 5.5-6, i.e. gross 454-496. The watch's 481 sits inside that band → accept
**as gross/total**. If 481 had been *active*, gross would be 563 → implied MET 6.8-7.2,
~15-20% optimistic for that HR.

**Outcome:** active burn locked at ~398 kcal (481 - 82), band 398-481 until the user
confirmed. Earlier MET-3.5-5 band (206-330) was produced WITHOUT HR data and was marked
**superseded**, not averaged in.

**Rejected cross-check:** Keytel men's equation at HR 131, 62 kg, 27 y →
`-55.0969 + 0.6309*131 + 0.1988*62 + 0.2017*27 = 45.3 kJ/min` = 10.83 kcal/min =
**825 kcal**. Known submaximal overestimate → discarded, never averaged.

---

## B. Badminton, 2026-11-09

**Device data:** 09:16 start, 01:31:34 = 91.57 min (5494 s), **713 kcal**,
avg HR 131, max 162, min 98. Zones: light 06:09, intensive 45:24, aerobic 36:58,
anaerobic 02:55, VO2max 00:00.

**Arithmetic**

| MILESTONE | value |
|---|---|
| resting over session | 99 kcal |
| MET 6.0 | gross 596 / net 497 |
| MET 7.0 | gross 695 / net 596 |
| MET 7.2 | gross 715 / net 616 |
| implied MET from 713 | 7.18 |
| if 713 were ACTIVE | gross 812 → implied MET 8.18 |

**Reasoning:** Compendium band for badminton (secondary source, NOT verified from the
primary table): social singles/doubles 5.5, competitive 7.0, competitive match play 9.0.
713 → implied MET 7.18 = squarely "competitive". Zone distribution (45 min intensive,
max HR 162 = 84-86% HRmax) supports genuine interval intensity, so the figure is
consistent rather than inflated. The active-calorie interpretation (MET 8.2) is
implausible for recreational play → rejected.

**Outcome:** 713 accepted as **total**; active burn locked at ~614 kcal. TDEE that day
= 1,692-1,765 base + 614 = 2,306-2,379.

---

## C. Corrections received from the owner

1. **No 1:1 cross-sport comparison.** An early reply computed "badminton burns 23% more
   per minute than cycling at the same average HR" and was rejected: "jangan samakan or
   compare dengan indoor cycling aku, sebab both definitely different sports … Satu sukan
   statik yang aku consistently done non-stop … satu lagi sukan yang ada masa intensity
   rendah ada masa tinggi." The note was rewritten as "Tiada perbandingan 1:1 dengan sukan
   lain."
2. **Comparison only for differentials** or for raising a research-grounded question —
   never to imply two sports should yield the same number.
3. **Don't quote an app default as a goal.** "Apa maksud 'target' kau dekat sini? … there
   is no need to 'reach' any target" — the `target_daily_intake_kcal: 1400` in the diet
   profile is metadata, not his objective. For him, a larger deficit is acceptable; the
   binding constraint is protein, not reaching an intake floor.
4. **Portion policy is MAX-BOUND.** When a portion is uncertain, take the UPPER end of the
   range so intake is biased high and deficit is biased low. Report the main figure with
   that ceiling, and give the "defisit sebenar" estimate separately with its justification.
