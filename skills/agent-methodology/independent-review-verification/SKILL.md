---
name: independent-review-verification
description: Use when reviewer flags candidate; reproduce it first.
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
tags: [review, debugging, candidates, provenance, tdd, verification]
metadata:
  hermes:
    tags: [review, debugging, candidates, provenance, tdd, verification]
    related_skills: [diagnosing-bugs, requesting-code-review, verification-before-completion]
---

# Independent Review Verification

## Purpose

Use this as the bridge between an adversarial reviewer result and a candidate
change. A reviewer report is a claim inventory, not proof. Reproduce each
material security, logic, scope, or provenance finding against the exact
candidate bytes before accepting it, dismissing it, or changing code.

This skill is especially important for wrappers, middleware, retries, fallbacks,
state transitions, and source candidates represented by ordered patch artifacts.
A happy-path test and a passing reviewer do not prove failure-path safety.

## When to Use

- A fresh reviewer reports a security, logic, scope, or provenance blocker.
- A wrapper, middleware, retry, or fallback may duplicate or bypass work.
- A candidate uses ordered patches and the reviewer’s claim must be tested against materialized bytes.
- A prior review PASS is being reused after candidate bytes changed.

## Non-negotiable boundaries

- Candidate, live-on-disk, active-process, pushed, deployed, and user-visible
  states are separate.
- Reviewer output is evidence to investigate, not an authority to rubber-stamp. External reviewers frequently over-assume, exhibit unverified confidence, or speculate without live data. Never accept an assertion without checking raw filesystem/git ground truth.
- Run probes against a fresh materialized candidate, never against production
  state or an unpatched working copy.
- Use temporary `HOME`/`HERMES_HOME` for imports that can read config, state,
  plugins, caches, or credentials. Never use production databases or medical
  state as fixtures.
- Do not let a reviewer or probe mutate the candidate, live source, config,
  persistent state, remote refs, or process state.

## Procedure

### 1. Freeze the boundary

Record:

- candidate worktree, branch, and exact HEAD;
- staged path set and working-tree status;
- donor/base SHA and overlay order;
- exact reviewer claim and the contract it is said to violate;
- permitted side effects (normally temporary files only).

Re-check the candidate after review. A “read-only” reviewer self-report is not
proof that the repository stayed unchanged.

### 2. Materialize the candidate

If the candidate uses patches, locks, manifests, or sanitized source:

1. create a fresh temporary tree from the pinned base;
2. apply the complete ordered patch series;
3. validate path, mode, per-file hash, series digest, and tree digest;
4. run the probe with isolated state paths;
5. keep the raw command and exit result.

A clean patch application proves structure only. It does not prove the changed
behavior is present, correct, or safe.

### 3. Reproduce the exact failure path

For broad wrapper/fallback code, split the probe into two independent cases:

1. **Provider/downstream failure:** middleware invokes the provider callback and
   the provider raises. Assert one physical provider invocation and propagation
   of the original error.
2. **Middleware failure:** middleware raises before invoking the provider. Assert
   zero provider invocations and propagation of the middleware error.

These cases detect the two common defects separately: duplicate billable or
non-idempotent requests, and policy/routing bypass through a raw fallback.

For state transitions, use a minimal object or fixture that starts at the
reported bad state and assert the exact state change. For parsers/resolvers,
assert both the positive result and the fail-closed negative case.

### 4. Use TDD for the correction

Before changing production logic:

1. add the smallest regression test at the real call seam;
2. run it and preserve the expected RED output;
3. make one minimal correction;
4. rerun the same test GREEN;
5. rerun the original un-minimized reproduction;
6. run affected and contract suites separately.

Do not “fix” a provider wrapper by catching a broader exception. Runtime
middleware exceptions must not silently become raw-provider fallback. If a
compatibility fallback is genuinely required, narrow it to the specific import
or availability failure and give it its own regression test.

### 5. Preserve source provenance

When the defective behavior came from a live-only commit:

- preserve the exact intentional live change as its own overlay when lineage
  matters;
- add a separate corrective overlay rather than silently rewriting history;
- state which behavior is live provenance and which is candidate hardening;
- recompute patch hashes, lock digest, manifest rows, and tree digest after every
  byte change;
- rerun materialization from the complete ordered series.

Selective source closure does not imply whole-file equality with live when
unrelated upstream history is intentionally excluded. Prove the affected
behavior, not an invalid whole-file parity condition.

### Validator-boundary matching

A repository may have multiple manifests with different schemas. Before running a
post-commit validator, inspect its accepted fields and match it to the intended
artifact. For example, a runtime reconstruction manifest (`base_sha`,
`patch_series_digest`, tree entries) is not the same object as a source-coverage
manifest (`candidate_sha`, `kind`, `source_sha256`, `destination`).

If the wrong manifest is supplied, classify the result as **VALIDATOR MISUSE**,
preserve the failed command, and rerun the correct validator against the exact
candidate SHA. Do not call the candidate invalid—or the gate passed—based on a
schema mismatch from the wrong validator input.

### 6. Fresh review and final gates

After correction, obtain a fresh review of the corrected staged bytes. A prior
review result is stale after any candidate byte change. Then run:

- patch applicability/materialization;
- affected failure-path tests and relevant contract tests;
- compile/import checks;
- secret scan and separate PII review;
- full staged whitespace check;
- exact lock/manifest/hash validation;
- candidate/live status re-check.

Classify the final state explicitly as `PROVEN`, `PARTIAL`, `BLOCKED`, or
`UNVERIFIED`. A candidate PASS never means pushed, merged, deployed, reloaded,
or live.

## Reporting shape

Use this compact order for the owner:

1. **Finding:** what the reviewer claimed.
2. **Reproduction:** exact isolated output and exit status.
3. **Verdict:** confirmed, contradicted, or unresolved.
4. **Correction:** files/overlay changed and why.
5. **Fresh verification:** raw test/scan/hash result.
6. **Boundary:** what remains candidate-only or unproven.

Never replace a failed gate with a reassuring summary. Never invent an ETA for a
background reviewer; report the live status and elapsed time separately.

## Reference

For reusable failure-path probe templates, patch-format handling, and a worked
wrapper/fallback matrix, see `references/reviewer-finding-reproduction.md`.
