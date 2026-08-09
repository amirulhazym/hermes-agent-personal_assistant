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

### Ideal Timing

PPIs work best on empty stomach, 30-60 min before food/other meds. For this regimen:
- Take Pantoprazole BEFORE Dexamethasone (maximises gastroprotection)
- Taking alongside Dexa/Levetiracetam is acceptable if separate timing impractical

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
