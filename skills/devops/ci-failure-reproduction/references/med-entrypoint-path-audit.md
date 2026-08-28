# Read-Only Med Entrypoint Path Audit

Use when investigating whether a medication system is running from a stale,
deleted, or degraded source path after Git/worktree cleanup.

## Evidence order

1. Inspect user crontab and `systemctl --user list-timers --all`.
2. Inspect Hermes cron registry for enabled med jobs, including exact script
   names, schedules, delivery targets, and last status.
3. Resolve the gateway's actual `HOOKS_DIR` and service `WorkingDirectory` from
   the live source/service; do not infer from the application repository.
4. Search active config, hooks, cron, scripts, and service definitions for the
   deleted/worktree paths. Historical docs and session dumps are not active
   references.
5. Inspect fallback imports in the live entry scripts. Distinguish fail-open
   consistency checks from fail-closed medication safety gates; a fallback in
   source is not proof that it executed.
6. Search the requested log window for import errors, tracebacks, fallback
   markers, and structured safety holds.
7. Build a direct hash matrix for live files, public `main`, feature branch,
   and the requested historical commit. Report hashes as evidence, then classify
   equality/difference.

## Required distinctions

- Active entry point vs historical reference.
- Live runtime path vs source worktree path.
- Fallback code exists vs fallback executed.
- Safety HOLD with `state_mutated=false` vs degraded resolver/import failure.
- Feature branch source drift vs live runtime drift.

## Output contract

Report exact commands/paths and use these labels:

- `LIVE-VERIFIED`: direct filesystem, service, cron, or log evidence.
- `SOURCE-VERIFIED`: direct Git object/hash evidence.
- `NOT-FOUND`: no matching active reference in the inspected scope.
- `UNPROVEN`: a fallback exists or a hypothesis is plausible, but execution was
  not evidenced.

Stop after the matrix and verdict. Do not create a commit, refresh a manifest,
push, restart, or mutate medication state during this audit.
