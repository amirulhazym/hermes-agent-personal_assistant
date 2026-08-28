# Snapshot Boundary and Overlay Comparison

Use this procedure when a reviewer compares a live repository, historical backup, candidate worktree, or temporary test overlay.

## 1. Pin the evidence boundary

Record, for every tree:

- timestamp and hostname/context;
- absolute path;
- `HEAD`, branch, and remote-tracking refs;
- exact status command and mode;
- `.git` marker type, git-dir, common-dir, and registered worktrees.

A statement such as “44 records” is meaningful only with the command and timestamp that produced it.

## 2. Identify clone versus linked worktree

A linked worktree normally has a regular-file `.git` marker and a git-dir under another repository's `.git/worktrees/` directory. Verify rather than infer:

```bash
stat -c 'type=%F mode=%a size=%s path=%n' "$TREE/.git"
git -C "$TREE" rev-parse --show-toplevel
git -C "$TREE" rev-parse --git-dir
git -C "$TREE" rev-parse --git-common-dir
git -C "$TREE" worktree list --porcelain
```

A clean status does not mean the tree is disposable: it can have unique refs, objects, ignored files, worktree registrations, or sole test evidence.

## 3. Compare sets before comparing counts

Keep these sets separate:

- tracked modified/staged records;
- untracked records (`?` in porcelain output);
- ignored records (`!` in porcelain output);
- historical/current path sets.

Compute and report `CURRENT-ONLY`, `BASELINE-ONLY`, and `COMMON`. Do not infer an exact delta from `30` versus `33`.

When parsing porcelain output, do not include `?` rows in the ignored set. A previous overlay comparison accidentally did this and produced inflated ignored counts; rerun with separate predicates and report the corrected values.

## 4. Path equality is not content equality

For common untracked files, hash both copies. Also hash binary tracked diffs and sorted path manifests:

```bash
git -C "$TREE" diff --binary | sha256sum
git -C "$TREE" diff --cached --binary | sha256sum
git -C "$TREE" status --porcelain=v2 --untracked-files=all
```

If the path sets differ by one file but common-file hashes differ, the trees are not equivalent. Report both facts explicitly. Governance ledgers, manifests, and progress files are source/evidence, not automatically disposable test output.

## 5. Bundle and recovery evidence levels

Use separate labels:

- `PRESENT`: artifact exists and metadata can be read;
- `VERIFY-PROVEN`: correctly-scoped integrity verification succeeded;
- `HISTORICAL-CLONE-PROVEN`: a prior raw tool result shows clone/checkout success;
- `FRESH-CLONE-NOT-PERFORMED`: no current restore exercise was run;
- `DIRTY-RESTORE-UNPROVEN`: encrypted patch/untracked archive has not been decrypted/listed/restored.

A historical clone/checkout result must not be silently downgraded to an unsupported claim, but it also must not be presented as a fresh current test. An encrypted archive's existence proves neither file membership nor byte-exact restoration without independent plaintext evidence.

## 6. Disk accounting

Report both `du --apparent-size --bytes` and allocated `du --bytes` (or an equivalent allocation measurement). Timestamp the `df -B1` snapshot. Calculate any projection from the same snapshot and state whether the percentage is an exact ratio or the filesystem's displayed/rounded `Use%`. Never treat theoretical reclaim as actual reclaim until post-action `df` is observed.

## 7. Deletion gate for temporary overlays

Before proposing deletion, read-only check:

- active process cwd and open file descriptors under the tree;
- unique refs and object statistics;
- registered worktrees/common git directory;
- ignored content and source-like ignored paths;
- unique logs, reports, manifests, and test evidence;
- exact apparent and allocated size.

Separate cleanup approvals by exact path set. “Clean baseline” is evidence for lower risk, not authorization.

## Evidence wording

Prefer:

> Path-set equality is proven; byte equality is unproven.

> Historical clone/checkout is proven from retained raw execution output; fresh restore was not performed.

> Projected reclaim is calculated from allocated bytes; actual disk relief remains unverified until deletion and a new `df` snapshot.

> Ignored-record count is proven, but source-worthiness classification remains open.
