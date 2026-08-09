# Drug Interaction Source Navigation Guide

Discovered patterns for extracting drug interaction info from common medical sites.

## RxList

**URL pattern:** `https://www.rxlist.com/<drugname>-drug.htm#interactions`

Example: Levetiracetam → `https://www.rxlist.com/keppra-drug.htm#interactions`
Example: Dexamethasone → `https://www.rxlist.com/decadron-drug.htm`

**Target section:** "What Drugs, Substances, or Supplements Interact with [Drug]?"

**Efficient extraction:** The page is very long. Use browser_console to find the section:
```javascript
let idx = document.body.innerText.indexOf('What Drugs, Substances, or Supplements Interact');
let text = idx > -1 ? document.body.innerText.substring(idx, idx + 1500) : 'not found';
```

**Also check:** The formal "Drug Interactions" subsection may say "No Information Provided" — the consumer-facing section above is usually more useful.

**Status:** RxList generally allows browser access (no Cloudflare blocking observed).

## DailyMed (NIH/FDA Official Labels)

**URL:** `https://dailymed.nlm.nih.gov/dailymed/`

**Workflow:**
1. Search for drug name
2. Click the label result (usually first) — verify it's an oral tablet label, not a combo product or elixir
3. Click "VIEW ALL SECTIONS" to expand the label's table of contents
4. Click the **PRECAUTIONS** section header to expand it — Drug Interactions is a subsection inside PRECAUTIONS
5. If the expanded PRECAUTIONS still doesn't show Drug Interactions text, try clicking the specific "PRECAUTIONS" expandable row (its generic `cursor:pointer` element)
6. Alternative: click "OFFICIAL LABEL (PRINTER FRIENDLY)" for the full raw text label — this renders the complete label in a flat scrollable page without expand/collapse JS

**Critical: The accessibility tree often truncates DailyMed's expandable sections.** After clicking, browser_snapshot may show the same unexpanded state. Use browser_console JavaScript search instead:

```javascript
// Check for specific interaction terms in the full label text
const labelText = document.body.innerText.toLowerCase();
const searchTerms = ['calcium carbonate', 'antacid', 'calcium supplement', 'magnesium'];
searchTerms.filter(term => labelText.includes(term));
// Returns array of terms found — empty means no mention in the label

// Read the Drug Interactions section directly (works on printer-friendly view)
const pos = document.body.innerText.indexOf('Drug Interactions');
document.body.innerText.substring(pos, pos + 3000);
// Dumps the full Drug Interactions text from the label

// Search for any mention of a specific drug pair
const t = document.body.innerText.toLowerCase();
t.includes('drug X') && t.includes('drug Y');
```

**Searching across the full label for interaction terms is more reliable than navigating expandable sections.** The printer-friendly view especially renders all text flat.

**How to open the printer-friendly view:**
- On the label page, find and click the "OFFICIAL LABEL (PRINTER FRIENDLY)" link
- This navigates to a simpler URL with the full raw label text
- Then use browser_console JavaScript to search for "Drug Interactions", "calcium", etc.

**Status:** Accessible to browser tools. DailyMed blocks search crawlers but allows browser access. The JS expand/collapse sections are tough to navigate via accessibility tree — prefer printer-friendly view + console search.

## MedlinePlus

**URL pattern:** `https://medlineplus.gov/druginfo/meds/<code>.html`

**Status:** Accessible. The drug-specific page uses a letter-number code (not drug name) so searching from the homepage is required.

## Sites That Block Bots

These commonly block browser-based access:
- Drugs.com interaction checker (Access Denied)
- Medscape interaction checker (Cloudflare)
- WebMD interaction checker (404 after URL manipulation)
- NCBI/PubMed (Access Denied via automated tooling)

**Fallback strategy when blocked:**
1. Try RxList first (least blocked)
2. Try DailyMed (NIH — generally accessible)
3. If both fail, state the gap clearly
