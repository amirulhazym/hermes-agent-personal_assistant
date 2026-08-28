# Read-Only Git Forensics Command Book

Reusable probes for multi-repository reconciliation. Run commands per repository and preserve raw output. These commands are discovery-only unless a section explicitly says it creates temporary files.

## 1. Repository / Clone / Worktree Identity

```bash
repo=/absolute/path

git -C "$repo" rev-parse \
  --show-toplevel \
  --git-dir \
  --git-common-dir

git -C "$repo" rev-parse --show-superproject-working-tree 2>/dev/null || true

test -d "$repo/.git" && echo '.git=directory'
test -f "$repo/.git" && echo '.git=file'

git -C "$repo" branch --show-current
git -C "$repo" rev-parse HEAD
git -C "$repo" worktree list --porcelain
```

Interpretation:

- `.git` directory + git-dir equals common-dir: normal clone/repository.
- `.git` file or separate git-dir with shared common-dir: linked worktree.
- A submodule/superproject relationship is separate from worktree identity; check `--show-superproject-working-tree`.

## 2. Refs and Remote State Without Fetch

```bash
git -C "$repo" for-each-ref \
  --format='%(refname:short) %(objectname) upstream=%(upstream:short)' \
  refs/heads refs/remotes

git -C "$repo" remote
```

Inspect remote URLs only when needed and redact embedded credentials before sharing.

Check current remote heads without changing local refs:

```bash
git ls-remote --symref https://github.com/OWNER/REPO.git HEAD
git ls-remote --heads https://github.com/OWNER/REPO.git
```

Do not call stale remote-tracking refs “current GitHub state.”

## 3. Exact Dirty Counts

`git status` normally compacts untracked directories. Use `--untracked-files=all` when comparing inventories:

```bash
git -C "$repo" status --porcelain=v2 --branch --untracked-files=all

git -C "$repo" status --porcelain=v1 --untracked-files=all \
  | python3 -c '
import collections, sys
rows = [line.rstrip("\n") for line in sys.stdin]
counts = collections.Counter(row[:2] for row in rows)
print({
    "total": len(rows),
    "tracked_changed": sum(v for k, v in counts.items() if k != "??"),
    "untracked": counts.get("??", 0),
    "statuses": dict(sorted(counts.items())),
})'
```

State the timestamp and counting mode when reconciling contradictory reports.

## 4. Nested Repository / Gitlink Check

From the parent repository:

```bash
git -C "$parent" ls-files --stage -- nested-path
git -C "$parent" check-ignore -v nested-path
git -C "$parent" submodule status
test -f "$parent/.gitmodules" \
  && python3 -c 'print(open("'$parent'/.gitmodules").read())' \
  || echo 'NO .gitmodules'
```

Mode `160000` means a gitlink. Empty `ls-files` plus a matching ignore rule means the nested clone is not represented in the parent index.

## 5. Graph Relationship

```bash
a=branch-or-sha-A
b=branch-or-sha-B

git -C "$repo" rev-parse "$a^{commit}" "$b^{commit}"
git -C "$repo" merge-base "$a" "$b" || echo NONE
git -C "$repo" rev-list --left-right --count "$a...$b"

git -C "$repo" merge-base --is-ancestor "$a" "$b"
echo "a_is_ancestor_b_exit=$?"   # 0 yes, 1 no

git -C "$repo" merge-base --is-ancestor "$b" "$a"
echo "b_is_ancestor_a_exit=$?"
```

A local branch can be stale while all its commits are already ancestors of another pushed branch. Check ancestry before calling work “unpushed” or “missing.”

Check whether reported objects exist without fetching:

```bash
git -C "$repo" cat-file -e "$sha^{commit}" \
  && echo PRESENT \
  || echo ABSENT
```

## 6. Exact Change Scope

```bash
git -C "$repo" diff --cached --name-status
git -C "$repo" diff --name-status
git -C "$repo" diff --numstat HEAD -- path/to/file
git -C "$repo" ls-files --others --exclude-standard
```

Before proposing staging:

```bash
git -C "$repo" check-ignore -v -- path/to/secret path/to/runtime-state
```

Never use `git add -A --dry-run` as proof that bulk staging would be safe; it only previews what would be added.

## 7. Isolate a Fix From Older WIP

If a trusted pre-change backup exists:

```bash
sha256sum path/to/file.before path/to/file.current
diff -u \
  --label a/path/to/file \
  --label b/path/to/file \
  path/to/file.before \
  path/to/file.current
```

Placement-only check against the intended source repository:

```bash
diff -u \
  --label a/path/to/file \
  --label b/path/to/file \
  path/to/file.before \
  path/to/file.current \
  | git -C "$source_repo" apply --check -
echo "apply_check_exit=${PIPESTATUS[1]}"
```

Exit 0 proves the patch context applies. It does not prove semantics; run tests after an approved transplant.

## 8. Modern Merge Forecast Across Separate Object Databases

`git merge-tree --write-tree` uses the current merge machinery, including rename detection, but creates tree objects. Isolate those writes in a subshell and temporary object database:

```bash
repo_a=/path/to/repo-a
repo_b=/path/to/repo-b
commit_a=FULL_SHA_A
commit_b=FULL_SHA_B

(
  set -u
  tmp=$(mktemp -d /tmp/git-merge-forecast.XXXXXX)
  trap 'rm -rf "$tmp"' EXIT
  mkdir -p "$tmp/objects"

  common_a=$(git -C "$repo_a" rev-parse --path-format=absolute --git-common-dir)
  common_b=$(git -C "$repo_b" rev-parse --path-format=absolute --git-common-dir)

  export GIT_OBJECT_DIRECTORY="$tmp/objects"
  export GIT_ALTERNATE_OBJECT_DIRECTORIES="$common_a/objects:$common_b/objects"

  git -C "$repo_a" merge-tree \
    --write-tree \
    --name-only \
    --messages \
    "$commit_a" "$commit_b"
  rc=$?
  echo "merge_tree_exit=$rc"  # 0 clean, 1 conflicts, >1 error
)
```

Why the subshell matters: Hermes terminal sessions may preserve exported environment variables between calls. Exporting `GIT_OBJECT_DIRECTORY` in the parent shell and deleting its directory can make later Git commands report “not a git repository.” Keep all exports inside the subshell.

Do not use deprecated/trivial three-tree output as the final conflict forecast when rename-aware behavior matters. If results differ, report both and privilege the modern strategy while reviewing auto-resolved paths semantically.

## 9. Post-Reviewer Mutation Check

A reviewer’s “read-only” self-report is not evidence. Re-check:

```bash
git -C "$repo" rev-parse HEAD
git -C "$repo" branch --show-current
git -C "$repo" for-each-ref \
  --format='%(refname:short) %(objectname)' \
  refs/heads refs/remotes
git -C "$repo" diff --cached --name-status
git -C "$repo" status --porcelain=v2 --branch --untracked-files=all
```

If an internal-object side effect occurred, report it exactly. Do not manually delete object files; preserve first and obtain approval for remediation.

## 10. Evidence Packet for an Inaccessible Machine

Ask the operator on that machine for raw output, not a narrative summary:

```bash
git status --porcelain=v2 --branch --untracked-files=all
git worktree list --porcelain
git for-each-ref \
  --format='%(refname:short) %(objectname) upstream=%(upstream:short)' \
  refs/heads refs/remotes
git remote -v
git fsck --unreachable --no-reflogs
```

For reported orphan/dangling SHAs:

```bash
git show --no-patch --format='commit=%H%nparents=%P%nsubject=%s' SHA...
git branch --contains SHA
git diff --name-status orphan-branch intended-branch
```

Tell the operator not to fetch, GC, prune, clean, stash, branch, tag, or create rescue refs until the preservation plan is approved. Redact tokens in remote URLs.
