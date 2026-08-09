---
name: medication-safety-research
description: >-
  Structured research protocol for answering medication/drug safety questions.
  When user asks "is it safe to take X and Y together" or "can I take this with food",
  follow this protocol instead of relying on training data alone.
trigger:
  - User asks about drug safety, interactions, or medication compatibility
  - User asks "is it safe to take X with Y"
  - User asks about medication timing relative to food
  - User asks "take now vs wait" / "should I take it now or later" / "which is better, now or at X time"
  - User asks about delaying a dose or taking it at an irregular hour due to disrupted sleep/wake schedule
  - User asks "confirm safe for my body"
  - User says a medication has run out, is running low, or they're short on supply
  - User asks "what can I do" about a medication supply gap before their appointment
  - User reports unexplained side effects, body changes, or symptoms from medication (weight gain, moon face, acne, mood changes, muscle weakness)
  - User asks "is this normal" about a medication side effect
  - User says "I don't understand why this is happening to my body"
  - User asks for analysis of medication side effects beyond simple interactions
---

# Medication Safety Research Protocol

## Phase 1: Scope Clarification (MOST CRITICAL — avoid the mistake below)

**Don't do this** — adding dimensions the user didn't ask about or assuming worst-case scenarios:
> "You want to take B + C together? That means double dexamethasone!"
> → User didn't mention doubling anything. They asked about taking C-slot meds alongside B-slot meds at breakfast.

**Do this instead:**
1. Restate back exactly what drugs and what timing the user described
2. Confirm: is this a one-off or a new routine?
3. Ask ONLY about what they asked — don't add hypothetical complications
4. If MULTIPLE interpretations exist, list the ones you see and ask which one

**Formula:** "Let me confirm I understand: you want to take [drug A], [drug B], [drug C] together at [time/meal] — is that right?"

---

### 1.1 Act first when the question is checkable

If the user says they want us to check the medication/timing question, perform the source and regimen check immediately. Do not reflexively reply with “ask your doctor/pharmacist” before doing the available verification yourself. Escalate to the clinician only when the exact drug, dose, prescription instruction, contraindication, or red-flag symptoms cannot be resolved—or when the verified sources conflict with the prescriber’s instructions.

If the dose has already been taken, provide immediate harm-reduction guidance while checking: do not repeat or compensate the dose; apply the verified food/timing advice as soon as practical; and state the specific red flags requiring urgent care. Keep the unresolved part explicit instead of making a blanket “safe” claim.

## Phase 2: Source Verification (NEVER rely on training data for medical claims)

For each drug in the combination, check its interaction profile from authoritative online sources.

**Primary sources (most accessible):**
- **RxList** — `https://www.rxlist.com/<drugname>-drug.htm#interactions`
  Look for section: "What Drugs, Substances, or Supplements Interact with [Drug]?"
  Also check the formal "Drug Interactions" section in the prescribing info.
- **DailyMed** — `https://dailymed.nlm.nih.gov/dailymed/` — official FDA labels
  Search, then navigate to section 7 (DRUG INTERACTIONS)
- **MedlinePlus** — `https://medlineplus.gov/druginfo/` — consumer drug info
- **Singapore HealthHub** — `https://www.healthhub.sg/medication-devices-and-treatment/medications/<drugname>` — government health authority, regionally relevant for SE Asia/Malaysia users. Each medication page has sections: Uses, Administration (timing relative to food), Missed Dose, Precautions, Side Effects. Reviewed June 2025. Accessible without bot detection.

**Secondary (if primary blocked or insufficient):**
- Drugs.com interaction checker (may block bots)
- WebMD drug interaction checker (may block bots)

**What to check for each drug:**
1. Does the OTHER drug appear in its interaction list? (e.g., does Levetiracetam list Dexamethasone?)
2. Does the interaction list include the drug class? (e.g., "antacids" for Calcium Carbonate)
3. Are there food interactions? (e.g., "take with food", "empty stomach", "avoid grapefruit")
4. Any supplement/vitamin interactions listed?

---

## Phase 3: Cross-Check Known Pharmacology

For each pairwise combination that doesn't appear in interaction lists:
- Check if one drug affects the OTHER's metabolism pathway (CYP450, transport proteins, etc.)
- Check if they compete for absorption (chelation, pH effects)
- Check if they have additive side effects (both cause sedation, both affect QTc, etc.)

**If you can't verify a specific pairwise interaction from a source, state it:**
> "I checked [Source A] and [Source B] for Drug X — [Other Drug] does NOT appear in its interaction list. However, I couldn't find a specific study on this exact combination."

---

## Phase 4: Present Findings

**Structure:**
1. **Verdict** (safe / likely safe / uncertain / not safe)
2. **Evidence table** — each drug, what interactions are listed, whether the other drug appears
3. **Mechanism reasoning** — why it's safe (or why to be cautious)
4. **Source citations** — specific URLs for each source checked
5. **Remaining uncertainty** — any gaps you couldn't verify

**Example verdict format:**
```
Drug X interactions listed on [Source]: [list of drugs]
  → Drug Y: NOT listed ✅

Drug Y interactions listed on [Source]: [list of drugs]
  → Drug X: NOT listed ✅
```

---

## Phase 5: Supply Gap / Stock-Out Assessment

When the user says a medication has run out before their next appointment:

0. **CHECK EXISTING REGIMEN FIRST — before researching external options.**
   - Does the user already take another product that contains the same active ingredient?
   - Example: User's Pyridoxine ran out, but they already have Swisse B-Complex in Slot C (contains 41.1mg B6). That's an immediate bridge — no pharmacy trip needed.
   - This step is easy to miss because the instinct is to search external sources. But the answer might already be in their medicine cabinet.
   - Only proceed to external options (OTC purchase, clinic call) if the existing regimen doesn't cover it.

1. **Determine severity of gap**
   - How many days of supply are missed? (1 day vs 1 week matters)
   - Is this a "must not miss" drug (antibiotics for active infection, immunosuppressants, anti-epileptics) vs a supportive/side-effect-prevention drug (vitamins, supplements)?
   - Check the drug's half-life: drugs with long half-lives build up steady state — missing 1-2 doses is less critical than drugs with short half-lives that clear fast.

2. **Assess medical risk of gap**
   - Research the specific risk of missing this drug for the gap duration
   - For TB drugs (INH/RIF/PZA/EMB): missing doses of the CORE antibiotics is serious (risk of resistance), but missing supportive Pyridoxine for 1-2 days is low risk — peripheral neuropathy is a cumulative effect over weeks/months, not acute from 1 missed dose. Source: MSD Manual Professional Edition (TB treatment section): "Pyridoxine 25 to 50 mg orally once/day can prevent this complication" but neuropathy onset is gradual.
   - For Dexamethasone: abrupt cessation after long-term use can cause adrenal insufficiency — even 1 missed dose matters. Gap assessment differs by drug class.
   - For Levetiracetam: missing doses can trigger breakthrough seizures. Gap is higher risk.

3. **Research OTC/Practical bridging options**
   - Is this drug available over the counter? (Vitamins, minerals, some analgesics)
   - What strength/formulation is available OTC vs prescribed?
   - Can you advise a safe temporary substitute? (e.g., Vitamin B6 25mg OTC as temporary Pyridoxine replacement)
   - If OTC not available: what are the alternatives? (call clinic/hospital for emergency supply, advance appointment, nearby government clinic for bridging prescription)
   - Consider Sunday/holiday constraints — not all pharmacies are open, not all clinics operate

4. **Connect to appointment timing**
   - When is the next appointment? Can it be moved earlier?
   - Does the gap bridge safely to the appointment date?
   - Can they get a same-day refill at the appointment?

5. **Log the supply gap in medication status**
   - Note the unavailable drug in med-status as pending (not "taken")
   - If user opts for OTC substitute: log the substitute intake separately if needed
   - If user skips: mark as pending with note "out of stock — awaiting refill"

**Example output structure:**
```
Risk Assessment: [drug] — [gap duration]
  Risk Level: Low / Moderate / High / Depends
  Evidence: [source — specific quote or finding]
  Why: [1-2 sentence clinical rationale]

Options:
  1. [Option A] — [availability + cost + effort] — [recommendation]
  2. [Option B] — [availability + cost + effort]
  3. [Option C] — [availability + cost + effort]

Recommendation: [clear practical advice]
```

**Pitfall — don't over-medicalize common supplements:** Pyridoxine, Vitamin D, Calcium, B-Complex are widely available OTC. The user can buy them at any pharmacy without prescription. Don't imply they need a doctor's visit for these. Conversely, for controlled drugs or antibiotics, DON'T recommend OTC substitutes — flag that they need a prescription and help them find the fastest legitimate path.

**Pitfall — half-life ≠ clinical significance:** A drug with a 12-hour half-life doesn't mean a missed dose is dangerous if the drug has a wide therapeutic margin (e.g., Pyridoxine). And a drug with a 24-hour half-life can be dangerous to miss if withdrawal effects are severe (e.g., high-dose corticosteroids). Look at the clinical consequences of missed doses, not just the pharmacokinetics.

## Phase 5b: Dose Timing Decision — "Take Now vs Wait"

Trigger: user asks whether to take a dose now (at an irregular hour) or wait, typically due to disrupted sleep/wake schedule (insomnia, late nights, unpredictable wake times).

### 5b.1 Establish the drug's administration rules

Research the drug's official administration guidelines from authoritative sources:

1. **Empty stomach requirement** — Does food affect absorption? By how much? (e.g., rifampicin absorption drops ~30% with food)
2. **Consistency requirement** — How critical is same-time-daily dosing?
3. **Missed dose protocol** — What does the official leaflet say? (Usually: "take as soon as you remember, next dose at usual time, don't double up")
4. **Half-life** — How long does the drug stay in therapeutic range?

**Extraction technique for HealthHub SG pages:**
HealthHub pages use anchor-based navigation tabs (Uses / Administration / Missed Dose / etc.). To extract specific sections without scrolling blindly:
```javascript
// In browser_console, extract the Administration section:
document.body.innerText.substring(
  document.body.innerText.indexOf('How should I take'),
  document.body.innerText.indexOf('How should I take') + 2000
)
// Extract the Missed Dose section:
let idx = document.body.innerText.indexOf('What should I do if I forget');
if(idx < 0) idx = document.body.innerText.indexOf('If you forget to take');
let result = document.body.innerText.substring(idx, idx + 2000);
```

### 5b.2 Build a decision table

Compare the two options (take now vs wait) across these factors:

| Factor | Take now (irregular hour) | Wait until normal time |
|--------|---------------------------|----------------------|
| Empty stomach | ✅/❌ depends on when last ate | ❌ Risk of food interference if breakfast comes first |
| Absorption | Optimal if empty stomach | Risk of reduced absorption with food |
| Schedule consistency | Shifts timing by X hours | Closer to normal timing |
| Risk of forgetting | ✅ Awake now, can take | ❌ May oversleep / wake late |
| Next dose gap | ~X hours (acceptable?) | ~X hours (acceptable?) |

### 5b.3 Considerations specific to the drug class

- **TB drugs (rifampicin/isoniazid/pyrazinamide/ethambutol):** Empty stomach is critical. A one-off 2-3 hour shift is clinically insignificant for treatment outcomes. What matters is long-term adherence. Official guidance: "If you forget, take as soon as you remember. Don't double up."
- **Corticosteroids (dexamethasone):** Timing consistency matters more due to HPA axis suppression. A single shift of a few hours is acceptable but should be avoided habitually. Abrupt cessation is dangerous — don't miss completely.
- **Anti-epileptics (levetiracetam):** Maintaining therapeutic levels is important to prevent breakthrough seizures. Missed/late doses are higher risk than for TB drugs.
- **PPIs (pantoprazole):** Best taken 30-60 min before breakfast. Taking at odd hours reduces efficacy for that day but is not dangerous.

### 5b.4 Present verdict clearly

Structure:
1. **Verdict** — take now / wait / depends on [condition]
2. **Evidence** — quoted guidelines from sources
3. **Decision table** — concise factors comparison
4. **Conditions** — any caveats (e.g., "take now only if 2+ hours since last ate")
5. **Next dose guidance** — what to do tomorrow (e.g., "next dose at usual time, ~26h gap is fine")

**Key principle:** The risk from a few hours' shift in a single dose is almost always lower than the risk of skipping the dose entirely. Default to recommending the dose be taken when the user can do it correctly (empty stomach, awake, able to track it) rather than waiting for an ideal schedule that may not materialize.

**Data Gap:** If the official source doesn't explicitly address dosing at irregular hours, state the gap rather than inferring. The "take as soon as you remember" rule from missed-dose protocols is the closest applicable guideline for most cases.

## Phase 6: Complex Side Effect / Iatrogenic Condition Analysis

Trigger: user reports unexplained symptoms, side effects, or body changes from their medication (weight gain, moon face, acne, muscle weakness, mood changes) and asks "what is happening to me" or "is this normal."

### 6.1 Establish the iatrogenic framework

1. Identify the drug class(es) the user is on (e.g., glucocorticoids, anti-epileptics, TB therapy)
2. Research the KNOWN side-effect syndrome for that drug class from medical literature
3. Cross-reference the user's specific complaints against the known syndrome
4. Quote directly from sources to confirm — don't rely on training data alone

**Research method when medical sites are blocked:** Use Wikipedia API via curl — it reliably returns clean text and is rarely blocked:

```bash
curl -sL "https://en.wikipedia.org/w/api.php?action=query&prop=extracts&explaintext=true&titles=ArticleTitle&format=json"
```

Then pipe through python3 to extract and find relevant sections:
```bash
... | python3 -c "import sys,json; d=json.load(sys.stdin); pages=d['query']['pages']; [print(v['extract'][:2000]) for k,v in pages.items() if 'extract' in v]"
```

See `references/wikipedia-api-medical-research.md` for detailed usage patterns (extracting specific sections, searching within articles, chaining multiple lookups).

### 6.2 Explain the mechanism — address the "contradiction"

When the user says something feels contradictory ("dose turun tapi berat naik"):
- Trace the actual physiology: cumulative exposure > current dose at high-dose ranges
- Explain WHY it's not contradictory — insulin resistance lag, water retention, appetite cycle
- Use analogies (e.g., "tutup paip sikit tapi air dalam kolam masih naik")
- Acknowledge that their confusion is VALID (the pattern looks counterintuitive) but grounded in real biology

### 6.3 Tiered intervention (most important structure)

Present in THREE tiers:

**Tier 1: High impact, can start TODAY**
- Dietary changes (sodium restriction for water weight, protein for muscle preservation, low GI for insulin resistance)
- Lifestyle adjustments within treatment limits
- Clear, specific, actionable — not generic "eat healthy"

**Tier 2: Medium impact, needs doctor clearance first**
- Exercise / physical activity (ask doctor what's safe for their condition)
- Intermittent fasting or other metabolic interventions
- Supplement considerations (if evidence-based)

**Tier 3: Medical decisions — simplified doctor questions**
- The user may be overwhelmed or embarrassed to ask complex medical questions
- Break down the questions into SIMPLE, short versions they can actually ask
- Example: Instead of "Is there a role for metformin in steroid-induced insulin resistance?" → ask "Boleh check gula dalam darah?"
- Provide 3-4 short questions max

### 6.4 Realistic timeline

Set expectations honestly:
- What CAN improve at current dose (water weight, stopping acceleration)
- What WON'T meaningfully improve until dose drops below threshold (fat loss, full metabolic recovery)
- Give phase-by-phase projections tied to their specific taper plan
- Never promise quick fix — at supraphysiological steroid doses, metabolism is pharmacologically overridden

### 6.5 Emotional handling — critical for this class

When the user is in distress (use of 😭, "berat untuk terima", self-blame):
1. **First validate** — acknowledge their distress directly. Don't jump to analysis without this step.
2. **Then fact** — "This is not abnormal, not your fault, not contradictory — here is the evidence."
3. **Then act** — tiered plan they can start immediately.
4. **Then hope** — grounded in evidence, not false optimism. "Once taper reaches X threshold, real reversal begins."

**Pitfall — don't overpromise:** "We can definitely get your weight down" while on 14mg+ dexa is misleading. Say: "We can stop the acceleration and reduce water weight now. Real fat loss starts when dose drops below ~7.5mg equivalent."

---

## Pitfalls

- **Scope creep**: User asks about taking meds at breakfast. Don't analyse their entire daily regimen unless they ask. Answer what was asked.
- **Training data overconfidence**: "I know from pharmacology that..." — don't. Check actual sources. Medical knowledge in training data may be outdated or incomplete.
- **Blocked sites**: Many medical sites (Drugs.com, Medscape, WebMD interaction checker) detect bots. Accept the block, try an alternative source (Wikipedia API via curl often works), and explicitly flag the gap. Don't fabricate what you would have found.
- **Single source confidence**: One source saying "no interaction" is suggestive but not definitive. Flag it as such.
- **Layout complexity**: RxList pages are long. Use browser_console to search for specific section headings (e.g., `document.body.innerText.indexOf('What Drugs, Substances')`) to jump directly to the interaction section instead of scrolling blindly.
- **Complex questions user can't ask**: Don't give the user a list of medical jargon questions they'd be too embarrassed or overwhelmed to ask the doctor. Always provide SIMPLIFIED versions they can actually verbalize.
- **Emotion before analysis**: When user is in visible distress (😭, "sedih", "berat nak terima"), do NOT start with clinical analysis. Validate first, THEN fact.
- **False hope on steroid side effects**: Weight gain from high-dose glucocorticoids doesn't reverse until dose drops below Cushingoid threshold (~7.5mg prednisolone equivalent). Be honest about this timeline — don't say "exercise more and eat less" as if that solves a pharmacological override.
- **Attribution error**: Never make the user feel their weight gain is a failure of willpower or discipline. The mechanism is pharmacological (insulin resistance, leptin resistance, metabolic shift) — state this clearly.

---

## References

- `references/interaction-source-guide.md` — which URLs to use for each drug and how to navigate each source's layout.
- `references/wikipedia-api-medical-research.md` — how to use the Wikipedia API via curl for medical literature when other medical sites are blocked.
- `references/supply-gap-pyridoxine-inh.md` — case study: Pyridoxine supply gap bridging.
- `references/ppi-tb-steroid-interactions.md` — Pantoprazole interactions with TB regimen (Akurit-4) + Dexamethasone + Levetiracetam. Covers ideal timing, rifampin CYP induction vs PPI local action, and research method used when major medical sites were blocked.
- `references/akurit4-timing-empty-stomach.md` — Akurit-4 (rifampicin/isoniazid) timing and empty stomach guidelines from Singapore HealthHub. Decision framework for "take now vs wait" scenarios when user is awake at irregular hours.
- `references/dexamethasone-interaction-profile.md` — Complete interaction profile from FDA label: what IS and is NOT listed (calcium/antacid absent). Verified 2026-07-12. Use when researching dexamethasone interactions.
