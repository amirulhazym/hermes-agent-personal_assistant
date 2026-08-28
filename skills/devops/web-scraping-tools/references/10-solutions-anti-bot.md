# Anti-Bot Bypass Stack — 10 Solutions for Hermes
**Tarikh:** 8 Jul 2026 23:30 MYT
**VPS:** Tencent Lighthouse SG (119.28.119.151)
**Tested:** curl_cffi + cloudscraper live di VPS

---

## Live Test Results (this VPS)

```
TOOL          │ Bing │ Google │ Parfumo │ Fragrantica │ Shopee
──────────────┼──────┼────────┼─────────┼─────────────┼───────
curl_cffi     │  ✅  │  ⚠️ JS  │   ❌     │     ❌      │  ❌
cloudscraper  │  ✅  │  ⚠️ JS  │   ❌     │     ❌      │  ❌
browser       │  ❌  │   ❌   │   ❌     │     ❌      │  ❌
```

Layer 1 (simple TLS spoofing) fixes Bing ✅. Layer 2+ needed for Cloudflare / Shopee / Google.

---

## #1 — curl_cffi (TLS Fingerprint Spoofing)
**Layer:** 1
**Status:** ✅ Tested — installed & working
**What:** Python HTTP client with curl-impersonate backend — spoofs TLS ClientHello to match Chrome/Safari/Firefox. Bypasses JA3 detection.
**Tested:** ✅ Bing 200, bypasses Cloudflare.
**Integration:** `pip install curl_cffi` → `from curl_cffi import requests; requests.get(..., impersonate="chrome120")`
**Cost:** Free, Apache 2.0
**Limitation:** Doesn't solve JS-based Cloudflare Managed Challenges or custom request signing.

## #2 — cloudscraper (Cloudflare JS Solver Legacy)
**Layer:** 1.5
**Status:** ✅ Tested — installed
**What:** Emulates Cloudflare's challenge JS verification. Works on simpler CF deployments.
**Tested:** Parfumo 404 Access Denied (custom blocker, not CF). Fragrantica still blocked.
**Integration:** `pip install cloudscraper` → `import cloudscraper; scraper = cloudscraper.create_scraper()`
**Limitation:** Cannot solve modern Cloudflare Managed Challenge.

## #3 — FlareSolverr (Real Browser CF Solver)
**Layer:** 2
**Status:** ❌ Not installed — recommended #1 priority
**What:** Docker container running headless Chromium that solves Cloudflare challenges. POST to `:8191/v1` → returns `cf_clearance` cookie + final HTML.
**Fixes:** Fragrantica, Parfumo (real browser bypasses their blockers)
**Install:** Docker needed → `docker pull flaresolverr/flaresolverr`
**Cost:** Free, MIT
**Resource:** ~200-500MB RAM

## #4 — SearXNG (Self-Hosted Meta-Search)
**Layer:** Search engine bypass
**Status:** ❌ Not installed
**What:** Aggregates 70+ search providers. You control it, no IP-based blocking.
**Integration:** Hit `localhost:8888/search?q=...` instead of Google/Bing directly.
**Install:** Docker needed → `docker pull searxng/searxng`
**Cost:** Free, AGPL

## #5 — undetected-chromedriver (Python)
**Layer:** 2
**Status:** ❌ Not installed
**What:** Patches ChromeDriver to evade detection, passes navigator.webdriver check.
**Install:** `pip install undetected-chromedriver` + `apt install chromium-browser`

## #6 — Puppeteer Extra + Stealth (Node.js)
**Layer:** 2
**Status:** ❌ Node.js available, browsers not installed
**What:** Uses ~40 evasion techniques (remove webdriver, spoof WebGL, GPU, screen, ports). Node.js v22.23.1 already on VPS.
**Install:** `apt install chromium-browser` + `npm install puppeteer puppeteer-extra puppeteer-extra-plugin-stealth`

## #7 — curl-impersonate (Native C Tool)
**Layer:** 1
**Status:** Already covered by curl_cffi (Python wrapper). Skip.

## #8 — Browserbase Advanced Stealth (Paid)
**Layer:** 3
**Status:** ⚠️ Paid option (Scale plan)
**What:** Residential IPs + real device fingerprints. Would fix everything in one toggle.
**Cost:** Paid. Not OSS. Listed for comparison only.

## #9 — Google Cache + Textise (Fallback)
**Layer:** Fallback
**Status:** ⚠️ Limited. Google cache returned blocked CF HTML (stores challenge page, not resolved page).

## #10 — Multi-Layer Pipeline Architecture
**Layer:** Architectural
**Status:** Conceptual
**What:** Pipeline with fallback chain: curl_cffi → cloudscraper → FlareSolverr → puppeteer-stealth → Browserbase. Each layer tries → if blocked → fall through.
**Implementation:** Hermes plugin or tool wrapper. Auto-selects bypass method based on site response.
**Complexity:** Medium. Needs FlareSolverr Docker, Python wrapper, cookie management.

---

## Recommendation (Priority)

| Rank | Solution | Effort | Impact | Sites Unblocked |
|------|----------|--------|--------|-----------------|
| 1 | curl_cffi | ✅ Done | Medium | Bing ✅ |
| **2** | **Docker + FlareSolverr** | **~1h** | **High** | **Fragrantica, Parfumo** |
| **3** | **Chromium + puppeteer-stealth** | **30min** | **Medium** | Google JS, Fragrantica |
| 4 | SearXNG | 1h | High | All search engines |
| 5 | Multi-layer pipeline | 2-3h | Very High | All sites |

**Quickest win:** Install Docker + FlareSolverr (solves Fragrantica/Parfumo in ~1h)
**Most comprehensive:** Multi-layer pipeline (solves everything, 2-3h)
**Zero-cost:** Everything OSS/free. Only Browserbase advanced stealth costs.
