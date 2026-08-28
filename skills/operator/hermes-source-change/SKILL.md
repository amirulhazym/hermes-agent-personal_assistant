---
name: hermes-source-change
description: Isolated source-change workflow for the Hermes application repository, including bounded capture of a live-first fix.
---

# Hermes Source Change

`AGENTS.md` is normative. Every promotion to public `main`, including docs,
governance and tests, is protected by one exact-SHA owner release approval.
There is no docs-only bypass and no approval-per-command loop.

## 1. Establish the base

1. Verify remote `main` with `git ls-remote`.
2. Require the approved expected base SHA; stop on mismatch.
3. Use a clean local application worktree/branch from that SHA.
4. Never commit from `/home/ubuntu/.hermes` or its nested upstream Git lineage.

Temporary worktrees/branches are local by default. A remote temporary branch is
optional and needs a concrete preservation/review reason.

## 2. Planned and live-first work

Default flow: clean source → targeted tests → scans/validators → exact
candidate SHA → owner release approval.

For an urgent live-first fix that the active task genuinely requires:

1. Preserve readable pre-change state and a bounded diff.
2. Make only the bounded live fix.
3. Port the exact intentional change into clean application source.
4. Sanitize private values while preserving reconstructable behavior.
5. Test the source candidate and close the capture in the same work item.

Dormant/unloaded/privacy-adjacent custom source is not silently excluded.

## 2A. Fail-safe update guard and current-overlay capture

Before allowing a live updater to mutate a checkout, run a read-only preflight
before backup, stash, checkout, pull or dependency work. Refuse dirty state,
local commits ahead of the target remote, unrelated history, missing merge-base,
comparison errors and malformed history counts. Never convert a failed
`git pull --ff-only` into `git reset --hard origin/<branch>`.

For a dirty live checkout, preserve a bounded exact candidate separately:
tracked changes via `git diff --binary --full-index HEAD --`, all untracked
files in a non-dereferencing archive, and a manifest containing exact base
`HEAD`, status, hashes, modes, file types and symlink targets. Restore into a
fresh directory from the exact base SHA, apply/extract, explicitly reapply
manifest modes when host umask changes them, and compare every manifest field.
A clean patch application is structural evidence only; do not call it
byte-exact restore proof. Keep updater-candidate, overlay-restore, off-device
transfer, live update and channel smoke tests as separate gates. See the
systematic-debugging reference `references/fail-safe-update-overlay-preservation.md`.

## 3. Required gates

- secret scan fails on scanner error, missing base, malformed input or a hit;
- secret-hit output contains path/rule/category only, never matching bytes;
- PII review is separate from token scanning;
- manifest parser validates every declared row and rejects malformed, duplicate,
  unknown, missing, hash-invalid or unsafe-destination rows;
- tests run in isolated state, never against production DB/medical/session data.

## 4. Finish the candidate

Commit locally only after tests and evidence are collected. Return exact base
SHA, candidate SHA, changed-path list/count, disposition ledger, test outputs,
scan/manifest results, and live/remote no-mutation proof. Then stop and ask
once: `APPROVE RELEASE <full-sha>`.

Do not push, promote, deploy, restart, reset sessions or delete preservation
artifacts during candidate construction.
