# Anti-Bot Bypass Stack — 10 Solutions for Hermes
**Tarikh:** 8 Jul 2026 23:30 MYT
**VPS:** Tencent Lighthouse SG (119.28.119.151)
**Tested:** curl_cffi + cloudscraper live di VPS

---

## Live Test Results (today, this VPS)

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
**Layer:** 1 (anti-TLS-fingerprinting)
**Status:** ✅ Tested — installed & working
**What:** Python HTTP client with `curl-impersonate` backend — spoofs TLS ClientHello to match Chrome/Safari/Firefox exactly. Many anti-bots (JA3 detection) check TLS fingerprint first.
**Tested:** ✅ Bing 200, bypasses their Cloudflare.
**Integration:** `pip install curl_cffi` → `from curl_cffi import requests; requests.get(..., impersonate="chrome120")` — drop-in replacement for `requests`
**Cost:** Free, open source (Apache 2.0)
**Limitation:** Doesn't solve JS-based Cloudflare challenges (Fragrantica) or custom request signing (Shopee).

---

## #2 — cloudscraper (Cloudflare JS Solver Legacy)
**Layer:** 1.5 (anti-Cloudflare-turnstile)
**Status:** ✅ Tested — installed & working for some
**What:** Python lib that emulates Cloudflare's challenge JS verification. Works on simpler Cloudflare deployments.
**Tested:** ✅ Same results as curl_cffi for most sites. Parfumo returned 404 Access Denied (they use a different anti-bot).
**Integration:** `pip install cloudscraper` → `import cloudscraper; scraper = cloudscraper.create_scraper()`
**Limitation:** Cannot solve modern Cloudflare Managed Challenge (Fragrantica). Detected by Parfumo's custom blocker.

---

## #3 — FlareSolverr (Real Browser Cloudflare Solver)
**Layer:** 2 (real-browser Cloudflare solver)
**Status:** ❌ Not installed but recommend #1 priority
**What:** Docker container running headless Chromium that solves Cloudflare challenges and returns cookies+HTML. You make a POST to `http://localhost:8191/v1` → it spins a browser → solves the challenge → returns `cf_clearance` cookie + final HTML.
**How it works:**  FlareSolverr is the standard in the arr-stack (Sonarr/Radarr) community. It reliably handles managed challenges that curl_cffi/cloudscraper cannot.
**Potential fix for:** Fragrantica, Parfumo (bypassing their blockers)
**Installation:** Docker needed (not installed on VPS — `apt install docker.io` + `docker pull flaresolverr/flaresolverr`). Python client: `pip install flaresolverr` or just POST requests.
**Cost:** Free, open source (MIT), self-hosted.
**Resource:** ~200-500MB RAM (headless Chromium).

---

## #4 — SearXNG (Self-Hosted Meta-Search)
**Layer:** Search engine bypass
**Status:** ❌ Not installed
**What:** Self-hosted meta-search engine aggregating 70+ providers (Google, Bing, DuckDuckGo, Brave, Wikipedia, etc.). You own the instance, so no per-IP rate limiting. Fixes the "every search engine blocks my IP" problem permanently.
**Integration:** Hermes would hit `http://localhost:8888/search?q=...` instead of going to Google/Bing directly.
**Installation:** Docker recommended (`docker pull searxng/searxng`) but also has manual install via Python. Docker needed.
**Cost:** Free, open source (AGPL), self-hosted.
**Bonus:** JSON API for programmatic queries. Can be used as a Hermes tool backend.

---

## #5 — undetected-chromedriver (Python)
**Layer:** 2 (stealth browser automation)
**Status:** ❌ Not installed but can test
**What:** Patches Chrome/Chromium WebDriver to evade bot detection. Passes navigator.webdriver check, modifies JS fingerprints, etc. Standard for bypassing Cloudflare managed challenges without FlareSolverr.
**How it works:**  Installs a patched CDP (Chrome DevTools Protocol) client that hides automation traces. Many Cloudflare sites that block regular Selenium work with undetected-chromedriver.
**Installation:** `pip install undetected-chromedriver` + `apt install chromium-browser` (chromium not installed on VPS currently).
**Test method:** If installed, we can test against Fragrantica directly.

---

## #6 — Puppeteer Extra + Stealth (Node.js)
**Layer:** 2 (stealth browser automation)
**Status:** ❌ Not installed but Node.js already available (v22.23.1)
**What:** Node.js library `puppeteer-extra` + `puppeteer-extra-plugin-stealth`. Uses ~40 evasion techniques: removes `navigator.webdriver`, spoofs WebGL, GPU, screen resolution, ports, permissions, Chrome runtime flags.
**Why Node.js works here:** Hermes VPS already has Node.js v22.23.1 + npm 10.9.8. Just need to install Chromium (`apt install chromium-browser`) + npm packages.
**Installation:** `npm install puppeteer puppeteer-extra puppeteer-extra-plugin-stealth`
**Comparison vs #5:** Both solve same problem. Puppeteer has more stealth plugins but heavier. undetected-chromedriver = lighter.

---

## #7 — curl-impersonate (Native Layer 1)
**Layer:** 1 (TLS/HTTP2 fingerprint impersonation)
**Status:** ❌ Not installed but curl_cffi already covers this
**What:** The native C tool that `curl_cffi` wraps. Replaces system `curl` with one that spoofs browser TLS fingerprints. Useful for shell scripts.
**Note:** Already covered by curl_cffi in Python. Only useful if we want to fix `terminal()` shell commands.
**Skippable** since curl_cffi gives us the same capabilities in Python.

---

## #8 — Browserbase Advanced Stealth (Paid Bullet)
**Layer:** 3 (residential proxy + full browser fingerprinting)
**Status:** ⚠️ Paid option (Scale plan)
**What:** Browserbase's advanced stealth mode uses residential IPs + real device fingerprints. The current browser tool runs in "local stealth" which triggered Cloudflare on everything. Upgrading to BROWSERBASE_ADVANCED_STEALTH=true with a Scale plan would fix ALL blocks at once — Fragrantica, Parfumo, Google, Shopee.
**Cost:** Paid (Browserbase Scale plan). Not open source.
**Why list it:** Sometimes building an OSS bypass stack takes weeks. For $15-50/month you get everything working in one toggle. Worth listing for comparison.

---

## #9 — Google Cache + Textise + Alternative Proxies
**Layer:** Fallback / read-only access
**Status:** ⚠️ Partially worked (got Fragrantica HTML but it was blocked content)
**What:** Instead of hitting sites directly, route through Google Cache (`webcache.googleusercontent.com`), textise proxies, or `textise dot iitty`. These serve cached/stripped versions that bypass anti-bot.
**Tested:** ❌ Google cache returned blocked Cloudflare HTML for Fragrantica (the cache doesn't store the resolved page, it stores the challenge page). Limited utility.
**Can work for:** Older cached pages, simple text content. Not reliable.

---

## #10 — Multi-Layer Pipeline Architecture
**Layer:** Architectural (combines all above)
**Status:** Conceptual — recommend implementing
**What:** A request pipeline with fallback chain:
```
curl_cffi → cloudscraper → FlareSolverr → (optional) puppeteer-stealth → Browserbase
```
Each layer tries → if blocked → fall through to next. Implement as a Hermes plugin or tool wrapper.
**Usage:** `hermes_tools.fetch(url)` → auto-selects the bypass method based on site response.
**Implementation:**
1. Try `curl_cffi` (TLS-only, fastest)
2. If blocked (403/503/Cloudflare), try `cloudscraper`
3. If still blocked, try `FlareSolverr` (slowest but most reliable)
4. Cache results + cookies for re-use
**Complexity:** Medium. Needs FlareSolverr Docker container, Python wrapper, and cookie management. But solves the problem permanently.

---

## Recommendation (Priority Order)

| Rank | Solution | Effort | Impact | Sites Unblocked |
|------|----------|--------|--------|-----------------|
| 1 | curl_cffi (layer 1) | ✅ Done | Medium | Bing ✅ |
| **2** | **Install Docker + FlareSolverr** | **1h** | **High** | **Fragrantica, Parfumo** |
| **3** | **Install Chromium + puppeteer-stealth** | **30min** | **Medium** | Google JS, Fragrantica |
| 4 | SearXNG (self-hosted) | 1h | High | All search engines |
| 5 | Multi-layer pipeline plugin | 2-3h | Very High | All sites |

**Quickest win:** Install Docker + FlareSolverr (solves Fragrantica/Parfumo in ~1h)
**Most comprehensive:** Multi-layer pipeline (solves everything but takes 2-3h)
**Zero-cost:** Everything listed is open source / free. Only Browserbase advanced stealth costs money.

---

## Actionable Next Step
Nak aku:
A) Install Docker + FlareSolverr sekarang (solves Fragrantica/Parfumo)
B) Install Chromium + puppeteer-stealth (Node.js)
C) Setup layered pipeline wrapper
D) Kau nak decide dulu based on this document
