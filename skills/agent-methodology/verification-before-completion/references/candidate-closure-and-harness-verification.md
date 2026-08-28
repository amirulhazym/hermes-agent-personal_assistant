# Candidate closure and harness verification

Use this reference when constructing a local candidate from a baseline plus live/nested source closure.

## Evidence rules

- Treat a candidate SHA, manifest SHA, source-closure ledger, test result, remote ref, and live runtime as separate evidence layers.
- After every post-commit mutation, obtain a new exact SHA and rerun every gate affected by the changed bytes. Do not reuse a prior PASS merely because the logical change looks unrelated.
- A targeted suite is not a full-suite result. Report the exact test command, isolation environment, pass/fail count, and unrun scope.
- A wrapper's documented usage is not enough: inspect its parser and run a minimal probe showing where arguments are forwarded.

## Safe candidate closure loop

1. Start from the exact approved base SHA and isolated worktree.
2. For every ported test, run it in the candidate environment. If it imports an adjacent source file missing from the candidate, classify that file as a real closure dependency and add it; do not rely on a fuller donor overlay to hide the gap.
3. Recompute the source ledger from actual path records. If bounded testing discovers an intentional source dependency, expand the ledger and arithmetic rather than forcing a previously expected count.
4. Regenerate manifest hashes and runtime destinations. Validate both source-only and runtime-deploy rows; a runtime row with a missing/unsafe destination must fail.
5. Commit. Record the full SHA, parent, base SHA, and branch.
6. Rerun exact-SHA gates: whitespace, secret, PII, manifest positive/negative tests, ledger arithmetic, targeted tests, and remote-main read-only check.
7. Run the authoritative broader suite only after validating the runner invocation. If slice flags are passed through to per-file pytest, that is a harness error, not a test failure; stop and correct the invocation.
8. If the broader suite cannot be validly completed, report `NOT-RUN` or `INCOMPLETE` with the exact transcript. Never convert setup failures, killed runs, or argument errors into PASS.

## Overlay rules

- Build overlays from a clean donor commit, then copy candidate bytes over matching paths.
- Copy custom runtime source into each temporary `HOME`/`HERMES_HOME` when tests load hooks, skills, plugins, or agents from runtime paths. Use copies rather than symlinks when tests could write.
- Verify that the overlay contains every dependency imported by the candidate test; a donor overlay containing a file absent from the candidate can produce a false PASS.
- Independently verify donor/live repository HEAD and status before and after the run.

## Reporting template

```text
CANDIDATE SHA: <full SHA>
BASE SHA: <full SHA>
CHANGED PATHS: <exact count>
LEDGER: <classified>/<total>; dispositions sum exactly
TARGETED: PASS/HOLD + exact count
BROADER: PASS / NOT-RUN / INCOMPLETE + exact reason
MANIFEST: <parsed>/<validated>
SECRET/PII: PASS/HOLD
REMOTE MAIN: exact read-only SHA
LIVE MUTATION: NONE OBSERVED / exact exception + recheck limitation
```
