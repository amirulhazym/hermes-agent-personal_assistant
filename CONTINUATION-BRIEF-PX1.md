# Hermes Agent Overhaul — CONTINUATION BRIEF PX-1 (Research Track)

> **Attach BOTH this file AND `OVERHAUL-EXECUTION-PROMPT.md`.**  
> Also open: `PX1-RESEARCH-TRACK-PLAN.md`  
> P4 is **ON HOLD** — see `CONTINUATION-BRIEF-P4.md` + `docs/superpowers/specs/2026-07-11-phase4-os-vision-HOLD.md`.  
> **Do not touch med logic** (`med_*`, `chain_*`, `med-auto-confirm`, med JSON).

---

## 0. ROLE & MANDATE

You are executor for **PX-1 Research Capability Track** (post-P3, parallel to held P4).

**Goal:** Turn Hermes research from weak DDGS + broken hybrid-web extract into a proper
**Research Expert** (domain owner): deep, cited, verified research with fallbacks —
aligned with OS vision (staged execution, artifact handoff, depth=1/max=3) without
building the full multi-agent OS.

**Principles:** evidence-first · incremental · per-step user go · zero/low cost ·
connect don’t rebuild · Research Expert composes skills/tools (skills ≠ expert).

## 1. HARD CONSTRAINTS

| Rule | Detail |
|---|---|
| No med touch | Never modify med_*, chain_*, med-auto-confirm, med JSON |
| Concurrency | depth=1 / max=3 children **hard default** |
| Cost | Prefer free/self-host; **Tavily needs key + user OK** before enable |
| Paid | No paid service without explicit yes |
| Push | **No git push** unless user says so |
| Secrets | Never print API key values; env names only |
| Context | hy3-free 60% hard stop — fresh session if near limit |
| MJ | Verifier only; only OpenCode changes VPS |

## 2. WHY PX-1 NOW (not full P4)

- P4 multi-agent OS redesign is **held** (too large; vision captured in HOLD doc).  
- PX-1 is a **shippable vertical**: Research Expert + tools — feeds later P4 patterns.  
- Not redundant with P0–P3 med work; does not require finished OS spine to start Fasa 0.

## 3. LIVE STATE (validated 2026-07-13)

| Item | State |
|---|---|
| `web.backend` / search | `ddgs` (weak) |
| `web.extract_backend` | `hybrid-web` |
| Plugin | `~/.hermes/plugins/hybrid-web/` exists |
| trafilatura in venv | **False (missing)** |
| crawl4ai in venv | **False (missing)** |
| playwright in venv | **False (missing)** |
| Singapore VPS | Possible third-party throttle risk |

## 4. USER DECISIONS (2026-07-13)

| Topic | Decision |
|---|---|
| Sequence | Freeze P4 → **PX-1 next** (new session OK) |
| Tavily | **Primary when key ready**; confirm before Fasa 1 config change |
| SearXNG | **Later (Fasa 1b)** — not blocking Fasa 0 |
| Playwright + Chromium | **Yes in Fasa 0** |
| Design skills | Do not delete |
| P4 | ON HOLD |

## 5. PHASED PLAN (execute one Fasa at a time)

### Fasa 0 — Foundation fix (START HERE)
**Objective:** Make extraction work again.

1. Check disk/`free -h` before large installs.  
2. Install in Hermes venv:

```bash
~/.hermes/hermes-agent/venv/bin/pip install trafilatura crawl4ai playwright
~/.hermes/hermes-agent/venv/bin/playwright install chromium
```

3. Verify hybrid-web extract (static + JS URL if possible).  
4. Optional thin Playwright wrapper skill if crawl4ai insufficient.  
5. **STOP** — show install + extract evidence — user gate before Fasa 1.

**Must not:** change med files; enable paid APIs in Fasa 0.

### Fasa 1 — Search backend + fallback
**Primary:** Tavily (after key + go)  
**Fallback:** DDGS always; SearXNG self-host = **1b later**  

Configure primary + simple fallback on error/rate-limit. Benchmark vs DDGS.  
**Gate** before Fasa 2.

### Fasa 2 — Research Expert + pipeline
- `skills/experts/research-expert/SKILL.md`  
- Staged pipeline: plan → search → extract → verify → synthesize → **artifact package**  
- Respect depth=1 / max=3  
**Gate** before Fasa 3.

### Fasa 3 — Platform verification + logging
Cross-check, freshness, contradictions; research trace log (like med_chain_trace).  
Leverage SOUL grounding rules.

### Fasa 4 — Knowledge layer contract (Obsidian prep)
Read/write policy + artifact format; stub Knowledge interface. **Not** full Obsidian product.

### Fasa 5 — E2E validation
One full research workflow; fallback under failure; quality vs baseline.

## 6. REORIENTATION (run first in new session)

```bash
# Local
git -C "F:\AI Prep\OVIS\Hermes Agent\MJay" status
git -C "F:\AI Prep\OVIS\Hermes Agent\MJay" log --oneline -5

# Open
# OVERHAUL-EXECUTION-PROMPT.md
# CONTINUATION-BRIEF-PX1.md
# PX1-RESEARCH-TRACK-PLAN.md
# CONTINUATION-BRIEF-P4.md (HOLD only)

# VPS
ssh -o ConnectTimeout=10 ubuntu@119.28.119.151 'systemctl --user is-active hermes-gateway'
ssh ubuntu@119.28.119.151 'grep -nE "backend|extract|ddgs|tavily|hybrid" ~/.hermes/config.yaml | head -20'
ssh ubuntu@119.28.119.151 '~/.hermes/hermes-agent/venv/bin/python -c "import importlib.util as u; print(bool(u.find_spec(\"trafilatura\")), bool(u.find_spec(\"crawl4ai\")), bool(u.find_spec(\"playwright\")))"'
ssh ubuntu@119.28.119.151 'free -h; df -h ~ | tail -1'
ssh ubuntu@119.28.119.151 'ls ~/.hermes/plugins/hybrid-web/'
```

## 7. ENVIRONMENT

- VPS: `ubuntu@119.28.119.151` · home `/home/ubuntu`  
- Hermes: `~/.hermes/` · venv: `~/.hermes/hermes-agent/venv`  
- Gateway: `systemctl --user restart hermes-gateway` (only if needed; after each risky step verify)  
- Local branch: `overhaul/exec` · VPS hermes git: `hermes-local`  
- Backups: create `~/hermes-overhaul-backup/pre-px1/` before changes  

## 8. DELIVERABLES (end of PX-1)

- [ ] hybrid-web extract works (+ Playwright where needed)  
- [ ] Search: Tavily (if approved) + DDGS fallback (+ SearXNG later)  
- [ ] `skills/experts/research-expert/`  
- [ ] Deep-research pipeline + artifact handoff  
- [ ] Platform verification + research trace log  
- [ ] Knowledge layer contract doc  
- [ ] One E2E documented example  
- [ ] Med tests still green if any shared surface touched (prefer zero touch)  

## 9. RISKS

| Risk | Mitigation |
|---|---|
| VPS disk/RAM (Playwright) | Check free space first; monitor after install |
| Tavily cost | Gate on user key + approval |
| SearXNG load | Deferred 1b |
| Accidental med edit | Explicit path denylist; never open med files |
| Context blowup | Fasa-per-session if needed |

## 10. FIRST ACTIONS IN NEW SESSION

1. Load skills: using-superpowers, evidence-first, incremental-implementation, verification-before-completion.  
2. Run reorientation commands (section 6).  
3. Create `~/hermes-overhaul-backup/pre-px1/`.  
4. **Fasa 0 only** → evidence → STOP for user gate.  
5. Do not start Fasa 1 until Tavily/key decision confirmed in-session.

---

*End CONTINUATION-BRIEF-PX1.md — start here for next context window.*
