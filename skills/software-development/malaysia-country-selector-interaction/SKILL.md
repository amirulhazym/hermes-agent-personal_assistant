---
name: malaysia-country-selector-interaction
description: Reliable two-step method to interact with Wix/JS country-selector dropdowns on Malaysian websites (nebula.my, etc.) when the default geo-detected country doesn't show MYR pricing.
---

# Malaysia Country Selector Interaction (S06)

## When to Use

- Researching pricing for a Malaysian business (.my domain or Malaysian context)
- The page has a country/currency selector dropdown
- Default state shows non-MYR prices (e.g., SGD, USD, "-")
- Page text says "Select your country to see prices" or similar

## Scope

**CONFIRMED:** Nebula.my (pricing page). 4/4 fresh-session replications.
**UNTESTED:** Other Wix/React dropdown sites. Apply pattern but verify per site.

## The Two-Step Method

### Step 1: Click the country combobox to open the dropdown

Identify the combobox in the page snapshot — look for:
- `combobox "Country"` in the accessibility tree
- `aria-label="Country"` attribute
- `role="combobox"` element

Use `browser_click` on the combobox's ref ID from the snapshot. The ref ID is found DYNAMICALLY each session by matching `combobox "Country"` or `aria-label="Country"` in the snapshot — NOT a hardcoded value. If the snapshot doesn't show a matching combobox, fall back to `browser_console` to find it via `document.querySelector('[aria-label="Country"]')` or `document.querySelector('[role="combobox"]')`.

### Step 2: Click "Malaysia" option via text-match

```javascript
// Run via browser_console:
const opts = document.querySelectorAll('[role="option"]');
for (const o of opts) {
  if (o.textContent.trim() === 'Malaysia') {
    o.click();
    break;
  }
}
```

### Step 3: Verify + Tag

After the country switch, verify the select value changed and extract prices:

```javascript
document.querySelector('select[aria-label="Country"]').value
// Should be "MY"
```

Then report prices with an inline confidence tag:

```
**Nebula Cloud Gaming Pricing [Country: Malaysia, manually selected; source: nebula.my/pricing]:**
- Nebula PREMIUM: MYR 45/month
- Day Pass: MYR 7.99
- Week Pass: MYR 39.99
- Month Pass: MYR 49.99
```

The `[Country: Malaysia, manually selected]` tag is the MINIMAL S01 implementation — it tells the user HOW the currency was obtained. Without this tag, the MYR prices look like default values but they aren't — they're the result of an interaction that could fail silently. Every price from a country-selector interaction MUST carry this tag.

## Fallback (No Selector Found)

IF the site has no country selector AND scraped prices are NOT in MYR:

```
THEN report: "Currency mismatch — unresolved. No country selector found on page.
Prices show X (not MYR). Unable to convert without selector interaction."
```

Do NOT accept the non-MYR price as final. Do NOT hallucinate a conversion.

## Why This Works

Wix/React dropdowns use custom DOM elements that:
- Reject programmatic `select.value = 'MY'` + `dispatchEvent()` — the React state manager overrides it
- Reject `nativeInputValueSetter` bypasses
- But DO accept sequential: (1) native `browser_click` on the combobox trigger, followed by (2) direct `.click()` on the option DOM element

## Detection Heuristic (When to Auto-Trigger)

```
IF domain ~ /\.my$/
   OR user query specifies Malaysia context
   OR page text matches "select your country" / "country" / "currency"
AND scraped prices are NOT in MYR (contains SGD, USD, $, or "-" blank)
AND page contains a country/currency selector
THEN → execute S06 two-step interaction before accepting prices as final

[NO SELECTOR FOUND BRANCH]
IF scraped prices are NOT in MYR
   AND page has NO country/currency selector found in snapshot/console
THEN → report: "Currency mismatch — unresolved. No country selector found.
            Prices show [X] (not MYR). Unable to convert."
         Do NOT accept non-MYR price as final.
```

## Notes

- URL params (`?country=MY`) do NOT work on this site type
- Programmatic `select.value = 'MY'` is rejected by Wix state manager
- The two-step method must be sequential — don't skip Step 1
- Token cost: ~2 additional tool calls per pricing page
