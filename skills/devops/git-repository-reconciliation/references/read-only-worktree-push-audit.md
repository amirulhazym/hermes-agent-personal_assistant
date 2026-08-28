# Read-only worktree / push-status audit

Use this reference when the owner asks whether work remains uncommitted or unpushed. It is a Git-state audit, not a release or cleanup procedure.

## Boundary

Unless explicitly approved otherwise, allow only read operations:

- `git status`, `git diff`, `git log`, `git rev-list`, `git merge-base`, `git show-ref`, `git branch`, `git worktree`, `git stash`, `git fsck`;
- `git ls-remote --heads <remote>` for current remote heads.

Do **not** run `fetch`, `add`, `commit`, `push`, `stash`, `reset`, `checkout`, `switch`, `merge`, `rebase`, branch/ref creation, clean, prune, or config writes during this audit.

## 1. Scope every Git surface

For each candidate repository:

```bash
git rev-parse --show-toplevel
git rev-parse --git-dir
git rev-parse --git-common-dir
git worktree list --porcelain
git remote -v
git status --porcelain=v2 --branch --untracked-files=all
```

Then inspect **every existing path** returned by `git worktree list --porcelain`, not only the repository root:

```bash
git -C <worktree> status --porcelain=v2 --branch --untracked-files=all
git -C <worktree> diff --name-status --no-renames
git -C <worktree> diff --cached --name-status --no-renames
git -C <worktree> diff --stat --no-renames
git -C <worktree> diff --cached --stat --no-renames
```

A linked worktree can be dirty while the root worktree is clean. Record its path, branch, HEAD, staged paths, tracked-modified paths, conflicted paths, and non-ignored untracked paths independently.

## 2. Inspect stashes as a separate layer

```bash
git stash list
git stash show --name-status --stat 'stash@{0}'
```

A stash is preserved WIP, not a branch commit and not a pushed artifact. Do not report a repository as clean if a relevant stash exists; label the stash separately.

## 3. Pin direct remote heads without mutating local refs

For every configured remote:

```bash
git ls-remote --heads origin
git ls-remote --heads origin-vps
```

Record the exact timestamp and SHA for every relevant direct head. Compare these values with, but do not replace, local tracking refs:

```bash
git for-each-ref --format='%(refname:short)\t%(objectname)\t%(upstream:short)\t%(upstream:trackshort)' refs/heads
git for-each-ref --format='%(refname:short)\t%(objectname)' refs/remotes
```

`origin/main` is a local ref, not proof of the current remote. If repeated `ls-remote` calls return different SHAs, retain the observations, pin the final query, and say the remote moved during the audit. If a direct remote SHA is not present locally, exact ancestry against that SHA cannot be proven without a mutating fetch; report `PARTIAL`/`UNVERIFIED` rather than guessing.

## 4. Prove local-only commits

For each local branch, record:

- branch name and full tip SHA;
- upstream and tracking state;
- same-name direct remote branch, if any;
- whether the tip is an ancestor of a current direct remote head;
- local-only commit list where the graph is available.

Safe command shape:

```bash
git log <branch> --not --remotes --format='%H%x09%ad%x09%s' --date=iso-strict
git rev-list --left-right --count <remote-ref>...<local-branch>
git merge-base <local-branch> <remote-ref>
git merge-base --is-ancestor <local-tip> <remote-tip>
```

In a programmatic probe, pass these as separate argv elements. Do not construct one argument such as `"<branch> --not --remotes"`; Git treats it as one revision and the failure says nothing about repository state. Preserve the failed probe as a tool error, correct only the argv construction, and rerun.

A local branch with no upstream is not automatically unpublished: its commit may be reachable from a differently named remote branch. Conversely, a branch whose tip is pushed can still have an uncommitted overlay in one or more worktrees.

## 5. Classification ledger

| Evidence | Classification |
|---|---|
| `1`/`2` porcelain entry with unstaged or staged XY bits | `UNCOMMITTED — tracked modification` |
| `u` porcelain entry | `UNCOMMITTED — conflict` |
| `?` porcelain entry | `UNCOMMITTED — non-ignored untracked` |
| `!` ignored entry | `IGNORED — not classified for publication` |
| Local branch commits not reachable from any checked current remote head | `COMMITTED-LOCAL-ONLY` |
| Branch tip remote-reachable, but any worktree on it is dirty | `PUSHED-BUT-DIRTY-OVERLAY` |
| No local-only commits; local branch behind remote | `CLEAN-BEHIND` |
| Stash exists | `PRESERVED-WIP — not committed/pushed` |
| Remote head object unavailable locally | `REMOTE-GRAPH-DATA-GAP` |

Never collapse these into one binary `clean`/`dirty` value.

## 6. Exact reporting shape

Start with the audit timestamp and read-only boundary. Then report:

1. repositories and registered worktrees checked;
2. uncommitted counts and exact path sets per dirty worktree;
3. committed-local-only branch tips and recent subjects;
4. stash entries and file counts;
5. direct remote heads and local-tracking discrepancies;
6. pushed-but-dirty overlays;
7. ignored/private paths requiring separate classification;
8. contradictions, moving targets, missing objects, or failed probes;
9. explicit statement that no Git mutation occurred.

Use evidence labels:

- `DIRECTLY VERIFIED` — returned by the current command;
- `PARTIAL` — one graph layer is unavailable or the remote moved;
- `UNVERIFIED` — plausible but not proven by current output;
- `DATA GAP` — exact missing evidence and why it could not be obtained.

## Common failure modes

- Checking only the repository root and missing dirty linked worktrees.
- Calling a branch pushed because its tip SHA matches a remote while ignoring dirty files on that commit.
- Calling a local branch unpublished solely because it has no upstream, without checking alternate remote refs.
- Treating `origin/main` as current after the remote has advanced.
- Fetching during a read-only audit and then presenting the mutated local tracking ref as historical evidence.
- Treating ignored runtime/private files as safe source candidates.
- Counting `?` untracked rows together with `!` ignored rows.
- Reporting a malformed scripted Git command as evidence of repository state.
- Treating a stash as either a clean tree or a committed backup.
