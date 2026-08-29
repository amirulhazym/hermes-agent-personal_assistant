# Nightly Git Closure Contract

**Scope:** This is a bounded correction of the existing 23:55 MYT Git flow. It
keeps the current SSOT, manifest/deployment lane, no-agent scheduler, raw
receipt paths, and `PASS`/`HOLD`/`FAIL` vocabulary. It does not create a second
Git repository or change the framework architecture.

## Purpose

The nightly flow is an audit followed by same-night closure of *resolvable*
Git work discovered in that day's SSOT state. It must not repeatedly report a
local-ahead branch, safe merged branch, or deterministic conflict-free sync as
if the issue can wait forever.

## Two outputs

1. **Machine record:** the complete JSON receipt remains at
   `/home/ubuntu/.hermes/logs/git-nightly-receipt.json`. A per-run copy is kept
   under `~/.hermes/logs/git-nightly-history/`. JSON display is independent:
   `cron.nightly_json_display: show|hide` controls Telegram/stdout rendering;
   `hide` never suppresses receipt creation.
2. **Owner report:** the normal output is a concise human report describing the
   state found, healthy gates, proposed action, reason, deadline, confirmation
   command, final result, and unresolved blockers. It follows the installed
   `/non-tech` contract: goal first, plain mechanics, and no rounding of partial
   state to success.

## State machine

```text
23:55 audit
  ├─ no issue + gates PASS → PASS, no Git mutation
  ├─ safe plan exists → HOLD + pending JSON + 30-minute native one-shot cron job
  │    ├─ `/nightly approve RUN_ID` → execute immediately
  │    ├─ `/nightly reject RUN_ID REASON` → retain state, no execution
  │    └─ no response at deadline → execute the stored plan automatically
  └─ failed gate / hard stop → FAIL or HOLD, no automatic Git mutation
```

The exact baseline HEAD, working-tree status, remote HEAD, action list, and
deadline are persisted before execution. A later approval/timeout rechecks
those preconditions; changed state invalidates the plan rather than being
silently absorbed.

## Automatically admissible actions

Only the stored, revalidated plan may perform:

- normal non-force `git push origin main`;
- a fast-forward-only local sync from `origin/main`;
- a conflict-free `origin/main` merge followed by a normal push;
- commit of explicitly listed safe tracked source paths after all gates pass;
- deletion of a merged local branch that is not checked out or attached to a
  worktree.

The timeout policy is owner-authorized for this nightly flow only. It does not
permit force-push, protection bypass, deletion of unique unmerged work,
private/secret/PII commits, guessed conflict resolution, failed-gate bypass, or
unrelated architecture/configuration changes.

## Hard stops

The flow retains unique unmerged branches, ambiguous/untracked/private work,
substantive merge conflicts, changed plan preconditions, missing Git identity,
remote movement after recommendation, security/PII failures, test failures,
and scheduler persistence failures. These produce `HOLD` or `FAIL` with the
reason; they do not become a false `PASS`.

## Activation boundary

The target and timeout wrapper are no-agent runtime artifacts and run per tick.
The `/nightly` control is a user plugin under
`~/.hermes/plugins/nightly-git-closure/`; it must be enabled in the active
profile and discovered by the gateway. Plugin discovery/restart is a separate
operational boundary and is not implied by a candidate commit or on-disk copy.
