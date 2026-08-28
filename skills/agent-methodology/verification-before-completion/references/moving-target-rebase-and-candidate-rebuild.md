# Moving-Target Rebase and Candidate Rebuild

Use this when integrating intentional local/custom commits onto a newer upstream ref, especially before an upgrade or deployment.

## Failure pattern

A candidate can be syntactically clean and targeted tests can pass while the candidate still contains an older conflicting file. This commonly happens when a rebased branch was created with `git rebase -X theirs` or a blanket `git checkout --theirs`: Git resolves the conflict, but the chosen side may silently discard current upstream additions. Typical symptoms are missing upstream methods, stale schema, missing initialization, or tests failing with `AttributeError`/missing-symbol errors.

## Required workflow

1. **Pin the upstream target immediately before integration.**
   ```bash
   git ls-remote <remote> refs/heads/main
   ```
   Record the exact SHA. Do not trust a stale local `origin/main` ref. If the remote advances during a long investigation, mark the previous candidate `STALE-TARGET` and rebuild/rebase against the new SHA.

2. **Preserve the original custom lineage.**
   Record the common base and original custom commit sequence. Do not replay only a previously rebased copy whose conflict resolutions may already have lost upstream content.

3. **Build in a fresh temporary worktree from the pinned SHA.**
   Keep the live worktree untouched. Replay original custom commits in order.

4. **Resolve conflicts semantically.**
   - Keep the current upstream contract/schema/API.
   - Port only intentional custom behavior and tests.
   - Never accept an entire old file solely because a conflict strategy makes Git report success.
   - For high-churn files, compare base, upstream, and custom trees or use a three-way merge; inspect every conflict block.

5. **Run narrow checks after each difficult resolution.**
   At minimum: `py_compile`/compile check, `git diff --check`, and the directly affected tests. Do not continue to the next custom commit while the current resolution is syntactically or behaviorally unproven.

6. **Invalidate prior evidence after every byte change.**
   Conflict resolution, fixture edits, missing-symbol fixes, target-SHA changes, and manifest changes all invalidate previous candidate test evidence. Stop a running test process before editing so it cannot observe mixed bytes; rerun affected gates from the updated candidate.

7. **Separate test verdicts.**
   - Targeted pass = affected component only.
   - Canonical full runner pass = full suite only when the documented runner finishes with an aggregate result.
   - Killed, timed out, truncated, serial-bypass, or harness-invalid runs = `INCOMPLETE/INVALID`, never PASS.
   - A valid runner that exposes concrete failures is a blocker; do not call the candidate green because unrelated targeted tests pass.

8. **Apply live mutation only after final gates.**
   The candidate must have an exact final SHA, compile/diff gates, applicable/full-suite evidence, and explicit live-update approval. A local candidate commit is not a release; a tested candidate is not deployed; a remote ref is not live runtime.

## Evidence fields to record

```text
UPSTREAM_TARGET_SHA=
TARGET_SOURCE=git ls-remote
COMMON_BASE=
ORIGINAL_CUSTOM_COMMITS=
CANDIDATE_HEAD=
CONFLICTS_RESOLVED_SEMANTICALLY=
TARGETED_TESTS=
FULL_RUNNER_COMMAND=
FULL_RUNNER_RESULT=
CANDIDATE_STATUS=LOCAL/PUSHED/DEPLOYED/LIVE
LIVE_MUTATION=NO/YES
```

## Known example pattern

If `origin/main` contains a queue initializer or schema column but the candidate does not, do not add only the missing symbol as a symptom fix until checking whether the whole file was resolved from an older custom side. Compare the candidate file with upstream and the common base; rebuild the lineage or perform a semantic three-way merge if the divergence is broad.
