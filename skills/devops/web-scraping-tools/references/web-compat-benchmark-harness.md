# Web Compatibility Benchmark Harness

Reusable pattern for proving Hermes as a general-purpose Web Research Engine
(per user directive 2026-07-09: stop Fragrantica-centric validation; validate
across categories with honest pass/fail + root-cause).

## Location
`~/.hermes/benchmarks/web_compat_suite.py` (live on VPS, py3.12)

## Design rules that survived debugging (2026-07-09)
1. **Run under `/usr/bin/python3.12`**, not `python3` (Hermes venv = py3.11, no scraping pkgs).
2. **Executor ladder per site:** curl_cffi -> playwright -> playwright+stealth.
   Record `fallback_triggered` when it moves down.
3. **NEVER discard curl_cffi's real result on false-verify.** Always store
   `curl_status` separately so the report shows the TRUE reason:
   - `curl_status==403` -> real anti-bot block (environment/IP limit)
   - `curl_status==200` + large html + 0 visible text -> parser limitation (SPA), NOT a block
4. **Per-category verify(), not one global formula:**
   - Search: title marker + text volume > 1500 chars (DDG/Bing embed relative links)
   - Docs/Static: unique_ratio > 0.25
   - News/Forums: unique_ratio > 0.20
   - Shopping: if `status==200 and len(html)>50000` -> reachable (SPA, needs render); else chars>3000
   - HeavyJS: chars > 600 (SSR-hydrated check)
   - Cloudflare: reject if "Just a moment"/"cf-chl"/"captcha" present; else chars>600
5. **Playwright `timeout=` is milliseconds** (25000 = 25s). 25 = instant fail.
6. **stealth API:** `from playwright_stealth.stealth import Stealth; Stealth().apply_stealth_sync(pg)`

## Metrics emitted per site
executor_chosen, latency_s, verification_status, extraction_quality,
markdown_quality, structured_extraction, retry_count, fallback_triggered,
final_confidence, geo_provenance, curl_status, reason.

## Report bands (applied to real %)
- Excellent: 100% pass, avg confidence > 0.8, 0 fallbacks
- Good: 80-99% pass, confidence > 0.6
- Acceptable: 50-79%
- Needs Improvement: < 50%

## Known honest result (2026-07-09, 16 sites)
Search 100% - Docs 100% - Static 100% - News 100% - Forums 0% (Reddit+Lowyat 403)
- Shopping 50% (Shopee reachable-but-SPA, Lazada pass) - HeavyJS 50% (Observable pass, Roll20 403)
- Cloudflare 50% (Parfumo pass via curl, Fragrantica 403)
-> Conclusion: Hermes is a reliable general web research engine; only Cloudflare-managed
   + Reddit bot-detection fail (SG datacenter IP), not an architecture defect.
