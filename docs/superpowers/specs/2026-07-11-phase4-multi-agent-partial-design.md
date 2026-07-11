# Phase 4 — Partial Multi-Agent Expert System (Design Spec)

> **Status:** DRAFT for user review (2026-07-11). No VPS execution until user says go.
> **Skills used:** brainstorming (design), writing-plans (downstream plan), mattpocock-style
> task breakdown, evidence-first (live config + Z.ai L2), YAGNI (partial build per Q5).

---

## 1. Problem & goal

**Problem:** User vision is a multi-agent expert system that *acts* (not only chats).
Today the platform already has siloed foundations (delegation, kanban, skills, hooks,
med engine, cron no_agent) but they are **undocumented and unwired** — assessed as
~5% of target (USER.md / Z.ai §8.7).

**Q5 decision (locked):** *Split but partially build multi-agent setup; document for later.*

**Phase 4 goal (this overhaul slice):** Move from ~5% → ~20–25% by:
1. Documenting canonical multi-agent patterns for MJ + OpenCode.
2. Wiring **3 expert roles** as first-class, invokable recipes (not new runtimes).
3. One thin **router** so the right expert is chosen without the user micromanaging.
4. Leaving full productization (Obsidian, sellable white-label, deep kanban product)
   for post-overhaul.

**Non-goals for P4:**
- Rebuild Hermes gateway / agent loop.
- Full multi-agent mesh (agents spawning agents of agents).
- Drop design skills (user interest area).
- Git push / GitHub productization (push still blocked).
- Breaking med chain or freeze rules.

---

## 2. Current foundation (VALIDATED live + audit)

| Capability | Live state | Evidence |
|---|---|---|
| Subagent delegation | `orchestrator_enabled: true`, `max_concurrent_children: 3`, `max_spawn_depth: 1`, `subagent_auto_approve: false` | `config.yaml` |
| Delegate tools | `delegate_tool.py`, `async_delegation.py`, official docs under `website/docs/.../delegation.md` | VPS hermes-agent |
| Kanban | Config block + skills `kanban-orchestrator` / `kanban-worker` | config + skills |
| Skill-trigger | Med keywords → `med-tracker` | hook live |
| Med engine v3 | Built P1, 21 tests | `scripts/med_chain/` |
| Restart SOP | `clean-restart-gateway` + hello-world-watch 30s | P3-S2 |
| Memory | Healthy post P3-S3 (46% / 67%) | memories/ |
| MJ role | Verifier only during overhaul | MEMORY + freeze |

**Z.ai insight (adopt):** CONNECT AND CLEAN, not rebuild from scratch (§8 preface).

---

## 3. Approaches considered

### Approach A — Pure documentation
Write patterns only; no wiring.
- Pros: zero risk.
- Cons: stays unused (same failure mode as today).

### Approach B — New multi-agent framework (custom orchestrator service)
Build a separate process that routes to agents.
- Pros: clean architecture on paper.
- Cons: YAGNI, fights Hermes, high freeze risk, cost.

### Approach C — **Partial wiring on existing Hermes (RECOMMENDED)**
Define 3 expert **roles** as skill packs + SOUL/MEMORY routing rules + optional
`delegate` recipes; document when to use kanban vs delegate vs no_agent cron.
- Pros: uses live capabilities; reversible; freeze-safe; matches Q5 “partial”.
- Cons: not a full product; limited by `max_spawn_depth: 1`.

**Recommendation: C.**

---

## 4. Target architecture (P4 partial)

```
USER (WA / TG)
    │
    ▼
GATEWAY (systemd) ── hooks: skill-trigger, med-auto-confirm, hello-world
    │
    ├─► ROUTER (rules in SOUL + MEMORY + skill-trigger extensions)
    │       │
    │       ├─ med / timing / confirm ──► EXPERT: Med (med-tracker + med_chain)
    │       ├─ research / drug safety ──► EXPERT: Research (medication-safety-research)
    │       ├─ restart / ops / health ──► EXPERT: Ops (clean-restart-gateway + monitor)
    │       └─ general chat ───────────► MJ default (persona + memory)
    │
    ├─► DELEGATE (optional, depth 1, max 3 children) for parallel research/tasks
    ├─► KANBAN (optional) for multi-day overhaul / build work items
    └─► CRON no_agent (med monitor, hello-world-watch, supply, etc.)
```

**Hard boundary:** Med math stays deterministic (`med_chain` / `chain_calc`).  
LLM experts **explain and coach**; they do **not** replace the solver.

---

## 5. Expert role definitions (partial build)

### E1 — Med Expert
- **Trigger:** skill-trigger keywords + explicit “med expert”.
- **Must load:** `med-tracker`.
- **May call:** `chain_calc.py --display`, med scripts (read-only unless user go).
- **Must not:** invent drug_ids; rewrite pre-9/7 history; skip dry-run on prod state.
- **SSOT:** `med-schedule.json`, `med_chain/rules.json`, dexa_taper.json.

### E2 — Research Expert
- **Trigger:** interaction / safety / “research” / “verify online”.
- **Must load:** `medication-safety-research` (+ web tools if available).
- **Must:** cite sources; never guess clinical claims.
- **Must not:** change live med JSON without user go.

### E3 — Ops Expert
- **Trigger:** restart / gateway down / cron not ticking / “clean restart”.
- **Must load:** `clean-restart-gateway` only.
- **Must:** anti-cascade latch; Hello World success signal; never SIGKILL.
- **Must not:** second kill within 2 min; treat hello-world-watch as stale.

### Default — MJ Generalist
- Persona + MEMORY/USER + methodology skills.
- Routes to E1–E3 when domain matches.

---

## 6. Router design (thin)

Not a new service. Three layers (defense in depth):

1. **skill-trigger hook** (already): expand map slightly for ops/research keywords
   (optional P4-S2; freeze-safe, fail-open).
2. **SOUL / MEMORY one-liners:** “If domain X, load skill Y before answering.”
3. **Optional skill:** `multi-agent-router` (short) — decision table for MJ.

**No LLM meta-router process** in P4 (cost + complexity).

---

## 7. Delegation patterns (document + 1 dry-run recipe)

Document these **only** (and one optional live dry-run with user go):

| Pattern | When | Constraints |
|---|---|---|
| D1 Parallel research | User asks multi-source question | max 3 children; no med writes |
| D2 Worker + review | Non-med code/docs task | parent reviews; subagent_auto_approve false |
| D3 Never for med confirm | Med confirmation path | Main agent + hook + scripts only |

**Forbidden:** delegate that restarts gateway; delegate that writes med-status.

---

## 8. Kanban (partial)

- Document when to use kanban vs chat todos.
- Optional: create a small set of kanban cards for “post-overhaul backlog”
  (Obsidian, fetcher product, skill archive) — **not** live med work.
- Fix `max_in_progress` only if live config is unbounded (verify in P4-S0).

---

## 9. Safety & freeze

| Rule | P4 handling |
|---|---|
| Med engine regression | Re-run 21 tests after any skill/hook touch |
| MJ verifier / OC executor | Unchanged |
| Push | Still blocked |
| Paid providers | No enable without yes |
| Approvals | `subagent_auto_approve: false` stays |
| Spawn depth | Keep `max_spawn_depth: 1` |

---

## 10. Success criteria (P4 done)

- [ ] `CONTINUATION-BRIEF-P4.md` + this design + implementation plan exist (this draft).
- [ ] Multi-agent patterns doc on VPS skill or `docs/` readable by MJ.
- [ ] Three experts invokable via clear triggers (skills + router notes).
- [ ] Optional skill-trigger expansions for ops/research (if approved).
- [ ] One documented delegate recipe tested (dry-run or supervised).
- [ ] Med tests 21/21 still green; gateway healthy; hello-world-watch still on.
- [ ] User can say “use Med Expert” / “use Ops Expert” and MJ loads the right skill.

**Out of scope success (later):** Obsidian wired, full kanban product, white-label med engine, push/sync pipeline.

---

## 11. Risks

| Risk | Mitigation |
|---|---|
| Over-orchestration confuses MJ | Keep router thin; default MJ stays |
| Delegate burns cost | depth 1, max 3, auto_approve false, no_agent cron for hot paths |
| Skill-trigger false positives | Fail-open; order specific patterns first |
| Scope creep to full multi-agent | Q5 partial; checklist non-goals |

---

## 12. Dependency graph

```
P0–P3 DONE
    │
    ▼
P4-S0 Orient + inventory live orchestrator/kanban
    │
    ├─► P4-S1 Patterns doc (multi-agent-patterns skill or docs)
    ├─► P4-S2 Expert packs (Med/Research/Ops) + MEMORY/SOUL pins
    ├─► P4-S3 Router (skill-trigger optional + multi-agent-router skill)
    ├─► P4-S4 Delegate recipe dry-run (supervised)
    ├─► P4-S5 Kanban backlog cards (optional)
    └─► P4-S6 Verify med tests + gateway + Hello World
```

---

## 13. Open questions for user (before execute)

1. Prefer expert packs as **new small skills** under `skills/experts/` vs only **docs + MEMORY**?
2. Expand **skill-trigger** for ops/research keywords, or MEMORY-only routing first?
3. Include **kanban backlog cards** in P4 or document-only?

Defaults if no answer: (1) `skills/experts/` + docs, (2) MEMORY + thin router skill first, skill-trigger only for high-confidence ops keywords, (3) document-only kanban.

---

*End of design. Implementation plan: `docs/superpowers/plans/2026-07-11-phase4-multi-agent-partial.md`.*
