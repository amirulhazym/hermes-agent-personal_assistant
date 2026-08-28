# Fact-Check Accuracy Audit — 2026-07-02

## Context

Multi-phase structured analysis of Hermes agent's fact-check weaknesses, triggered by a
price-research failure (Nebula Cloud Gaming — JS-heavy Wix site, agent returned SGD prices
instead of MYR, used behavioral promises instead of structural fixes).

## 7-Phase Pipeline Used

1. **Parallel Extraction** — 5 responses analysed via `delegate_task` subagents
2. **Cross-Compare Matrix** — 32 solutions mapped across 5 responses, consensus scored
3. **Live Feasibility Test** — `spike` methodology, 5 spikes run against live VPS
4. **Doubt Review** — adversarial subagent cross-examination (pending)
5. **Synthesis + Ranked Solution Stack** (pending)
6. **Pre-Flight Checklist** (pending)
7. **Boss Approval** (pending)

## Phase 2 Consensus Results (8 solutions ≥2/5)

| # | Solution | Category | Consensus |
|---|----------|----------|:---------:|
| D3 | Structured output template | Output Format | 4/5 |
| D1 | Confidence scoring (verified/single_source/unverified) | Output Format | 2.5/5 |
| D2 | Refusal protocol (refuse>guess) | Output Format | 2.5/5 |
| A1 | SearXNG self-hosted | Search Infra | 2/5 |
| B3 | API/Network Interception (XHR capture) | Scraping | 2/5 |
| C1 | Source hierarchy T1-T4 | Verification | 2/5 |
| C6 | Chain of Verification (CoVe) | Verification | 2/5 |
| D4 | Verbatim Grounding (No Quote=No Data) | Output Format | 2/5 |

## Phase 3: Live Feasibility Test Results

### S01: Structured Output + Confidence Scoring (D3+D1+D2+D4) — ✅ VALIDATED

Injection point: `~/.hermes/SOUL.md` (61 lines, 3,672 bytes).

Persona is slot #1 in system prompt, loaded at session creation. To add fact-check
instructions, append to SOUL.md:
- Structured output schema: `{value, source_url, confidence: verified|single_source|unverified}`
- Refusal protocol: "If you cannot find the exact source text for a claim, refuse to state it"
- Verbatim grounding: "Every factual claim must quote the source text that supports it"

Zero infra changes needed. Session-level testing requires `/new` after SOUL.md edit
(rendered system prompt stored in `sessions.system_prompt` column in `state.db`).

### S02: SearXNG Self-Hosted (A1) — ⚠️ PARTIAL

Tested 4 public SearXNG instances from VPS (Tencent Lighthouse, Singapore):
- `searx.be` → 403 Forbidden (OpenResty)
- `search.sapti.me` → 429 Too Many Requests
- `searx.tiekoetter.com` → 429 Too Many Requests
- `search.bus-hit.me` → connection refused

DDG Lite (`lite.duckduckgo.com`) → bot-blocked ("Unfortunately, bots use DuckDuckGo too.")

Self-hosted path: Docker NOT installed on VPS (2 vCPU, 2GB RAM, 18GB/40GB free).
Docker install ≈500MB. SearXNG container ≈200MB. Feasible but needs Docker setup.

Alternative: Direct endpoint calls (used in `malaysia-telco-research` skill — navigate
directly to official sites, extract via `browser_console`).

### S03: Chain of Verification (C6) — ✅ VALIDATED

Two-pass approach via system prompt:
1. Draft answer with claims
2. Generate verification questions for each claim
3. Re-check each claim against sources (web_search/web_extract)
4. Revise answer, dropping or flagging unverifiable claims

Feasible as behavioral pattern in SOUL.md. Risk: guard against infinite verification loop.

### S04: Source Hierarchy (C1) — ✅ VALIDATED

T1-T4 tier rules addable to SOUL.md:
- **T1**: Official primary sources (.gov.my, .my official pages, first-party APIs)
- **T2**: Major publishers, reputable news outlets, official press releases
- **T3**: Forums (Lowyat), wiki, community sources
- **T4**: Unverifiable, anonymous, or stale content

Already partially implemented in `malaysia-telco-research` skill.

### S05: API Interception (B3) — ✅ VALIDATED

`browser_console` tool already available. Can execute arbitrary JavaScript in the browser
context to intercept XHR/fetch calls or extract rendered content:

```javascript
// Extract all visible text from JS-heavy SPA
document.body.innerText

// Intercept fetch calls
window.__fetch_log = [];
const origFetch = window.fetch;
window.fetch = (...args) => {
    window.__fetch_log.push(args[0]);
    return origFetch(...args);
};
```

Pattern proven in `malaysia-telco-research` skill for JS-heavy sites.

## Key Infrastructure Learnings

1. **SOUL.md is the persona injection point** — all behavioral rules (structured output,
   confidence scoring, refusal protocol, source hierarchy, CoVe) go here.
2. **Public search engines are unreliable from VPS IPs** — rate-limiting and bot-blocking
   are the norm, not the exception. Self-hosted SearXNG or direct endpoint calls are
   the reliable path.
3. **browser_console bridges JS-heavy sites** — when `browser_snapshot` returns incomplete
   accessibility trees, `browser_console(expression="document.body.innerText")` extracts
   all rendered text.
4. **System prompt stored in session DB** — `sessions.system_prompt` column (24,975 chars
   for default MarryJane persona). Modifications to SOUL.md take effect on next `/new`.
