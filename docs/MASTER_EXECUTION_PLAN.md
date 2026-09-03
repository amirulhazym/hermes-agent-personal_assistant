# Master Execution Plan V2 — FINAL
**Hermes Web Research Engine**
**Tarikh:** 9 Jul 2026 00:50 MYT
**Status:** FINAL — approved for autonomous execution
**Mode:** Engineering → Validation → Production

---

## 0. Execution Mandate

User approved autonomous execution (point 16 of review). After this plan is written, execution begins immediately. No further approval gates. Stop ONLY for: login, password, OTP, payment, or truly undecidable action.

**Git:** Local commits at phase milestone ONLY. NO push. NO merge. NO remote.

**Reporting:** Milestone-level only (phase complete / major blocker / architecture change due to evidence / production-ready).

---

## 1. Engineering Philosophy (binding)

1. Simplicity over cleverness.
2. Stable contracts over convenience.
3. Measurable evidence over assumptions.
4. Modular over tightly coupled.
5. Interface first, implementation second.
6. Optimization only after measurement.
7. Local-first and open-source whenever practical.
8. Backward compatibility whenever reasonable.
9. Fail gracefully, never fail silently.
10. Every phase delivers visible user value.

---

## 2. Architecture Discipline (FINAL)

- Architecture changes ONLY with: benchmark, production evidence, measurable bottleneck, real implementation limitation.
- No new components, no hierarchy changes, no theoretical proposals.
- Crawl4AI = CURRENT browser implementation. Swappable without touching Router.
- Knowledge = fallback behavior, NOT a tool.

---

## 3. Current State Assessment (verified 00:30 MYT)

| Item | Status |
|------|--------|
| Python 3.12.3 | ✅ |
| curl_cffi | ✅ installed + working (Bing 200) |
| cloudscraper | ✅ installed + working |
| Node v22.23.1 / npm 10.9.8 | ✅ |
| Docker | ❌ NOT installed (fallback plan ready) |
| Crawl4AI / Playwright / Chromium | ❌ MISSING (need install) |
| bs4 / lxml | ❌ MISSING (need install) |
| Disk | ✅ 22G free |
| Git repo | ✅ mjay/ is git |

---

## 4. Final Architecture Snapshot

```
┌─────────────┐
│   Planner   │  (Phase 5) Query → typed Tasks
└──────┬──────┘
       ▼
┌─────────────┐
│Policy Engine│  (Phase 5) per-domain safety + rate rules
└──────┬──────┘
       ▼
┌──────────────────┐
│Concurrency Manager│ (Phase 5) rate limiter + queue
└──────┬───────────┘
       ▼
┌─────────────────┐
│  Adaptive Router │  selects by Capability Registry + Analytics + Cost
└──────┬──────────┘
       ▼
┌──────────────────────┐
│  Capability Registry  │  YAML: per-domain required capabilities (16 types)
└──────┬───────────────┘
       ▼
┌──────────────────────────────────────────────────┐
│            Unified Tool Executors (interface)       │
│                                                      │
│  curl_cffi          → static, TLS fingerprint        │
│  cloudscraper       → simple Cloudflare              │
│  FlareSolverr       → Managed Cloudflare (Docker)    │
│  BrowserExecutor     → browser abstraction           │
│     └─ Crawl4AIExecutor (CURRENT impl)               │
│           └─ Playwright (internal dependency)        │
│  BrowserAct         → [STUB, deferred: payment]       │
└──────┬─────────────────────────────────────────────┘
       │ (all executors fail)
       ▼
┌──────────────────────────────────────┐
│  FallbackPolicy → KnowledgeResponse    │  ← NOT an executor
│  Returns Document with UNVERIFIED tag  │
└──────────────┬───────────────────────┘
               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│Cookie Store │  │Content Cache│  │  Analytics  │
└─────────────┘  └─────────────┘  └─────────────┘
       ▼                ▼                ▼
┌──────────────────────┐  ┌──────────────────────┐
│  Extraction Pipeline  │→│ Normalization (Document)│
└──────────────────────┘  └──────────┬───────────┘
                              ▼
                       ┌─────────────┐
                       │Domain Memory│  behavioral learning
                       └─────────────┘

Site Adapters (own all domain logic):
  Fragrantica, Shopee, Google, Reddit, GitHub
  Each knows: preferred executor, retry policy, rate limit,
  cache TTL, content extractor, normalizer, validation rules.
```

**Executors = 4 active + 1 stub (BrowserAct) + 1 fallback behavior (Knowledge).**
Router NEVER references Crawl4AI by name. It references `BrowserExecutor`.

---

## 5. Document Contract (CORE — all executors return EXACTLY this)

```python
@dataclass
class Document:
    # ── metadata ──
    source: str                 # executor name (e.g. "curl_cffi", "flaresolverr", "browser")
    url: str
    domain: str
    timestamp: float
    executor: str
    latency: float              # seconds
    estimated_cost: float       # 0.0 for free tools
    verification_status: str    # VERIFIED | UNVERIFIED | PARTIAL
    confidence: float           # 0.0–1.0
    cache_status: str           # HIT | MISS | BYPASS
    cookies_used: bool
    browser_profile: str | None
    headers: dict
    # ── content ──
    content: str | None         # raw HTML / text
    markdown: str | None
    structured_data: dict | None
    tables: list | None
    links: list | None
    images: list | None
    artifacts: dict | None      # arbitrary extracted artifacts
    screenshots: list | None
    attachments: list | None
    raw_response: dict | None   # transport metadata (status, headers)
    # ── diagnostics ──
    errors: list | None
    warnings: list | None
    telemetry: dict | None      # memory_mb, cpu_pct, retry_count,
                                # fallback_count, proxy_used, extraction_ms,
                                # normalization_ms, response_size
```

This contract is the stable boundary. Parsers, memory, analytics, RAG, summarizer all consume `Document`.

---

## 6. Capability Registry (16 capabilities, extensible)

```yaml
capabilities:
  supports_browser: false
  supports_js: false
  supports_api: false
  supports_markdown: false
  supports_structured_extract: false
  supports_pdf: false
  supports_tables: false
  supports_login: false
  supports_captcha: false
  supports_infinite_scroll: false
  supports_download: false
  supports_streaming: false
  supports_authentication: false
  supports_proxy: false
  requires_confirmation: false
  cf_managed: false   # needs Cloudflare Managed Challenge solver
```

Per-domain overrides in `config/capabilities.yaml`:
```yaml
domains:
  fragrantica.com:
    cf_managed: true
    preferred_executor: flaresolverr
    cache_ttl: 3600
  github.com:
    preferred_executor: curl_cffi
    cache_ttl: 86400
  shopee.com.my:
    supports_js: true
    preferred_executor: browser
    cache_ttl: 1800
```

---

## 7. Implementation Roadmap (strict acceptance criteria per task)

Each task has: Objective | Files changed | Verification command | Expected output | Evidence | Rollback | Known limitation.

### Phase 1a — Foundation (no external deps)
| ID | Task | Objective | Files | Verify | Accept | Rollback | Limitation |
|----|------|-----------|-------|--------|--------|----------|------------|
| T001 | Package skeleton | fetcher/ imports | `__init__.py` | `python -c "import fetcher"` | no error | rm dir | — |
| T002 | Unified Executor interface + Document contract | base.py, models.py | base.py, models.py | `python -c "from fetcher.base import Executor, Document"` | 8 abstract methods + Document dataclass | git revert | — |
| T003 | BrowserExecutor abstraction | browser_executor.py | browser_executor.py | `from fetcher.browser_executor import BrowserExecutor` | abstract, extends Executor | git revert | — |
| T004 | Cookie & Session Store | cookie_store.py | cookie_store.py | store+retrieve cf_clearance, TTL expiry | roundtrip works | rm file | sqlite only |
| T005 | curl_cffi executor | executors/curl_cffi_executor.py | file | live: Bing → Document | returns Document, VERIFIED | rm file | no JS |
| T006 | cloudscraper executor | executors/cloudscraper_executor.py | file | live: simple CF site | returns Document | rm file | no Managed CF |
| T007 | FallbackPolicy + KnowledgeResponse | fallback.py | fallback.py | all executors fail → UNVERIFIED Document | label correct | rm file | not fetched |
| T008 | Fragrantica adapter (curl path) | adapters/fragrantica.py | file | parse fixture HTML | extracts perfume fields | rm file | needs CF solver |
| T009 | Normalization layer | normalization.py | file | all executors → unified Document | schema consistent | rm file | — |

### Phase 1b — FlareSolverr (Cloudflare)
| ID | Task | Objective | Files | Verify | Accept | Rollback | Limitation |
|----|------|-----------|-------|--------|--------|----------|------------|
| T010 | Docker install OR fallback | docker.io or pip flaresolverr | — | `docker --version` OR `python -c "import flaresolverr"` | one works | uninstall | Tencent may block apt |
| T011 | FlareSolverr deploy | container on :8191 | — | `curl localhost:8191` health | 200 OK | `docker rm -f` | — |
| T012 | FlareSolverr executor (REST) | executors/flaresolverr_executor.py | file | live: Fragrantica via FS | **HTML returned, VERIFIED** | rm file | cookie expires |
| T013 | Fragrantica via FS | update adapter | adapters/fragrantica.py | live: Fragrantica | **accessible** ✅ | revert | — |

**FALLBACK if Docker fails (T010):** `pip install flaresolverr` (bundles solver) OR headless Chromium via Playwright solves challenge directly. Autonomous.

### Phase 1c — Crawl4AI (Browser + Extraction)
| ID | Task | Objective | Files | Verify | Accept | Rollback | Limitation |
|----|------|-----------|-------|--------|--------|----------|------------|
| T014 | Playwright + Chromium | install | — | `python -c "from playwright import sync_playwright"` | import OK | uninstall | 150MB dl |
| T015 | Crawl4AI install | install + bs4/lxml | — | `python -c "import crawl4ai"` | import OK | uninstall | — |
| T016 | Crawl4AIExecutor (impl of BrowserExecutor) | executors/crawl4ai_executor.py | file | live: JS page → markdown Document | markdown+fields, VERIFIED | rm file | v0.9.x pre-v1 |
| T017 | Shopee/Google/Reddit adapters use BrowserExecutor | adapters/*.py | files | live: Shopee → markdown | **accessible** ✅ | revert | — |

### Phase 2 — Adaptive Router + Registry
| ID | Task | Objective | Files | Verify | Accept | Rollback | Limitation |
|----|------|-----------|-------|--------|--------|----------|------------|
| T018 | Capability Registry loader | capability_registry.py | file | load YAML, query fragrantica→cf_managed | correct | rm file | — |
| T019 | Adaptive Router | router.py | file | mock: fragrantica→FS, github→curl | correct routing | git revert | — |
| T020 | Cost Optimizer | cost_optimizer.py | file | prefers cheap capable tool | weight correct | rm file | — |

### Phase 3 — Analytics + Domain Memory
| ID | Task | Objective | Files | Verify | Accept | Rollback | Limitation |
|----|------|-----------|-------|--------|--------|----------|------------|
| T021 | Analytics DB (extended metadata) | analytics.py | file | log fetch w/ telemetry | row inserted | rm file | sqlite |
| T022 | Domain Memory (behavioral) | domain_memory.py | file | after N fetches, stores best executor + strategy + TTL | weight shifts | rm file | needs data |
| T023 | Wire router→memory | router.py update | router.py | self-optimizes | correct | git revert | — |

### Phase 4 — BrowserAct (DEFERRED — payment)
| ID | Task | Status |
|----|------|--------|
| T024 | BrowserAct stub only (interface, not wired) | ✅ In scope (no install) |
| T025 | Install/integrate | 🚫 BLOCKED: payment |

### Phase 5 — Planner + Concurrency + Policy (if time)
| ID | Task |
|----|------|
| T026 | Planner (query→typed Tasks) |
| T027 | Concurrency Manager (rate limiter) |
| T028 | Policy Engine (safety/routing) |

### Phase 6 — Production Hardening
| ID | Task |
|----|------|
| T029 | Logging/Monitoring/Metrics |
| T030 | Error Recovery (retry+escalate+fallback) |
| T031 | Hermes CLI (`fetcher` command) |
| T032 | Final Live Verification (all sites) |

---

## 8. Execution Order (dependency graph)

```
T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009
                                              │
T010 (Docker/fallback) → T011 → T012 → T013
                                              │
T014 → T015 → T016 → T017
                                              │
T018 → T019 → T020
              │
T021 → T022 → T023
              │
T024 (stub only)
              │
T026 → T027 → T028  (Phase 5, if time)
              │
T029 → T030 → T031 → T032  (Phase 6)
```

Sequential, no parallelism needed. Each task depends on prior. Autonomous run proceeds T001→T032.

---

## 9. Folder Structure (FINAL)

```
/home/ubuntu/mjay/fetcher/
├── __init__.py
├── base.py                    # Executor (8 methods) + Document + Task + Capability
├── browser_executor.py        # BrowserExecutor(Executor) abstract — Router talks to THIS
├── models.py                  # re-export for convenience
├── fallback.py                # FallbackPolicy → KnowledgeResponse (UNVERIFIED)
├── cookie_store.py            # SQLite cookie/session persistence
├── content_cache.py           # stores markdown+JSON+screenshots+metadata
├── router.py                  # Adaptive Router (capability + analytics + cost)
├── capability_registry.py     # loads config/capabilities.yaml
├── cost_optimizer.py          # cost/speed/success weight
├── analytics.py               # Analytics DB (extended telemetry)
├── domain_memory.py           # behavioral learning per domain
├── normalization.py           # Document normalization
├── planner.py                 # Task decomposer (Phase 5)
├── concurrency.py             # Rate limiter (Phase 5)
├── policy.py                  # Policy engine (Phase 5)
├── cli.py                     # Hermes integration
├── executors/
│   ├── __init__.py
│   ├── curl_cffi_executor.py
│   ├── cloudscraper_executor.py
│   ├── flaresolverr_executor.py
│   ├── crawl4ai_executor.py   # implements BrowserExecutor (CURRENT impl)
│   └── browseract_executor.py # STUB only (deferred, payment)
├── adapters/
│   ├── __init__.py
│   ├── base.py                # Adapter base: owns preferred executor, retry, rate, ttl, extractor, normalizer, validation
│   ├── fragrantica.py
│   ├── shopee.py
│   ├── google.py
│   ├── reddit.py
│   └── github.py
├── config/
│   └── capabilities.yaml
└── tests/
    ├── test_base.py
    ├── test_cookie_store.py
    ├── test_executors.py
    ├── test_router.py
    └── fixtures/
```

---

## 10. Module List

| Module | Purpose | Depends On | Status |
|--------|---------|------------|--------|
| base.py | Executor ABC (8 methods) + Document/Task/Capability | — | TODO |
| browser_executor.py | BrowserExecutor ABC — Router's browser entry | base | TODO |
| fallback.py | FallbackPolicy + KnowledgeResponse (UNVERIFIED) | base | TODO |
| cookie_store.py | Persist cf_clearance/session/JWT w/ TTL | base | TODO |
| content_cache.py | Cache markdown+JSON+screenshots+metadata | base | TODO |
| executors/curl_cffi_executor.py | TLS-spoof fetch | base, curl_cffi | TODO |
| executors/cloudscraper_executor.py | Simple CF | base, cloudscraper | TODO |
| executors/flaresolverr_executor.py | CF Managed (REST) | base, Docker | TODO |
| executors/crawl4ai_executor.py | Browser impl (Crawl4AI) | browser_executor, crawl4ai | TODO |
| executors/browseract_executor.py | STUB (deferred) | base | STUB |
| adapters/base.py | Adapter: preferred executor, retry, rate, ttl, extractor, normalizer, validation | base | TODO |
| adapters/*.py | Site parsers + domain logic | adapters/base | TODO |
| normalization.py | Document normalization | models | TODO |
| router.py | Adaptive selection | registry, analytics, cost, fallback | TODO |
| capability_registry.py | Load YAML | config | TODO |
| cost_optimizer.py | Weight cost/speed/success | — | TODO |
| analytics.py | SQLite + telemetry | models | TODO |
| domain_memory.py | Behavioral learning | analytics | TODO |
| planner.py | Query→Task (Phase 5) | router | TODO |
| concurrency.py | Rate limiter (Phase 5) | — | TODO |
| policy.py | Safety/routing (Phase 5) | — | TODO |
| cli.py | Hermes command | router | TODO |

---

## 11. Testing Strategy

| Module | Unit | Integration | Live Verify | Success |
|--------|------|-------------|-------------|---------|
| base.py | 8 abstract methods enforced | — | — | ABC works |
| browser_executor.py | abstract enforced | — | — | ABC works |
| cookie_store.py | store/retrieve/expiry | — | real cf_clearance | TTL works |
| curl_cffi | mock parse | local server | **Bing 200** | Document |
| cloudscraper | mock parse | — | simple CF | Document |
| flaresolverr | mock REST | container health | **Fragrantica** | HTML |
| crawl4ai | mock crawler | local HTML | **JS page→markdown** | Document |
| fallback | returns UNVERIFIED | all fail | — | label correct |
| router | correct tool per mock | full pipeline | fragrantica→FS | routing |
| analytics | log write/read | — | real fetch | row |
| domain_memory | weight update | — | after 5 fetches | shift |
| adapters | fixture parse | — | live parse | fields |

Live verification is PRIMARY gate. Unit tests secondary.

---

## 12. Logging / Monitoring / Metrics / Analytics / Error / Recovery

**Logging:** JSON to `~/.hermes/fetcher/logs/fetch.log`. Each fetch: ts, domain, executor, latency_ms, success, error, cache_hit.

**Monitoring:** `fetcher/cli.py status` shows executor availability + per-domain success rate (rolling 100).

**Metrics:** success_rate(domain,tool), avg_latency(tool), cost_estimate(tool), cache_hit_rate.

**Analytics (extended):** tool, latency, memory_mb, cpu_pct, cache_hit, cache_miss, retry_count, fallback_count, proxy_used, browser_profile, response_size, extraction_ms, normalization_ms, timestamp.

**Error Reporting:** executor fail → router picks next capability-matching → escalate (CF→FlareSolverr, JS→Browser) → all fail → FallbackPolicy (UNVERIFIED). Never crash pipeline.

**Recovery:**
```
executor fails
 → next capability-matching executor
 → CF detected → FlareSolverr
 → JS needed → BrowserExecutor (Crawl4AI)
 → all fail → FallbackPolicy → UNVERIFIED Document
```

---

## 13. Domain Memory (behavioral, not just stats)

Per domain stores:
- best_executor
- avg_latency
- last_success_ts
- common_failures (list)
- best_extraction_strategy
- recommended_cache_ttl
- login_frequency (if any)
- rate_limit_pattern (if observed)

Learned from Analytics. Router consults Domain Memory to prefer proven path.

---

## 14. Content Cache (stores everything)

On cache hit (ETag/Last-Modified valid):
- markdown (from Crawl4AI)
- structured_data (JSON)
- screenshots
- metadata
- raw HTML

No re-processing. Cache key = normalized URL + executor + capability hash.

---

## 15. Adapters (own all domain logic)

`Adapter` base provides:
- `preferred_executor`: which executor to try first
- `retry_policy`: max retries, backoff
- `rate_limit`: min interval between requests
- `cache_ttl`: per-site cache duration
- `content_extractor`: how to pull fields from Document
- `normalizer`: site-specific Document cleanup
- `validation_rules`: assert extracted data shape

Router does NOT hardcode domain logic. Adapter owns it.

---

## 16. Implementation Priority

| Priority | Items |
|----------|-------|
| CRITICAL | T001–T013 (1a+1b): Foundation + FlareSolverr → Fragrantica unblocked |
| HIGH | T014–T017 (1c): Crawl4AI → JS sites |
| HIGH | T018–T020 (2): Router + Registry |
| MEDIUM | T021–T023 (3): Analytics + Domain Memory |
| LOW | T026–T028 (5): Planner/Concurrency/Policy |
| TECH DEBT | BrowserAct stub (deferred). Content cache lightly used until Phase 3. |
| BACKLOG | Multi-agent orchestration, proxy rotation service, PDF pipeline. |

---

## 17. Deliverables (per-phase visible value)

| Phase | User-visible value | Proof |
|-------|-------------------|------|
| 1a | Can query static sites (Bing, GitHub) via Document | Bing fetch returns Document |
| 1b | **Can query Fragrantica** (Cloudflare solved) | Live Fragrantica HTML |
| 1c | **Can query Shopee/Google** (JS rendered + extracted) | Live markdown Document |
| 2 | System routes correctly per domain automatically | Router test output |
| 3 | System learns per-domain best path | Memory weight shift |
| 5 | Complex queries decomposed | Planner test |
| 6 | Production-ready, observable, CLI usable | Final verification log |

---

## 18. Git Strategy

- Local commits at phase milestone ONLY:
  - `Phase 1a complete`
  - `Phase 1b complete`
  - `Phase 1c complete`
  - `Phase 2 complete`
  - `Phase 3 complete`
  - `Phase 5 complete` (if reached)
  - `Phase 6 complete` (if reached)
- NO push. NO merge. NO remote. All local.
- Commit message style: concise, imperative, no emoji (per AGENTS.md).

---

## 19. Completion Checklist (production-ready)

- [ ] fetcher/ imports cleanly
- [ ] Executor ABC enforces 8 methods
- [ ] BrowserExecutor ABC separates Router from Crawl4AI
- [ ] Document contract returned by ALL executors identically
- [ ] curl_cffi: Bing → Document ✅
- [ ] cloudscraper: simple CF → Document
- [ ] FlareSolverr: **Fragrantica accessible** ✅ (live)
- [ ] Crawl4AIExecutor: Shopee/Google → markdown Document ✅ (live)
- [ ] FallbackPolicy: all-fail → UNVERIFIED Document
- [ ] Cookie Store: cf_clearance reused (no re-solve)
- [ ] Content Cache: markdown+JSON+screenshots cached
- [ ] Capability Registry: YAML loaded, 16 capabilities
- [ ] Adaptive Router: selects by capability+analytics+cost
- [ ] Analytics: extended telemetry logged
- [ ] Domain Memory: behavioral learning works
- [ ] Adapters: own preferred executor/retry/rate/ttl/extractor/normalizer/validation
- [ ] Fragrantica adapter: parses perfume data
- [ ] Shopee adapter: parses price/data
- [ ] Google adapter: parses search results
- [ ] Reddit adapter: parses (Jina or direct)
- [ ] GitHub adapter: curl-only
- [ ] Logging: structured logs present
- [ ] Error recovery: graceful degradation verified
- [ ] Hermes CLI: `fetcher` command usable
- [ ] Final live verification: all sites tested, evidence in DELIVERY_LOG.md
- [ ] BrowserAct: stub only, noted deferred (payment)

---

## 20. Autonomous Execution & Reporting Rules

- Execute T001→T032 sequentially. No stop between tasks.
- Stop ONLY for: login / password / OTP / payment / undecidable.
- Report at: phase complete / major blocker / architecture change due to evidence / production-ready.
- BrowserAct: NOT installed, NOT integrated. Stub interface only.
- Docker fallback: if apt fails, use pip flaresolverr or Playwright direct. Autonomous.
- DELIVERY_LOG.md: append each milestone (ts, task ID, what done, verify cmd+output, files).

**This is the baseline. Execution begins now.**
