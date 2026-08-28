# Dirty live update versus clean candidate

Use this reference before an agent-driven update or release candidate rebuild.

## Decision gate

Classify the live checkout before running an updater:

```text
NORMAL UPDATE:
  clean tree
  expected branch/lineage
  target is fast-forwardable
  sufficient backup and rollback disk space

CANDIDATE REQUIRED:
  modified or untracked source-like files
  local history diverged or unrelated to target
  custom behavior not mapped to source
  rollback/source preservation is uncertain
  disk headroom is too low for a safe backup/update/test cycle
```

## What the updater can and cannot prove

A standard updater may:

1. back up runtime state;
2. stash tracked and untracked working-tree files;
3. fetch and fast-forward the target;
4. reapply the stash;
5. reinstall dependencies and restart.

That proves only that the updater completed its mechanics. It does **not** prove:

- all custom source bytes were captured;
- the target history was compatible;
- stash application was conflict-free;
- the resulting custom behavior still works;
- ignored/private runtime state was preserved;
- the live process loaded the intended version.

If fast-forward fails and the updater has a reset-to-remote fallback, treat that as a material risk on a dirty/diverged checkout. A stash or backup may still preserve bytes, but the live tree can be left on upstream code, with custom behavior requiring manual recovery. Record this as `SOURCE-RESTORE-UNPROVEN`, not as data loss unless hashes prove loss.

## Minimal candidate route

For `CANDIDATE REQUIRED`:

1. Record live HEAD, branch, remote target, status, ignored source-like paths, and disk authority.
2. Preserve the exact live overlay with path-level hashes, modes/symlinks, and a restore test.
3. Build a clean candidate from the pinned upstream target; do not construct from the dirty live checkout.
4. Port only intentional changes; keep unrelated history separate.
5. Run affected tests, then the canonical authoritative full suite in isolated state.
6. Report candidate SHA and full-suite evidence separately from live status.
7. Stop at the approval boundary. Live swap, restart, and channel changes are separate actions.

## Scope stop rule

This is a safety gate, not permission to launch an indefinite audit. Once the exact candidate passes the authoritative gate, do not reopen topology, repeat broad census work, or add architecture tasks. State the remaining approval and the explicit non-goals.

## Evidence labels

- `NORMAL-UPDATE-ELIGIBLE`: clean, compatible, rollback-ready.
- `CANDIDATE-REQUIRED`: direct evidence shows the updater cannot be treated as a safe blind operation.
- `UPDATER-MECHANICS-PASSED`: backup/fetch/stash/pull steps completed.
- `SOURCE-RESTORE-UNPROVEN`: custom bytes or behavior were not independently compared after restore.
- `CANDIDATE-FULL-SUITE-PASSED`: canonical runner passed for the exact candidate SHA.
- `LIVE-SWAP-PENDING`: candidate is not yet deployed; do not call it live.
