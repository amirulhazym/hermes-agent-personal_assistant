# V2 Architecture — Critical Analysis & Proposal
**Tarikh:** 8 Jul 2026 23:55 MYT  
**Author:** Jane  
**Subject:** Hermes Web Research Engine — Tier-0 Architecture + BrowserAct Evaluation

---

## Part 1: BrowserAct — Critical Analysis

### What BrowserAct Actually Is

| Dimension | Finding |
|-----------|---------|
| Nature | **Commercial CLI tool** (NOT open source) |
| Install | `uv tool install browser-act-cli` — PyPI package |
| Pricing | $0.064/browser, 5 credits/step, 100 credits/mo base + pay-as-you-go |
| Trial | 7-day free trial, 100 free credits |
| CAPTCHA solving | Sends challenge image to **their cloud API** (privacy: only image, no cookies/page) |
| Auth handling | Login flows, form submission, file upload — all require user confirmation |
| Sessions | Per-browser isolated profiles, stored locally |
| Cross-platform | Can hand off to human on Telegram/Discord when stuck |
| Stealth | Claims anti-bot detection bypass (exact mechanism undocumented) |

### Where Does It Fit?

```
Not replacement for:   Potential fit as:
────────────────────   ────────────────────
FlareSolverr           CAPTCHA solving (unique feature)
Playwright stealth     Human handoff when automation fails
SearXNG                Cross-platform browser orchestration
curl_cffi              ONE MORE Tool Executor — NOT the primary anytihng
```

### Critical Assessment

**Arguments AGAINST making BrowserAct primary:**

1. **Cost.** 5 credits/step × hundreds of pages/day = $5-15/week just for browsing. Compare: FlareSolverr = $0 (Docker on existing VPS). Playwright = $0 (already installed). curl_cffi = $0.

2. **Not OSS.** Conflicts with "prioritize open-source" principle. If BrowserAct shuts down/changes pricing, you're locked. FlareSolverr, Playwright, curl_cffi are all open source.

3. **Overlap with Playwright.** Both automate browsers. Playwright stealth + persistent profiles already does most of what BrowserAct does, without per-step cost. The difference: BrowserAct has a CAPTCHA-solving cloud API and cross-platform handoff.

4. **Black box.** BrowserAct's stealth mechanisms are proprietary. If a site blocks it, you can't patch it. FlareSolverr and Playwright are fully auditable.

**Argument FOR including BrowserAct (as optional):**

1. **CAPTCHA solving is genuinely hard.** No other tool in this stack solves visual CAPTCHAs (reCAPTCHA/hCaptcha). BrowserAct sends challenge images to their API. This is the ONLY tool that handles visual CAPTCHAs.
2. **Human handoff.** When automation truly fails (Cloudflare JS challenge changes, custom CAPTCHA), BrowserAct can hand off to a human on Telegram/Discord. This is a unique capability.
3. **Cross-platform isolation.** Per-browser isolated profiles mean you could run 5 different sessions with different fingerprints without conflict.

### Verdict

**BrowserAct should be: an OPTIONAL Tool Executor in the Capability Registry — specifically tagged for CAPTCHA solving and human handoff only.**

```
Capability Registry entry:
─────────────────────────────
  browseract:
    capabilities: [captcha_solving, human_handoff, multi_session]
    cost_per_step: 5_credits
    requires_confirmation: true
    priority: [only_when_captcha_detected, only_when_others_fail]
```

It should NOT be:
- ❌ Primary browser backend (Playwright wins on cost + OSS)
- ❌ Browser orchestration layer (Hermes' Adaptive Router is the orchestrator)
- ❌ Cloudflare solver (FlareSolverr wins on cost + purpose-built)

---

## Part 2: Architecture Critique

### What's Good (+)

| Component | Why It's Right |
|-----------|----------------|
| Adaptive Router (not static pipeline) | This is the most important design decision. Solves the "one size fits none" problem. |
| Cookie/Session Store | Essential. cf_clearance reuse is an order-of-magnitude savings. |
| Domain Memory + Capability Registry | Separates learned data (memory) from declared rules (registry). Clean. |
| Site-specific Adapters | Keeps each site's quirks isolated. |
| Analytics DB | Enables self-optimization. |
| Unified Tool Executor interface | Critical. Without this, swapping tools breaks the router. |

### What Needs Critique (—)

**1. Planner is under-defined**

Current: `Planner → Policy Engine → Adaptive Router`

What the Planner actually does matters. A research query like "Find me Fragrantica reviews of Lattafa Yara and compare price on Shopee MY" needs to be decomposed into:
- fetch("fragrantica.com/perfume/Lattafa/Yara") → extract rating, notes
- search("shopee.com.my", "Lattafa Yara") → extract prices
- compare(ratings, prices)

Without explicit query decomposition, the Adaptive Router doesn't know what KIND of fetch to do (browse vs scrape vs search). **Recommendation:** Formalize Planner as a query decomposer that outputs typed Tasks, not raw URLs.

**2. Capability Registry vs Domain Memory overlap**

Both store per-domain information:
- Capability Registry: requires_browser, cf_managed, login_needed (DECLARATIVE)
- Domain Memory: success_rate_with_curl_cffi, last_successful_tool (LEARNED)

These need a clear boundary. **Recommendation:** Capability Registry = what the domain REQUIRES (human-curated, stable). Domain Memory = what TOOLS work (machine-learned, dynamic). The Router should query BOTH: start with requirements, optimize with learned data.

**3. No query/page type classification**

The Router treats "fetch a JSON API" and "interact with a multi-page JS form" the same way. They need completely different tools:
- Static HTML → curl_cffi (fast, cheap)
- JS-rendered page → Playwright/FlareSolverr (slower, expensive)
- API with JSON → curl_cffi with proper headers
- CAPTCHA-protected → BrowserAct (paid)

**Recommendation:** Add a page classifier BEFORE the router that categorizes the page type, so the router can choose tools optimally.

**4. Rate limiting / concurrency not addressed**

Shopee MY bans after too many requests. Google has per-IP rate limits. The current architecture has no rate limiter or concurrency manager.

**Recommendation:** Add a Concurrency Manager between Policy Engine and Router that:
- Enforces domain-specific rate limits
- Queues requests per domain
- Rotates between request patterns

**5. Fallback chain incomplete**

The adaptive routing handles tool failures, but what happens when ALL tools fail? The router has no "knowledge fallback" — i.e., if every tool fails, query the model's training data with honest flagging.

**Recommendation:** Add a Knowledge Fallback executor that returns model knowledge (with clear UNVERIFIED label) when all tool executors fail.

**6. Cost optimizer vs speed**

User specification: Cheapest → Fastest → Highest Success. This is correct for a cost-conscious setup, but for time-sensitive tasks (user waiting), speed should sometimes rank above cost. **Recommendation:** Make the optimization axis configurable per task — the Planner should set a priority hint (cost_sensitive / balanced / speed_critical).

**7. No content cache**

If Hermes fetches the same page twice (e.g., Fragrantica Yara page), the architecture re-fetches and re-solves Cloudflare. ETag/Last-Modified headers are ignored. A simple disk cache saves significant time and resources.

**Recommendation:** Add a Content Cache between Cookie Store and Analytics DB that respects ETag, Last-Modified, and TTL.

**8. Missing: Extraction pipeline**

Current architecture stops at fetching. But a research engine needs to EXTRACT structured data from raw HTML/JSON. Different page types need different extractors (HTML parser, JSON parser, PDF text extractor, table extractor).

**Recommendation:** Add an Extraction Layer after fetching, before Analytics DB. Each adapter defines its own extractor, and there's a generic fallback.

---

## Part 3: Proposed Architecture (V2 Final)

```
┌──────────────────────────────────────────────┐
│                   Planner                      │
│  Query decomposition → Typed Task generation  │
│  Output: Task(url, type, priority, context)    │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│              Policy Engine                     │
│  Site rules: rate limits, safety gates        │
│  User rules: confirmation requirements        │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│            Concurrency Manager                 │
│  Per-domain queue + rate limiter              │
│  Request dedup + batching                     │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│              Adaptive Router                   │
│  Reads: Analytics DB + Domain Memory          │
│       + Capability Registry + Cost Optimizer  │
│  Chooses: Tool Executor + Strategy            │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│           Capability Registry                  │
│  fragrantica: requires_browser=true           │
│  shopee: signed_requests=true                  │
│  github: curl_only=true                        │
│  (Declarative / curated)                       │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│              Unified Tool Executors            │
│  Interface: fetch(), interact(), extract(),    │
│             login(), solve_captcha()           │
│                                                │
│  ┌─────────┬──────────┬──────────────┐        │
│  │curl_cffi│cloudscraper│FlareSolverr  │        │
│  │(Layer 1)│(Layer 1.5)│(Layer 2)     │        │
│  ├─────────┼──────────┼──────────────┤        │
│  │ Playwright│ BrowserAct│ Knowledge    │        │
│  │ Stealth  │ (Optional) │ Fallback     │        │
│  │(Layer 2) │(CAPTCHA+HH)│(UNVERIFIED) │        │
│  └─────────┴──────────┴──────────────┘        │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│           Cookie & Session Store               │
│  cf_clearance, session cookies, JWT, ETag     │
│  Browser profiles (Playwright persistent)     │
│  Expiry-aware cache + source tracking         │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│           Content Cache                        │
│  ETag/Last-Modified aware                      │
│  TTL-based expiration                          │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│           Extraction Pipeline                  │
│  HTML → structured data                       │
│  JSON → parsed objects                        │
│  Site-specific (via adapter)                  │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│           Analytics DB                         │
│  domain, tool, latency, cost, success,         │
│  failure_reason, confidence, last_success      │
└──────────────────────┬───────────────────────┘
                       │
┌──────────────────────▼───────────────────────┐
│           Domain Memory                        │
│  Learned: "fragrantica → FlareSolverr: 95%"   │
│  Updates after each successful/failed fetch   │
└─────────────────────────────────────────────
```

---

## Part 4: Folder Structure

```
~/.hermes/fetcher/
├── __init__.py
├── planner.py              # Query → Task decomposition
├── policy_engine.py        # Site + user rules
├── concurrency_manager.py  # Rate limiter + queue
├── router.py               # Adaptive routing (main logic)
├── capability_registry.py  # Declarative domain configs
├── cost_optimizer.py       # Cost/speed success optimizer
├── cookie_store.py         # Cookie + session persistence
├── content_cache.py        # ETag/TTL content cache
├── extraction/
│   ├── __init__.py
│   ├── base.py             # Extractor protocol
│   ├── html_extractor.py   # CSS selectors / readability
│   ├── json_extractor.py   # JSONPath extraction
│   └── text_extractor.py   # Raw text fallback
├── executors/
│   ├── __init__.py
│   ├── base.py             # Unified interface (fetch, interact, extract, login, solve_captcha)
│   ├── curl_cffi_executor.py
│   ├── cloudscraper_executor.py
│   ├── flaresolverr_executor.py
│   ├── playwright_executor.py
│   ├── browseract_executor.py   # Optional / CAPTCHA-only
│   └── knowledge_fallback.py   # Last resort
├── adapters/
│   ├── __init__.py
│   ├── base.py             # Adapter interface
│   ├── fragrantica.py
│   ├── shopee.py
│   ├── google.py
│   ├── reddit.py
│   └── github.py
├── analytics/
│   ├── __init__.py
│   ├── store.py            # Analytics DB read/write
│   └── schema.sql          # SQLite schema
├── domain_memory.py        # Learned routing weights
├── cli.py                  # Hermes command integration
└── tests/
    ├── test_router.py
    ├── test_executors.py
    ├── test_cookie_store.py
    └── fixtures/           # Mock page responses
```

---

## Part 5: Migration Plan (Current → V2)

### Phase 0: Assessment (NOW)
- [x] curl_cffi installed and verified (Bing ✅)
- [x] cloudscraper installed and verified (some sites ✅)
- [x] Mapping of what's blocked vs accessible

### Phase 1: MVP — FlareSolverr + Cookie Store (Week 1)

**Remove:** Nothing yet. Static fallback chain still works for what it does.

**Add:**
1. Install Docker + FlareSolverr
2. Create `executors/base.py` — define the unified interface
3. Create `executors/flaresolverr_executor.py` — wrap FlareSolverr API
4. Create `cookie_store.py` — SQLite-backed cf_clearance + session storage
5. Create `adapters/fragrantica.py` — first working adapter

**Verification:** Fragrantica and Parfumo accessible via Hermes fetch.

**Risk:** Docker may need significant disk (~500MB for Chromium inside container).

### Phase 2: Foundation — Adaptive Router (Week 2)

**Remove:** Static fallback chain in current Hermes tools.

**Add:**
1. Create `router.py` — the adaptive routing engine
2. Create `capability_registry.py` — YAML-driven domain configs
3. Wrap curl_cffi and cloudscraper into executor interface
4. Create `cost_optimizer.py` — simple cost/speed model

**Verification:** Router correctly selects curl_cffi for GitHub, FlareSolverr for Fragrantica.

### Phase 3: Intelligence — Analytics + Domain Memory (Week 3)

**Add:**
1. SQLite database with analytics schema
2. `domain_memory.py` — learns from analytics data
3. Router integrates Domain Memory as input to decisions

**Verification:** After 3-4 fetches to Fragrantica, router automatically prefers FlareSolverr. After failures, tries alternatives.

### Phase 4: Playwright — Primary Browser Backend (Week 4)

**Add:**
1. Install Chromium + `playwright` + `playwright-extra` + stealth plugin
2. Create `executors/playwright_executor.py` with persistent profiles
3. Integrate into Router as Layer 2 for JS-heavy pages

**Verification:** Pages that need JS rendering work. Sessions persist across fetches.

### Phase 5: Optional — BrowserAct (If needed)

**Conditional:** Only if CAPTCHA solving or human handoff is genuinely blocking use cases.

**Add:**
1. `uv tool install browser-act-cli`
2. Create `executors/browseract_executor.py`
3. Register in Capability Registry as `only_when_captcha`

**Verification:** CAPTCHA-protected pages get solved with human handoff fallback.

### Phase 6: Production — Full Stack (Week 5-6)

**Add:**
1. `planner.py` — query decomposition
2. `concurrency_manager.py` — rate limiting
3. `content_cache.py` — ETag-aware cache
4. `extraction/` — structured data extraction
5. `policy_engine.py` — safety + routing policies

---

## Part 6: Priority Roadmap

```
Week 1                    Week 2                    Week 3                    Week 4                    Week 5-6
─────────────────────────┬─────────────────────────┬─────────────────────────┬─────────────────────────┬─────────────────────────
                         │                         │                         │                         │
  [MVP]                  │  [Foundation]           │  [Intelligence]         │  [Browser]              │  [Production]
                         │                         │                         │                         │
  FlareSolverr +         │  Adaptive Router        │  Analytics DB           │  Playwright Stealth     │  Planner
  Cookie Store           │  Cap Registry           │  Domain Memory          │  + Persistent Profiles  │  Concurrency
                         │  curl_cffi executor     │  Router self-optimize   │  Browser profile cache  │  Content Cache
  Fragrantica adapter    │  cloudscraper executor  │                         │                         │  Extraction pipeline
  Base executor          │  Cost Optimizer         │                         │                         │  Policy Engine
  interface              │                         │                         │                         │
                         │                         │                         │                         │
  ──────                 │  ──────                 │  ──────                 │  ──────                 │  ──────
  🔥 HIGHEST IMPACT      │  🏗️ FOUNDATION         │  🧠 SELF-LEARNING       │  🖥️ BROWSER BACKEND     │  🔧 FULL SYSTEM
  Unblocks Fragrantica   │  Makes it adaptive      │  Gets smarter over time │  Handles JS-heavy pages │  Production ready
  Parfumo immediately    │  instead of static      │  without manual config  │  with persistent auth   │  optimized & cached
                         │                         │                         │                         │
```

---

## Part 7: Design Decisions I'd Reconsider (if this were my system)

1. **Don't build your own cookie store for v1.** Just use SQLite with a simple table. You'll be tempted to build a complex cache with TTL, refresh logic, etc. Start simple: `(domain, cookie_type, cookie_value, expires_at, source)`. Add complexity as analytics data reveals the need.

2. **Capability Registry should be YAML files, not a database.** Human-curated data belongs in version-controlled YAML. Only the learned Domain Memory belongs in a DB. The split keeps configuration auditable.

3. **The Planner should not be part of this system initially.** For MVP, the fetch query comes from the user or the main Hermes agent, already decomposed. Planning adds complexity before you have data to plan with. Add in Phase 6 when the system is actually being used for multi-step research.

4. **BrowserAct should be the LAST thing you install.** Not because it's bad, but because it adds cost and opaque dependency. If CAPTCHA solving becomes a blocker, then evaluate. The free trial can tell you if it works for your use cases. Don't commit to paid plan until Phase 5 or later.

5. **Playwright persistent profile should map one-to-one with Hermes sessions.** Each Hermes conversation gets its own browser profile. This prevents session cross-contamination between different user contexts.

6. **The unified executor interface MUST include an async variant.** `await fetch()` vs `fetch_sync()`. The Adaptive Router will need to try multiple tools in parallel (try curl_cffi and if it fails within 3s, escalate to FlareSolverr). Sync-only interface forces sequential fallback.

7. **Store the raw fetch HTML in the Content Cache for at least 24h.** Analytics DB should link to cached content. When debugging why a parser failed, you need the raw HTML that was returned, not the current live page.

---

## Summary: Verdict

| Area | Score | Key Action |
|------|-------|------------|
| Architecture design | 9.8/10 | Add: Planner clarification, Concurrency Manager, Extraction pipeline, Content Cache. Split: Cap Registry vs Domain Memory clearer. |
| BrowserAct role | Optional CAPTCHA tool | Install LAST. Only if CAPTCHA solving blocks real use cases. |
| Priority | Phase 1 first | FlareSolverr + Cookie Store unblocks Fragrantica/Parfumo NOW. |
| Best insight | Unified Tool Executor interface | This is the most important design decision. Nail this interface and everything else slots in. |

---

## Next Action

Nak aku:
A) Start Phase 1 — install Docker + FlareSolverr, build base executor interface, Fragrantica adapter (live coding)
B) Start Phase 2 — build Adaptive Router + Capability Registry (design doc first)
C) Kau nak review this document dulu, refine anything, then go
