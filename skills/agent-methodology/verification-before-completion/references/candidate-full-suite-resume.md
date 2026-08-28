# Candidate full-suite resume recipe

Use this after context compaction, a candidate amend, a failed broad run, or an isolated test harness.

## 1. Re-establish boundaries

Record separately:

- candidate worktree, branch, exact HEAD, base/target SHA;
- `git status --porcelain`, unresolved index count, operation sentinels;
- live repository HEAD/status/processes;
- current filesystem headroom;
- whether any deployment, restart, push, or live swap occurred.

A candidate result never proves live runtime state.

## 2. Validate the runner before trusting its output

Read the repository wrapper and run its documented invocation. If it chooses a pytest environment under `$HOME`, an isolated HOME may make it exit before collection. That output is `HARNESS-INVALID` and proves zero tests.

For an isolated HOME, pass the wrapper's supported interpreter override (for example `HERMES_PYTHON=/path/to/python-with-pytest`) and preserve only documented test-runner knobs. Do not switch silently to a different ad-hoc command and call it the canonical result.

## 3. Run in evidence layers

1. compile/format/conflict-marker checks;
2. focused regression tests for changed behavior;
3. all affected files;
4. canonical full suite with the wrapper;
5. post-commit checks against the final exact SHA.

Report each layer independently. A killed, timed-out, zero-test, argument-error, or truncated run is incomplete/harness-invalid—not PASS.

## 4. Diagnose ordered-suite failures

If a test passes alone but fails after another file, suspect leaked module/global/context state, provider health state, or test-order coupling. Reproduce in a fresh process, inspect the lifecycle that sets/resets the shared state, and fix the lifecycle boundary rather than weakening the assertion. After the fix, rerun the pair/order-sensitive reproduction and the complete affected-file set.

## 5. Final gate

After every byte change:

- rerun affected tests;
- run `git diff --check`, compileall, and source marker sweep;
- amend/create a new local candidate commit;
- record the new exact SHA and clean status;
- rerun any gate that used the superseded SHA.

Only then ask for a separate live-swap/deployment approval. Do not push, deploy, restart, or change channel configuration as a side effect of candidate testing.
