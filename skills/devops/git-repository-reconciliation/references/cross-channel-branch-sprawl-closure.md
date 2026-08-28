# Cross-Channel Branch-Sprawl Closure

Use this reference when multiple Hermes sessions/channels report Git work, especially when the owner asks whether everything is committed/pushed or why branches have accumulated.

## Objective

Produce one current, read-only ledger before any cleanup or publication. Never treat a chat recap, local branch name, remote-tracking ref, PR-creation URL, or test result as proof of the end-to-end state.

Keep these lanes separate:

1. canonical application source;
2. provider/plugin repository;
3. nested live/upstream source checkout;
4. mutable runtime/config/state;
5. wiki/documentation repository;
6. registered worktrees;
7. stashes;
8. direct remote heads and PR objects.

## Read-only inventory

For every repository:

```bash
git -C "$repo" rev-parse --show-toplevel --git-dir --git-common-dir
git -C "$repo" status --porcelain=v2 --branch --untracked-files=all
git -C "$repo" worktree list --porcelain
git -C "$repo" stash list --date=iso
git -C "$repo" for-each-ref \
  --format='%(refname:short)%00%(objectname)%00%(upstream:short)%00%(authordate:iso-strict)%00%(subject)' \
  refs/heads
git -C "$repo" remote -v
git -C "$repo" ls-remote --heads <remote>
git -C "$repo" remote prune --dry-run <remote>
```

`git ls-remote --heads` is the current remote boundary. Do not call a stale `refs/remotes/<remote>/*` ref current merely because it exists locally. `remote prune --dry-run` only enumerates local tracking refs that would be removed; the real prune is a mutation and is not a prerequisite for opening a PR.

## Branch classification matrix

For each local branch record:

- full tip SHA and subject;
- direct same-name remote SHA, if any;
- whether the tip is an ancestor of the intended `main`;
- whether intended `main` is an ancestor of the branch;
- merge-base and left/right counts;
- whether the tip is reachable from another current direct remote head;
- worktree location, dirty paths, and stash references.

Use these labels, never a binary clean/dirty summary:

- `MERGED/REPRESENTED` — branch tip is an ancestor of intended `main`, or exact content/patch equivalence is proven;
- `PUSHED-WIP` — direct remote branch contains the exact tip but it is not merged into intended `main`;
- `LOCAL-ONLY-WIP/CANDIDATE` — tip is not reachable from a current direct remote head and is not represented by intended `main`;
- `LOCAL-ALIAS/STALE-NAME` — local branch points to a tip reachable from another current remote branch under a different name;
- `STALE/REDUNDANT` — same tree or patch is already represented and the same-name remote head is absent;
- `PUSHED-BUT-DIRTY` — branch tip is remote-reachable but a worktree on that commit has uncommitted overlay;
- `PRESERVE/UNKNOWN` — divergent or unrelated recovery/candidate lineage whose purpose is not proven.

Branch names and commit subjects are leads only. A branch with a different SHA can be content-equivalent; a branch with a familiar subject can still be unmerged.

## Proving content equivalence

Do not compare a filesystem SHA-256 directly with a Git blob SHA from `git rev-parse ref:path`; they hash different byte representations. Compare raw bytes using the same algorithm:

```bash
sha256sum <(git cat-file blob <ref>:<path>)
sha256sum <working-tree-path>
```

For whole-tree equivalence:

```bash
git rev-parse <ref>^{tree}
git diff --quiet <ref-a> <ref-b>
git cherry -v <intended-main> <candidate>
```

`git cherry` output `-` means the candidate patch is already represented in the upstream side even when commit IDs differ. Record both tree/patch equivalence and ancestry; they answer different questions.

## Upstream mirror trap

A nested checkout may have thousands of direct heads from an upstream remote. Do not compare every local branch against every upstream head: it creates noisy, slow probes and mixes unrelated lineages. First classify the repository remote roles, then compare local branches to:

1. the intended local `main`;
2. current direct heads of the personal/application remote;
3. same-name current direct heads on other remotes.

Report upstream mirror refs as a separate namespace/count. A personal remote branch and an upstream `refs/remotes/upstream/*` branch are not interchangeable.

Before reconciling a nested checkout with a personal repo, prove the graph relationship:

```bash
git merge-base <nested-main> <personal-main>
git rev-list --count <nested-main>..<personal-main>
git rev-list --count <personal-main>..<nested-main>
```

`merge-base` absent means unrelated lineages. Do not merge, reset, or force-push based on branch names.

## Dirty nested/live checkout

A nested live checkout with modified source files or a stash is not a stale branch-cleanup target. Inventory exact paths and classify each file:

- `DUPLICATE-OF-CANONICAL-CANDIDATE` — raw bytes match a canonical feature file;
- `LIVE/CORE-OVERLAY` — bytes differ and may be active or source-worthy;
- `RUNTIME/GENERATED/PRIVATE` — not normal application source;
- `UNKNOWN` — preserve until provenance is established.

Even a byte-identical copy of a canonical feature is still a live-on-disk overlay in the nested checkout. Do not reset/clean/stash-pop or blanket-commit it. Keep the stash separate from the worktree and report both.

## PR and publication boundaries

A pushed branch is not a PR. A URL ending in `/pull/new/<branch>` is only a PR-creation form. Verify the actual PR object with the GitHub API/CLI using the exact head owner and branch. Keep these states separate:

`COMMITTED-LOCAL-ONLY → PUSHED-BRANCH → PR-OPEN → REVIEWED → MERGED → DEPLOYED → LIVE-VERIFIED`

If the application candidate depends on a separate plugin/provider repository, verify that repository's direct remote head independently. Passing plugin tests or pushing the application branch does not publish the dependency.

Recommended publication order:

1. verify candidate identity and intended paths;
2. publish the provider/plugin commit and read back its direct remote SHA;
3. publish the application feature branch and read back its direct remote SHA;
4. create the actual PR and read back its number/state;
5. review/merge as a separate owner-approved gate;
6. clean redundant local refs only after publication evidence is recorded.

## Cleanup gate

Do not delete refs during the read-only audit. Before removing a redundant local branch, prove:

- no worktree uses it;
- no uncommitted/untracked overlay depends on it;
- its source bytes/patch are represented in the intended source or a retained remote/rescue artifact;
- unique commit objects have a deliberate preservation destination;
- any same-name remote absence is current direct `ls-remote` evidence;
- remote branches are treated separately and are not deleted by a local cleanup command.

After cleanup, re-run branch inventory, direct remote heads, worktree list, stash list, and status. Report exact refs removed and exact refs retained.

## Owner-facing workflow

Finish the audit before asking the owner to choose. Derive one recommended execution scope from the ledger rather than presenting a menu of branch-by-branch decisions. Ask for one explicit approval only at the first mutating boundary (publication, local-ref deletion, merge, or deployment). If approval is absent, report the exact ready-to-execute scope and make no mutation.
