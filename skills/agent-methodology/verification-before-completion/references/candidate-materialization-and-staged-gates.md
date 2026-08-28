# Candidate Materialization and Staged Gates

## Trigger

Use when a local candidate is assembled from an application baseline plus nested/upstream files, patch artifacts, tests, or sanitized representations.

## Failure pattern

A regression test can be copied into the candidate while the candidate test overlay still imports a clean donor implementation. Comparing donor and candidate files then falsely suggests that the implementation is missing. The candidate may already contain the implementation as a patch artifact.

## Required proof sequence

1. Record candidate HEAD, donor HEAD, patch path, and intended test path.
2. Confirm patch base blobs/ref against the donor.
3. Create a fresh throwaway worktree from the donor; never patch live or the candidate repository for this proof.
4. Apply the smallest relevant patch hunk first.
5. Copy the candidate regression test into the throwaway worktree.
6. Run the test in an isolated environment.
7. Classify:
   - apply + pass: test-materialization omission;
   - apply failure: provenance/base conflict;
   - apply + fail: behavior or patch defect.
8. For a broader candidate run, apply the complete compatible overlay first, then copy the candidate-recorded files over it. Exclude only files already supplied by the candidate copy and record those exclusions.

## Commit-quality gate

Run both checks; they prove different scopes:

```bash
git diff --check                 # tracked unstaged changes only
git add -A
git diff --cached --check        # actual proposed commit payload, including new files
```

Never infer the second from the first. Untracked files are invisible to the first command. After manifest/provenance regeneration or any formatting edit, rerun the staged check.

A targeted clean result for two files is not a full candidate clean result. Count affected files and diagnostics, report them, and obtain explicit approval before broad whitespace-only cleanup or a documented waiver.

## Baseline attribution

For residual suite failures:

- run the same failing node in a fresh process and isolated `HOME`/`HERMES_HOME` for baseline and candidate;
- compare the raw results;
- if both pass alone but the ordered suite fails, classify the residual as order-sensitive/harness debt;
- do not call the candidate fully green or modify unrelated behavior to suppress it.

## Evidence fields to retain

- donor and candidate exact SHAs;
- patch path and relevant included/excluded paths;
- patch-check/apply exit status;
- targeted test output and exit code;
- broader baseline/candidate counts with failure classification;
- staged file count and complete `git diff --cached --check` result;
- manifest/provenance hashes after the final byte changes;
- explicit no-push/no-live-mutation status.
