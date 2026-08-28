# Cross-boundary slice gates

Use this reference for a change that crosses a real runtime boundary: helper →
production entry point, Node bridge → Python adapter, adapter → gateway watcher,
CLI → updater, or worker → queue.

## Compact ownership matrix

Fill this out before implementation. There must be one retry owner for each
failure class.

| Failure/state | Scheduler owner | Resource cleanup owner | State owner | Handoff | Forbidden duplicate |
|---|---|---|---|---|---|
| transient transport failure | component controller | component controller | component controller | none while budget remains | adapter/gateway retry |
| terminal/auth failure | none | component preserves auth and retires resource | component + consumer terminal mapping | explicit non-retryable signal | generic crash retry |
| bounded component budget exhausted | none after timer clear | component first | supervisor | one process-level handoff | component retry after handoff |
| child/process exit | supervisor | adapter/process manager | adapter/gateway | one supervisor retry | old child retry loop |
| planned shutdown | none | shutdown owner | shutdown owner | none | fatal/reconnect queue |

If a row has two schedulers, stop and resolve ownership before adding code.

## RED/GREEN seam recipe

1. **Baseline:** record the exact production entry point and prove which old helper
   or scheduler it currently invokes.
2. **RED seam test:** call or exercise that entry point with a fake external
   resource. Assert an observable contract such as `one timer`, `one handoff`,
   `old resource retired`, `terminal state preserved`, or `stale callback ignored`.
   The test must fail because the current production path does not satisfy it.
3. **Smallest wiring:** import/invoke the new helper from the production path.
   Do not add broad policy or unrelated cleanup in the same increment.
4. **GREEN:** rerun the seam test, then pure helper tests and existing component
   tests.
5. **Next slice:** add one of duplicate suppression, stale-generation rejection,
   classification, cleanup, handoff, or observability. Repeat RED → GREEN.

A test that imports only a new helper is useful policy coverage, but it is not a
seam RED test and cannot establish that production behavior changed.

## Evidence ledger

Report the layers independently:

- `HELPER-TESTED`: pure helper test output;
- `CALL-SITE`: exact production import and invocation;
- `SEAM-TESTED`: test reaches the call site with a controlled fake;
- `COMPONENT-TESTED`: adapter/supervisor/router behavior;
- `CANDIDATE`: exact committed SHA and clean status;
- `PROCESS-LOADED`: PID/start/cwd/hash or equivalent runtime proof;
- `LIVE-PROVEN`: fresh external/user-visible result.

A lower layer never upgrades a higher layer. Say `PARTIAL` when the next layer
has not run.

## Async/socket/process checklist

For reconnect or supervision work, the seam test should eventually prove:

- one active attempt and at most one pending timer;
- generation/identity checks after every awaited startup boundary;
- old socket/process/listeners retired before replacement;
- duplicate close/exit notifications are idempotent;
- terminal logout/auth state does not delete credentials or enter generic retry;
- bounded local retries stop before supervisor retry starts;
- stop/shutdown clears timers, listeners, locks, and child ownership;
- health/status distinguishes HTTP process liveness from transport readiness.

## Failure pattern to avoid

A common false completion sequence is:

1. add a large controller/helper;
2. add fake-timer tests that import only that helper;
3. get green output;
4. leave the original production scheduler/call site unchanged;
5. report the controller as implemented.

The correct report is `HELPER-TESTED` / `PARTIAL` until call-site evidence and a
seam test prove the production path uses it.
