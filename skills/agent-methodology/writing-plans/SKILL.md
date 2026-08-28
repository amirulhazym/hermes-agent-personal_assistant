---
name: writing-plans
description: Use when you have a spec or requirements for a multi-step task, before touching code
---

# Writing Plans

## Overview

Write comprehensive implementation plans assuming the engineer has zero context for our codebase and questionable taste. Document everything they need to know: which files to touch for each task, code, testing, docs they might need to check, how to test it. Give them the whole plan as bite-sized tasks. DRY. YAGNI. TDD. Frequent commits.

Assume they are a skilled developer, but know almost nothing about our toolset or problem domain. Assume they don't know good test design very well.

**Announce at start:** "I'm using the writing-plans skill to create the implementation plan."

**Context:** If working in an isolated worktree, it should have been created via the `superpowers:using-git-worktrees` skill at execution time.

**Save plans to:** `docs/superpowers/plans/YYYY-MM-DD-<feature-name>.md`
- (User preferences for plan location override this default)

## Prerequisite: Architecture Design Gate

**When this applies:** The task involves architecture redesign — redefining components, boundaries, state ownership, or data flow — not just adding a feature within an existing architecture. The user's spec may be a problem statement or desired outcome rather than a concrete spec. In this case, DO NOT jump to plan writing. First, produce the design artifacts below.

**Related reference:** `references/hermes-current-runtime-architecture.md` contains a verified snapshot of Hermes' current runtime resolver architecture (resolve_runtime_provider, consumers, implicit priority chain). Consult and update this when doing architecture work on the Hermes codebase — it saves re-digging from scratch.

**Why this exists:** The root failure pattern in architecture work is that every component develops its own interpretation of shared terms ("current model", "runtime", "effective state", "configured") because the design wasn't locked before coding. Fixing ambiguous terminology post-implementation costs orders of magnitude more than settling it upfront.

### Required Artifacts

Produce these before writing any task list. Each artifact must be reviewed and approved before the next is started — do not batch-produce them:

**1. Terminology Lock**
Define every state/component/transition term formally in a glossary. Examples:
- `Configured` = what config.yaml stores
- `Requested` = what the user explicitly asked for via command/UI (may differ from Configured)
- `Resolved` = output of the resolver before applying fallback logic
- `Effective` = what actually executes (post-fallback, post-override)
- `Runtime` = the resolver output that lives for the lifecycle of a session
Do NOT proceed until every term used in the design has exactly one definition everyone agrees on.

**2. Resolution Map (Consumer | Reads | Writes | Owner)**
For each state field, a table:
```
State Field | Consumer | Reads? | Writes? | Owner
```
This surfaces hidden dependencies and implicit write access. A field written by three consumers with no formal owner is a data-race risk. Do NOT just list consumers — explicitly mark who READS vs WRITES vs OWNS each field.

**3. State Ownership Matrix**
```
State | Owner | Writable By | Readable By | Lifecycle
```
- Lifecycle: "entire runtime", "per-request", "per-model/provider", "per-session"
- Formalises who can mutate vs observe each state
- Identifies read-only projections (e.g. Dashboard reads but never writes)

**4. State Transition Specification**
A formal transition chain. Example:
```
Configured → Requested → Resolved → Effective → Persisted → Historical
```
For each transition arrow, define:
- Who triggers it
- Who validates it
- Who persists the result
- Who publishes the change event (if applicable)
Also handle re-resolution paths (e.g. fallback: Effective → Resolved with different inputs, not a linear continuation)

**5. Specification (Input | Priority | Rules | Conflict Rules | Failure Behaviour | Output | Invariant)**
Before implementing any resolver/engine function, write the formal spec:

```
Input: [all inputs with types]
Priority: [explicit priority chain]
Resolution Rules: [deterministic rules in order]
Conflict Rules: [what wins when two rules contradict]
Failure Behaviour: [what happens per failure mode]
Output: [all output fields with types]
Invariant: [properties that must always hold post-resolution]
```

**6. Engineering Invariants**
A MUST ALWAYS / MUST NEVER list that becomes the regression test contract.

```
[Component] MUST ALWAYS:
- return [field] (non-empty)
- produce deterministic output for same inputs
- log resolution reason before returning

[Component] MUST NEVER:
- silently guess or default when input is invalid
- return stale state without warning
- fallback without logging the fallback reason
```

**7. Separation of Concerns Boundary**
Explicitly separate:
- System-side behavior (your app's resolution, fallback, routing logic)
- External-side behavior (provider SDK behaviour, credential expiry, API quirks)
These may produce the same observable outcome but have different ownership. Define the boundary before implementation so bugs are routed to the right team/component.

### Design Review Gate

Before writing implementation tasks, confirm:

- [ ] Terminology locked — every term has one definition, no ambiguity
- [ ] Resolution Map complete — every field's consumer/reader/writer/owner known
- [ ] State Ownership Matrix complete — lifecycle and mutability clear for all states
- [ ] State Transitions specified — formal chain with trigger/validator/persist roles
- [ ] Component Specs written — input/priority/rules/output/invariants for each resolver
- [ ] Engineering Invariants drafted — MUST ALWAYS / MUST NEVER list
- [ ] Separation boundary drawn — system-side vs external-side ownership split
- [ ] User has reviewed and approved all artifacts

Only after this gate is passed should you proceed to writing implementation tasks. The user's own words from a production session: "Design cost now << patch cost later. Jangan coding sampai semua ni lock."

## Scope Check

If the spec covers multiple independent subsystems, it should have been broken into sub-project specs during brainstorming. If it wasn't, suggest breaking this into separate plans — one per subsystem. Each plan should produce working, testable software on its own.

## File Structure

Before defining tasks, map out which files will be created or modified and what each one is responsible for. This is where decomposition decisions get locked in.

- Design units with clear boundaries and well-defined interfaces. Each file should have one clear responsibility.
- You reason best about code you can hold in context at once, and your edits are more reliable when files are focused. Prefer smaller, focused files over large ones that do too much.
- Files that change together should live together. Split by responsibility, not by technical layer.
- In existing codebases, follow established patterns. If the codebase uses large files, don't unilaterally restructure - but if a file you're modifying has grown unwieldy, including a split in the plan is reasonable.

This structure informs the task decomposition. Each task should produce self-contained changes that make sense independently.

## Task Right-Sizing

A task is the smallest unit that carries its own test cycle and is worth a fresh reviewer's gate. When drawing task boundaries: fold setup, configuration, scaffolding, and documentation steps into the task whose deliverable needs them; split only where a reviewer could meaningfully reject one task while approving its neighbor. Each task ends with an independently testable deliverable.

## Bite-Sized Task Granularity

**Each step is one action (2-5 minutes):**
- "Write the failing test" - step
- "Run it to make sure it fails" - step
- "Implement the minimal code to make the test pass" - step
- "Run the tests and make sure they pass" - step
- "Commit" - step

## Plan Document Header

**Every plan MUST start with this header:**

```markdown
# [Feature Name] Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** [One sentence describing what this builds]

**Architecture:** [2-3 sentences about approach]

**Tech Stack:** [Key technologies/libraries]

## Global Constraints

[The spec's project-wide requirements — version floors, dependency limits,
naming and copy rules, platform requirements — one line each, with exact
values copied verbatim from the spec. Every task's requirements implicitly
include this section.]

---
```

## Task Structure

````markdown
### Task N: [Component Name]

**Files:**
- Create: `exact/path/to/file.py`
- Modify: `exact/path/to/existing.py:123-145`
- Test: `tests/exact/path/to/test.py`

**Interfaces:**
- Consumes: [what this task uses from earlier tasks — exact signatures]
- Produces: [what later tasks rely on — exact function names, parameter
  and return types. A task's implementer sees only their own task; this
  block is how they learn the names and types neighboring tasks use.]

- [ ] **Step 1: Write the failing test**

```python
def test_specific_behavior():
    result = function(input)
    assert result == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/path/test.py::test_name -v`
Expected: FAIL with "function not defined"

- [ ] **Step 3: Write minimal implementation**

```python
def function(input):
    return expected
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/path/test.py::test_name -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/path/test.py src/path/file.py
git commit -m "feat: add specific feature"
```
````

## No Placeholders

Every step must contain the actual content an engineer needs. These are **plan failures** — never write them:
- "TBD", "TODO", "implement later", "fill in details"
- "Add appropriate error handling" / "add validation" / "handle edge cases"
- "Write tests for the above" (without actual test code)
- "Similar to Task N" (repeat the code — the engineer may be reading tasks out of order)
- Steps that describe what to do without showing how (code blocks required for code steps)
- References to types, functions, or methods not defined in any task

## Remember
- Exact file paths always
- Complete code in every step — if a step changes code, show the code
- Exact commands with expected output
- DRY, YAGNI, TDD, frequent commits

## Self-Review

After writing the complete plan, look at the spec with fresh eyes and check the plan against it. This is a checklist you run yourself — not a subagent dispatch.

**1. Spec coverage:** Skim each section/requirement in the spec. Can you point to a task that implements it? List any gaps.

**2. Placeholder scan:** Search your plan for red flags — any of the patterns from the "No Placeholders" section above. Fix them.

**3. Type consistency:** Do the types, method signatures, and property names you used in later tasks match what you defined in earlier tasks? A function called `clearLayers()` in Task 3 but `clearFullLayers()` in Task 7 is a bug.

If you find issues, fix them inline. No need to re-review — just fix and move on. If you find a spec requirement with no task, add the task.

## Variant: Master Execution Plan (Large Projects)

For multi-phase, multi-day projects with infrastructure dependencies (Docker, Chromium, external services), the standard task-by-task plan is insufficient. Use the **11-section Master Execution Plan** format, which the user approved as a one-shot blueprint before autonomous execution.

### When to Use

- Project spans multiple phases or days
- Requires infrastructure (Docker, Chromium, external services)
- User wants a single approval gate before autonomous execution
- Dependency chain is complex (tool A → tool B → integration)

### The 11 Sections

```
1. **Current State Assessment** — Verified inventory: what's installed, working, missing, blocked
   └─ Table: Item | Status | Evidence (freshly verified, not assumed)

2. **Final Architecture Snapshot** — No discussion. No options. The approved architecture as a diagram.
   └─ Include: executor count, abstraction layers, component relationships

3. **Implementation Roadmap** — Phase/Milestone/Task/Subtask/Dependencies/Expected output/Acceptance criteria/Risk/Rollback
   └─ Each task: ID, objective, files, verify command, expected output, rollback, known limitation

4. **Execution Order (Dependency Graph)** — Task IDs with explicit precedence arrows
   └─ Sequential path for autonomous execution: T001 → T002 → ...

5. **Folder Structure (FINAL)** — No options. The actual directory tree.

6. **Module List** — Module name, purpose, owner, dependency, status (TODO/DONE/BLOCKED)

7. **Testing Strategy** — Per module: Unit test, Integration test, Live verification, Success criteria

8. **Logging / Monitoring / Metrics / Analytics / Error / Recovery**
   └─ Structured logging, error escalation chain, fallback behavior

9. **Implementation Priority** — Critical → High → Medium → Low → Tech debt → Future backlog

10. **Deliverables (per-phase visible value)** — What the user can SEE working after each phase
    └─ Proof format: verification command + expected output

11. **Completion Checklist** — Binary (✅/❌) for each requirement until production-ready
```

### Key Differences from Standard Plan

| Aspect | Standard Plan | Master Execution Plan |
|--------|--------------|----------------------|
| Scope | Single feature | Multi-phase project |
| Acceptance | Per-task gate | Single pre-approval, then autonomous |
| Verification | Red-green TDD | Live system test with real sites |
| Risk handling | Relies on TDD | Explicit rollback per task |
| User reporting | Per-task completion | Milestone-level only |
| Dependency tracking | Implicit (task order) | Explicit graph |
| Current state | Assumed working | **Verified inventory** |

### Acceptance Criteria Format (per task)

Every task must have these 7 fields:

```markdown
| ID | Task | Objective | Files | Verifiy Command | Expected Output | Rollback | Limitation |
|----|------|-----------|-------|-----------------|-----------------|----------|------------|
| T01 | Foo | What it does | list | exact command | VERIFIED len=500 | revert | no JS |
```

If a task cannot be verified with a repeatable command producing stable output, the task is not yet well-defined. Fix the task definition before executing.

### Phase Value Delivery

Every phase must produce a visible user-facing capability. The user should be able to see progress:

```
Phase 1a: Can query static sites (Bing, GitHub) via Document
Phase 1b: Can query Cloudflare sites (Parfumo) — CF bypass verified
Phase 1c: Can query JS-heavy sites (Shopee, Google) — markdown extraction
Phase 2:   System routes correctly per domain automatically
Phase 3:   System learns per-domain best path from analytics
```

If a phase doesn't deliver a visible user value, reconsider its design.

### Git Strategy for Autonomous Execution

- Commits at phase milestone ONLY (not per-task)
- NO push, NO merge, NO remote (all local)
- Commit message: `"Phase N: what was done"`
- User pushes to remote in batch when ready

## Execution Handoff

After saving the plan, offer execution choice:

**"Plan complete and saved to `docs/superpowers/plans/<filename>.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?"**

**If Subagent-Driven chosen:**
- **REQUIRED SUB-SKILL:** Use superpowers:subagent-driven-development
- Fresh subagent per task + two-stage review

**If Inline Execution chosen:**
- **REQUIRED SUB-SKILL:** Use superpowers:executing-plans
- Batch execution with checkpoints for review
