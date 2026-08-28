# Interrupted Release/Update Resume Checklist

Use this for a candidate, release, upgrade, migration, or deploy task that resumes after context compression, a timeout, a killed process, a tool-budget boundary, or a prior agent summary.

## Resume evidence ledger

Record these fields before any mutation:

```text
candidate_path        = exact path
candidate_branch      = exact branch
candidate_head        = exact SHA
candidate_base        = exact base/target SHA
remote_target        = fresh git ls-remote SHA
worktree_type         = main or linked
operation_sentinel   = CHERRY_PICK_HEAD / REBASE_HEAD / MERGE_HEAD / absent
unmerged_paths        = exact count + path list
conflict_check        = command + exit code + output count
live_head             = exact SHA
live_status           = tracked/untracked summary
active_processes      = relevant PIDs and commands
fresh_test_status     = PASS / TARGETED-ONLY / INCOMPLETE / KILLED / INVALID
mutation_status       = exact changes made by this resume pass
```

## Linked-worktree operation-state trap

`<worktree>/.git` may be a file containing the actual Git directory. Do not test only:

```bash
test -f <worktree>/.git/CHERRY_PICK_HEAD
```

Use Git's path resolution instead:

```bash
git -C <worktree> rev-parse --git-dir
git -C <worktree> rev-parse --git-common-dir
git -C <worktree> rev-parse --git-path CHERRY_PICK_HEAD
git -C <worktree> rev-parse --git-path REBASE_HEAD
git -C <worktree> status
```

A status such as `UU` plus `git ls-files -u` proves an unresolved index state. `git diff --check` is a useful red-capable gate for leftover conflict markers, but do not use it as a substitute for semantic conflict review.

## Moving-target rule

Query the remote directly immediately before candidate construction or rebuild:

```bash
git -C <repo> ls-remote origin refs/heads/main
```

If the returned SHA differs from the candidate's recorded base, classify the old candidate as `STALE-TARGET`. Do not resolve conflicts, reuse tests, or request release approval for it. If the local repository lacks the new object, do not infer ancestry from a failed local `merge-base`; record that fetch/object availability is a separate gap and use the remote comparison endpoint or a controlled fetch only under the approved scope.

## Semantic conflict rule

When a compatibility/purge policy or other behavior decision appears on both sides of a cherry-pick, `ours` and `theirs` are not safe generic choices. Inspect representative source and test conflicts, identify which policy is owner-ratified, and resolve the behavior consistently across implementation, fallback/routing, normalization, pricing/metadata, and tests. A conflict-free merge is not proof that the intended behavior survived.

## Approval boundary

The resume audit itself is read-only. It does not authorize:

- abort/reset/clean of the candidate;
- fetch that changes refs;
- conflict resolution or `git add`;
- commit, push, deploy, restart, or configuration change;
- replacing live runtime;
- downstream channel/account migration.

After the audit, ask only for the first genuine owner decision, such as which exact remote target to pin. Then execute only the candidate scope covered by that decision and re-run the affected gates from the new SHA.

## Evidence labels

Use these labels explicitly:

- `CURRENT / PROVEN` — fresh command output supports it.
- `HISTORICAL / PARTIAL` — prior output exists but was not rerun or belongs to an old SHA.
- `STALE-TARGET` — candidate base differs from fresh remote target.
- `CONFLICTED / NOT-TESTABLE` — unresolved index or conflict markers remain.
- `TARGETED-ONLY` — affected tests passed but authoritative full suite did not complete.
- `INCOMPLETE` — killed, timed out, harness-invalid, or missing final output.
- `LIVE-UNCHANGED` — fresh live boundary check shows no approved mutation.

Never collapse these into one `A4 complete`, `release-ready`, or `update done` label.
