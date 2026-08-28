---
name: web-scraping-tools
description: Anti-bot bypass tools and techniques for accessing web content from restricted environments (VPS with datacenter IP). Covers TLS fingerprint spoofing, Cloudflare challenge solvers, stealth browser automation, and self-hosted search aggregators.
---

# Web Scraping Tools — Anti-Bot Bypass Stack

## When to Use

- Browser tool is blocked by Cloudflare, CAPTCHA, or IP-based blocking
- Web search returns blocked/empty results
- Need to access Fragrantica, Google, Shopee, or other heavily protected sites
- The VPS IP (datacenter) triggers bot detection on every target

## Architecture: Multi-Layer Pipeline

Sites that block bots employ different detection methods. A single tool won't solve all — use a layered approach:

```
Layer 1: curl_cffi
  (TLS fingerprint spoofing — fastest, bypasses JA3/HTTP2 checks)
  ↓ If 403/503/Cloudflare/blocked
Layer 2: cloudscraper
  (Cloudflare JS challenge solver — handles simpler Turnstile deployments)
  ↓ If still blocked
Layer 3: FlareSolverr
  (Real headless Chromium — solves Cloudflare Managed Challenge)
  ↓ If still blocked
Layer 4: puppeteer-extra + stealth plugin
  (Full browser fingerprint randomization — last resort)
```

## Tool Details

### Layer 1: curl_cffi (TLS Fingerprint Spoofing)

**Install:** `pip install curl_cffi` (already done on this VPS)
**Usage:**
```python
from curl_cffi import requests
r = requests.get("https://example.com",
                 impersonate="chrome",   # "chrome" maps to latest; "chrome120" also valid
                 timeout=20)
# NOTE: curl_cffi does NOT accept follow_redirects= kwarg. It follows redirects by default.
```
**Proven on this VPS (2026-07-09, python3.12):**
- ✅ DuckDuckGo HTML (`html.duckduckgo.com/html/?q=`) — 200, real results
- ✅ Bing Search — 200, real results
- ✅ GitHub, MDN, Wikipedia, Python Docs, BBC — 200, full content
- ✅ Berita Harian — 200 (only 770 chars visible text, low but pass)
- ✅ Lazada MY — 200, 7.4K chars
- ✅ Parfumo — 200, 8.9K chars (curl works; NOT uniformly CF-blocked)
- ✅ Observable (SPA) — 200, 7.4K chars from SSR
- ❌ Reddit — 403 (bot detection)
- ❌ Lowyat.NET — 403 (Cloudflare "Just a moment...")
- ❌ Roll20 — 403 (Cloudflare)
- ❌ Fragrantica — 403 (Cloudflare "Just a moment...")
- ⚠️ Shopee MY — 200 but 0 visible text (JS SPA shell, 176KB HTML). Reachable, needs JS render. NOT a hard block.

### CRITICAL: Python interpreter mismatch on this VPS (2026-07-09)

`curl_cffi`, `playwright`, `playwright_stealth` are installed for **`/usr/bin/python3.12`** (user site `~/.local/lib/python3.12/site-packages`), NOT the Hermes venv that `python3` resolves to (`/home/ubuntu/.hermes/hermes-agent/venv/bin/python3`, py3.11.15).

**If you run a scraping harness under `python3` it will ModuleNotFoundError on all three.** Always invoke with `/usr/bin/python3.12` explicitly, or write the harness as a `.py` file and run `python3.12 script.py`. Do NOT rely on `sys.executable` inside a subprocess launched from the Hermes venv.

### playwright_stealth correct API (2026-07-09)

The package `playwright_stealth` exposes `stealth` as a **submodule**, not a callable. Correct usage:
```python
from playwright.sync_api import sync_playwright
from playwright_stealth.stealth import Stealth   # NOT: from playwright_stealth import stealth_sync
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, args=["--no-sandbox"])
    pg = b.new_page()
    Stealth().apply_stealth_sync(pg)             # correct method name
    pg.goto(url, wait_until="domcontentloaded", timeout=25000)  # ms, NOT seconds
```
Pitfalls found: `stealth_sync` import fails; `stealth(page)` as module-call fails (TypeError module not callable); Playwright `timeout=` is in **milliseconds** (25000 = 25s, not 25ms — a 25ms timeout silently fails every goto).

### Playwright browser binary

Chromium IS installed: `~/.cache/ms-playwright/chromium-1228` + `chromium_headless_shell-1228`. No need to run `playwright install`. Launch with `args=["--no-sandbox"]` (root on VPS).

### Layer 2: cloudscraper

**Install:** `pip install cloudscraper` (already done on this VPS)
**Usage:**
```python
import cloudscraper
scraper = cloudscraper.create_scraper(
    browser={'browser': 'chrome', 'platform': 'windows', 'desktop': True}
)
r = scraper.get("https://example.com")
```
**Proven on this VPS (2026-07-08):**
- Same results as curl_cffi for most sites
- Not effective for modern Cloudflare Managed Challenges

### Layer 6: Chrome Extension Turnstile Bypass (turnstilePatch)

**When to use:** When even a stealth browser through a proxy fails to auto-solve Cloudflare Turnstile on signup/login pages. This patches Turnstile's bot-detection JS at the execution level rather than just faking browser fingerprints.

**How it works:** A Chrome extension (`turnstilePatch`) that runs before page load and patches `MouseEvent.prototype.screenX` and `screenY` to return random realistic values. Cloudflare Turnstile checks these properties to determine if a human with a real mouse is using the browser. Patching them tricks Turnstile into thinking a real user is present.

**The extension's script.js:**
```javascript
function getRandomInt(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}
let screenX = getRandomInt(800, 1200);
let screenY = getRandomInt(400, 600);
Object.defineProperty(MouseEvent.prototype, 'screenX', { value: screenX });
Object.defineProperty(MouseEvent.prototype, 'screenY', { value: screenY });
```

**Proven tool using this method:** `ReinerBRO/grok-register` (GitHub, 361⭐) automates xAI/Grok account creation using:
- Python's DrissionPage (browser automation library, alternative to Playwright)
- turnstilePatch Chrome extension (at `turnstilePatch/` in the repo)
- DuckMail API (api.duckmail.sbs) for temp emails — avoids QRYPTY captcha rate limits
- Xvfb for headless server support
- ~35 seconds per account, ~90% success rate
- Auto-extracts SSO cookie after registration for Grok API use

**Pitfalls:**
- The turnstilePatch extension patches Turnstile at the **JS execution level** inside the page, NOT at the proxy/network level. A **FLAGGED PROXY IP** still gets a hard CF block (HTTP 403 "Sorry, you have been blocked") BEFORE Turnstile even loads. The extension only helps when the challenge page (Turnstile widget) IS presented.
- For IP pre-blocks (hard 403), a residential proxy or different egress IP is still required regardless of the extension.
- DuckMail API requires a Bearer token obtained by registering at duckmail.sbs and extracting from browser DevTools. Without it, the tool cannot create temp emails.
- Python 3.14 has TLS issues with curl_cffi — use Python 3.12/3.13.
- **TIMING CRITICAL:** The extension must run at `document_start` (set in manifest.json) before any page scripts load. Injecting `turnstilePatch` script.js via `browser_console()` AFTER the page has loaded is too late — the Turnstile widget has already initialised and collected browser-integrity signals. The Hermes browser tool DOES NOT support loading Chrome extensions; for `document_start` patching, DrissionPage or Playwright must be used to launch a real Chromium browser with the extension loaded (`--load-extension=path/to/turnstilePatch`).
- **Auth0 + Turnstile quirk (2026-07-14):** Even with a valid Turnstile token (752-char token in the hidden captcha field), Auth0 forms may reject form submission from automated browsers on datacenter IPs. The page stays on the same step without advancing, no visible error. This suggests Auth0 performs server-side session integrity checks beyond the Turnstile token. The VLESS proxy + Playwright approach (Layer 5) is more likely to succeed for Auth0-gated signups.

**IP reputation degradation watch (2026-07-14):** The VLESS proxy IP (DigitalOcean, same class as the tool's proxy) that worked 2 days ago is now flagged by Cloudflare. Datacenter IPs degrade over time as abuse signatures accumulate. Plan for periodic proxy rotation even when using turnstilePatch.

### FLARESOLVERR

**Installation requires Docker:**
```bash
apt install docker.io
docker pull flaresolverr/flaresolverr
docker run -d --name flaresolverr -p 8191:8191 flaresolverr/flaresolverr
```

**Usage via Python:**
```python
import requests
resp = requests.post("http://localhost:8191/v1", json={
    "cmd": "request.get",
    "url": "https://www.fragrantica.com/...",
    "maxTimeout": 60000
})
data = resp.json()
html = data.get("solution", {}).get("response")
```
**NOT yet installed on this VPS.** Recommended as highest-impact next step.

### Layer 4: Puppeteer Extra + Stealth (Node.js)

**Node.js is already available** (v22.23.1 on this VPS).
**Install:**
```bash
apt install chromium-browser
npm install puppeteer puppeteer-extra puppeteer-extra-plugin-stealth
```

### Layer 5: VLESS Proxy + Playwright Stealth (async) — PROVEN on x.ai/Cloudflare

**When to use:** Cloudflare Managed Challenge ("Just a moment...") blocks even
curl_cffi AND a local headless browser from the VPS datacenter IP. A real
browser through a proxy with a DIFFERENT egress IP can solve the Turnstile.

**Key insight (2026-07-13, verified on x.ai):** The proxy egress does NOT
need to be residential. x.ai returned HTTP 403 (hard "abusive traffic" block)
direct from the VPS IP, but a managed-challenge page via a VLESS tunnel whose
egress was ALSO a datacenter IP (DigitalOcean, 159.89.203.211) — a real
Playwright-stealth browser SOLVED the Turnstile and loaded the signup page.
Cloudflare's managed challenge is solvable by a genuine browser UA + JS
execution; the hard block is IP-reputation, the managed challenge is
browser-integrity. A stealth browser passes integrity even from a flagged IP.

**Step 1 — xray-core as local SOCKS5 proxy:**
```bash
# Download xray-core (linux amd64) — already cached at /tmp/xray on this VPS
mkdir -p /tmp/xray && cd /tmp/xray
curl -sL -o xray.zip "https://github.com/XTLS/Xray-core/releases/download/v1.8.24/Xray-linux-64.zip"
unzip -o xray.zip -d xray_bin/ && chmod +x xray_bin/xray
```
Config (`/tmp/xray/config.json`) — VLESS → SOCKS5 :1080:
```json
{
  "inbounds": [
    {"port": 1080, "protocol": "socks", "settings": {"udp": true}, "tag": "socks-in"},
    {"port": 8118, "protocol": "http", "tag": "http-in"}
  ],
  "outbounds": [{
    "protocol": "vless",
    "settings": {"vnext": [{
      "address": "<PROXY_HOST>", "port": <PROXY_PORT>,
      "users": [{"id": "<UUID>", "encryption": "none"}]
    }]},
    "streamSettings": {
      "network": "ws",
      "wsSettings": {"path": "<WS_PATH>", "headers": {"Host": "<WS_HOST>"}}
    },
    "tag": "vless-out"
  }]
}
```
Run: `./xray_bin/xray run -c config.json &` (background). Verify egress:
`curl -s --socks5-hostname 127.0.0.1:1080 https://api.ipify.org`

**Step 2 — Playwright async + stealth through the proxy:**
```python
from playwright.async_api import async_playwright
from playwright_stealth import Stealth   # submodule, NOT stealth_async

async with Stealth().use_async(async_playwright()) as p:
    browser = await p.chromium.launch(
        headless=True,
        proxy={"server": "socks5://127.0.0.1:1080"},
        args=["--disable-blink-features=AutomationControlled",
              "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"])
    ctx = await browser.new_context(viewport={"width":1920,"height":1080},
                                   locale="en-US", timezone_id="America/New_York")
    page = await ctx.new_page()
    await page.goto("https://accounts.x.ai/sign-up", wait_until="domcontentloaded", timeout=45000)
    # Cloudflare Turnstile auto-solves in a real browser; poll title for ~90s
```
**Verified result:** x.ai signup page loaded (`Title: Create Your Grok Account`),
"Sign up with email" clickable, email form fillable. Bypass is real, not a
timeout artifact.

**Pitfall — playwright_stealth async API:** `Stealth().use_async(...)` wraps
the playwright context manager (applies init scripts to every page). Do NOT call
`stealth_async(page)` — that symbol does not exist in this package version
(2.0.3). Use `from playwright_stealth import Stealth` and the `use_async`
context manager.

**Pitfall — egress IP reputation still matters for HARD blocks:** If the
target serves a hard "Blocked due to abusive traffic" page (not a Turnstile),
no browser will pass it from a datacenter IP. That needs residential egress.
The managed-challenge solvable case is the common one for login/signup flows.

**SYNC API also proven (2026-07-13):** `from playwright_stealth import Stealth; Stealth().apply_stealth_sync(page)` works identically to the async `use_async` wrapper. Use sync when the rest of your script is `sync_playwright`.

**End-to-end Grok/xAI signup via proxy — see `references/xai-grok-signup-proxy.md`** for the full flow: email submit → QRYPTY inbox code read → single-input code entry → account setup. Key findings (verified 2026-07-14): (1) verification code is 6-char alphanumeric (`XXU-25B` format) entered into a SINGLE `input[name='code']` with maxlength=6, NOT individual boxes; (2) after code confirmation, the "Complete your sign up" page has a **Cloudflare Turnstile** widget that cannot be auto-solved from a headless datacenter VPS — requires either residential egress or manual completion; (3) xAI rate-limits verification codes per email ("Too many validation codes sent"); (4) QRYPTY domain (qrypty.com) is accepted by xAI; Mail.tm domains (web-library.net) are rejected with "Your email domain has been rejected".

### SearXNG (Self-Hosted Search)

**What:** Self-hosted meta-search engine aggregating 70+ providers. Fixes search-engine blocking permanently.
**Installation:** Docker recommended (`docker pull searxng/searxng`)
**NOT yet installed on this VPS.** Recommended for search-intensive workflows.

## Quick Reference: Sites vs curl_cffi (verified 2026-07-09, py3.12, SG VPS IP)

| Site | curl_cffi status | Reachable? | Notes |
|------|-----------------|------------|-------|
| DuckDuckGo HTML | 200 | ✅ | Real results. Use `html.duckduckgo.com/html/?q=` not `/?q=` |
| Bing Search | 200 | ✅ | Real results |
| GitHub | 200 | ✅ | Full repo/content |
| MDN | 200 | ✅ | Full article body |
| Wikipedia | 200 | ✅ | Full article |
| Python Docs | 200 | ✅ | Full doc section |
| BBC | 200 | ✅ | Headlines + body |
| Berita Harian | 200 | ✅ | Only 770 visible chars (low but pass) |
| Lazada MY | 200 | ✅ | 7.4K chars |
| Parfumo | 200 | ✅ | 8.9K chars — curl WORKS (not uniformly blocked) |
| Observable | 200 | ✅ | SPA, SSR content present |
| Reddit | 403 | ❌ | Bot detection on SG IP |
| Lowyat.NET | 403 | ❌ | Cloudflare "Just a moment..." |
| Roll20 | 403 | ❌ | Cloudflare |
| Fragrantica | 403 | ❌ | Cloudflare "Just a moment..." (stress-test only) |
| Shopee MY | 200 | ⚠️ | 176KB JS shell, 0 visible text. Reachable, needs JS render |

**Summary pattern:** ~69% of tested categories pass via curl_cffi alone. Only Cloudflare-managed + Reddit bot-detection fail. Shopee is a parser-edge-case, not a block.

## Pitfalls

- **Parfumo is NOT Cloudflare-blocked** — they return HTTP 404 with "Access Denied" body to hide that it's an anti-bot measure. Don't confuse with Cloudflare. (2026-07-09: curl_cffi got 200 on Parfumo root — it IS reachable; specific pages may 404.)
- **Shopee MY is reachable, not hard-blocked** — curl_cffi returns 200 with a 176KB JS SPA shell (0 visible text after script stripping). This is a PARSER limitation, not a block. Don't mark 200/large-HTML as FAIL. If `status_code==200 and len(html)>50000`, the page is reachable; full content needs JS render.
- **Reddit / Lowyat / Roll20 / Fragrantica = real 403 blocks** from the SG datacenter IP. curl gets 403, Playwright gets the CF "Just a moment..." interstitial. These are environment/IP limitations, not architecture flaws.
- **Benchmark harness anti-pattern (2026-07-09):** If your verify() rejects curl_cffi's content and falls through to Playwright, the final report shows "FAIL via playwright" and HIDES the real curl_status (e.g. 403 vs 200). Always record `curl_status` separately and report the TRUE failure reason (anti-bot 403 vs parser limitation). Discarding the first executor's real result produces false 0% categories.
- **Playwright `timeout=` is milliseconds** — `timeout=25` = 25ms = instant failure. Use `timeout=25000` for 25s. This silently breaks every goto if missed.
- **Never run scraping code under `python3` (Hermes venv)** — use `/usr/bin/python3.12`. See interpreter-mismatch note above.
- **Don't retry the same failed tool 3 times** — if curl_cffi returns 403, skip to the next layer. The user explicitly prefers fast dead-end recognition (pivot rule).
- **Clarify email intent before signup (2026-07-13 correction):** If a user
  provides an email AND asks to "create an account," confirm the email is NOT
  already tied to an EXISTING account they want to access (e.g. a purchased
  subscription). Using it for signup can trigger a conflicting verification
  flow. Ask: "This email for a NEW account, or login to an existing one?"
  before initiating signup. The user explicitly corrected this: an email they
  handed over was for a bought SuperGrok account, not for fresh signup.

## Blocked-Source Research Fallback (job postings, company profiles, etc.)

When the research target is a bot-blocked page (e.g. an Indeed job posting behind
Cloudflare "Additional Verification Required"), follow this ladder BEFORE declaring a
Data Gap. The #1 mistake is burning 15+ attempts on **plain `curl` + reader proxies** —
plain curl (even with a browser UA) has no TLS impersonation and gets 403/CF from the
datacenter IP every time, which produces a FALSE "everything is blocked" conclusion.

**Correct order:**
1. `curl_cffi` with `impersonate="chrome120"` — first tool, not last resort. (See Layer 1.)
2. If 403/CF -> `cloudscraper`, then `FlareSolverr` (real Chromium), then Playwright stealth.
3. Search-engine fallback: query the target's unique ID/title via DDG-HTML or Bing with
   curl_cffi (both documented 200 on this VPS). Do NOT assume search is also blocked —
   it usually is NOT when curl_cffi is used.
4. Reader-proxy services (e.g. `r.jina.ai/<url>`) are NOT a guaranteed bypass. Observed
   2026-07-13: jina.ai returned Cloudflare's "Additional Verification Required" page for
   an Indeed origin — the SAME CF interstitial as a direct fetch. Use only as a secondary probe.
5. If ALL layers fail: report a genuine **Data Gap** with method-by-method failures, then
   ask the user to **paste the source text** (job description, page HTML). Do NOT fabricate
   the blocked content (salary, legitimacy, payment method). This pivot is the user-approved
   "fast dead-end recognition" rule — state the gap and request the paste.

**Pitfall — wrong tool class gave a false "everything blocked" result (2026-07-13):**
A session probed Indeed + Google/Bing/DDG/Brave/Mojeek/Yahoo/SearXNG with plain `curl`
and reader proxies, concluded "all engines blocked," and reported a Data Gap. That
conclusion is UNVERIFIED: `curl_cffi` (the documented bypass) was never tested, and the
skill's own table shows DDG-HTML/Bing return 200 via curl_cffi. Always start with
curl_cffi; plain curl is not evidence of a hard block.

## Verification

**Reusable benchmark harness:** see `references/web-compat-benchmark-harness.md` for the
proven multi-category compatibility suite (executor ladder, per-category verify, curl_status
visibility). This is the user-approved "baseline rasmi Hermes" pattern.

**Custom captcha solving:** see `references/browser-captcha-solving.md` for
programmatic solving of all 5 QRYPTY captcha variants (row-typing, color-counting,
color-typing, different-character, shape-counting) via JS DOM inspection. Proven on
QRYPTY Mail registration (2026-07-13).

**SPA API reverse engineering:** see `references/spa-api-reverse-engineering.md` for
techniques to extract API endpoints from JS bundle files via curl + grep. Proven on
QRYPTY Mail (2026-07-13).

**Temp-mail OTP reading (ShadowMail):** see `references/shadowmail-temp-inbox-api.md`
for reading verification codes from `*.nexaroin.com` / ShadowMail-hosted temp domains
via their JSON API. Proven on x.ai signup (2026-07-13).

**Auth0 + Turnstile signup (Tavily):** see `references/tavily-signup-flow.md`
for the full flow breakdown: Auth0 URL structure, Turnstile sitekey, form field details,
observed failures from datacenter IP, and recommended bypass approaches.
Documented after a 2026-07-14 attempt.

```bash
script for bulk QRYPTY account creation. Handles all 5 captcha variants
(see references/browser-captcha-solving.md). Run with `/usr/bin/python3.12`.

```bash
# Test curl_cffi against Fragrantica
python3 -c "
from curl_cffi import requests
r = requests.get('https://www.fragrantica.com/perfume/Lattafa/Yara-62421.html',
                 impersonate='chrome120', timeout=15)
print(r.status_code, 'BLOCKED' if 'Just a moment' in r.text else 'CONTENT')
"

# Test cloudscraper against Parfumo
python3 -c "
import cloudscraper
s = cloudscraper.create_scraper()
r = s.get('https://www.parfumo.com/Perfumes/Lattafa/Yara')
print(r.status_code, 'BLOCKED' if 'Access Denied' in r.text else 'CONTENT')
"
```
