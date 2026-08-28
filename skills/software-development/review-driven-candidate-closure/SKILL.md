---
name: review-driven-candidate-closure
description: "Use when independent review challenges a stateful candidate."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [code-review, candidate, verification, stateful-systems, release-gates]
    related_skills: [systematic-debugging, verification-before-completion, hermes-source-change, test-driven-development]
---

# Review-Driven Candidate Closure

## Overview

Use this skill when an independent reviewer, subagent, CI gate, or adversarial test returns findings against a source candidate that was previously considered testable or ready.

The review result is a *claim inventory*, not proof of the defect and not permission to deploy. Each finding must be reproduced in an isolated environment, converted into a regression contract, fixed at the causal boundary, and re-verified against the final exact candidate identity.

This is especially important for stateful systems where a bounded unit suite can be green while the real failure is in configuration interpretation, precedence, state mutation, process reload, or a stale runtime boundary.

## Core Rules

1. `CHANGES_REQUESTED` reopens the candidate gate. Do not dismiss it because an earlier bounded suite passed.
2. Reviewer output is a lead. Reproduce it locally and label it **HYPOTHESIS** until execution confirms it.
3. Write the smallest regression test before production code. If the test passes immediately, label it **coverage-only** rather than pretending it was RED→GREEN.
4. Fix the root cause, not the narrow input string that exposed it.
5. Fail closed when safety-critical authority is absent, malformed, ambiguous, or contradictory.
6. Keep these boundaries separate:
   - candidate worktree;
   - tested bytes;
   - final commit SHA;
   - pushed/remote ref;
   - deployed files;
   - running process imports;
   - user-visible end-to-end behavior.
7. A passing bounded suite does not erase a valid broader-suite failure. Classify baseline, harness, stale-test, flake, and candidate-specific failures separately.
8. No local commit, reviewer approval, or passing test grants release/deploy/restart authorization.

## When to Use

Use when any of these occurs:

- an independent review returns `CHANGES_REQUESTED`;
- an adversarial probe finds an input that bypasses a safety gate;
- a new test reveals a fail-open path;
- a candidate changes how schedule/configuration authority is interpreted;
- a final commit differs from the bytes that were tested;
- a release report must distinguish candidate readiness from live activation.

Do not use this as a substitute for ordinary code review. Use it after a finding or contradiction appears and the candidate needs closure.

## Phase 1 — Freeze the Candidate Boundary

Before changing anything:

1. Record the worktree path, branch, current `HEAD`, base SHA, and repository guidance.
2. Record complete status, including untracked files and operation sentinels.
3. Identify the exact files and bytes used by the earlier test run.
4. Record the review finding verbatim enough to preserve the input, expected result, observed result, and code location.
5. Inspect the live boundary independently. Never use live files or a running process as an implicit source for candidate tests.
6. State the current disposition:
   - `CANDIDATE-OPEN` — review finding not yet reproduced;
   - `CANDIDATE-BLOCKED` — finding reproduced or evidence insufficient;
   - `CANDIDATE-RETEST` — fix applied, final gates pending;
   - `CANDIDATE-CLOSED` — exact-SHA gates pass, still not live;
   - `LIVE-VERIFIED` — only after a controlled runtime reload and user-visible check.

## Phase 2 — Reproduce Each Finding in Isolation

For each finding, use a throwaway fixture or isolated `HOME`/application root:

1. Copy only the minimum schedule/config/source/state required.
2. Do not run confirmation, migration, or write commands against production state.
3. Execute the exact reviewer input and capture the raw structured result.
4. Compare the observed result to the reviewer claim.
5. If it does not reproduce, keep the reviewer claim as **UNVERIFIED**; do not invent a defect to match the report.
6. If it reproduces, write a one-sentence causal hypothesis:
   `I think X happens because Y; the boundary to change is Z.`
7. Check a nearby negative case to ensure the proposed fix will not weaken the guard.

A reviewer saying “read-only” is not sufficient proof that no side effect occurred. Independently hash production state files and inspect relevant side-effect logs when the review process had access to live paths.

## Phase 3 — Test-First Closure

For every reproduced finding:

### 3.1 Write the smallest contract test

The test must assert behavior, not implementation details. Include:

- the exact triggering input;
- the expected decision/state;
- the relevant finding/rule when a HOLD or rejection is required;
- at least one nearby allowed/negative case;
- isolated state paths and deterministic reference time.

### 3.2 Run and classify the first result

- **RED** — the test fails for the expected candidate defect. Proceed with the minimal fix.
- **COVERAGE-ONLY** — the test passes before the fix because the behavior already exists. Keep it only if it protects the contract; do not claim RED→GREEN evidence.
- **HARNESS-INVALID** — collection/import/setup failed. Repair the harness or label the endpoint `NOT-RUN`; never call it a product failure or PASS.
- **WRONG-RED** — it fails because the fixture, assertion, or environment is wrong. Fix the test before touching production code.

### 3.3 Implement one logical fix

Do not bundle unrelated reviewer findings. After each fix:

1. run the new regression test;
2. run the affected file/suite;
3. inspect the structured output, not only the exit code;
4. perform a nearby negative probe;
5. only then move to the next finding.

## Phase 4 — Stateful and Schedule-Driven Safety Patterns

These patterns generalize to medication gates, policy engines, quotas, workflow state, and other systems where configuration controls whether a write is safe.

### 4.1 Derive canonical recognition from the authority

Do not use a partial hardcoded whitelist for safety-critical entities. Build detection from the active canonical schedule/registry/resolver and its aliases, including active entries and extras/PRN entries where applicable.

A reviewer may expose this class of bug with an omitted entity such as a canonical drug name that was absent from a hand-maintained regex. The durable fix is authority-derived recognition plus a regression case for the omitted category—not adding one more literal to the regex.

### 4.2 Separate temporal authorities

If one source carries reminder metadata and another carries clinical/operational timing, define their roles explicitly:

- reminder tolerance is not automatically a hard execution boundary;
- actual late events should be preserved when the contract allows them;
- early events must be compared against the active lower anchor;
- a phase/taper/feature transition must replace stale static timing for the affected entity;
- record the selected authority in the decision output so a test can prove which time was used.

For ordered phase schedules, derive the slot/entity mapping from non-zero dose/position keys and the phase’s ordered times. Do not hardcode a time-to-slot map that only works for one frequency; a two-dose phase may map B/D to `08:00`/`14:00` while an old static D value remains `16:00`.

### 4.3 Fail closed on malformed authority

A helper returning `None`, `False`, or an empty parse result must not silently fall through to ALLOW. Distinguish:

- valid late/allowed input;
- valid early/blocked input;
- invalid/missing actual value;
- missing/malformed active authority;
- inactive entity/slot.

Emit an explicit configuration or input finding and HOLD when the system cannot safely compare the event to the active authority. Test malformed/missing values directly.

### 4.4 Precedence before generic matching

When inputs can contain exact canonical IDs and generic aliases, reserve exact spans first. Otherwise a specific ID such as `entity_3` can also match the generic `entity` alias, producing duplicate mentions, conflicting slots, or a false cross-entity decision.

The same rule applies to parser tokens, route IDs, model IDs, and state keys: specific canonical forms must win over broad aliases before resolution.

## Phase 5 — Candidate Gate After the Fix

Run gates in layers and preserve every result:

1. new finding-specific regression tests;
2. complete affected suite;
3. broader relevant suite;
4. syntax/compile and whitespace checks;
5. clean-baseline comparison for every broader failure;
6. candidate identity and staged/committed byte checks;
7. live-file hashes/process state.

Use explicit labels:

- `PROVEN` — raw output directly demonstrates the claim;
- `PARTIAL` — bounded evidence passes but a broader gate remains open;
- `BASELINE` — the same failure exists on the clean baseline;
- `CANDIDATE-DEFECT` — deterministic failure introduced by the candidate;
- `HARNESS-INVALID` — the test did not exercise the intended code;
- `UNRESOLVED` — evidence is insufficient;
- `UNVERIFIED` — live/runtime behavior was not exercised.

Never report “all tests pass” when the authoritative broader command has one failure. Say exactly what passed, what failed, and how the failure was attributed.

## Phase 6 — Exact-SHA Closure

Any byte change invalidates earlier candidate evidence.

1. Stage only the intended paths.
2. Run staged whitespace/static checks.
3. Create the local commit only after pre-commit gates pass.
4. Capture the final full SHA.
5. Re-run the affected gate against the final committed tree.
6. Compare worktree file hashes with `git show <final_sha>:<path>` bytes.
7. Verify branch/status and explicitly report push status.
8. Do not reuse a prior SHA’s test result after an amend or follow-up fix.

A clean local commit is `CANDIDATE-CLOSED`, not `RELEASED`, `DEPLOYED`, or `LIVE`.

## Phase 7 — Release Boundary

Stop after candidate closure unless the owner explicitly authorizes release. Deployment requires its own exact-SHA approval and exact-manifest procedure. Gateway restart/reload is a separate side effect and requires a separate operational go-ahead when an active session could be disrupted.

Before any live swap, require:

- candidate regression and broader-gate evidence;
- preserved/rollback-ready live state;
- exact per-path destination manifest;
- pre-copy live hashes and process state;
- a controlled reload plan;
- post-reload import/hash proof;
- a user-visible smoke test separated from lower-level component success.

## Compact Evidence Ledger

Maintain one row per finding:

```text
finding_id | reviewer_claim | isolated_repro | test_status | fix_boundary | affected_suite | baseline_attribution | final_sha | live_status
F1          | ...             | PROVEN          | RED→GREEN   | ...           | ...            | ...                  | ...       | NOT-DEPLOYED
```

A missing field is a gap, not permission to upgrade the disposition.

## Common Failure Modes

| Failure mode | Durable response |
|---|---|
| Reviewer finding dismissed because 49 tests passed | Reproduce the finding; add a focused contract test; reopen the candidate gate |
| Partial medication/entity whitelist | Derive terms from active authority and aliases; test an omitted canonical entry |
| Static schedule time used after phase transition | Carry active phase anchors into the snapshot and test the transition boundary |
| `None` from an invalid anchor reaches ALLOW | Add an explicit configuration HOLD and malformed-authority regression test |
| Exact ID also matched by generic alias | Reserve exact spans before generic matching |
| Full suite has one old failure | Compare clean baseline and report `BASELINE`; do not call the suite green |
| Test passed before implementation | Label `COVERAGE-ONLY`; keep the guard test but do not claim RED evidence |
| New commit created after tests | Rerun gates against final exact SHA and compare committed bytes |
| Local candidate described as live | Hash live files and inspect the running process separately |
| Release approval inferred from “proceed” on an earlier scope | Require the explicit release boundary/command for the current SHA |

## References

- `references/reviewer-driven-stateful-candidate-closure.md` — isolated reproduction examples, stateful safety patterns, and the evidence ledger filled with representative cases.
- Existing debugging/release skills may overlap with this workflow; use the narrowest applicable skill and keep their candidate/live boundary rules consistent.
