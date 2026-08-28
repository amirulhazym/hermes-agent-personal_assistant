---
name: ordered-overlay-candidate-closure
description: Use for ordered upstream-overlay candidate reconstruction.
version: "1.0.0"
author: "Hermes Agent"
license: "MIT"
metadata:
  hermes:
    tags: [devops, release, provenance, testing]
    related_skills:
      - hermes-source-change
      - verification-before-completion
---

# Ordered Overlay Candidate Closure

## Purpose

Use this skill when the destination repository is a partial source/recovery index and the real runtime is reconstructed from an approved upstream base plus an ordered series of custom patch artifacts. The goal is a reproducible, testable **candidate**, not an implicit merge, deployment, or live update.

This is a class-level workflow for Model-B-style source authority:

```text
approved upstream base
  + ordered patch series
  + source lock / patch hashes
  + tree/deployment manifest
  = reconstructed candidate
```

Keep these states separate at all times:

```text
base → patch artifact → materialized candidate → local commit
→ pushed ref → deployed disk → active process → user-visible behavior
```

A later state is never inferred from an earlier one.

## When to use

- The destination Git repository does not contain the complete upstream runtime tree.
- Runtime files exist in a nested/live source lineage or are represented by patch artifacts.
- A multi-file fix must be preserved without importing an unrelated upstream release.
- The user requires exact SHA, manifest, no-push, no-deploy, or owner-gated release evidence.
- A long candidate test needs to survive interruption, context compaction, or tool-budget exhaustion.

## Hard boundaries

1. Do not commit from the live Hermes runtime checkout.
2. Do not replace a partial index with a full upstream merge merely because the merge is easier.
3. Do not run tests against the live database, medical state, session DB, or active runtime.
4. Do not push, deploy, restart, reset sessions, or delete preservation/evidence artifacts during candidate construction.
5. Treat an owner approval phrase as a scope gate, not as proof that tests or deployment succeeded.
6. If a previous candidate is amended or any candidate byte changes, all SHA-scoped evidence after that byte boundary is stale.

## Workflow

### 1. Pin and classify the source boundary

Record, with raw command output:

- destination remote target via `git ls-remote`;
- approved upstream/donor base SHA;
- live runtime HEAD and status, separately;
- candidate worktree path, branch, and current HEAD;
- whether the destination is a full source tree or a partial source index;
- exact non-goals: schema migration, DB repair, runtime config change, channel cutover, or restart.

A live dirty tree is evidence about live state only. It is not an implicit candidate source.

### 2. Build thin logical slices

For each logical fix:

1. Write the regression test or contract assertion.
2. Run it in a fresh isolated state root and capture the RED result.
3. Implement the smallest complete slice.
4. Run the same test and capture the GREEN result.
5. Run affected-file tests and compile checks.
6. Commit one logical slice locally, or preserve it as one ordered patch artifact if the destination is a partial index.

Do not bundle unrelated fixes merely to reduce commit count. A later slice must not silently change the meaning of an earlier slice.

### 3. Preserve the implementation as an ordered overlay

For each custom slice:

- generate a deterministic binary/full-index patch from the clean donor baseline;
- store it in the established upstream-overlay lane;
- compute and record its SHA-256 in the source lock;
- preserve patch order explicitly (`order=1`, `order=2`, ...);
- update the tree/coverage manifest for every controlled path;
- describe whether the artifact is `OVERLAY-REPRESENTED` or `SOURCE-MERGED`.

Do not call a patch artifact runtime behavior until it has been materialized and exercised.

### 4. Prove fresh applicability and materialization

Never use a dirty candidate tree as the only patch test. Create a fresh donor-baseline copy and run:

```bash
git apply --check <ordered-patch>
git apply <ordered-patch>
```

Then compare every intentional changed path byte-for-byte with the working candidate. `git apply --check` alone proves applicability, not equivalence.

Reconstruct from the source lock and tree manifest using the repository’s reconstruction script. Run its validation mode and record:

- exact base SHA;
- ordered patch IDs and hashes;
- file count/path count;
- tree-manifest hash;
- output directory;
- validation exit code.

Test the reconstructed tree, not only the development copy.

### 5. Verify identity projection, not just control flow

For session/listing/resume/search fixes, distinguish these identities:

- physical row/message that matched the query;
- compression-lineage identity used for deduplication;
- generic ownership/current-session fence used for visibility exclusion;
- user-visible listing/resume projection.

Do not use a generic `parent_session_id` root for every purpose. Reset/new/idle/daily/cron children may be related rows while still representing a new user-visible conversation. Regression coverage should include:

- `/sessions` versus numeric `/resume` ordered-sequence parity;
- activity ordering, not only creation-time ordering;
- current-session exclusion;
- reset/new child non-deduplication;
- physical FTS message ID and physical title preservation;
- real copied-DB anchors when available;
- each affected platform/channel through isolated fixtures.

### 6. Run gates before and after the final commit

Before commit:

- `git diff --check`;
- staged-path manifest and staged `git diff --cached --check`;
- secret scan over the intended candidate paths;
- manifest/hash validation;
- reconstruction tests;
- affected tests and compile checks.

After the final commit/amend:

1. record the new exact SHA;
2. rerun manifest validation using that SHA;
3. rerun secret scan and reconstruction validation;
4. rebuild the exact-SHA candidate output;
5. rerun affected tests on that output;
6. rerun copied-DB probes if the runtime representation changed;
7. only then start the authoritative full suite.

A previous pass on a superseded SHA is historical evidence, not final evidence.

### 7. Use the canonical full-suite runner

Read the repository wrapper before invoking it. For this Hermes runner family, the canonical full-suite pattern is:

```bash
env -u HERMES_HOME scripts/run_tests.sh -j <workers>
```

The wrapper/conftest owns the test sandbox. Do not inject an arbitrary temporary `HERMES_HOME` and call a direct pytest run as if it were equivalent to the canonical suite. Direct pytest is useful for targeted isolation, but it is a different evidence scope.

Record the full-suite process ID, command, candidate path, interpreter, worker count, and start state. Interim counters are provisional. Only the runner’s final aggregate and exit state can classify the full suite.

If the reconstructed candidate has no `.git` directory and the wrapper’s precompile phase prints a Git warning, preserve the raw warning and classify it separately from pytest results. Do not silently call the run clean or treat the warning as a test failure without the final runner verdict.

### 8. Classify failures against a clean baseline

For each final failed test node:

- rerun the node in a fresh isolated process;
- run the equivalent node against the clean donor baseline;
- compare candidate and baseline outputs;
- classify as `BASELINE`, `CANDIDATE-DEFECT`, `CONTRACT-CHANGE/STALE-TEST`, `HARNESS`, `ORDER-SENSITIVE/FLAKY`, or `UNRESOLVED`.

A baseline failure remains a failure in the unconditional full-suite result. An exclusion rerun is separate evidence and must be reported as such; it does not upgrade the full suite to PASS.

A killed, timed-out, setup-invalid, argument-invalid, or still-running suite is `INCOMPLETE`, never PASS or FAIL.

### 9. Incident-shaped copied-state probes

When a large incident DB is involved:

- use a reflink/sparse copied DB or equivalent read-only copy;
- record source backup size and SHA-256 before probes;
- use read-only SQL/DB access where possible;
- never write, migrate, rebuild FTS, or repair rows in the incident copy unless the scope explicitly allows it;
- report physical IDs, titles, and resolver outputs separately;
- do not infer live deployment from a copied-DB pass.

### 10. Disk pressure during long candidates

At 90%+ filesystem usage:

1. inventory `df` and allocated `du` sizes;
2. identify active process CWD/open-FD references;
3. classify cache, test-temp, source-overlay, baseline, and evidence groups;
4. preserve source/evidence/rollback copies;
5. ask for explicit approval per deletion batch;
6. post-verify disk and process health after approved cleanup.

An unanswered cleanup prompt is **no approval**. Do not delete caches or old overlays merely because they appear disposable.

## Completion report

Use a status table with separate rows for:

- candidate implementation;
- exact local SHA;
- reconstruction/materialization;
- targeted tests;
- copied-state probes;
- full-suite final result;
- baseline failures;
- manifest/secret gates;
- remote push state;
- deployment/live state;
- owner approval boundary;
- remaining data gaps.

Use `PROVEN`, `PARTIAL`, `INCOMPLETE`, `UNVERIFIED`, or `BLOCKED`. Never write “done,” “validated,” “full suite passed,” or “live” from an interim counter, a superseded SHA, a copied DB, or a local candidate alone.

## References

- `references/model-b-ordered-overlay-closure.md` — compact command/evidence recipe and failure-classification fields.
- `references/fast-contract-subset-runner.md` — fast session/lineage/resume contract-subset pre-gate (Phase 4.5 / `scripts/run_contract_tests.sh` pattern, work-vs-live `PYTHONPATH` and best-effort lineage handling).
- Existing verification references in `verification-before-completion` remain complementary; this skill is specific to partial-source ordered overlays.
