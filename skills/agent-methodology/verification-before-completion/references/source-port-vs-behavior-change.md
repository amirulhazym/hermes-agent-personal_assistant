# Source-port vs behavior-change boundary

Use this when a source-closure candidate contains a regression test and/or patch artifact that is not reflected in the implementation tree.

## Core distinction

A patch artifact is evidence of an intended or historical change. It is not proof that the change is live, and it is not authorization to introduce that behavior into a release candidate.

A test that expects behavior absent from the implementation is an **incomplete source port** until proven otherwise. Do not label the test stale, and do not apply the patch automatically.

## Evidence sequence

1. Reproduce the failing test directly in the isolated candidate environment.
2. Read the test assertion and the actual implementation call path.
3. Locate the patch artifact and read the complete relevant hunks, including related files.
4. Inspect live/nested Git status and history to determine whether the implementation file was actually changed, merely described by a patch, or intentionally left unapplied.
5. Run the affected test file against clean baseline with an equivalent isolated HOME/HERMES_HOME.
6. Classify:
   - **Baseline failure** — fails without candidate overlay.
   - **Candidate-specific incomplete port** — candidate test/patch expects behavior absent from candidate implementation.
   - **Candidate regression** — baseline passes and candidate fails after the candidate overlay.
   - **Order-sensitive** — full suite fails but isolated candidate and baseline file runs pass.
   - **Harness/environment** — argument, setup, timeout, missing-state, or dependency failure prevents valid assertion execution.

## Decision gate

- If the implementation is absent but the patch represents an intentional new behavior, stop at **HOLD** and request explicit scope approval before porting it.
- If approved, port the complete behavior boundary—not only the line that makes the regression test pass. Include related CLI, gateway, persistence, continuation, and state-accounting hunks identified by the patch.
- Create a new candidate SHA after the behavior port. Re-run the focused regression test, affected suites, and all gates affected by changed bytes.
- If the owner does not approve the behavior change, preserve the patch/test as source evidence or classify it explicitly as incomplete/experimental; do not silently delete it to make CI green.

## Harness rules learned from runner failures

- Read the wrapper and parser before passing flags.
- Treat `pytest: unrecognized arguments` as **HARNESS-INVALID**, never as a candidate test failure.
- For this runner shape, start with the canonical wrapper command without pytest flags: `scripts/run_tests.sh`.
- A killed, timed-out, setup-failed, or argument-invalid run cannot be upgraded to PASS.

## Reporting format

Report separately:

```text
FULL SUITE: PASS / FAIL / INCOMPLETE / HARNESS-INVALID
BASELINE COMPARISON: exact command + pass/fail counts
CANDIDATE-SPECIFIC: exact files and reproduced evidence
ORDER-SENSITIVE: exact isolated replay evidence
BEHAVIOR CHANGE: authorized / not authorized / unresolved
RELEASE: READY / HOLD
```

Never ask for release approval while a candidate-specific incomplete port remains unresolved.