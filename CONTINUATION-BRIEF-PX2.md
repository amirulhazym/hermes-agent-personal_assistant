# Hermes Agent — CONTINUATION BRIEF PX-2

> **Attach this file +** `docs/superpowers/specs/2026-07-18-px1-family-closeout-handoff.md`  
> **+** `docs/superpowers/specs/PX-PLANNING-FRAMEWORK.md`  
> **Do not touch med logic** (`med_*`, `chain_*`, `med-auto-confirm`, med JSON).  
> **Do not re-open PX-1 / PX-1b acceptance** without regression evidence.

---

## 0. ROLE & MANDATE

You are executor for **PX-2** (next capability track after PX-1 Research + PX-1b Web Operator).

**Prerequisite:** PX-1 family is **CLOSED** (see closeout handoff).  
**Current mandate:** **PLANNING ONLY** until human names goal, fills Q&A, and locks design.

**Principles:** evidence-first · PX Planning Framework · no paid services without yes · compose existing tools · depth=1/max=3 · P4 remains ON HOLD unless reopened explicitly.

---

## 1. PRIOR TRACKS (do not re-do)

| Track | Status |
|-------|--------|
| P0–P3 | COMPLETE LIVE |
| PX-1 Research | COMPLETE LIVE (2026-07-14 + recheck 2026-07-18) |
| PX-1b Web Operator | COMPLETE LIVE 20/20 (2026-07-17) |
| P4 multi-agent OS | ON HOLD |

Live stack already includes: search-cascade (11 Tavily keys), hybrid-web, research-expert, web-operator L1–L4, TG+WA gateway.

---

## 2. FIRST ACTIONS IN NEW SESSION

1. Read closeout: `docs/superpowers/specs/2026-07-18-px1-family-closeout-handoff.md`  
2. Read framework: `docs/superpowers/specs/PX-PLANNING-FRAMEWORK.md`  
3. Confirm VPS still healthy (gateway, plugins, experts) — smoke only.  
4. **Ask human for PX-2 one-line goal** (or present candidate list from closeout §4).  
5. Produce Doc B audit + Doc A sequential Q&A for that goal.  
6. Wait for filled Q&A → lock → design → plan → implement.  

**Forbidden:** implement PX-2 features before step 6 lock; reinstall PX-1 deps; re-debug Turnstile; silent Hermes upgrade.

---

## 3. CANDIDATE GOALS (not decided)

From closeout §4:

- A. Ops hardening (PC worker, retention, post-restart smokes)  
- B. Knowledge / Obsidian productization  
- C. Research formalization residual (always-on trace/artifacts in chat)  
- D. Private-site / portal drills (owner-gated)  
- E. New domain expert vertical  
- F. Overhaul V2 / Hermes version path  

---

## 4. HARD CONSTRAINTS

| Rule | Detail |
|------|--------|
| No med touch | Never modify med_*, chain_*, med JSON |
| Concurrency | depth=1 / max=3 |
| Paid | Explicit yes required |
| Secrets | Env names / fingerprints only |
| Push | No git push unless user says so |
| MJ | Verifier only; OpenCode changes VPS |
| Hermes version | Stay v0.17.0 unless explicit upgrade decision |

---

## 5. ENVIRONMENT

- VPS: `ubuntu@119.28.119.151` · `~/.hermes/`  
- Branch: `overhaul/exec`  
- Gateway: `systemctl --user restart hermes-gateway` only when needed  

---

## 6. DELIVERABLES (end of PX-2 planning phase)

- [ ] PX-2 one-line goal locked  
- [ ] Doc B audit recap  
- [ ] Doc A sequential Q&A filled  
- [ ] Locked design  
- [ ] Implementation plan  
- [ ] Explicit human go before first code Fasa  

---

*End CONTINUATION-BRIEF-PX2.md — start here for PX-2 sessions.*
