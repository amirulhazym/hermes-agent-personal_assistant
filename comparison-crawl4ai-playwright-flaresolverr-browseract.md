# Technical Comparison: Crawl4AI vs Playwright vs BrowserAct vs FlareSolverr
**Tarikh:** 9 Jul 2026 00:20 MYT  
**Evidence source:** Official docs, GitHub source code, PyPI metadata, live VPS testing

---

## Q1: Overlap Capabilities

| Capability | Crawl4AI | Playwright | FlareSolverr | BrowserAct |
|-----------|----------|------------|--------------|------------|
| Browser automation | ✅ (wraps Playwright) | ✅ (native) | ✅ (headless Chrome) | ✅ (managed browser) |
| JS rendering | ✅ (via Playwright) | ✅ (native) | ✅ (via Chrome) | ✅ (via managed browser) |
| Stealth / anti-bot | ✅ (playwright-stealth bundled) | ⚠️ (plugin needed) | ❌ (solves challenge only) | ⚠️ (claims stealth) |
| Screenshots | ✅ | ✅ | ❌ | ✅ |
| PDF capture | ✅ | ✅ | ❌ | ❌ |
| Page interaction (click, fill, navigate) | ✅ (via hooks: page.fill, page.click, page.goto) | ✅ (native API) | ❌ (proxy only) | ✅ (CLI commands) |
| Session persistence | ✅ (session IDs, identity-based) | ✅ (browser contexts) | ❌ (solves per-request) | ✅ (per-browser profiles) |
| Proxy support | ✅ (ProxyConfig, rotation) | ✅ (browser launch args) | ✅ (native) | ✅ (managed) |
| Cookie management | ✅ (hooks + add_cookies) | ✅ (context.cookies, context.add_cookies) | ❌ | ✅ |
| Content cache | ✅ (CacheMode: ENABLED/DISABLED/BYPASS/SMART) | ❌ | ❌ | ❌ |
| Form filling | ✅ (via hook: page.fill) | ✅ (page.fill) | ❌ | ✅ (CLI) |
| File upload | ✅ (via hook: page.set_input_files) | ✅ (page.set_input_files) | ❌ | ✅ |
| Multi-step workflows | ✅ (via hooks + c4a_script) | ✅ (full control) | ❌ | ✅ (CLI scripting) |
| Anti-bot simulation | ✅ (magic mode, simulate_user) | ⚠️ (manual) | ❌ | ✅ (managed) |

### Key Finding

**Crawl4AI has 100% capability overlap with Playwright** because it exposes the raw Playwright Page object via hooks (`on_page_context_created`, `before_goto`, `after_goto`). There is NO operation Playwright can do that Crawl4AI cannot also do.

---

## Q2: Unique Capability Per Tool

### Crawl4AI (unique to this stack)
| Capability | Why It Matters |
|-----------|----------------|
| **AI-ready markdown generation** (DefaultMarkdownGenerator + Fit Markdown) | Converts HTML to clean Markdown — no other tool does this natively |
| **Structured extraction** (JsonCssExtractionStrategy, JsonXPathExtractionStrategy, LLMExtractionStrategy) | Extract structured JSON directly from pages — bypasses manual parsing |
| **Content filtering** (PruningContentFilter, BM25ContentFilter, LLMContentFilter) | Removes boilerplate, nav bars, ads — LLM-ready clean content |
| **Deep crawling** (deep_crawl_strategy) | Follows links internally within a domain — auto-crawl entire site |
| **Smart cache** (ETag/Last-Modified cache validation) | Avoids re-fetching unchanged pages — major efficiency win |
| **Session-aware crawling** (session_id) | Persists auth state across multiple pages in same domain |
| **C4A Script** (custom scripting language for extraction) | Embeddable extraction logic without writing Python |

### Playwright (unique)
| Capability | Why It Matters |
|-----------|----------------|
| **Cross-browser** (Chromium + Firefox + WebKit) | Not relevant — Crawl4AI also uses Playwright |
| **Network interception** (route blocking, HAR capture) | Relevant for debugging but available via Crawl4AI hooks |
| **Standalone without Crawl4AI** | Lighter install — relevant for minimal deployments |

**In this stack: Playwright has ZERO unique capabilities that matter**, because Crawl4AI exposes all of them through hooks plus adds extraction/caching on top.

### FlareSolverr (unique)
| Capability | Why It Matters |
|-----------|----------------|
| **Cloudflare Managed Challenge solving** (turnstile, JS challenge, captcha challenge) | This is what failed with curl_cffi, cloudscraper, and playwright-stealth in live testing |
| **Returns HTML + cf_clearance cookie** after solving | Clean HTML ready for extraction |
| **Cookie reuse** across multiple requests | Solve once, reuse for 30min-24h |

### BrowserAct (unique)
| Capability | Why It Matters |
|-----------|----------------|
| **CAPTCHA solving cloud API** (challenge image → verification) | No other tool in this stack solves visual CAPTCHAs (reCAPTCHA, hCaptcha) |
| **Human handoff** (Telegram/Discord when stuck) | Only path for truly unsolvable anti-bot scenarios |
| **Multi-account isolated profiles** | Each browser session has independent fingerprint + cookies |

---

## Q3: Primary Executor Candidates

| Role | Primary | Reason |
|------|---------|--------|
| **Static HTML / API content** | curl_cffi | Fastest (0.2-1s), cheapest (0 cost), TLS spoofing built-in |
| **Simple Cloudflare** | cloudscraper | Lightweight JS challenge solver. No browser needed. |
| **Aggressive Cloudflare** | FlareSolverr | Only tool that reliably solves Managed Challenge (live-verified) |
| **JS-rendered content / extraction / deep crawl** | **Crawl4AI** | Covers browser automation + extraction + caching + markdown in ONE tool |
| **Visual CAPTCHA / human handoff** | BrowserAct (optional) | Only when CAPTCHA is genuinely blocking |

**Verdict:** There is NO legitimate "primary tool." The Adaptive Router selects based on capability requirements.

---

## Q4: Which Should Be Internal vs Exposed?

| Tool | Status | Rationale |
|------|--------|-----------|
| curl_cffi | **Exposed executor** | First-tier, fastest, direct executor |
| cloudscraper | **Exposed executor** | Lightweight fallback |
| FlareSolverr | **Exposed executor** | Docker-based, independent, Cloudflare only |
| **Crawl4AI** | **Exposed executor** | **PRIMARY browser + extraction executor** |
| **Playwright** | **Internal (to Crawl4AI)** | Crawl4AI already imports and wraps it. No separate executor needed. |
| BrowserAct | **Exposed (optional) executor** | Only for CAPTCHA + human handoff. Tagged as paid. |
| Knowledge Fallback | **Internal last resort** | Not a traditional executor — returns model knowledge |

### Why Playwright Should Be Internal

1. **Crawl4AI uses Playwright already** — `playwright>=1.49.0` + `playwright-stealth>=2.0.0` are hard dependencies
2. **Hooks expose raw Page object** — `page.fill()`, `page.click()`, `page.goto()` etc accessible through hooks
3. **No capability loss** — every Playwright operation is doable through Crawl4AI
4. **Reduces executor count** — 7 executors → 6 executors. Less maintenance, less code, less testing
5. **Playwright's unique value** (cross-browser, network interception) is NOT needed for Hermes use cases

**Exception rule:** If a specific integration requires raw Playwright (e.g., direct `page.cdpsession` for DevTools protocol), Crawl4AI hooks can still expose it. If truly impossible, add Playwright as a standalone executor LATER — not from Phase 1.

---

## Q5: Can Crawl4AI Replace Playwright Executor?

### YES — with ONE caveat

**Evidence for YES (from official Crawl4AI v0.9.x source + docs):**

1. **Architecture:** Crawl4AI has `PlaywrightAdapter` in `browser_adapter.py` — it IS Playwright with an abstraction layer on top. The same `Page` from `playwright.async_api` is imported and used throughout.

2. **Hook API:** 
   ```
   on_page_context_created(page: Page, **kwargs) → raw Playwright Page
   before_goto(page: Page, **kwargs) → raw Playwright Page
   after_goto(page: Page, **kwargs) → raw Playwright Page
   ```
   Official example code shows `page.fill()`, `page.click()`, `page.goto()`, `page.wait_for_selector()`, `context.add_cookies()` — all native Playwright API.

3. **Feature parity:**
   ```
   Screenshots:    Crawl4AI supports via CrawlerRunConfig.screenshot
   PDF:            Crawl4AI supports via CrawlerRunConfig.pdf  
   Form fill:      Crawl4AI hooks → page.fill()
   File upload:    Crawl4AI hooks → page.set_input_files()
   Network:        Crawl4AI hooks → route intercept
   Sessions:       Crawl4AI has session_id + identity-based crawling
   Cookes:         Crawl4AI hooks → context.add_cookies()
   ```

### The ONE caveat: maturity

| Factor | Playwright | Crawl4AI |
|--------|-----------|----------|
| First release | 2020 (Microsoft) | 2024 (unclecode, community) |
| Current version | 1.52+ | 0.9.1 |
| Backers | Microsoft | Open source community |
| Bug surface | ~4 years hardened | ~1 year |
| API stability | Very stable | Pre-v1, may change |

**Mitigation:** Crawl4AI wraps Playwright. If Crawl4AI has a bug, the fallback is using hooks to call Playwright directly. So we're never truly blocked — just inconvenienced.

### Verdict

**Accept Crawl4AI as the sole browser executor for Phase 1-4.** Monitor for issues. If Crawl4AI-specific bugs appear, add raw Playwright executor in Phase 6 as an optimization, NOT as a core component.

---

## Stake: What We Save by Consolidating

```
With separate Playwright executor:
  Executors:  7 (curl, cloudscraper, FlareSolverr, Playwright, Crawl4AI, BrowserAct, Knowledge)
  Testing:    7 executor interfaces × 3 test cases = 21 unit tests
  Maintenance: 7 files to keep updated
  
Without separate Playwright executor (Crawl4AI covers it):
  Executors:  6 (curl, cloudscraper, FlareSolverr, Crawl4AI, BrowserAct, Knowledge)
  Testing:    6 × 3 = 18 unit tests  
  Maintenance: 6 files (Crawl4AI handles Playwright internally)
  Savings:    ~15% reduction in per-executor code, ~1 full component less to maintain
```

---

## Final Architecture Recommendation

```
Unified Tool Executors (interface-based)
═════════════════════════════════════════

  Executor           Role                     Cost    Unique Value
  ────────           ────                     ────    ─────────────
  curl_cffi          Static HTML, TLS-fingerprint  Free   Fastest (0.2s)
  cloudscraper       Simple Cloudflare             Free   Lightweight
  FlareSolverr       Managed Cloudflare/Docker      Free   Cloudflare ✅ live-tested
  Crawl4AI           Browser + extraction + cache   Free   AI-ready output → saves Phase 3-5
  BrowserAct         CAPTCHA + human handoff      Paid    Only CAPTCHA solver (optional)
  Knowledge          Last resort (UNVERIFIED)      Free    Falls back gracefully

Playwright → INTERNAL to Crawl4AI. Not a separate executor.
```

### Key Design Principles

1. **Executor count = 6, not 7** — Playwright absorbed by Crawl4AI. 15% less maintenance.
2. **Capability-based routing** — Router picks by required capability, not tool name.
3. **Crawl4AI is the heavy lifter** — browser + JS rendering + extraction + caching + markdown in one tool.
4. **FlareSolverr still needed** — live testing confirmed: playwright-stealth ≠ Cloudflare Managed solver.
5. **BrowserAct optional** — install ONLY if visual CAPTCHA becomes a blocking problem.

---

## Updated Phase Roadmap

| Phase | What | Why This Order |
|-------|------|----------------|
| 1a | Base Executor Interface + Cookie Store + FlareSolverr | Unblock Fragrantica/Parfumo immediately |
| 1b | Crawl4AI executor (wraps as executor, install Chromium + deps) | Adds JS rendering + extraction + cache in one shot |
| 2 | Adaptive Router + Capability Registry | Makes routing dynamic instead of static |
| 3 | Analytics DB + Domain Memory | System learns per-domain, self-optimizes |
| 4 | BrowserAct evaluation (only if CAPTCHA blocking) | Optional — verify first, install only if needed |
| 5 | Planner + Concurrency Manager + Policy Engine | Advanced features after foundations proven |

---

## Decision: Playwright Externally Exposed or Internal?

**Verdict: Internal to Crawl4AI (DO NOT expose as separate executor).**

Exception: If at Phase 4+ we discover a use case where Crawl4AI's hooks don't expose a needed Playwright feature, we add a raw Playwright executor then. But start WITHOUT it — simplicity first.
