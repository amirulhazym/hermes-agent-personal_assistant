# Branch disposability audit — is a branch safe to delete?

Verified 2026-08-20 during the gate-2 cleanup review. Owner rule: "kalau dah
push, consider delete; kalau tak push, jangan buang" — pushed+merged = safe
delete; unmerged+unpushed = KEEP or push-to-origin first.

## Sequence (read-only; run before any `git branch -D`)

1. Merge status + unique commits:
   ```bash
   git merge-base --is-ancestor <branch> main && echo merged || echo NOT-MERGED
   git rev-list --count main..<branch>        # unique commit count
   git log --oneline --no-merges main..<branch>
   ```
2. Patch equivalence (`+` = patch unique to branch, `-` = already in main):
   ```bash
   git cherry -v main <branch>
   ```
3. Unique files — TWO-dot diff (vs branch tip, not merge-base):
   ```bash
   git diff --name-status main..<branch> | awk '{print $1}' | sort | uniq -c
   git diff --name-status main..<branch> | awk '$1=="A"{print $2}'   # files ONLY on branch
   ```
   **Zero `A` = nothing unique; the branch is an older snapshot and main has evolved.**
4. Key-fix carry check — a fix commit may be in main under a different patch-id
   (cherry says `+` but content identical):
   ```bash
   git show --stat <fix-sha> | head -15       # what the fix touched
   git show main:<file> | sha256sum ; git show <branch>:<file> | sha256sum
   ```
   Identical hash = fix already in main. Also verify config/manifest evidence,
   e.g. `git show main:docs/reconciliation/hermes-runtime-source-lock.json`
   already carrying `runtime_destination_root`.
5. Live tri-state — what is actually deployed, and is the branch the ONLY source:
   ```bash
   sha256sum <live-file>                      # vs git show main:<f> vs git show <branch>:<f>
   ```
   Live == main → branch work not deployed. Live == branch → branch is the only
   source of a deployed fix → KEEP/push. Live == neither → uncommitted live drift
   (separate reconciliation item, not a deletion decision).
6. Worktree check: `git worktree list` — a checked-out branch refuses `-D`.

## Verdicts

| Evidence | Verdict |
|---|---|
| merged + pushed (origin ref exists) | DELETE safe |
| 0 unique files + key fixes hash-identical in main | SUPERSEDED → DELETE safe |
| unique unpushed commits touching live-relevant code | KEEP → recommend `git push -u origin <branch>` then optional local delete |
| branch checked out in worktree | `git worktree remove` first (never `-D` while checked out) |

After deletions: `git gc --prune=now` (plain; `--aggressive` = marginal gain,
heavy CPU). gc prunes commits reachable only from deleted branches — verify each
branch's commits are truly disposable first.

## Worked example (gate-2 cleanup, 2026-08-20)

- `feat/med-hook-envelope-time-parse` @0f079c3ba — 3 commits, all `+` in
  `git cherry`, no origin ref. 5 files, 362 insertions (med hook handler,
  med_safety_gate.py, tests). Live `med_safety_gate.py` == MAIN (not branch);
  live `handler.py` == neither (uncommitted drift, 13 Aug). Verdict: **KEEP →
  push to origin for preservation.** Never blanket-delete.
- `v3-source-closure-candidate-20260808` @9c95990a8 — 4 commits `+` BUT two-dot
  diff = 0 `A` files, 24 M / 45 D, branch lacks 59,951 lines vs main; fix files
  (`scripts/whatsapp-bridge/reconnect-controller.js`, `tests/gateway/test_status_canonical_display.py`)
  hash-identical in main; main source-lock already carries
  `runtime_destination_root`. Verdict: **SUPERSEDED → safe delete** (after
  `git worktree remove /tmp/hermes-v3-source-closure-candidate`).

## Combined branch+/tmp cleanup ordering

1. `git worktree remove <path>` + `git worktree prune` (parent repo).
2. `git branch -D <superseded>` (never `-f` on unmerged without owner approval).
3. `git gc --prune=now`.
4. Only then the /tmp sweep — otherwise `rm -rf` hits a live worktree dir.
