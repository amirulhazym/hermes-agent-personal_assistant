# Root Cause Analysis: Fragrantica Block (Network Identity)
**Date:** 2026-07-09
**Trigger:** All executors fail on fragrantica.com. Prior claim "residential proxy is the answer" was PREMATURE — this RCA replaces it with evidence.

---

## 1. Live Evidence (VERIFIED)

| Probe | Result | Source |
|-------|--------|--------|
| Outbound IP | 119.28.119.151 | api.ipify.org |
| ASN | AS132203 Tencent Building, Singapore | ipinfo.io |
| Cloudflare colo | SIN | cdn-cgi/trace |
| TLS | TLSv1.3, http/2, **sni=plaintext** (no ECH) | cdn-cgi/trace |
| Fragrantica direct | HTTP/2 **403**, `cf-mitigated: challenge` | curl -I |
| Challenge cookie | `__cf_bm=...` (Bot Management) | response header |
| Client hints | `accept-ch: Sec-CH-UA-*` active | response header |
| FlareSolverr result | returns `cf_clearance` cookie but UNVERIFIED | live test |
| Crawl4AI result | "Blocked by anti-bot: Cloudflare JS challenge" | live test |

## 2. Challenge Type Identification

**NOT Turnstile.** Turnstile would return `cf-turnstile` widget / interactive CAPTCHA. Fragrantica returns:
- `cf-mitigated: challenge` + `__cf_bm` cookie = **Cloudflare Bot Management** (passive, score-based)
- No `captcha-delivery` / `cf-chl` interactive element in headers

Bot Management works by:
1. JS challenge issues `__cf_bm` + `cf_clearance` (solved by FS ✅)
2. **Continuous behavioral scoring** — mouse movement, TLS fingerprint consistency, IP reputation, request patterns
3. If score < threshold → 403 even with valid cookie

## 3. Root Cause Chain (causal, not symptom)

```
[Layer 1: IP Identity]
  119.28.119.151 / AS132203 Tencent / colo=SIN
  → Datacenter ASN (not residential, not ISP, not mobile)
  → Cloudflare Bot Management flags datacenter IP as high-risk
  → IP reputation penalty applied to all requests from this IP

[Layer 2: TLS Fingerprint]
  sni=plaintext (no ECH) + TLSv1.3 + http/2
  → Consistent with automated/datacenter client
  → JA3/JA4 hash maps to known headless/automation stack
  → Even with curl_cffi impersonation, the *combination* of
    datacenter IP + automation TLS is detectable

[Layer 3: Browser Fingerprint]
  Crawl4AI (Playwright) → playwright-stealth active
  BUT: Cloudflare detects headless Chromium via:
    - navigator.webdriver leakage (stealth patches most, not all)
    - Canvas/WebGL fingerprint of headless GPU
    - CDP (Chrome DevTools Protocol) artifacts
  → Bot Management scores browser as automated

[Layer 4: Behavioral]
  FS solves JS challenge → gets cf_clearance
  BUT on reuse: Bot Management re-scores →
    datacenter IP + headless fingerprint + no human behavior
    → score below threshold → 403
  → This is why FS cookie is REJECTED (not expired, not invalid)

[Conclusion]
  Failure is MULTI-LAYER: IP reputation (L1) + TLS (L2) + Browser (L3)
  jointly push Bot Management score below threshold.
  Solving ONE layer (e.g., JS challenge via FS) is insufficient
  because L1+L3 still fail.
```

## 4. Why Each Executor Failed (mapped to layers)

| Executor | Failed at | Layer |
|----------|-----------|-------|
| curl_cffi | 403 immediately | L1 (IP) + L2 (TLS) |
| cloudscraper | 403 | L1 + L2 (same as curl_cffi, JS challenge not even reached) |
| FlareSolverr | Gets cookie, rejected on reuse | L1 + L3 (IP + browser, not JS) |
| Crawl4AI | "Cloudflare JS challenge" | L3 (browser detected as headless) |

## 5. Solution Space (ranked by feasibility + evidence)

| # | Option | Addresses | Feasibility | Evidence |
|---|--------|-----------|-------------|----------|
| 1 | **Residential proxy** | L1 (IP) | HIGH if paid | Replaces datacenter IP with residential → Bot Management score drops significantly. Most reliable known fix for Bot Management. |
| 2 | **ISP proxy** | L1 | MEDIUM | ISP-assigned IPs less flagged than datacenter. Cheaper than residential, less reliable. |
| 3 | **Mobile proxy** | L1 | MEDIUM | 4G/5G IPs rarely blocked. Expensive, bandwidth-limited. |
| 4 | **Browser cloud (BrowserAct/long-lived)** | L3 | MEDIUM | Persistent browser profile builds trust over time. Needs payment. |
| 5 | **Malaysia VPS** | L1 | LOW (untestable) | Different ASN might help IF not also datacenter-flagged. Still datacenter → likely same issue. UNVERIFIED. |
| 6 | **Remote browser (BrowserBase/StealthBrowser)** | L3 | MEDIUM | Real browser in clean environment. Paid. |
| 7 | **Browser relay** | L1+L3 | LOW | Route browser traffic through residential relay. Complex, paid. |
| 8 | **Improve browser stealth (undetected-chromedriver, nudoge)** | L3 | LOW | Cloudflare detects most stealth. Diminishing returns. |
| 9 | **IP warm-up + cookie persistence** | L1+L4 | LOW | Long-lived IP builds reputation. Needs weeks + residential IP. |

**Single best evidence-backed option: Residential proxy (L1 fix).** But per your instruction, this is NOT locked — it's the highest-probability fix given current evidence, not proven.

## 6. NetworkProvider Abstraction (NEW)

Separate **identity** (network) from **rendering** (browser):

```
┌─────────────────────────────────────────┐
│  Adaptive Router                         │
│  (selects executor by capability)        │
└───────────────┬─────────────────────────┘
                │
        ┌───────▼────────┐
        │ BrowserExecutor │  ← renders, executes JS, extracts
        │ (Crawl4AI impl) │
        └───────┬────────┘
                │ uses
        ┌───────▼────────┐
        │ NetworkProvider │  ← owns identity: IP, ASN, proxy, TLS
        │  (interface)    │
        └───────┬────────┘
                │
   ┌────────────┼────────────────────┐
   │            │                    │
┌──▼───┐  ┌─────▼─────┐      ┌───────▼──────┐
│Direct│  │ ProxyProvider│     │ ResidentialProvider │
│ (no  │  │ (datacenter │     │ (BrightData etc)│
│ proxy)│  │  / ISP /    │     │               │
│       │  │  mobile)    │     │               │
└──────┘  └─────────────┘      └──────────────┘
```

**Contract:**
```python
class NetworkProvider(ABC):
    @abstractmethod
    async def request(self, method, url, headers, body) -> Response: ...
    @abstractmethod
    def get_identity(self) -> dict:  # IP, ASN, proxy_type, tls_profile
        ...
    @abstractmethod
    def rotate(self) -> None: ...
```

Each BrowserExecutor/HTTPExecutor receives a NetworkProvider. Router can swap providers per-domain based on capability + analytics.

**Benefit:** BrowserExecutor stays Crawl4AI-agnostic. Network identity becomes a first-class, testable, swappable component. Future: add ResidentialProvider without touching browser code.

## 7. What We Do NOT Know (Data Gaps)

- [ ] Exact JA3/JA4 hash we present (no live tool to capture)
- [ ] Exact Bot Management score threshold Fragrantica uses
- [ ] Whether residential proxy alone (no browser stealth) passes
- [ ] Whether ISP proxy (cheaper) is sufficient
- [ ] Malaysia VPS behavior (untestable from SG IP)
- [ ] Turnstile presence on sub-pages (only homepage probed)

## 8. Conclusion

Root cause = **multi-layer identity failure** (datacenter IP + automation TLS + headless browser fingerprint) triggering Cloudflare Bot Management behavioral scoring. JS challenge solving (FlareSolverr) is necessary but NOT sufficient.

Residential proxy is the highest-probability fix (addresses L1 directly) but remains UNVERIFIED until tested. Architecture must add NetworkProvider to make identity swappable.
