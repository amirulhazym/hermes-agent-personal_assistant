---
name: web-research-benchmark
description: Run and interpret the Hermes Web Research Engine (WRE) Compatibility Benchmark. Use when (a) validating WRE capability after changes, (b) establishing/refreshing baseline, (c) comparing a new executor/strategy against the V1 baseline, (d) user says "benchmark", "compatibility", "validate Hermes web". Defines the honest reporting discipline and the known executor pool.
---

# Web Research Engine — Compatibility Benchmark

## When to use
- After ANY change to fetching/extraction/routing/anti-bot in Hermes WRE.
- To prove (or disprove) a capability claim with live evidence, not theory.
- When user wants to know "can Hermes research X website?"

## Core discipline (NON-NEGOTIABLE — user-explicit 2026-07-09)
1. **Invalidate broken harness runs. Do NOT average bad runs into the result.** If the benchmark tool has a bug, the run is INVALID. Re-run after fix. Label discarded runs explicitly (run1, run2...) so they never leak into the final number.
2. **Distinguish limitation types before reporting:**
   - parser limitation (extracted 0 chars but HTTP 200 + large HTML → SPA needs JS render)
   - network limitation (timeout, DNS)
   - anti-bot limitation (403, CF challenge, captcha) — usually ENVIRONMENT (datacenter IP), not architecture
   - architecture limitation (no executor exists for the job)
   - implementation bug (harness wrong, not the site)
   - capability limitation (Hermes genuinely can't)
   - speculation (we guessed, no evidence)
3. **No `idea → architecture → idea` loop without implementation.** Architecture is mature. Change it only from: production evidence, benchmark trend, profiling, scalability, maintainability, reliability — never "prettier architecture."
4. **Every improvement needs justification from ≥1 axis:** implementation evidence, production observation, measurable bottleneck, reliability, maintainability, scalability, DX, ops efficiency, cost, UX, quality, repeatability, observability, testability. If none apply, it's not important yet.
5. **Challenge your own clean results.** If benchmark looks too perfect, the benchmark itself is probably wrong. A benchmark fixed 5× until trustworthy > one accepted without question.
6. **Fragrantica = stress-test/outlier, NOT KPI.** Parfumo (same Cloudflare vendor) passing proves CF is not a universal wall. Don't optimize the whole system for one aggressive domain.

## Executor pool (actual, verified in env)
- `curl_cffi` (TLS-impersonation HTTP) — `/usr/bin/python3.12 -c "from curl_cffi import requests as r; r.get(url, impersonate='chrome')"`
  - NO `follow_redirects` kwarg (curl_cffi follows by default)
- `playwright` (headless chromium) — goto timeout is in **MS**, e.g. `timeout=25000`
- `playwright + stealth` — `from playwright_stealth.stealth import Stealth; Stealth().apply_stealth_sync(page)`

## CRITICAL env gotcha
Packages `curl_cffi`, `playwright`, `playwright_stealth` live in **python3.12 user site** (`~/.local/lib/python3.12`), NOT the Hermes venv (py3.11.15). `python3` in terminal = Hermes venv → ModuleNotFoundError. **Always invoke with `/usr/bin/python3.12`.**

## Harness location
- `~/.hermes/benchmarks/web_compat_suite.py` — run: `cd ~/.hermes/benchmarks && /usr/bin/python3.12 web_compat_suite.py`
- Output: `compatibility_report.md` (pattern table + root-cause), `web_compat_raw.json` (per-site: executor, latency, curl_status, verification_status, extraction_quality, etc.)
- Ladder per site: curl_cffi → playwright → playwright+stealth. `fallback_triggered` = moved down ladder.

## V1 Baseline (2026-07-09, run6 valid)
| Category | Rate | Note |
|----------|------|------|
| Search | 100% | curl_cffi bypasses search bot filters |
| Documentation | 100% | server-rendered, open |
| Static | 100% | same |
| News | 100% | BBC + Berita Harian open |
| Shopping | 100% | SPA shells reachable (200 + 160–462KB); content needs JS render |
| HeavyJS | 50% | Observable passes, Roll20 (403-CF) blocked |
| Cloudflare | 50% | Parfumo passes, Fragrantica (403-CF) blocked |
| Forums | 0% | Reddit (403) + Lowyat (403-CF) — SG datacenter IP flagged |

**Conclusion:** WRE V1 = functional general-purpose engine for ~88% of categories. Gaps are IP-reputation (datacenter) + JS-render-step, both solvable WITHOUT architecture overhaul (residential proxy + render pass).

## Verification of a benchmark run
Before reporting numbers, confirm:
- [ ] Harness ran under `/usr/bin/python3.12` (not Hermes venv)
- [ ] `curl_status` field present (distinguishes 403 blocks from parser limits)
- [ ] No discarded runs leaked into the percentage
- [ ] Shopping SPA early-return (200 + >50KB html) fires before `chars<400` guard
- [ ] Fragrantica isolated as stress-test, not counted in "Hermes fails" narrative
