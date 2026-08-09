---
name: malaysia-telco-research
description: "Research current telco info from Malaysian providers (CelcomDigi, Yes, Maxis, U Mobile, Unifi, etc.) — plans, promos, port-in/out processes, coverage. Handles JS-heavy SPA websites and bot-blocked search engines."
version: 1.0.0
author: Jane (MarryJane)
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [telco, malaysia, research, celcomdigi, yes, maxis, umobile, unifi, mnp, port-in, prepaid, postpaid]
    related_skills: [web-research, agent-best-practices]
---

# Malaysian Telco Research

Use this skill when the user asks about **current Malaysian telco information**: plans, promotions, port-in/out (MNP) processes, eSIM conversion, coverage, prices, or any active offering from a Malaysian mobile operator.

Malaysian telco websites are **JS-heavy SPAs** (React/Angular) that resist traditional curl scraping. Search engines (Google, DuckDuckGo, Bing) aggressively bot-block residential IPs, and consumer forums (Lowyat) are the primary secondary source.

## Core methodology

### Step 1 — Go direct, don't search

Do NOT start with search engines (Google/DuckDuckGo/Bing). Residential IPs without proxies are almost always bot-blocked (CAPTCHA or "sorry" page). Instead:

1. **Navigate directly to the official website** of the telco in question
2. Use `browser_navigate` with known landing pages:
   - CelcomDigi: `www.celcomdigi.com/switch` (port-in), `www.celcomdigi.com/prepaid` (prepaid plans)
   - Yes: `www.yes.my/faq` (FAQ), `www.yes.my` (main)
   - Maxis: `www.maxis.com.my`
   - U Mobile: `www.u.com.my`
   - Unifi: `unifi.com.my`
3. If the target URL returns a 404, try the homepage and navigate from there

### Step 2 — Extract text from JS-heavy SPAs

SPA pages often don't render content in the `browser_snapshot` accessibility tree. Instead:

- After `browser_navigate` has loaded the page, use **`browser_console`** with:
  ```
  expression: "document.body.innerText"
  ```
- This extracts ALL visible text rendered by the SPA, bypassing the snapshot's limited tree
- If the page is long, add `.substring(0, 15000)` to get the first portion
- Review the text to find the relevant section, then scroll and re-extract for more

### Step 3 — Look for the right page

Telco sites bury port-in/MNP info on specific pages, not always in FAQ:
- **CelcomDigi**: The port-in process is on the **"Switch to CelcomDigi"** page (`/switch`), not in FAQ or support
- **Yes**: Port-in FAQ is under "Switch to Yes" category in their FAQ knowledgebase
- **General MNP process**: Always see "3 simple steps" style landing pages — these are the source of truth, not outdated forum posts

### Step 4 — Cross-check with forums if needed

If the official site is unclear, use Lowyat.net as secondary source:
- Search: `site:lowyat.net [provider] [topic] 2025` or `site:lowyat.net [provider] [topic] 2026`
- But prefer official site first — forum info can be stale

## Current reference data (2026)

See `references/port-in-procedures.md` for specific MNP/port-in details collected from official sources.

## Pitfalls

- **Don't trust old FAQ articles**: Yes's FAQ knowledgebase has articles from 2022 that look current but may describe outdated processes. Always verify the date/version.
- **Don't cancel old service before porting**: MNP auto-terminates the old line on successful port. Cancelling first breaks the number.
- **Don't assume "Get Help" links work**: CelcomDigi's "GET HELP" menu item leads to a 404 page. Navigate directly to `/switch` or `/prepaid` instead.
- **Don't trust Google previews**: Search result snippets are often cached text from before the SPA migration.
- **Bot blocks are normal**: If search engines block you, it's not a failure — proceed directly to Step 1 (direct navigation). The `browser` tool with local stealth mode works on most SPA sites even when search engines don't.

## Verification

After collecting info, verify key claims by cross-referencing the telco's official page or terms. If a specific step isn't on the official site (e.g. "SMS format to confirm port out"), note the uncertainty explicitly rather than guessing.
