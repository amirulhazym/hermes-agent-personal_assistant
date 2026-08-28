# Candidate full-suite failure classification

Use this reference when a release candidate has a valid authoritative full-suite result with failures and the clean baseline is available.

## Required evidence boundary

Record separately:

- exact candidate SHA and clean status;
- exact baseline SHA and clean status;
- authoritative runner command, exit code, final summary, skipped count, elapsed time;
- affected test-node list from the raw log;
- equivalent baseline results for the affected nodes;
- fresh isolated reruns for failures suspected to be order-sensitive or flaky.

Do not classify from an interim progress counter, a truncated log, or a reviewer narrative.

## Classification matrix

| Class | Evidence threshold | Release meaning |
|---|---|---|
| `BASELINE` | Same node fails on exact clean baseline | Not introduced by candidate; still report it and decide whether the baseline failure is in scope |
| `CANDIDATE-DEFECT` | Relevant candidate bytes changed, failure is deterministic, and isolated candidate reproduction fails while clean baseline passes | Block; fix root cause and create a new candidate SHA |
| `CONTRACT-CHANGE/STALE-TEST` | Candidate intentionally changes an explicit product/model/policy contract and the old test asserts superseded behavior | Do not silently waive; update the test/spec or revert the behavior, then rerun |
| `HARNESS/FIXTURE` | Test cannot exercise candidate because isolated HOME, fixture, patch, dependency, or runner setup is missing | Repair the harness or remove the test from candidate scope with evidence; do not call the failed run green |
| `ORDER-SENSITIVE/FLAKY` | Full run fails, but fresh isolated repeats and equivalent baseline repeats show non-determinism or shared failure | Keep the full-suite gate non-green; stabilize or explicitly disposition the test before release |
| `UNRESOLVED` | Evidence does not distinguish the above | Block; do not infer harmlessness from a plausible explanation |

## Root-cause grouping

A raw failure count can contain many assertions from one defect (for example, one missing locale key causing key-set and placeholder assertions across many locales). Report both:

1. raw failed test-node count; and
2. deduplicated root-cause count with affected paths/tests.

Never use root-cause grouping to hide the raw count.

## Safe replay sequence

1. Run the authoritative full candidate suite with the canonical wrapper and no unproven passthrough flags.
2. Extract every failed node from the final log.
3. Run the same affected node set on a detached clean baseline with the same interpreter, worker count, and isolated HOME semantics.
4. For suspicious failures, run the node alone in a fresh candidate HOME and then a fresh baseline HOME.
5. Compare candidate source changes touching the failing path; code reading is a hypothesis until the isolated test confirms behavior.
6. Classify each node and preserve the raw command/output paths.
7. Keep the candidate blocked if any deterministic candidate defect, invalid candidate test, unresolved contract change, or un-dispositioned flake remains.
8. Any source, test, fixture, manifest, or harness change invalidates prior test evidence and any approval tied to the old candidate SHA. Regenerate the SHA-scoped evidence and rerun affected gates.

## Communication shape

For owner-facing status, lead with:

```text
A4 = READY or BLOCKED
Full suite = passed/failed/skipped/files/exit code
Baseline comparison = exact result
Failure buckets = raw node counts + root causes
Live status = unchanged/changed with exact HEAD
Next action = one bounded action
Owner approval = none now OR one exact scope sentence
```

Do not present a targeted rerun as a full-suite pass, and do not present an old candidate approval as approval for a new SHA.
