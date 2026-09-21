# PPI Interactions with TB Regimen + Steroids

## Context

User on TB Meningitis treatment: Akurit-4 (Rifampin/Isoniazid/Pyrazinamide/Ethambutol), Dexamethasone (14mg TDS), Levetiracetam. Asked about adding Pantoprazole (a PPI) for gastric protection.

## Findings

### Pantoprazole + Dexamethasone ✅ SAFE — Expected Combination

Dexamethasone (high-dose steroid) increases gastric acid secretion and risk of peptic ulcers. PPIs are routinely co-prescribed as gastroprotection. This is standard clinical practice — NOT an interaction risk.

### Pantoprazole + Akurit-4 Components ✅ LIKELY SAFE

- **Rifampin:** Strong CYP3A4/CYP2C19 inducer — can theoretically reduce pantoprazole plasma levels. But PPIs work primarily via LOCAL effect on gastric pH (acid suppression), which is not dependent on systemic plasma levels. Clinical significance of this pharmacokinetic interaction is minimal. PPIs are commonly used in TB treatment without issue.
- **Isoniazid:** Potential reduced absorption if gastric pH elevated — but clinical significance is low at standard PPI doses when taken >=1h apart.
- **Pyrazinamide / Ethambutol:** No significant interaction.

**Timing note:** User took Akurit-4 ~1 hour before asking about Pantoprazole. By then, Akurit-4 absorption is mostly complete, so zero overlap concern.

### Pantoprazole + Levetiracetam ✅ SAFE — No interaction

Levetiracetam is not pH-dependent for absorption and not metabolized by CYP pathways. No interaction mechanism exists.

### Ideal Morning Timing & Spacing Sequence (Updated 2026-09)

Current regimen uses **Akurit-2** (Rifampicin + Isoniazid) + **Pyridoxine** (Akurit-4 ended July 2026).
When taking PRN Pantoprazole in the morning alongside Slot A and Slot B:

1. **Mechanism vs Antacid Distinction:**
   - Pantoprazole is NOT a physical coating agent (like antacid/sucralfate/Gaviscon) that lines the stomach immediately.
   - It is an enteric-coated prodrug absorbed in the small intestine into the systemic circulation, where it irreversibly binds and inactivates active parietal cell H+/K+-ATPase (proton pumps).
   - Because it targets active proton pumps, taking it 30–60 minutes before food ensures peak plasma concentration coincides with food-triggered acid secretion.

2. **Slot A (Akurit-2 + Pyridoxine):**
   - Must be on empty stomach (stomach acid and food delay/reduce rifampin absorption).
   - Best taken early morning (e.g. 04:15 – 06:00).

3. **Pantoprazole (PRN 40mg) Flexible Timing:**
   - Do NOT rigidly force a late clock time (e.g. insisting on 07:00–07:30 AM if the user woke early and finished Slot A by 04:15).
   - Physiological requirement:
     - At least **1–2 hours after Slot A** (so Akurit absorption is complete on an empty stomach).
     - **30–60 minutes before breakfast / food** (so the drug is in the bloodstream when food stimulates proton pumps).
   - Example: If Slot A is at 04:15 AM, Pantoprazole can be taken anytime from ~05:45–06:00 AM onwards, followed by food/Slot B 30–60 minutes later.

4. **Breakfast / Lapik Perut & Slot B (Dexamethasone + Levetiracetam):**
   - Must be taken **with or immediately after food** to minimize steroid-induced gastric ulceration/gastritis (the primary reason for pantoprazole gastroprotection).
   - Ensure the gap from Slot A to Slot B is at least 1 hour (rule_001) and subsequent slot constraints (e.g. 6h gap from B to BD Slot F at 14:00/14:30) are preserved.

### Long-Term Note

PPI + Rifampin long-term (>3 months) can theoretically reduce B12/calcium/magnesium absorption over time. User already takes Calcium + Calcitriol (Slot C) which covers the calcium concern.

## Research Method Used (when medical sites blocked)

1. Wikipedia API for basic interaction profile: `curl -s "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext&titles=Pantoprazole&format=json"`
2. Extracted "Interactions" section text via Python script
3. Wikipedia listed: ampicillin esters, ketoconazole, atazanavir, iron salts, amphetamine, mycophenolate mofetil, bisphosphonates, fluconazole, clopidogrel, methotrexate — NONE are in user's regimen
4. Cross-referenced known pharmacology (CYP induction by Rifampin vs PPI action mechanism)
5. Major medical databases (Drugs.com, NCBI/PubMed) were blocked — flagged as data gap
6. Used clinical pharmacology reasoning for the specific pairwise combinations not covered by Wikipedia

## Verdict

Pantoprazole is safe to take before/with Dexamethasone + Levetiracetam, and has no clinically significant interaction with Akurit-4 components when taken >=1 hour apart.

## Source Gaps

- No primary source confirmed the rifampin-pantoprazole interaction specifically (Drugs.com blocked, NCBI blocked)
- Clinical reasoning is based on known CYP induction mechanism + PPI local action pharmacology
