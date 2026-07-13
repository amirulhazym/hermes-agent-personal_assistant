# Phase 4 — Personal AI OS Vision (ON HOLD)

> **Status: ON HOLD (2026-07-13).** Do not execute multi-agent OS build until user
> explicitly re-opens P4. Next executable track = **PX-1 Research Capability**.
>
> This document freezes the full architecture discussion so a later session can
> resume without re-deriving from chat. It supersedes the narrow “3-expert wrapper”
> draft as the *intent* record; the earlier partial plan remains historical.

---

## 1. Why P4 is held

The first P4 draft optimized for wrapping existing Med/Research/Ops into three neat
experts. User feedback (and a second pass) established that Hermes is meant to become
a **Personal AI Operating System** — multi-expert, execution-oriented, 2–3 year
horizon — not a reorganized chatbot.

That vision is **correct but too large** for one phase without unfinished architecture
risk. Decision: **hold P4 architecture execution**; ship **PX-1 (Research vertical)**
next; return to P4 when ready.

---

## 2. Long-term vision (reconstructed)

Hermes is **not** a generic chatbot. It is intended to be:

1. **Personal AI OS** — agentic multi-expert platform for daily life (meds, knowledge, ops).
2. **Consulting execution engine** — OVIS Digital Solutions: research, proposals, delivery, QA, KM.
3. **Team of specialists** that execute artifacts, hand off work, share durable truth, and improve via operation (not model retrain).
4. **Extensible** — add/remove experts without redesigning the spine (dozens→hundreds over time).

Target maturity (user language): from **~5%** of vision toward **~20–25%** in a
shippable phase slice — full vision is multi-phase (P4+ / P5 / P6 / PX tracks).

---

## 3. Layer model (do not collapse)

| Layer | Owns | Hermes today | Gap |
|---|---|---|---|
| **Expert** | Domain reasoning & ownership | Missing as first-class | Need registry + contracts |
| **Skill** | Reusable capability | Strong (SKILL.md) | Keep; never *define* expert |
| **Tool** | Execute action | Strong | Keep |
| **Hook** | Event trigger | Strong | Keep |
| **Delegate** | Bounded child run | Partial: depth=1, max=3 | Use staged fan-out |
| **Executor** | Who runs work | Gateway + cron no_agent + OC | Keep; don’t rebuild |
| **Memory** | Compact durable prefs | MEMORY.md / USER.md | Keep bounded |
| **Knowledge** | Long-term source of truth | Obsidian path unwired | Contract first, product later |
| **Router** | Ownership of goal | skill-trigger + SOUL partial | Need task-level router |
| **Planner** | Decompose → task graph | Kanban partial | Need research/work planner |
| **Orchestrator** | Multi-stage coordination | Partial | Staged stages, not deep trees |

**Rule:** Experts compose skills/tools. Skills never define an expert.
Example: Medical Expert owns many capabilities; `med_chain` is a tool/engine inside that domain — not “the expert.”

---

## 4. Depth=1 / max=3 children (explicit)

**P4/PX default: KEEP hard limit.** Do not silently raise.

**How 9+ experts work under that limit:** hub-and-spoke + **staged** execution +
**artifact-mediated** handoff:

1. Router assigns primary ownership of a user goal.
2. Planner produces a staged task graph.
3. Orchestrator runs **one stage at a time**.
4. Each stage: ≤3 parallel delegates (depth 1 only).
5. Results → shared artifact store (files / task record / later Obsidian).
6. Next stage reads **artifacts**, not sibling chat transcripts.
7. QA often platform-level, not always a parallel child.

Raising depth/max children = **P5+ experiment only**, explicit user go, cost caps, no med-path delegation.

---

## 5. Platform vs expert (cross-cutting)

| Concern | Prefer |
|---|---|
| Verification, safety, logging, audit trail, memory hygiene | **Platform** |
| Med, Research, Writing, Code, Browser, Business, … | **Experts** |
| Obsidian | **Knowledge layer** first; thin Knowledge Expert as interface later |
| Self-improvement | **Platform**: lessons store, execution history, workflow registry |

### Obsidian

Primary: long-term **knowledge / source-of-truth** (research, clients, decisions, lessons).  
Not a second MEMORY.md. Hybrid: MEMORY = compact ops prefs; vault = bulk truth.  
Full wire = P5+; P4/PX define contracts only unless user expands scope.

---

## 6. Challenges to raw vision (correctness > agreement)

1. Hundreds of peer experts without registry → chaos → need **registry + active set**.
2. Free multi-agent chat handoff → prefer **artifact/task-graph** handoff.
3. Unsupervised consulting send → need **autonomy levels** (draft default).
4. Self-improve without schema → diary spam → **typed lessons**.
5. Full re-architect allowed for Overhaul V1, but P4 should still ship a **spine**, not replace working gateway.

---

## 7. Scope split (when P4 reopens)

### P4 (when resumed) — architecture foundation
- Layer contracts + expert registry  
- Task graph + staged orchestration under depth=1/max=3  
- Artifact package format  
- Router + Planner roles (rules-first)  
- Platform QA hooks  
- Knowledge contract for Obsidian  
- Lessons/execution-history schema  
- Med path preserved; regression tests hard gate  
- Worked example (e.g. client proposal path)

### P5/P6 — deferred
- Full Obsidian product integration  
- Deep kanban product UX  
- Spawn depth/concurrency experiments  
- Many fully staffed experts  
- Autonomous external client send  
- Browser expert full stack hardened  
- Analytics dashboards / multi-tenant  

### PX-1 (NEXT — not waiting for P4 execute)
Research Expert vertical: fix extract, search backends, pipeline, verification, knowledge contract prep.  
See `CONTINUATION-BRIEF-PX1.md` + `PX1-RESEARCH-TRACK-PLAN.md`.

---

## 8. User decisions locked (2026-07-13)

| Topic | Decision |
|---|---|
| P4 multi-agent OS | **ON HOLD** |
| Next track | **PX-1 Research** |
| Sequence | Freeze P4 docs → new session PX-1 Fasa 0 |
| Tavily | Planned primary when key/approval ready; gate Fasa 1 |
| SearXNG | **Later** (Fasa 1b optional), not blocking Fasa 0–1 start |
| Playwright/Chromium | **Yes** in PX-1 Fasa 0 |
| Design skills | **Do not delete** |
| Push | **Blocked** until explicit go |
| Depth/max children | Keep 1 / 3 default |

### Defaults if P4 reopens without re-asking
- Autonomy: draft until approve send  
- Knowledge: contracts first  
- Inter-expert: artifact/task-graph  
- Audit: platform first  
- Orchestrator config: keep depth=1/max=3  

---

## 9. Historical note

Earlier files (narrow 3-expert design/plan) remain for history:

- `docs/superpowers/specs/2026-07-11-phase4-multi-agent-partial-design.md` — **superseded as intent** by this HOLD doc  
- `docs/superpowers/plans/2026-07-11-phase4-multi-agent-partial.md` — do not execute as-is  

When P4 reopens: redesign from **this** document + user feedback, not the narrow wrapper plan alone.

---

*End of P4 OS vision HOLD freeze.*
