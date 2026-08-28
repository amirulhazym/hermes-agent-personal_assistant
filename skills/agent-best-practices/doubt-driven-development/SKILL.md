---
name: doubt-driven-development
description: Subjects every non-trivial decision to a fresh-context adversarial review before it stands. Use when correctness matters more than speed, when working in unfamiliar code, when stakes are high (production, security-sensitive logic, irreversible operations), or any time a confident output would be cheaper to verify now than to debug later.
---

# Doubt-Driven Development

## Overview

A confident answer is not a correct one. Long sessions accumulate context that quietly turns assumptions into "facts" without anyone noticing. Doubt-driven development is the discipline of materializing a fresh-context reviewer — biased to **disprove**, not approve — before any non-trivial output stands.

This is not `/review`. `/review` is a verdict on a finished artifact. This is an in-flight posture: non-trivial decisions get cross-examined while course-correction is still cheap.

## When to Use

A decision is **non-trivial** when at least one of these is true:

- It introduces or modifies branching logic
- It crosses a module or service boundary
- It asserts a property the type system or compiler cannot verify (thread safety, idempotence, ordering, invariants)
- Its correctness depends on context the future reader cannot see
- Its blast radius is irreversible (production deploy, data migration, public API change)

Apply the skill when:

- About to make an architectural decision under uncertainty
- About to commit non-trivial code
- About to claim a non-obvious fact ("this is safe", "this scales", "this matches the spec")
- Working in code you don't fully understand
- **Meta-application: questioning whether the system's own safeguards actually work.**
  Spawn a fresh-context adversarial review of the CLAIM that "the current system
  architecture is sufficient to prevent [failure mode X]." The reviewer gets the
  architecture description as ARTIFACT and your safety/verification requirements
  as CONTRACT. This catches blind spots where the system expects the agent to
  self-regulate without architectural enforcement.

**When NOT to use:**

- Mechanical operations (renaming, formatting, file moves)
- Following a clear, unambiguous user instruction
- Reading or summarizing existing code
- One-line changes with obvious correctness
- Pure tooling operations (running tests, listing files)
- The user has explicitly asked for speed over verification

If you doubt every keystroke, you ship nothing. The skill applies only to non-trivial decisions as defined above.

## Loading Constraints

This skill is designed for the **main-session orchestrator**, where Step 3 (DOUBT, detailed below) can spawn a fresh-context reviewer.

- **Do NOT add this skill to a persona's `skills:` frontmatter.** A persona that follows Step 3 would spawn another persona — the orchestration anti-pattern explicitly forbidden by `references/orchestration-patterns.md` ("personas do not invoke other personas").
- **If you find yourself applying this skill from inside a subagent context** (where nested subagent spawn is prevented): the preferred path is to surface to the user that doubt-driven cannot run nested and let the main session handle it. As a last resort only, a degraded self-questioning fallback exists — rewrite ARTIFACT + CONTRACT as a fresh self-prompt with a hard mental separator from your prior reasoning, and walk Steps 1–5. This is **not fresh-context review** (you carry your own context with you), so flag the result as degraded and prefer escalation whenever the user is reachable.

## The Process

Copy this checklist when applying the skill:

```
Doubt cycle:
- [ ] Step 1: CLAIM — wrote the claim + why-it-matters
- [ ] Step 2: EXTRACT — isolated artifact + contract, stripped reasoning
- [ ] Step 3: DOUBT — invoked fresh-context reviewer with adversarial prompt
- [ ] Step 4: RECONCILE — classified every finding against the artifact text
- [ ] Step 5: STOP — met stop condition (trivial findings, 3 cycles, or user override)
```

### Step 1: CLAIM — Surface what stands

Name the decision in two or three lines:

```
CLAIM: "The new caching layer is thread-safe under the
        read-heavy workload described in the spec."
WHY THIS MATTERS: a race here corrupts user data and is
                  hard to detect in QA.
```

If you can't write the claim that compactly, you have a vibe, not a decision. Surface it before scrutinizing it.

### Step 2: EXTRACT — Smallest reviewable unit

A fresh-context reviewer needs the **artifact** and the **contract**, not the journey.

- Code: the diff or the function — not the whole file
- Decision: the proposal in 3–5 sentences plus the constraints it has to satisfy
- Assertion: the claim plus the evidence that supposedly supports it

Strip your reasoning. If you hand over conclusions, you'll get back validation of your conclusions. The unit must be small enough that a reviewer can hold it in mind in one read — if it's a 500-line PR, decompose first.

### Step 3: DOUBT — Invoke the fresh-context reviewer

The reviewer's prompt **must be adversarial**. Framing decides the answer.

```
Adversarial review. Find what is wrong with this artifact.
Assume the author is overconfident. Look for:
- Unstated assumptions
- Edge cases not handled
- Hidden coupling or shared state
- Ways the contract could be violated
- Existing conventions this might break
- Failure modes under unexpected input

Do NOT validate. Do NOT summarize. Find issues, or state
explicitly that you cannot find any after thorough examination.

ARTIFACT: <paste artifact>
CONTRACT: <paste contract>
```

**Pass ARTIFACT + CONTRACT only. Do NOT pass the CLAIM.** Handing the reviewer your conclusion biases it toward agreement. The reviewer must independently determine whether the artifact satisfies the contract.

### Step 3a: Contain the Reviewer’s Side Effects

A prompt saying “read-only only” is not a sandbox. A reviewer can still choose a plumbing command that avoids the worktree but writes internal state. Before delegation:

1. Give an explicit mutation denylist appropriate to the domain (for Git: no `add`, `commit`, `fetch`, `merge`, `push`, `update-ref`, branch/tag/worktree creation, stash, clean, GC/prune, or real-repo `merge-tree --write-tree`).
2. Capture a minimal baseline: HEAD, branch, refs, staged diff, working status, and any internal surface the proposed probe may mutate.
3. Prefer probes that write only to an isolated temporary location. For Git merge forecasts, set a temporary `GIT_OBJECT_DIRECTORY` and use the real repositories only through `GIT_ALTERNATE_OBJECT_DIRECTORIES`; remove the temp store and unset both variables in the same bounded command.
4. Re-check the baseline after delegation. Do not trust “no changes made” from the reviewer without direct evidence.
5. If the reviewer violates scope, keep the gap visible. Report the exact side effect, verify blast radius, and do not clean internal objects or refs without approval.

Important Git example: `git merge-tree --write-tree` does not touch the working tree or index, but it creates tree objects. Running it against the real object database is therefore not strictly read-only. Isolate its object writes when the contract forbids repository mutation.

### Step 4: RECONCILE — Fold findings back

The reviewer's output is data, not verdict. **You are still the orchestrator.** Re-read the artifact text against each finding before classifying — rubber-stamping the reviewer is the same failure mode as ignoring it.

**Before accepting any finding that cites code, verify the citation against the real codebase.** A reviewer may cite a wrong file/line, a stale assumption (e.g. "deepseek-chat is V3, no thinking" after a server-side alias remap), or a code path that a later edit moved. Proven 2026-08-07: of 18 adversarial findings on a Hermes fix design, every accepted one was verified in the repo first (fallback_models, MODEL_ALIASES, usage_pricing, aux client) — verification turned one "CRITICAL" claim (deployment window kills token persistence) into a solved design change and confirmed others exactly. A finding that cites code you can't reproduce in the repo is a contract-misread or noise until you can.

For each finding, classify in this **precedence order** (first matching class wins):

1. **Contract misread** — reviewer flagged something specifically because the CONTRACT you provided was unclear or incomplete. Fix the contract first, re-classify on the next cycle.
2. **Valid + actionable** — real issue requiring a change to the artifact. Change it, re-loop.
3. **Valid trade-off** — issue is real but cost of fixing exceeds cost of accepting. Document the trade-off explicitly so the user sees it.
4. **Noise** — reviewer flagged something that's actually correct under context the reviewer didn't have. Note it, move on, and ask: would adding that context to the contract have prevented the false flag?

A fresh reviewer can be wrong because it lacks context. Don't defer just because it's "fresh."

### Step 5: STOP — Bounded loop, not recursion

Stop when:

- Next iteration returns only trivial or already-considered findings, **or**
- 3 cycles completed (escalate to user, don't grind a fourth alone), **or**
- User explicitly says "ship it"

If after 3 cycles the reviewer still surfaces substantive issues, the artifact may not be ready. Surface this to the user — three unresolved cycles is information about the artifact, not a reason to keep looping.

If 3 cycles is "obviously insufficient" because the artifact is large: the artifact is too big — return to Step 2 and decompose. Do not lift the bound.

## Common Rationalizations

| Rationalization | Reality |
|---|---|
| "I'm confident, skip the doubt step" | Confidence correlates poorly with correctness on novel problems. Moments of certainty are exactly when blind spots hide. |
| "Spawning a reviewer is expensive" | Debugging a wrong commit in production is more expensive. The check is bounded; the bug isn't. |
| "The reviewer will just nitpick" | Only if unscoped. Constrain the prompt to "issues that would make this fail under the contract." |
| "I'll do doubt at the end with `/review`" | `/review` is a final gate. Doubt-driven catches wrong directions early when course-correction is cheap. By PR time it's too late. |
| "If I doubt every step I'll never ship" | The skill applies to non-trivial decisions, not every keystroke. Re-read "When NOT to Use." |
| "Two opinions are always better than one" | Not when the second has less context and produces noise. Reconcile, not defer. |
| "It can't be done — the tool/system/architecture forbids it" | **The "can't do" reflex.** This is the most dangerous rationalization because it terminates inquiry. Before reporting impossibility, run a one-shot adversarial review on the barrier itself: "Is this *actually* impossible, or have I simply not found the alternative path?" Common cases: assuming a tool/API is broken when the real issue is a configuration gap; assuming a DB schema forbids an operation when a different approach works around it; assuming a platform limits you when the limitation is session-scoped. Give the barrier 1–2 alternate-attempt tries before calling it impossible, and always surface the constraint as data for the user to judge rather than as a final verdict. |
| "The reviewer disagreed so I was wrong" | The reviewer lacks your context — disagreement is information, not verdict. Re-read the artifact, classify, then decide. |
| "I obviously know what 'tu' / 'itu' / 'that' refers to — we were JUST talking about it" | **The stale-context assumption trap.** At session start (or after context expiry), the user may open with a vague reference like "Dah finalize ke tu?" — and you will confidently map it to whatever YOU were last thinking about. This is not just a memory problem (session_search fixes recall); it's a **framing** problem: your last turn's focus biases which session you reach for and how you interpret the reference. Doubt the mapping: search session history, find ALL candidate topics the user could mean, and only after seeing the evidence commit to one — or ask. The cost of guessing wrong is worse than asking: user has to re-explain AND re-earn trust on the real topic. |

## Red Flags

- Spawning a fresh-context reviewer for a one-line rename or formatting change
- Treating reviewer output as authoritative without re-reading the artifact text
- Looping >3 cycles without escalating to the user
- Prompting the reviewer with "is this good?" instead of "find issues"
- Skipping doubt under time pressure on a high-stakes decision
- Re-spawning fresh-context on an unchanged artifact (you'll get the same findings; you're stalling)
- **Doubt theater (checkable signal)**: across 2 or more cycles where the reviewer surfaced substantive findings, zero findings were classified as actionable. You are validating, not doubting. Stop and escalate.
- Doubting only after committing — that's `/review`, not doubt-driven development
- Stripping the contract from the reviewer's input
- Passing the CLAIM to the reviewer (biases toward agreement)

## Architecture-Level Design Review (Variant)

When the artifact is an **architecture design document, proposal, or spec** (not code), adapt the process:

### Framing

**Adopt a "try to reject this PR" posture.** Your goal is not to validate the design — it's to find reasons it should NOT be accepted. The user explicitly prefers this framing over validation (confirmed 2026-07-16: "terbaik... kali ni dia bukan cuba mengesahkan design. Dia cuba mematahkan design").

### Finding Structure

Each finding follows this format:

```
## Finding #[N] — [SEVERITY]: [Title]

**Design says:** [quote from document]
**Current code proves otherwise:** [evidence from codebase]
**Gap:** [what's wrong — the precise contradiction or omission]
**Verdict:** [severity label]
```

Severity classification:

- 🔴 **CRITICAL** — Blocks implementation. Must be resolved before freeze.
- 🟡 **MAJOR** — Requires significant change but doesn't invalidate architecture.
- 🟢 **MINOR** — Clarification, documentation gap, future concern. Accept with note.

### Finding Types to Look For

1. **Specification ambiguity** — design says X, but X can mean two different things. Always worse than it sounds.
2. **Implementation contradiction** — design says X, but current code does Y (verify against codebase).
3. **Ownership orphan** — a defined object/state with no owner, no lifecycle, no consumer.
4. **Concurrency blind spot** — design assumes single-threaded, but deployment is multi-threaded/async.
5. **Contract conflict** — design contract (e.g., /model output) contradicts existing UX (e.g., interactive picker).
6. **Rule-violation-by-existing-code** — a "MUST NEVER" rule that existing code already violates.
7. **Missing transition** — a state is defined but no one defines how you get there or leave.
8. **Missing Finding** — after your review, actively ask: "what did I miss?" Then find 1-2 more issues the author wouldn't have thought of.

### Reconciliation

After listing findings, produce a **Reconciliation Table**:

| # | Severity | Fixed in Doc? | Accept Design? |
|---|----------|---------------|----------------|
| 1 🔴 | Title | Yes/No/Partial | Must patch / Accept |
| ... | | | |

Then derive **Blockers Before Freeze** — the minimum set of findings that must be resolved before the design can be frozen. Everything else is accepted with notes.

### Blockers vs Non-Blockers

- A blocker is a finding that, if unresolved, would cause the implementation to produce a system that violates the design's own requirements.
- A non-blocker is a finding that can be deferred to implementation notes or future phases.
- Group blockers as: "These N items must be resolved. After that, freeze. No re-opening architecture discussion unless a genuinely critical blocker appears during implementation."

### Worked Example

See `references/architecture-challenge-review-2026-07-16.md` for a full worked example: 10+3 findings against a 400-line architecture design doc, producing 5 blockers, resulting in design freeze + implementation plan. The user rated the output 9.8/10.

### Verification Checklist for Architecture Reviews

- [ ] Every finding has a QUOTE from the design doc and a CODE REFERENCE from the codebase
- [ ] Severity classification uses the 🔴/🟡/🟢 system consistently
- [ ] "Missing Findings" were explicitly searched for (at least 1-2 added after main review)
- [ ] Reconciliation table produced with clear accept/reject per finding
- [ ] Blockers before freeze identified (not just a list of all findings)
- [ ] Final verdict stated as "APPROVED WITH CONDITIONS" or "REJECTED — see blockers"

---

## Interaction with Other Skills

- **`test-driven-development`**: TDD's RED step is doubt made concrete — a failing test is a disproof attempt. When TDD applies, that failing test *is* the doubt step for behavioral claims.
- **`debugging-and-error-recovery`**: when the reviewer surfaces a real failure mode, drop into the debugging skill to localize and fix.
- **`references/adversarial-review-prompt-pattern.md`**: Detailed guide for constructing review prompts when the doubt cycle invokes a fresh-context reviewer (Step 3). Includes prompt structure, cross-check protocol, and false positive handling. Essential when the review spans multiple files or non-trivial logic (2026-07-05 session: reviewed 15 files, found 7 real issues).
- **`references/architecture-adversarial-review.md`**: Architecture-level review pattern — applies the doubt cycle to architecture design documents rather than code. Adds code-verification protocol (check current codebase against design claims), finding classification (CRITICAL/MAJOR/MINOR), and freeze decision flow. Essential before committing to a new architecture (2026-07-16 session: found 10 issues, 3 critical, architecture conditionally frozen).
- **`references/architecture-challenge-review-2026-07-16.md`**: Full worked example of an architecture-level design review — 13 findings, 5 blockers, reconciliation table, final verdict. Reference for the Architecture-Level Design Review variant.

## Verification

After applying doubt-driven development:

- [ ] Every non-trivial decision (per the definition above) was named explicitly as a CLAIM before standing
- [ ] At least one fresh-context review per non-trivial artifact (a failing test produced by TDD's RED step satisfies this for behavioral claims)
- [ ] The reviewer received ARTIFACT + CONTRACT — NOT the CLAIM, NOT your reasoning
- [ ] The reviewer's prompt was adversarial ("find issues"), not validating ("is it good")
- [ ] Findings were classified against the artifact text (not rubber-stamped) using the precedence: contract misread / actionable / trade-off / noise
- [ ] A stop condition was met (trivial findings, 3 cycles, or user override)
