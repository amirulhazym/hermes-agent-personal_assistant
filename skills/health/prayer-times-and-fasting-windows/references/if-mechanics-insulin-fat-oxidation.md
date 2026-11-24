# IF mechanics: insulin, fat oxidation, autophagy — answer bank (first used 2026-11-23)

Trigger: *"But IF aku harini berfungsi dengan baik atau tak? … How about insulin, and segala proses
fat burning etc regarding of the my actual purposes."* Asked after an accidental break (protein drink at
16.18 h, optimum 17 h). He wants mechanism + verdict, not reassurance.

## Answer shape that worked

1. **Verdict line first**: functional but not optimal; the shortfall is ~0.8 h, and the lever is weekly
   deficit (quote his real 7-day average, tool-computed), not the hour count.
2. Mechanism bullets, each with an evidence label.
3. The real risk of the day (unplanned calories / grazing), not the missed hour.

## Content (label evidence strength in the reply)

- **No cliff at 16/17 h.** Fat oxidation rises gradually as glycogen and insulin fall; by 16 h he is well
  inside the fasting state. 16.2 vs 17.0 h is noise, not a physiological switch. [mechanistic, robust]
- **Fasting does not raise energy expenditure.** 24 h EE is unchanged or slightly lower; IF wins by
  removing eating opportunities and appetite, not by burning faster. Never frame IF as a metabolic boost.
  [robust]
- **Protein calories are not "wasted" but do end the fast.** Whey/soy protein is insulinotropic (leucine),
  glucose response modest, TEF ~20–30%. Effect on the day's fat balance is small; the real consequence is
  that the hours stop counting and the item must be logged. [robust for TEF range]
- **Insulin-sensitivity gains from IF are modest and mostly mediated by weight loss**, not by fast length.
  [moderate]
- **Autophagy/repair claims at 16–18 h are weak in humans** — largely extrapolated from rodent work.
  Tell him plainly not to count it as a purpose. [weak]
- **Steroid confound.** On dexamethasone (OD phase) insulin resistance and appetite are raised by the drug;
  that is a bigger insulin variable than 0.8 h of fasting. Use it as context, not as a reason to change dosing.
- **Accidental break handling.** Log the actual `fasting_hours` (do not round up to the target), keep the
  item in `meal_items`, and state that the next fast anchors to that day's **last** intake, so one early
  break does not compound. Watch the follow-on risk: 22 Nov intake jumped to 1447.5 kcal against a ~857 kcal
  average — an unplanned break that opens a grazing window is the actual deficit threat.

## Do not

- Praise the day or moralise about the missed hour.
- Quote a metabolism/fat-burning percentage without a source; the numbers that matter are his own deficit
  and protein-floor figures, computed from `diet-log.json`.
- Turn the Dexa note into dosing advice.

## Companion data used

22 Nov 2026 at the time of the answer: 7-day deficit avg 1018 kcal (range 736.5–1371.6), intake avg 857 kcal,
fasting avg 18.47 h. Protein floor at 59 kg: 70.8–94.4 g.
