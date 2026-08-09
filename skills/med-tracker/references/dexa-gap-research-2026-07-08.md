# Dexamethasone Dose-Gap Research — 2026-07-08

## Context
User (TB meningitis taper, TDS phase: Dexa 8am/12pm/4pm + Letram 8am/8pm) asked whether
compressing B→C gap from 4h to ~3h17m (C at 1pm instead of 1:43pm) is acceptable, because
he doesn't want the last dose to finish "petang sangat" (too late afternoon).

## Calculation
- B taken 09:43, C at 13:00 → gap = 197 min = 3h17m (target 240 min, shortfall 43 min)
- Propagated: D at 17:00 (4h from C), E at 21:43 (B+12h, independent)

## Verified Sources (accessible, read live 2026-07-08)
1. **Medical News Today** — medicalnewstoday.com/articles/drugs-dexamethasone-oral-tablet
   - "Typical dosage: 0.75 to 9 mg every day... taken in three or four divided doses"
   - "If you miss a dose, wait and take the next dose as planned. Do not double your dose."
   - NO exact hour-gap mandate for divided doses.
2. **MedlinePlus (NIH)** — medlineplus.gov/druginfo/meds/a682792.html
   - "Your doctor will prescribe a dosing schedule that is best for you."
   - "Take dexamethasone exactly as directed."
   - Missed-dose: if once daily, take as soon as remembered unless near next dose.
3. **Wikipedia** — en.wikipedia.org/wiki/Dexamethasone
   - Pharmacokinetics: biological half-life 36–54h, plasma half-life 4–5h.
   - Implication: between-dose level variance is minor for a 40-min gap slip.

## Blocked Sources (bot detection — NOT broken, just agent-blocked)
- drugs.com/dosage/dexamethasone.html → "Access Denied - not available from your region"
- mayoclinic.org/drugs-supplements/dexamethasone-oral-route → "Access Denied"
- reference.medscape.com/drug/dexamethasone-342472 → Cloudflare "Just a moment..."
- ncbi.nlm.nih.gov/books/NBK531462 → "WWW Error Blocked Diagnostic" (abuse block)
- healthhub.sg/medications/dexamethasone* → 404 (wrong URL path)

## Conclusion for user
- 3h17m gap is pharmacologically tolerable (long half-life, no hard interval in public refs).
- BUT tapering protocol (4h TDS) is doc-prescribed → must confirm with doctor before habit.
- Always propagate gap compression forward to downstream slots; never leave stale times.

## Lesson for agent
- Patient-info sites describe GENERAL practice, not the user's specific taper.
- "Divided doses" ≠ "exact 4h mandatory". Don't overclaim safety from 1-2 sources.
- Bot-blocked sites are a real constraint for automated research — surface as Data Gap,
  never substitute a guessed value or pretend the source confirmed something.
