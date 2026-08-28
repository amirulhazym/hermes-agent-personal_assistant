# Architecture-Level Adversarial Review Pattern

> **Source:** 2026-07-16 runtime resolver architecture challenge
> **Outcome:** 10 findings found (3 CRITICAL, 3 MAJOR, 4 MINOR), 5 blockers resolved, architecture frozen
> **User verdict:** "9.8/10 — tak ada satu pun finding yang memusnahkan architecture"

## When to Use

Use when reviewing an **architecture design document**, not just code. The key difference from code review:

| Aspect | Code Review | Architecture Review |
|--------|-------------|-------------------|
| What you inspect | Functions, classes, logic | Data flow, ownership, state transitions |
| Failure mode | Runtime crash | Design drift, ambiguity, ownership gaps |
| How to verify | Run tests | Check codebase — do the current files match the design? |
| Classification | Bug, edge case, style | CRITICAL (blocks freeze), MAJOR (must resolve), MINOR (document) |
| Output | Fix PR | Blocker list + freeze decision |

## Process

### Phase 1: Read the Design Document

Read the ENTIRE design doc before forming opinions. Do not jump to conclusions on page 1.

As you read, note:
- Terms that are defined but have NO code equivalent → potential dead objects (Finding #2)
- Claims that sound right but you haven't verified → mark for code check
- Transitions or flows that can't be traced to actual code paths

### Phase 2: Code-Verify Every Verifiable Claim

For each claim in the design, ask: **does the current codebase actually behave this way?**

```
Claim: "Fallback calls resolve_runtime_provider() again"
Code:  try_activate_fallback() iterates _fallback_chain → static, NOT re-resolution
Verdict: ❌ CLAIM DISPROVED — design describes different mechanism than code implements
Action: Resolve ambiguity → hybrid approach (Phase 1 static, Phase 2 dynamic)
```

Tools:
- `search_files()` grep for key terms across the codebase
- `read_file()` specific lines the design references
- `python -c "import ..."` run actual function calls to check return shape
- `git log` check if the doc references stale code state

### Phase 3: Classify Findings

Use this classification — it maps directly to freeze decisions:

| Severity | Meaning | Blocks Freeze? |
|----------|---------|---------------|
| 🔴 CRITICAL | Architecture contradiction — design says A, code does B, and they can't coexist without resolution | YES |
| 🟡 MAJOR | Significant gap or contradiction that must be resolved, but resolution doesn't invalidate the architecture | Recommended |
| 🟢 MINOR | Clarification, documentation, or process gap | No |

**The acid test for CRITICAL:** "If we freeze the design as-is and start coding, will the implementation produce a system that matches the design?" If no (because the design contradicts itself or the codebase), it's CRITICAL.

### Phase 4: Reconcile

For each finding:
1. **State the claim from the design** (verbatim quote or summary)
2. **State the code evidence** (file + line + actual behaviour)
3. **Classify the gap** (ambiguity, contradiction, missing detail)
4. **Propose resolution**

Resolutions fall into categories:
- **Resolve ambiguity** — pick one interpretation (e.g., "Phase 1 static chain, Phase 2 dynamic")
- **Merge/remove dead objects** — e.g., RequestContext had no owner → merge into ExecutionContext
- **Add missing section** — e.g., Concurrency Model, Migration Strategy
- **Downgrade claim** — "MUST" → "SHOULD" when the rule is too strict for existing code

### Phase 5: Present + Freeze Decision

Format your findings as a numbered list. End with a **final verdict**:

```
**Verdict on the PR:** Conditionally accept — fix N critical gaps, then freeze.
```

The user decides whether to freeze. If freeze:
- Lock the design document (mark as v2, v3, etc.)
- Produce implementation plan
- Do NOT reopen architecture discussion unless a genuinely critical implementation flaw appears

## Example Classification Applied (from 2026-07-16 session)

```
# Finding #1 — CRITICAL: Fallback re-resolution contradicts current implementation
Design says: "On fallback, call resolve_runtime_provider() again"
Code says: try_activate_fallback() iterates _fallback_chain, mutates agent attrs in-place
Resolution: Hybrid — Phase 1 static chain, Phase 2 dynamic re-resolution

# Finding #2 — CRITICAL: RequestContext has No Owner
Design defines RequestContext with 8 fields, but Ownership Matrix has no row for it.
Resolution: Merged into ExecutionContext as RequestMetadata

# Finding #3 — CRITICAL: No Concurrency Model
Design assumes single-threaded but runs under asyncio, ThreadPoolExecutor, and subprocesses.
Resolution: Added §9 Concurrency Model with environments, locking, trace propagation

# Finding #5 — 🟡 MAJOR: MCP "CANNOT Override" rule contradicts existing code
Design says "NOTHING (same model as caller)"
Existing tools (web_tools.py, image_generation_tool.py) have model override mechanisms
Resolution: "NOTHING" → "SHOULD NOT unless explicitly required by tool contract"
```

## Common Architecture Failure Patterns to Check

1. **Dead-object smell** — Defined in terminology but no owner, no lifecycle, no consumer → CRITICAL
2. **Design-code mismatch** — Design describes mechanism A, code implements mechanism B → CRITICAL
3. **Concurrency blind spot** — Architecture assumes single-threaded but runtime is multi-threaded → CRITICAL
4. **Over-specification** — Design says "MUST NOT" but existing code violates it → MAJOR
5. **Missing migration** — Design describes new architecture but says nothing about how to get there → MAJOR
6. **Enum incomplete** — Design lists 5 values, code returns 12 different ones → MINOR
7. **Vague computation** — "X is computed from Y" without specifying how → MINOR

## Pitfalls

- **Don't validate, DISPROVE.** Your job is to find what's wrong, not confirm what's right. The user says "cuba patahkan design ini seolah-olah kau reviewer yang nak reject PR ni."
- **Code-evidence before acceptance.** Every design claim that references behaviour must be checked against actual code. Don't accept "R01: provider non-empty" without checking if the current function actually enforces it.
- **Don't conflate severity.** A MINOR finding about an incomplete enum doesn't block freeze. A CRITICAL finding about undefined fallback mechanism does. Label honestly.
- **No findings = you didn't look hard enough.** Perfect architecture docs don't exist. If you find zero issues, you're validating, not reviewing.
- **Reconcile findings — don't just dump them.** For each CRITICAL finding, propose a resolution. The user should be able to say "do that" and the blocker is resolved.
- **Missing Finding trap.** The user may find flaws you missed. Don't be defensive — add them and update the blocker list. User found 3 missing findings in the 2026-07-16 session (RuntimeContext versioning, resolver idempotency, migration strategy).
