# Unstaged Candidate Review Recipe

Use this reference when reviewing a local candidate before commit, especially when the candidate touches hooks, parsers, safety gates, or mutable runtime state.

## 1. Freeze candidate identity before tests

Run and retain:

```text
git status --short --branch
git rev-parse HEAD
git diff --full-index -- <intended paths>
```

Read `AGENTS.md` first. The reviewed object is `HEAD + unstaged bytes`; a commit-only diff or `git ls-files` view can omit the candidate. Keep the review read-only: no staging, commit, push, deployment, patch application, or live-runtime copy.

## 2. Build an isolated test boundary

For code that reads `Path.home()`, `HOME`, `HERMES_HOME`, schedules, medication state, databases, or logs:

- use a temporary home/runtime root;
- copy only the minimum read-only fixtures;
- patch/import modules after the temporary environment is set;
- ensure writes, audit logs, and subprocesses target the temporary root;
- independently confirm production/live files were not modified.

A host-only fixture gate may legitimately skip tests on a fresh clone; report that as a harness boundary, not as a candidate PASS.

## 3. Test each contract boundary directly

For a safety gate or parser, combine the affected suite with small isolated probes for:

- the lower clinical anchor versus reminder-window metadata;
- a late actual value that must remain allowed;
- an early value that must hold;
- missing, malformed, or contradictory configuration, which must fail closed;
- clinician-change language and the exact non-change exception;
- active taper/phase transitions where an anchor can differ from a static schedule value;
- envelope, compact, separator, and context-aware time forms.

Do not infer a finding from source reading alone. Execute the suspected path and record the returned decision/findings. In particular, a helper that returns `None` for malformed input is not fail-closed unless the caller converts `None` into a HOLD/error.

## 4. Review lexical guards against canonical data

When a diff replaces a broad safety guard with a medication/name whitelist, enumerate every canonical schedule and extra medication. A whitelist that covers the motivating example but omits another active medication can turn a real clinician change into an ALLOW. Prefer canonical schedule/resolver-derived matching, or isolate the exact timing-anchor exception instead of weakening the general guard.

## 5. Attribute test failures honestly

Run the affected file alone and the relevant combined command. Classify failures as:

- baseline: reproduced on the exact clean baseline;
- candidate-specific: changed behavior and deterministic in isolation;
- order-sensitive/environment: differs by module order, imported module state, clock, or environment;
- harness-invalid/incomplete.

A known baseline command-order assertion remains baseline when the candidate did not alter ordering. Do not relabel it as a candidate regression merely because it appears in a combined run.

## 6. Reconcile candidate drift before reporting

Repeat status, SHA, and the intended-path diff at the end. If another process commits or mutates the worktree during the review, earlier evidence is stale until the affected checks are rerun against the new bytes. Report the new SHA/status and distinguish the requested unstaged candidate from a now-committed candidate.

## 7. Final evidence shape

Report the exact files inspected, commands run, raw pass/fail counts, baseline attribution, concrete findings with file/line locations, and any workspace-state drift. Never claim the candidate is clean, unstaged, safe, or passing from an earlier snapshot.