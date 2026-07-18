# PX-1 Family Closeout & Handoff (Research + Web Operator)

> **Date:** 2026-07-18 (fresh verification this session)  
> **Branch:** `overhaul/exec`  
> **Purpose:** Official freeze of **PX-1 Research** and **PX-1b Web Operator** before any **PX-2** work.  
> **Method:** verification-before-completion · evidence labels · PX Planning Framework for next track  
> **Do not** re-open acceptance without regression evidence.

---

## 0. Executive status

| Track | Status | Evidence label |
|-------|--------|----------------|
| **PX-1 Research Capability** (Fasa 0–5 + multi-key) | **COMPLETE / LIVE** | VALIDATED (tools + VPS config); formal chat package/trace residual PARTIAL |
| **PX-1b Web Operator** | **COMPLETE / LIVE** | VALIDATED 20/20 design acceptance (2026-07-17) |
| **P0–P3** med/gateway overhaul | COMPLETE / LIVE | Prior trackers |
| **P4** multi-agent OS | **ON HOLD** | HOLD specs |
| **PX-2** | **NOT STARTED** | Planning required first (framework) |

**Fresh re-check (2026-07-18, this session):**

| Check | Result |
|-------|--------|
| `hermes-gateway` | `active` |
| `web.search_backend` | `search-cascade` |
| `web.extract_backend` | `hybrid-web` |
| Tavily key count (`TAVILY_API_KEYS`) | **11** |
| Plugins | `hybrid-web`, `search-cascade` (+ others) |
| Skills experts | `research-expert`, `web-operator` |
| `web_search` smoke | `success=True`, `backend=tavily`, `n=2`, `key_idx=0` |
| Deps trafilatura / crawl4ai / playwright | `True True True` |
| `~/.hermes/scripts/web_operator` | present |
| `~/.hermes/web-operator/acceptance-latest.json` | present |
| research_trace lines | 7 |
| tavily_key_usage lines | 116 |
| RAM | ~1.9Gi total, ~1.0Gi available (tight; respect L3=1) |

---

## 1. What PX-1 delivered (Research)

### 1.1 Capability inventory

| Layer | What | Where |
|-------|------|--------|
| Search | Tavily primary → DDGS fallback (`search-cascade`) | VPS plugins + config |
| Capacity | 11 free keys, sticky rotate, usage log | `.env` `TAVILY_API_KEY` + `TAVILY_API_KEYS` |
| Extract | hybrid-web: trafilatura → crawl4ai → Playwright | VPS plugin |
| Expert | Research Expert domain owner, 6-stage pipeline | `~/.hermes/skills/experts/research-expert/` + repo mirror |
| Verify | Cross-check / freshness / contradiction rules | `references/verification.md` |
| Trace | `~/.hermes/logs/research_trace.jsonl` | Fasa 3 |
| Knowledge | Contract + export stub `research_knowledge.py` | Fasa 4 |
| Ops (not product) | CDP Tavily signup, QRYPTY, PC-only | `F:\HermesPrivate\` — never agent default |

### 1.2 Canonical docs (PX-1)

| Doc | Path |
|-----|------|
| Journey | `docs/superpowers/specs/2026-07-14-px1-research-journey.md` |
| Track plan | `PX1-RESEARCH-TRACK-PLAN.md` |
| Skill | `skills/experts/research-expert/` |
| Ops | `RUNBOOK.md` §16 |

### 1.3 Residual (honest — do not inflate)

| Item | Label | Action for PX-2 |
|------|-------|-----------------|
| Every chat research always writes formal `research_trace.jsonl` + full artifact package | **PARTIAL** | Optional narrow repair if daily use hurts; not a PX-2 blocker |
| Journey §11 Wave 1 text in older copies | STALE if not updated | Prefer this closeout + PROGRESS |

### 1.4 Anti-repeat (still binding)

1. Do not re-install trafilatura/crawl4ai/playwright unless import fails.  
2. Do not re-debug Turnstile/signup on VPS.  
3. Do not rebuild search-cascade / multi-key unless broken.  
4. Captcha/account farming = PC ops + human gate only.  
5. No med_* / chain_* / med JSON.  
6. depth=1 / max=3.  
7. No paid Tavily / paid browser cloud without explicit yes.  
8. Never print API key values.

---

## 2. What PX-1b delivered (Web Operator)

### 2.1 Capability inventory

| Layer | Role | Runtime |
|-------|------|---------|
| L0 | Refuse / approval pause | Policy |
| L1 | Public HTTP fetch | VPS |
| L2 | search-cascade + hybrid-web + research | VPS |
| L3 | Interactive browse (native + adapters) | VPS, concurrency **1** |
| L4 | Enrolled PC CUA worker (mailbox bridge) | Windows PC optional |
| L5 | Human handoff (captcha etc.) | Human |

Phone (TG/WA) = control surface. VPS = always-on brain. PC = optional power worker.

### 2.2 Acceptance

- **20/20 PASS** formal suite (2026-07-17).  
- Evidence: `docs/px1b-acceptance-evidence.md`  
- Live contracts: `docs/px1b-live-contracts.md`  
- Findings/residuals: `docs/px1b-findings.md`  
- Design: `docs/superpowers/specs/2026-07-17-px1b-web-operator-design.md`  
- Journey (other session): `docs/superpowers/specs/2026-07-17-px1b-web-operator-journey.md`  
- Plan: `docs/superpowers/plans/2026-07-17-px1b-web-operator.md`  
- Code: `scripts/web_operator/`, skill `web-operator`, Windows worker scripts under `windows/`

### 2.3 Ops hardening backlog (not PX-2 unless chosen)

From PX-1b journey §9A — short follow-ups, not re-acceptance:

1. PC worker after reboot runbook habit  
2. Task Scheduler / autostart discipline  
3. Artifact retention purge (14-day policy)  
4. Smoke TG `/browse` + WA after gateway restarts  

### 2.4 Hard rails still binding

- Hermes stay **v0.17.0** unless explicit upgrade decision.  
- No paid browser cloud.  
- No inbound PC ports for CUA (outbound mailbox only).  
- `computer_use.enabled` honesty: project bridge ≠ Hermes MCP CUA claim.  
- Medical portal isolation; no med automation state writes.

---

## 3. Track map (where we are)

```text
P0–P3 med/gateway ──────── COMPLETE LIVE
P4 multi-agent OS ───────── ON HOLD
PX-1 Research ───────────── COMPLETE LIVE  ← frozen here
PX-1b Web Operator ──────── COMPLETE LIVE  ← frozen here
PX-2 ────────────────────── NEXT (undefined until planning)
PX-3+ ───────────────────── later
```

**Planning method for any new PX:**  
`docs/superpowers/specs/PX-PLANNING-FRAMEWORK.md`

---

## 4. Gate to start PX-2

Do **not** start PX-2 implementation until:

1. [ ] Human names **PX-2 goal in one sentence**  
2. [ ] Agent produces Doc B audit + Doc A Q&A (or human reuses framework)  
3. [ ] Human fills Q&A offline and returns  
4. [ ] Joint lock → design → plan → build  

**Suggested PX-2 candidates** (pick one; do not invent paid scope):

| Candidate | Notes |
|-----------|--------|
| A. Ops hardening only | Short; finish PX-1b ops backlog |
| B. Knowledge / Obsidian productization | Builds on PX-1 Fasa 4 stub |
| C. Research formalization residual | Trace/artifact always-on in chat |
| D. Private-site / portal drills | Owner-gated; high safety |
| E. New domain expert vertical | e.g. ops, finance, content — not full P4 |
| F. Overhaul V2 / Hermes upgrade path | Explicit version decision required |

---

## 5. Specs index (`docs/superpowers/specs/`)

| File | Role |
|------|------|
| `PX-PLANNING-FRAMEWORK.md` | Reusable planning method |
| `2026-07-14-px1-research-journey.md` | PX-1 try/error + anti-repeat |
| `2026-07-14-px1b-web-operator-audit-recap.md` | PX-1b Doc B |
| `2026-07-14-px1b-web-operator-planning-qna.md` | PX-1b Doc A (+ Part 15 lock) |
| `2026-07-17-px1b-web-operator-design.md` | PX-1b locked design |
| `2026-07-17-px1b-web-operator-journey.md` | PX-1b execution narrative |
| `2026-07-18-px1-family-closeout-handoff.md` | **This file** — freeze before PX-2 |
| `2026-07-11-phase4-os-vision-HOLD.md` | P4 hold |
| `2026-07-11-phase4-multi-agent-partial-design.md` | P4 partial (held) |
| `2026-06-30-dual-rebuild-audit-decision.md` | Historical rebuild |

Related non-spec evidence:

- `docs/px1b-acceptance-evidence.md`  
- `docs/px1b-live-contracts.md`  
- `docs/px1b-findings.md`  
- `docs/superpowers/plans/2026-07-17-px1b-web-operator.md`  

---

## 6. Fresh session checklist (before PX-2 planning)

```bash
# Local
git -C "F:\AI Prep\OVIS\Hermes Agent\MJay" status
git -C "F:\AI Prep\OVIS\Hermes Agent\MJay" log --oneline -8

# Read
# docs/superpowers/specs/2026-07-18-px1-family-closeout-handoff.md  (this file)
# docs/superpowers/specs/PX-PLANNING-FRAMEWORK.md
# CONTINUATION-BRIEF-PX2.md  (when present)

# VPS smoke
ssh ubuntu@119.28.119.151 'systemctl --user is-active hermes-gateway'
ssh ubuntu@119.28.119.151 'grep -E "search_backend|extract_backend" ~/.hermes/config.yaml'
ssh ubuntu@119.28.119.151 'ls ~/.hermes/skills/experts/ ~/.hermes/plugins/'
```

**Do not:** re-run PX-1 Fasa 0 install; re-open PX-1b 20/20 without failure evidence; touch med_*.

---

## 7. Verification log (this closeout session)

| Time (session) | Action | Result |
|----------------|--------|--------|
| 2026-07-18 | Gateway active | PASS |
| 2026-07-18 | Config search-cascade + hybrid-web | PASS |
| 2026-07-18 | 11 Tavily keys | PASS |
| 2026-07-18 | web_search tavily n=2 | PASS |
| 2026-07-18 | research-expert + web-operator skills present | PASS |
| 2026-07-18 | web_operator package on VPS | PASS |
| 2026-07-18 | acceptance-latest.json present | PASS |
| 2026-07-18 | Specs tree reviewed | PASS |

---

## 8. Sign-off

| Role | Statement |
|------|-----------|
| Agent (this session) | PX-1 family closed for handoff on evidence above. Ready for **PX-2 planning only**. |
| Human | Approve this closeout before PX-2 Q&A package (optional explicit yes). |

---

*End closeout. Next: name PX-2 → Planning Framework → Doc B/A → lock → build.*
