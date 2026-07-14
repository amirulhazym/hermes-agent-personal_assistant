# PX Planning Framework (Reusable)

> **Purpose:** Standard method to plan any **PX-*** track (or major capability upgrade) before code.  
> **Origin:** PX-1b Web Operator planning (2026-07-14).  
> **Status:** CANONICAL — reuse for PX-1b, PX-2, PX-3, future verticals.  
> **Owner:** amirulhazym · Executor: OpenCode (MJ verifier only)

---

## 0. When to use this framework

Use for any track that is:

- multi-subsystem or multi-phase;
- safety / credential / cost sensitive;
- “more than chatbot” capability upgrade;
- likely to waste cycles if jumped straight to build.

**Do not** use for trivial one-file fixes. **Do** use when the human says “plan first” or when readiness is low.

---

## 1. Five-step loop (hard)

```text
(1) Agent produces planning package (docs on disk)
        ↓
(2) Human reviews offline (read, research, decide, fill answers)
        ↓
(3) Human returns filled document(s) + feedback
        ↓
(4) Joint final discussion → lock decisions → design freeze
        ↓
(5) Implementation (phased) + commit per wave + evidence
```

**Rules:**

- No implementation in steps (1)–(4).
- No “silent proceed” from “continue / go” earlier in chat — each commit still needs explicit yes if AGENTS.md requires it.
- After (4), produce: locked design + implementation plan (writing-plans skill) + continuation brief.
- After (5), update PROGRESS / DECISIONS / RUNBOOK.

---

## 2. Package shape (default: two linked docs)

| Doc | Role | Human fills? |
|-----|------|----------------|
| **B — Audit Recap** | Evidence only: EXISTS / STALE / MISSING / rails | Optional notes only |
| **A — Sequential Q&A Workbook** | Decision-making: earlier planning → confirm → choose | **Yes — primary** |

Optional later (after step 4):

| Doc | Role |
|-----|------|
| Locked design | `docs/superpowers/specs/YYYY-MM-DD-<px>-design.md` |
| Implementation plan | `docs/superpowers/plans/YYYY-MM-DD-<px>.md` |
| Continuation brief | `CONTINUATION-BRIEF-<PX>.md` |

**Linking rule:** Doc A Part 0 must link Doc B. Doc B must link Doc A. Journey / PROGRESS / CONTINUATION must point to both.

**Sequential rule:** Parts in A are ordered by dependency. Do not skip a Part that later Parts depend on (e.g. goals before architecture, safety before sessions).

---

## 3. Part template (every workbook section)

```markdown
### Part N — Title

#### N.0 Earlier planning (agent draft — NOT decided)
- ...

#### N.1 Double-confirm
| # | Statement | Your mark (YES / NO / CORRECT) | Correction if needed |
|---|-----------|--------------------------------|----------------------|
| 1 | ... | | |

#### N.2 Your decisions
| ID | Question | Options | Your answer | Notes |
|----|----------|---------|-------------|-------|
| N.2.a | ... | A/B/C | | |

Free text:
> ...

#### N.3 Your research / open questions
> ...

#### N.4 Status
- [ ] unanswered
- [ ] provisional (I may change later)
- [ ] locked (ready for design freeze)
```

---

## 4. Standard Part sequence (adapt per track)

| Part | Theme | Why this order |
|------|--------|----------------|
| 0 | Process lock + how to fill | Align method |
| 1 | Recap & verification of prior track | Don’t rebuild done work |
| 2 | North star & success metrics | Goal before tools |
| 3 | Goals / non-goals | Scope fence |
| 4 | Architecture / ladder | Structure before product |
| 5 | Safety & HITL | Rails before power |
| 6 | Domain-specific deep dive (e.g. CUA) | Expand when goal-critical |
| 7 | Data / secrets / sessions | Credential model |
| 8 | Product shape (skills/experts) | Package |
| 9 | Runtime limits (RAM, concurrency) | Feasibility |
| 10 | Integrations adopt/kill/defer | Inventory decisions |
| 11 | Phasing | Execution order |
| 12 | Acceptance tests | Done definition |
| 13 | Risks & anti-patterns | No repeat fails |
| 14 | Final sign-off table | Single lock sheet |

**Expand Part 6+** when the human’s goal is a “feature upgrade” with a favorite capability (e.g. CUA) or high harm surface (auth, bypass, money).

---

## 5. Agent duties before writing the package

1. Load skills: brainstorming (no code), writing-plans only **after** lock.  
2. Read: PRD §2/§7, AGENTS.md, relevant journey, PROGRESS, DECISIONS, RUNBOOK, CONTINUATION.  
3. Audit live system (VPS/PC) when relevant — labels VALIDATED / UNTESTED / REJECTED.  
4. Draft defaults in N.0 — always mark **NOT decided**.  
5. Prefer multiple-choice + free-text slots.  
6. Never put secrets in planning docs.  

---

## 6. Human duties when filling

1. Read Doc B first (context), then Doc A in order.  
2. Mark N.1 before N.2 when possible.  
3. Use **provisional** freely — step (4) will lock.  
4. Add personal research notes in N.3.  
5. Return the same files (or a copy) with answers filled.  

---

## 7. After return (step 4)

Agent must:

1. Diff answers vs draft defaults.  
2. Resolve conflicts / ask only remaining blockers.  
3. Write locked design (no open “TBD” on critical paths).  
4. Write implementation plan (bite-sized, testable).  
5. Write/update CONTINUATION brief for next session.  
6. Ask before git commit.  

---

## 8. Anti-patterns

| Anti-pattern | Instead |
|--------------|---------|
| Build while “planning” | Steps 1–4 doc-only |
| One giant undecided chat | Offline workbook + return |
| Skip safety Part | Safety before sessions/power |
| Treat N.0 as approved | Explicit N.4 locked |
| Re-plan finished Fasa | Part 1 recap + anti-repeat |
| Secrets in answers | Env names / fingerprints only |

---

## 9. Instantiation checklist (copy for each new PX)

- [ ] Name track: `PX-?` + one-line goal  
- [ ] Create Doc B: `docs/superpowers/specs/YYYY-MM-DD-<px>-audit-recap.md`  
- [ ] Create Doc A: `docs/superpowers/specs/YYYY-MM-DD-<px>-planning-qna.md`  
- [ ] Link both + framework in CONTINUATION / PROGRESS  
- [ ] Human fills offline  
- [ ] Return → lock → plan → build  

---

## 10. Reference instantiations

| Track | Doc B | Doc A |
|-------|-------|-------|
| PX-1b Web Operator | `2026-07-14-px1b-web-operator-audit-recap.md` | `2026-07-14-px1b-web-operator-planning-qna.md` |

---

*End of PX Planning Framework. Reuse this file; do not fork unless the method itself changes.*
