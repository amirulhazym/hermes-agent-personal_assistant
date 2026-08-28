---
name: planning-and-task-breakdown
description: Breaks work into ordered tasks. Use when you have a spec or clear requirements and need to break work into implementable tasks. Use when a task feels too large to start, when you need to estimate scope, or when parallel work is possible.
---

# Planning and Task Breakdown

## Overview

Decompose work into small, verifiable tasks with explicit acceptance criteria. Good task breakdown is the difference between an agent that completes work reliably and one that produces a tangled mess. Every task should be small enough to implement, test, and verify in a single focused session.

## When to Use

- You have a spec and need to break it into implementable units
- A task feels too large or vague to start
- Work needs to be parallelized across multiple agents or sessions
- You need to communicate scope to a human
- The implementation order isn't obvious

**When NOT to use:** Single-file changes with obvious scope, or when the spec already contains well-defined tasks.

## Design Gate: When NOT to Plan Yet

Before breaking work into tasks, verify that the design is ready. If the following are NOT locked, DO NOT write tasks — escalate to design freeze first:

- **Terminology** — does every component/state have a single definition?
- **Ownership** — who owns each state, who writes, who reads?
- **Lifecycle** — how does each state get created, consumed, destroyed?
- **Invariants** — what MUST ALWAYS/MUST NEVER happen?
- **Command contracts** — what does the user-facing output look like?

**Signal to stop planning and go back to design:** "But we haven't decided on X yet" or "that depends on how Y works." If you can't write the acceptance criteria for Task 1 because an architectural decision is pending, the design gate is not cleared.

### Architecture-Level Design Review Process

When the user presents an architecture proposal (not a well-defined spec), follow this sequence:

1. **Adversarial review** — try to BREAK the design, not validate it. Look for: ambiguity, dead-end objects (defined but unused), unstated assumptions, missing sections, concurrency gaps, migration gaps. Use `doubt-driven-development` skill for the review methodology.

2. **Extract findings** — classify each finding as CRITICAL (blocks implementation), MAJOR (needs significant change), MINOR (documentation gap, implementation note). Present them as a flat numbered list.

3. **Identify blockers** — from the critical findings, extract the minimum set that MUST be resolved before design can freeze. Blocker is not "everything wrong" — it is "the few things that would make implementation wrong if left unfixed."

4. **Resolve blockers** — for each blocker, present a concrete decision or patch. Do not leave blockers as open questions. Each blocker resolution must change the design document.

5. **Design freeze** — only after all blockers are resolved AND the user explicitly says "freeze" or "proceed" should you consider the design locked.

6. **Implementation plan** — now write the plan with ordered tasks. Never write tasks before freeze.

**Cues that the user wants this sequence:**
- "Jangan terus masuk implementation lepas [phase]"
- "Lock architecture dulu, define terminology dulu, settlekan ownership dulu, baru coding"
- "Cuba patahkan design ini seolah-olah kau reviewer yang nak reject PR ni"
- "Kalau selepas challenge itu tiada lagi critical architectural flaw, freeze design"

**Pattern from 2026-07-16 session:** A 400-line architecture doc went through: adversarial review -> 13 findings -> 5 blockers resolved -> design freeze -> implementation plan. The user explicitly required this sequence: "Jangan terus masuk implementation lepas Phase 4. Aku lagi prefer kita lock architecture dulu, define terminology dulu, settlekan ownership dulu, baru coding."

**Common blocker categories (check these first in your adversarial review):**
- **Terminology gaps** — two components using the same term for different concepts
- **Ownership vacuums** — state/object defined but no owner, no lifecycle, no consumer
- **Fallback ambiguity** — what happens when the happy path fails?
- **Concurrency assumptions** — does the design assume single-threaded access when the system is multi-threaded?
- **Migration gap** — design describes new world but does not explain how to get there from the current code
- **Versioning/staleness** — consumers holding stale state have no way to detect it

### When a Previously-Frozen Design Needs Updating

After implementation starts, new findings should be treated as implementation issues or bugs, not architecture re-openers — unless the finding exposes a fundamental design flaw that was missed. Signal that the user is in this mode: "Kalau jumpa issue baru semasa coding, treat sebagai implementation issue atau bug, bukan buka semula architecture discussion."

When the user does accept a post-freeze update: implement as a merge (additive change to existing files), not a replace (rewrite of existing files). This preserves the original design intent while layering on the fix.

### Implementation Execution Order (Post-Freeze)

After design freeze, follow this execution order to reduce risk and maintain backward compatibility at every step.

**Phase 1a: Adapter Pattern (Foundation)**

```
┌─────────────────┐     ┌──────────────┐     ┌──────────────────────┐
│ Old function    │────▶│  Adapter     │────▶│ New function         │
│ (unchanged)     │     │  (wrapper)   │     │ (typed output)       │
└─────────────────┘     └──────────────┘     └──────────────────────┘
```

Rules:
1. **New function wraps old function** — old function is NEVER modified. Zero regression risk.
2. **Old callers keep calling old function** — unchanged. Zero migration cost.
3. **New callers call new function** — adopt gradually.
4. Only in Phase 2+ does the adapter flip (old function calls new function internally).

**Epic Order for Runtime Architecture Migration:**

| Order | Epic | Risk | Deliverable |
|-------|------|------|-------------|
| 1 | Data model + new resolver service | Low | Typed context object (RuntimeContext), new resolve() wrapper |
| 2 | Status/display consumers | Low | Both commands produce consistent output from same resolver |
| 3 | Fallback reporting | Medium | resolution_reason + fallback_state always set (fix N01) |
| 4 | Execution context inheritance | Low | Child processes inherit parent context, not re-resolve |
| 5 | Invariant tests | Medium | Regression gate for all MUST ALWAYS/MUST NEVER rules |
| 6 | Dashboard read-path alignment | Low | Dual display (persisted + live runtime) |

**Within each epic, do in order:**
1. Write the data model/type first (frozen dataclass with invariants)
2. Write the wrapper/adapter (test it against old output)
3. Write unit tests for invariants
4. Wire into consumers incrementally (not all at once)
5. Verify backward compat: old callers produce identical output

**Test strategy during implementation:**
- Environment-dependent tests (needs API key, live credentials): **skip** with clear message when env not available, not fail
- Unit tests using SimpleNamespace/PlainObject for agent mocks (no circular import risk)
- Invariant tests using standalone class instances (no external deps)
- Regression tests compare adapter output vs old function output

**Rollback per task:** Each task must be individually revertible by reverting its file changes. No cross-task file coupling.

### Worked Example

See `references/implementation-execution-worked-example-2026-07-16.md` for the full execution trace from this session: 6 epics, 30+ tests, adapter pattern in practice.

---

## The Planning Process

### Explain scope before asking for scope decisions

If the user asks what "scope" means, do not repeat a scope question using unexplained labels. First translate scope into concrete system boundaries and give 2–3 named options with examples of what each includes and excludes. For extensible systems, distinguish the target architecture from the initial activation scope: it is valid to design toward a broad Option C while enabling only a smaller set of modules initially. Make the resource and migration trade-offs explicit before requesting a decision.

### Capacity planning for append-only/event systems

When proposing an append-only ledger, compare it against measured current state and separate facts from estimates:

- Measure current file sizes, record counts, and relevant process RSS where possible.
- Label event-size and annual-growth calculations as estimates until a prototype produces real measurements.
- Evaluate CPU, RAM, storage, migration, consistency, test, and privacy costs separately; do not reduce "performance" to CPU alone.
- Call out that the main risk for a small personal system is usually architectural complexity and migration correctness, not raw resource consumption.
- Prefer incremental activation: ledger core and existing projections first, then domain modules such as symptoms, vitals, labs, documents, and clinical instructions.

- Read the spec and relevant codebase sections
- Identify existing patterns and conventions
- Map dependencies between components
- Note risks and unknowns

**Do NOT write code during planning.** The output is a plan document, not implementation.

### Step 2: Identify the Dependency Graph

Map what depends on what:

```
Database schema
    │
    ├── API models/types
    │       │
    │       ├── API endpoints
    │       │       │
    │       │       └── Frontend API client
    │       │               │
    │       │               └── UI components
    │       │
    │       └── Validation logic
    │
    └── Seed data / migrations
```

Implementation order follows the dependency graph bottom-up: build foundations first.

### Step 3: Slice Vertically

Instead of building all the database, then all the API, then all the UI — build one complete feature path at a time:

**Bad (horizontal slicing):**
```
Task 1: Build entire database schema
Task 2: Build all API endpoints
Task 3: Build all UI components
Task 4: Connect everything
```

**Good (vertical slicing):**
```
Task 1: User can create an account (schema + API + UI for registration)
Task 2: User can log in (auth schema + API + UI for login)
Task 3: User can create a task (task schema + API + UI for creation)
Task 4: User can view task list (query + API + UI for list view)
```

Each vertical slice delivers working, testable functionality.

### Step 4: Write Tasks

Each task follows this structure:

```markdown
## Task [N]: [Short descriptive title]

**Description:** One paragraph explaining what this task accomplishes.

**Acceptance criteria:**
- [ ] [Specific, testable condition]
- [ ] [Specific, testable condition]

**Verification:**
- [ ] Tests pass: `npm test -- --grep "feature-name"`
- [ ] Build succeeds: `npm run build`
- [ ] Manual check: [description of what to verify]

**Dependencies:** [Task numbers this depends on, or "None"]

**Files likely touched:**
- `src/path/to/file.ts`
- `tests/path/to/test.ts`

**Estimated scope:** [Small: 1-2 files | Medium: 3-5 files | Large: 5+ files]
```

### Step 5: Order and Checkpoint

Arrange tasks so that:

1. Dependencies are satisfied (build foundation first)
2. Each task leaves the system in a working state
3. Verification checkpoints occur after every 2-3 tasks
4. High-risk tasks are early (fail fast)

Add explicit checkpoints:

```markdown
## Checkpoint: After Tasks 1-3
- [ ] All tests pass
- [ ] Application builds without errors
- [ ] Core user flow works end-to-end
- [ ] Review with human before proceeding
```

### Step 6: Surface the Plan to the User

Before executing ANY task:

1. **State your high-level plan in 2-4 bullet points.** TL;DR first, detail second. The user needs to know "what are you about to do" before you start.
2. **Get explicit approval** — on at least the first task. "Proceed" or "yes" or "create je la" counts. Silence does not.
3. **If the user asks "apa planning sebenar kau ni" or "what's your plan"** — you've already started executing without telling them. Stop. Present the TL;DR. Wait for approval.

This applies especially on session resume: when the user says "resume this session", start with a 3-line summary of where you were and what you'll do next — not with tool calls.

**Signals you skipped this step:**
- User says "aku tak tahu apa planning sebenar kau ni"
- User says "try explain in tldr points" (they had to ask for the summary you should have led with)
- First message after a resume request contains tool calls instead of a plan statement

## Task Sizing Guidelines

| Size | Files | Scope | Example |
|------|-------|-------|---------|
| **XS** | 1 | Single function or config change | Add a validation rule |
| **S** | 1-2 | One component or endpoint | Add a new API endpoint |
| **M** | 3-5 | One feature slice | User registration flow |
| **L** | 5-8 | Multi-component feature | Search with filtering and pagination |
| **XL** | 8+ | **Too large — break it down further** | — |

If a task is L or larger, it should be broken into smaller tasks. An agent performs best on S and M tasks.

**When to break a task down further:**
- It would take more than one focused session (roughly 2+ hours of agent work)
- You cannot describe the acceptance criteria in 3 or fewer bullet points
- It touches two or more independent subsystems (e.g., auth and billing)
- You find yourself writing "and" in the task title (a sign it is two tasks)

## Plan Document Template

```markdown
# Implementation Plan: [Feature/Project Name]

## Overview
[One paragraph summary of what we're building]

## Architecture Decisions
- [Key decision 1 and rationale]
- [Key decision 2 and rationale]

## Task List

### Phase 1: Foundation
- [ ] Task 1: ...
- [ ] Task 2: ...

### Checkpoint: Foundation
- [ ] Tests pass, builds clean

### Phase 2: Core Features
- [ ] Task 3: ...
- [ ] Task 4: ...

### Checkpoint: Core Features
- [ ] End-to-end flow works

### Phase 3: Polish
- [ ] Task 5: ...
- [ ] Task 6: ...

### Checkpoint: Complete
- [ ] All acceptance criteria met
- [ ] Ready for review

## Risks and Mitigations
| Risk | Impact | Mitigation |
|------|--------|------------|
| [Risk] | [High/Med/Low] | [Strategy] |

## Open Questions
- [Question needing human input]
```

## Parallelization Opportunities

When multiple agents or sessions are available:

- **Safe to parallelize:** Independent feature slices, tests for already-implemented features, documentation
- **Must be sequential:** Database migrations, shared state changes, dependency chains
- **Needs coordination:** Features that share an API contract (define the contract first, then parallelize)

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'll figure it out as I go" | That's how you end up with a tangled mess and rework. 10 minutes of planning saves hours. |
| "The tasks are obvious" | Write them down anyway. Explicit tasks surface hidden dependencies and forgotten edge cases. |
| "Planning is overhead" | Planning is the task. Implementation without a plan is just typing. |
| "I can hold it all in my head" | Context windows are finite. Written plans survive session boundaries and compaction. |

## Red Flags

- Starting implementation without a written task list
- Tasks that say "implement the feature" without acceptance criteria
- No verification steps in the plan
- All tasks are XL-sized
- No checkpoints between tasks
- Dependency order isn't considered
- **Jumping from problem statement to execution without Q&A** — when the user gives you multiple open-ended points/feedback, do NOT start executing. First: understand each point, confirm your understanding, get approval on the approach for point 1, THEN execute. Only after completion move to point 2. Skipping Q&A and executing against assumptions wastes more time than asking. Signal: user says "Jgn execute, habiskan qna dulu" or "selesaikan satu satu" or "jangan proceed point lain dulu".
- **Starting execution without telling the user your plan** — when resuming a session or starting a new task, do NOT immediately load skills/make tool calls/start analysis. First: state what you're about to do (2-4 bullet TL;DR), wait for acknowledgment, then execute. A user who says "aku tak tahu apa planning sebenar kau ni" or "try explain in tldr points" is telling you they had to ASK for the plan you should have led with. The first message after a resume should be a plan statement, not a tool call.
- **Correction ≠ Approval** — when the user corrects a specific value (e.g. "C should be 12pm"), that is a CORRECTION of that one value, NOT implicit approval to execute a full multi-step fix plan you've outlined. Respond with just the correction, then ask scope: "Nak saya update semua files yang affected, atau just this one value?" Only proceed with the full plan after explicit approval.
- **Proactive automation without explicit consent** — do NOT create recurring cron jobs, automated briefings, periodic reports, or any system that proactively messages the user unless they explicitly asked for it. A user saying "good morning" or asking about their schedule is NOT consent to set up a daily briefing. The user must say "yes, set that up" or initiate the feature request themselves. If you think a proactive system would be useful, describe the idea and ask — don't build it and let it fire 7 times before the user notices. Signal: user says "asal tiba² ada news?? Siapa setup? Bila setup?" — meaning you created something they never wanted or agreed to.
- **Reopening decided goals** — when the user has approved a requirement (e.g., "10 keys", "use provider X", "this specific architecture"), do NOT stop to reconfirm the goal, question "why N", or present alternatives as replacements. Your job is execution, not re-litigation. The goal was decided with context you may not have seen. If you genuinely see a technical blocker, state the blocker and ask how to proceed — do not reframe it as "maybe we should reconsider the whole goal." Signal: user says "goal aku kekal, kita betulkan execution" or "tu requirement aku, jgn tukar."
- **Alternatives are options, not replacements** — when you suggest an alternative (e.g., "PAYGO is cheaper"), present it as an alternative with trade-offs, NOT as "the cheapest path" that implies the user's original approach is wrong. The user chose their approach for reasons. Your job is to note the alternative and continue with the approved plan. If the alternative is genuinely better, make the case briefly and let the user decide — do not subtly redirect execution toward your preference. Signal: user says "MJ sekali lagi menggantikan requirement aku dengan preference mereka sendiri."

- **Verbose options/analysis after decision is re-litigation, not clarification** — when the user has already decided (e.g. "proceed with 100"), responding with a multi-paragraph root-cause analysis, limitations, or alternative options is re-opening a closed decision. The user's frustration signal is clear: "Aku malas nak baca apa kau tulis tu, panjang sangat. Nanti bagi tldr untuk aku review in short. Hence, aku tetap nak proceed with [their original choice]." Correct pattern: 1-2 line TLDR acknowledgment + immediate execution intent ("On it. [next step]"). If there are important caveats the user MUST know before proceeding, offer them as a single sentence with "I can elaborate if needed" — NEVER as the lead. The user chose their approach; if a real technical blocker surfaces during execution, report it as a blocker — do not dress it up as a reopened design discussion. Signal: user says "panjang sangat" or "tldr" or "aku tetap nak proceed with [original choice]" — you are over-explaining after a decision.
- **Audit → execution plan, not parking** — after completing a diagnostic audit, immediately derive the execution plan from your findings. Do NOT park at "confirm demand" or "reconfirm requirements" when the requirements were already clear. The audit's purpose is to inform execution, not to create another decision gate. Findings should become action items, not discussion topics. Signal: user says "audit sudah selesai, MJ patut terus derive execution plan."
- **Don't confuse your initiative with the user's directive** — your research, automation attempts, tool evaluation, and "nice to have" improvements are YOUR initiative. The user's stated goal is THEIR directive. These are separate tracks. Do not let your initiative derail, delay, or reshape the user's directive. Complete the directive first; propose your initiative separately. Signal: user says "Initiative MJ = research signup flow, cuba automation. Tugas aku = audit masalah dalam execution MJ. Bukan cabar atau tukar goal kau."

## Verification

Before starting implementation, confirm:

- [ ] Every task has acceptance criteria
- [ ] Every task has a verification step
- [ ] Task dependencies are identified and ordered correctly
- [ ] No task touches more than ~5 files
- [ ] Checkpoints exist between major phases
- [ ] The human has reviewed and approved the plan
