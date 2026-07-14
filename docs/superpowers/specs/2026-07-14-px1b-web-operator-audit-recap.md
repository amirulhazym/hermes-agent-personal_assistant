# PX-1b Web Operator — Audit Recap (Doc B)

> **Role:** Evidence-only companion. Read **before** filling Doc A.  
> **Does not decide.** Your decisions live in Doc A.  
> **Framework:** `docs/superpowers/specs/PX-PLANNING-FRAMEWORK.md`  
> **Linked Q&A:** `docs/superpowers/specs/2026-07-14-px1b-web-operator-planning-qna.md`  
> **Date:** 2026-07-14 · **Labels:** VALIDATED / UNTESTED / REJECTED / STALE

---

## 0. How to use this doc

1. Skim §1–2 (what PX-1b is / is not).  
2. Read §3 capability matrix.  
3. Note §4–5 constraints and kill paths.  
4. Open Doc A and fill Parts in order.  
5. Optional: jot notes in §9.

---

## 1. Track definition

| Item | Content |
|------|---------|
| **Track** | PX-1b Web Operator |
| **Parent** | PX-1 Research Capability (COMPLETE Fasa 0–5 + multi-key) |
| **Parallel** | P4 multi-agent OS = ON HOLD |
| **One-line goal (draft)** | Reduce PC dependence for web browse/scrape/session work while keeping CUA as favorite desktop power — without turning Hermes into silent captcha/account farmer |
| **Human north star** | “More than chatbot Hermes” — powerful web access from Telegram/WhatsApp |

---

## 2. PX-1 vs PX-1b (boundary)

### 2.1 PX-1 DONE (VALIDATED) — do not rebuild

| Capability | Evidence |
|------------|----------|
| Search Tavily→DDGS (`search-cascade`) | VPS config + E2E tests 2026-07-14 |
| 11 free Tavily keys + rotation + usage log | VPS `.env` + `tavily_key_usage.jsonl` |
| Extract hybrid-web (trafilatura→crawl4ai→Playwright) | Fasa 0 + Fasa 5 extract PASS |
| Research Expert skill + pipeline | `skills/experts/research-expert/` on VPS |
| Verification rules + research_trace.jsonl | Fasa 3 |
| Knowledge export stub | Fasa 4 `research_knowledge.py` |
| Ops signup/CDP/QRYPTY | PC only under `F:\HermesPrivate\` — not agent skills |

### 2.2 PX-1 residual (honest)

| Item | Label | Note |
|------|-------|------|
| Telegram/WhatsApp “user says research → skill fires” | UNTESTED | Fasa 5 used SSH pipeline, not full chat E2E |
| Journey §11 Wave 1 list | STALE | Fasa 3–5 now DONE in PROGRESS |

### 2.3 PX-1b NOT built

| Capability | Status |
|------------|--------|
| Interactive multi-step browser operator skill | MISSING |
| Session/cookie vault for logins | MISSING |
| Tool-selection policy (extract vs browser-use vs CUA) | MISSING |
| Formal CUA handoff policy | MISSING (partial MEMORY/AUDIT only) |
| Productized browser-use on VPS | UNTESTED as operator |
| Scrapling / curl-impersonate wired | STANDBY only |

---

## 3. Capability matrix (live truth)

| Layer | Name | Where | Status | Role |
|-------|------|-------|--------|------|
| L1 | HTTP / curl-impersonate | VPS | STANDBY docs | Cheap fetch |
| L2 | hybrid-web extract | VPS | VALIDATED | Public page content |
| L2b | search-cascade | VPS | VALIDATED | Search (not browse) |
| L3 | browser-use / Playwright interactive | VPS? | Docs claim install; operator skill MISSING | Multi-step web |
| L4 | CUA (cua-driver) | PC | VALIDATED historically on Windows; VPS REJECTED path | Desktop any-app |
| L5 | CDP signup / captcha ops | PC ops | VALIDATED for Tavily harvest | Ops only, human gate |

### 3.1 Integrations inventory (repo)

| Integration | Path | Status |
|-------------|------|--------|
| hybrid-web | `integrations/hybrid-web/` | Live plugin |
| crawl4ai | `integrations/crawl4ai/` | Used by hybrid-web |
| browser-use | `integrations/browser-use/` | Docs; not Hermes skill pack |
| curl-impersonate | `integrations/curl-impersonate/` | Standby |
| scrapling | `integrations/scrapling/` | Standby |
| Firecrawl | removed | AGPL/paid — REJECTED historically |

### 3.2 CUA / drivers

| Item | Status |
|------|--------|
| `cua-driver.exe` Windows | PC binary historically `F:\hermes\cua-driver\` |
| VPS mcp_servers cua path | BROKEN / empty — Windows path on Linux |
| `computer_use.enabled` | May be true while MCP empty — **config inconsistency** (audit) |
| `scripts/qwen_driver.py` | PC Brave + cua |
| `scripts/sakana_driver.py` | Incomplete stub |
| MEMORY skills `automation/sakana`, `automation/qwen` | Referenced; not clean in MJay `skills/` tree |

---

## 4. Hard rails (must not violate)

### 4.1 PRD / AGENTS

- No **paid hosted browser automation** without explicit yes (`PRD.md`).  
- No paid service without explicit yes (`AGENTS.md`).  
- STOP before credential-touching, costly, destructive, public-posting actions.  
- DeepSeek (or approved model stack) cost discipline; free infra preference.  

### 4.2 PX-1 decisions that carry forward

- Signup / Turnstile / captcha bypass = **PC ops + human gate**, never silent agent default.  
- depth=1 / max=3 concurrency hard default.  
- No med_* / chain_* / med JSON touch.  
- Secrets: never print key values.  

### 4.3 Kill paths (do not re-try as “smart fix”)

| Path | Result | Source |
|------|--------|--------|
| Playwright headless vs Cloudflare Turnstile | REJECTED (300030) | Journey multi-key war |
| Bare VPS Chromium for hard bot walls | REJECTED | Journey |
| Firecrawl cloud as default | REJECTED | DECISIONS / integrations |

---

## 5. VPS constraints (2026-07-14 sample)

| Resource | Approx | Implication |
|----------|--------|-------------|
| RAM | ~1.9 Gi total | Interactive Chromium is expensive |
| Swap | ~5.9 Gi | Softens OOM; not free performance |
| Gateway + platforms | Always on | Browser jobs compete with Telegram/WhatsApp |

**Design implication:** VPS L3 must be gated (single job, timeout, kill switch) or deferred to PC.

---

## 6. Goal analysis (why expand some Parts)

Human goals stated across sessions:

1. **Less PC dependence** for web automation / browse / scrape (and related).  
2. **Keep CUA** as favorite when desktop power is needed.  
3. **Hermes more than chatbot** — powerful, reliable, free-tier dominant.  
4. **Safety** — no silent dangerous automation; HITL.  

Therefore Doc A **expands**:

- **Part 5 Safety** — full HITL matrix.  
- **Part 6 CUA** — favorite-feature policy + handoff phrases + config truth.  
- **Part 7 Sessions** — auth without becoming a password manager disaster.  
- **Part 4 Ladder** — clear “when leave PC / when stay PC”.  

Less expansion needed on pure research search (PX-1 already owns it).

---

## 7. Recommended defaults (DRAFT ONLY — decide in Doc A)

These are agent recommendations for you to challenge:

1. Compose PX-1 tools; do not rebuild search/extract.  
2. New expert skill `web-operator` separate from `research-expert`.  
3. Ladder L0–L5 as in Doc A Part 4.  
4. MVP = public multi-step browse on VPS (no login) before session vault.  
5. Login always human-gated.  
6. Captcha/signup stay L5 PC ops.  
7. CUA stays PC; Hermes says when PC required.  
8. Self-hosted browser-use only; no cloud without yes.  
9. Single concurrent browser job on VPS.  

---

## 8. File index

| Topic | Path |
|-------|------|
| Framework | `docs/superpowers/specs/PX-PLANNING-FRAMEWORK.md` |
| Q&A workbook (Doc A) | `docs/superpowers/specs/2026-07-14-px1b-web-operator-planning-qna.md` |
| PX-1 journey | `docs/superpowers/specs/2026-07-14-px1-research-journey.md` |
| PX-1 plan | `PX1-RESEARCH-TRACK-PLAN.md` |
| Continuation | `CONTINUATION-BRIEF-PX1.md` |
| browser-use docs | `integrations/browser-use/README.md` |
| Research expert | `skills/experts/research-expert/` |
| PRD rails | `PRD.md` §2.2, §4.2, §7 |
| Ops multi-key | `RUNBOOK.md` §16 |

---

## 9. Your optional notes (Doc B)

> (Free space — not required)

---

## 10. Next action

→ Open **Doc A** and fill Parts 0 → 14 in order.  
→ Return filled Doc A (and any Doc B notes).  
→ Joint lock → design → implement.

---

*End Doc B — Audit Recap. Evidence only.*
