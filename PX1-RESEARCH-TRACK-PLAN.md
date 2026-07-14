# PX-1 Research Capability Track — Plan

**Status:** ACTIVE — Fasa 0–2 + Multi-Key Capacity done on VPS; next = Fasa 3  
**Track type:** Separate from P0–P3 med/gateway; **parallel to P4 (P4 ON HOLD)**  
**Owner:** amirulhazym  
**Created:** 13 July 2026 · **Updated:** 14 July 2026 (multi-key + journey doc)  
**Handoff brief:** `CONTINUATION-BRIEF-PX1.md`  
**Journey:** `docs/superpowers/specs/2026-07-14-px1-research-journey.md`  
**P4 freeze:** `CONTINUATION-BRIEF-P4.md` + `docs/superpowers/specs/2026-07-11-phase4-os-vision-HOLD.md`

---

## 0. ROLE & MANDATE

You are the executor for **PX-1 Research Capability Track**.

**Separate from** med/gateway overhaul execution. Do **not** touch:
`med_*`, `chain_*`, `med-auto-confirm`, or medication JSON state files.

**Goal:** Transform Hermes from basic/weak web search into a proper **Research Expert**
(domain owner) with deep, verified, cited research — better than current DDGS + broken
hybrid-web extract.

**Core principles (aligned with held P4 OS vision):**
- Research Expert = domain owner composing skills + tools (not “one skill = expert”)
- Staged orchestration + artifact-mediated handoff
- **depth=1 / max=3 children** hard default
- Platform verification/logging before extra experts
- Evidence-first + incremental + per-step user go

---

## 1. HARD CONSTRAINTS

- No med logic touch  
- depth=1 / max=3 remains default  
- Evidence-first with raw command output  
- Per-step approval for running-system changes  
- Zero/low cost priority; **Tavily only after key + explicit go**  
- SearXNG self-host = **Fasa 1b later** (not blocking Fasa 0)  
- Playwright + Chromium = **yes in Fasa 0** (check disk/RAM first)  
- No git push unless user says so  
- Watch context; fresh session if near limits  

---

## 2. CURRENT STATE (PX-1)

**Validated live (2026-07-13):**
- Search backend: **ddgs**
- extract_backend: **hybrid-web**
- hybrid-web plugin present under `~/.hermes/plugins/hybrid-web/`
- venv missing: **trafilatura, crawl4ai, playwright** (all False)
- Singapore VPS IP may throttle some backends

**Assets:** hybrid-web plugin, SOUL grounding rules, delegation/kanban exist for later stages

---

## 3. TARGET ARCHITECTURE (research slice of OS vision)

| Layer | Role | PX-1 action |
|---|---|---|
| Research Expert | Domain owner | Create first-class expert package |
| Router / Planner | Ownership + task graph | Strengthen in Fasa 2 |
| Orchestrator | Staged runs | Use existing + pipeline skill |
| Artifact handoff | Stage packages | Define format Fasa 2 |
| Extraction | Clean URL content | **Fasa 0 fix** + Playwright |
| Search | Sources | Fasa 1: Tavily→DDGS; SearXNG 1b |
| Verification | Anti-hallucination | Fasa 3 platform |
| Knowledge | Obsidian long-term | Fasa 4 contract only |

---

## 4. PHASED EXECUTION

### Fasa 0 — Foundation fix — DONE (2026-07-13)
Install deps + verify extract + Playwright.

```bash
# preflight
free -h; df -h ~ | tail -1

~/.hermes/hermes-agent/venv/bin/pip install trafilatura crawl4ai playwright
~/.hermes/hermes-agent/venv/bin/playwright install chromium
```

Verify hybrid-web / web_extract on static + JS URL.  
**Gate:** user confirmation before Fasa 1.

### Fasa 1 — Search backend + fallback — DONE (2026-07-13)
- Primary: **Tavily** via `search-cascade`  
- Fallback: **DDGS** on error/empty  
- MCP Tavily tools registered  
- Optional 1b: **SearXNG** self-host later (still deferred)  

### Fasa 2 — Research Expert + pipeline — DONE (2026-07-13)
- `skills/experts/research-expert/` (+ VPS `~/.hermes/skills/experts/research-expert/`)  
- Pipeline + artifact format + smoke package  
- skill-trigger research patterns  
- Max 3 parallel per stage; depth 1  
**Gate** before Fasa 3.

### Fasa 3 — Platform verification + logging
Cross-check, freshness, contradiction flags; research trace log; SOUL grounding.

### Fasa 4 — Knowledge layer contract
Obsidian-compatible artifact policy; thin Knowledge interface stub. Not full vault product.

### Fasa 5 — E2E validation
Full workflow + fallback under failure + quality vs baseline.

---

## 5. DELIVERABLES

- Fixed hybrid-web + Playwright capability  
- Tavily (if approved) + DDGS fallback (+ SearXNG later)  
- Research Expert package + deep-research pipeline  
- Platform verification + logging  
- Knowledge contract doc  
- One E2E documented example  

---

## 6. SESSION DISCIPLINE

- One Fasa at a time  
- After each Fasa: STOP → evidence → user go  
- Never touch med files  
- Labels: VALIDATED / UNTESTED / REJECTED  
- Local commits OK; no push  

---

## 7. RELATIONSHIP TO P4

PX-1 is **not** the full Personal AI OS. It is the **first expert vertical** that
proves staged research under existing Hermes constraints while P4 architecture
remains on hold. Patterns (expert package, artifacts, verification) feed future P4.

---

*End of PX1-RESEARCH-TRACK-PLAN.md*
