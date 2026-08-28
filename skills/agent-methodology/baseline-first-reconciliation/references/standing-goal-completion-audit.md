# Standing-Goal Completion Audit

Use this reference when a prior agent or automation reported a multi-step goal as complete and the owner asks for a real verification.

## Audit contract

**Goal:** <exact user acceptance text>
**Snapshot:** <date/time/timezone>
**Allowed operations:** read-only inspection and isolated tests; list prohibited mutations.
**Verdict vocabulary:** `COMPLETE`, `CONFIRMED NOT COMPLETE`, `PARTIAL`, `UNVERIFIED`, `BLOCKED`.

A negative verdict is still a successful audit when a required gate has direct failure evidence. Do not use `UNVERIFIED` to avoid saying that the goal failed.

## Evidence matrix

| Criterion | Required proof | Actual evidence | Verdict |
|---|---|---|---|
| User acceptance item | Exact artifact/behavior named by the goal | command, raw output, path, URL | PROVEN/FAIL/... |
| Source identity | path, branch, full SHA, cleanliness | `git status`, `git rev-parse` | ... |
| Remote publication | remote ref and target SHA | `git ls-remote`, remote API | ... |
| Merge/release state | PR/merge/base ancestry | remote PR query, compare | ... |
| Behavior | actual command/test against correct fixture | exit code + final assertion | ... |
| Runtime | process/service loaded current source | PID/start time/log/endpoint | ... |
| User-visible result | destination-side response/receipt | platform/API evidence | ... |

The parent is complete only if every required row is `PROVEN`.

## Repository reconciliation recipe

Run read-only checks against each relevant repository and save raw output:

```bash
git -C <repo> status --short --branch
git -C <repo> rev-parse HEAD
git -C <repo> rev-parse <tracking-ref>
git -C <repo> rev-list --left-right --count HEAD...<tracking-ref>
git -C <repo> diff --name-status <base>...HEAD
git ls-remote <remote> refs/heads/<target>
```

For a claimed path set, create an exact manifest and compute:

- requested path count;
- destination-ref path presence;
- destination blob/file hash;
- whether the destination is the required `main`/release ref;
- whether the remote ref is reachable and merged.

Never count a differently scoped diff as equivalent merely because its file count matches. A local branch, successful CI run, or “up to date” CLI label is not a pushed merge.

## Goal-state reconciliation

Inspect the goal store and source implementation separately. Record:

- all goal keys for the session and continuation lineage;
- `status`, `last_verdict`, `last_reason`, counters, contract, gates, and subgoals;
- parent/child session IDs and current routing ID;
- source behavior of `mark_done`, `clear`, and migration methods.

Treat DB status and free-text reasons as metadata. Empty contracts/gates mean there is no machine-readable acceptance gate to rely on. A `done` row cannot override a failed Git/test/runtime criterion. Do not write the DB merely to make status match a narrative.

## Test evidence

Run the authoritative suite on the exact candidate/ref and preserve the final output and exit code. Report targeted suites separately from full-suite status. If one required test fails, the parent is not green even if all other suites pass.

For dynamic/config-driven behavior, run a minimal isolated probe that prints both the canonical source value and the consumer output. This catches static fallback bugs where the resolver returns an inactive/zero value but a consumer keeps an old hardcoded/default value. If the test fixture encodes an older contract, report both facts: `STALE-TEST` and the independently observed consumer behavior; do not silently call either one a pass.

## Runtime and moving-target checks

A clean worktree proves cleanliness only. Query the remote immediately before a currentness claim; compare local ancestry in both directions. Capture service state and PID separately from source state. A process being active proves availability, not that every candidate gate passed.

If a tool says “up to date” while `git rev-list` says the local branch is behind/diverged, report the contradiction and use the direct Git comparison for the source-alignment verdict.

## Final report shape

1. Lead with `COMPLETE` or `CONFIRMED NOT COMPLETE`.
2. Restate the exact goal acceptance items in compact form.
3. Show a criterion-by-criterion matrix with raw evidence references.
4. Separate proven positives from failures and undecided gaps.
5. Explain any metadata/narrative contradiction.
6. State exact paths for raw evidence and explicitly state what was not changed.

Do not ask the owner to choose a remediation path until the audit itself is complete.