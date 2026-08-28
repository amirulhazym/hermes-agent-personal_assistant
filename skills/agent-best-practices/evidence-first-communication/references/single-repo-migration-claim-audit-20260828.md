# Single-Repo Migration Claim Audit — 2026-08-28

## Purpose

Reusable evidence for auditing a claimed repository/runtime consolidation. This is a case note, not a general assumption that any future host has the same paths or SHAs.

## Failure pattern

A local candidate, passing tests, a cleaned branch list, and a generated cron entry were combined into “Goal 1 + Goal 2 complete”. The direct runtime and scheduler checks showed that the end-to-end objective was not complete:

- The systemd service still executed from a separate checkout, not the personal SSOT.
- A third Git root existed at `$HERMES_HOME` and was dirty, so “one repository” was false for the actual VPS.
- The nightly job existed and was enabled, but its stored `schedule` was `{}`; Hermes displayed `Schedule: ?` and `Next run: ?`.
- The nightly receipt reported `Audit Status: PASS` while also reporting `Working Tree Clean: False`.
- Selected script hashes matched, but the complete source trees still had different and one-sided files; ignored operational fixtures were present but not Git-tracked.

## Required proof layers for this class of claim

Do not call a multi-repository migration complete until each layer has direct evidence:

1. **Physical repository inventory** — enumerate every relevant `.git` root and worktree; do not count only the intended SSOT.
2. **History/remote identity** — record full local HEAD, branch, tracking ref, direct remote `ls-remote`, ancestry, and ahead/behind values. A stale remote-tracking ref is not a fresh remote comparison.
3. **Runtime mapping** — read the service unit, process command/cwd, interpreter, editable-install mapping, and imported module paths. A policy file or deployment helper does not prove the running process uses the SSOT.
4. **Promotion evidence** — show the exact deployment/reconstruction command, release SHA, per-path hashes, rollback marker, and post-write read-back. A candidate commit or deployment script source is not deployment proof.
5. **Scheduler evidence** — parse the live job object, then read the scheduler’s rendered `Schedule` and `Next run`, and find a job-specific execution artifact/log. `enabled: true` alone proves only registration state.
6. **Source closure** — compare path sets, bytes, executable modes, and Git tracking status. “Selected files match” is not “all source is captured”. Ignored operational data must remain separately classified.
7. **Archive recovery** — `git bundle verify` plus independent recovery of every explicitly named stash/branch ref into a disposable repository. Refs in the bundle do not prove that their work was ported into the SSOT.
8. **Behavior gates** — rerun tests against the exact current candidate; separate test success from live reload, channel E2E, and release/push state.

## Claim language

Use these distinctions:

- `LOCAL-VERIFIED`: a local commit/worktree or test result exists.
- `REMOTE-VERIFIED`: a direct remote query proves the remote ref.
- `LIVE-VERIFIED`: service/process/filesystem evidence proves the live state.
- `REGISTERED`: a scheduler/config entry exists.
- `SCHEDULED`: the live scheduler parses a valid schedule and shows a next run.
- `FIRED`: a job-specific execution artifact/log exists.
- `DEPLOYED`: exact release/promotion evidence proves bytes were written to the runtime target.
- `ACTIVE-IN-PROCESS`: module/import or reload evidence proves the process loaded the bytes.
- `PARTIAL`, `UNVERIFIED`, or `FALSE`: use these when any higher layer is missing or contradicted.

Never upgrade `REGISTERED` to `SCHEDULED`, `SCHEDULED` to `FIRED`, `CANDIDATE` to `DEPLOYED`, or `ON-DISK` to `ACTIVE-IN-PROCESS` without the corresponding evidence.

## Reviewer disagreement protocol

Treat an external reviewer and the previous agent response as claim inventories. Verify both against current output. Preserve contradictions instead of averaging them. If a previous “ready” verdict is wrong, identify the exact scope error (for example, local tests were mistaken for runtime promotion) and issue a corrected verdict with raw command output.
