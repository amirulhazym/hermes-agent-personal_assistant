# Stale Live Runtime and Partial-Source Harness Gates

Use this reference when a source candidate is tested while a long-running
Hermes gateway or a partial application clone is present on the same host.

## Evidence layers

Keep these claims separate:

1. **Candidate bytes** — worktree or committed source content.
2. **Candidate identity** — exact commit SHA and committed-path hashes.
3. **Live files** — hashes and mtimes under the runtime home.
4. **Process-loaded code** — running PID, start time, reload/restart evidence.
5. **User-visible behavior** — a controlled end-to-end exercise after reload.

A PASS at layer 1 or 2 does not prove layers 3–5.

## Reusable sequence

1. Record candidate `HEAD`, branch, status, intended paths, and `git diff --check`.
2. Run the affected tests against the exact candidate bytes/SHA.
3. If a broad suite fails during collection, inspect every traceback. When a
   partial source closure resolves missing modules from a live/donor checkout,
   classify the run `HARNESS-INVALID`; preserve the raw `ImportError` output.
4. Reproduce unrelated failures on the exact clean baseline before adding
   scope. A failure that occurs at baseline is not candidate-specific.
5. Capture live PID/start time and live-vs-candidate hashes before any cutover.
6. Keep copy/deploy, process reload, and user-visible smoke testing as separate
   approvals/evidence gates.

## Status vocabulary

- `PROVEN`: direct command output supports the exact claim.
- `BASELINE`: reproduced on the clean baseline.
- `HARNESS-INVALID`: the runner did not execute the relevant tests because the
  environment/source closure could not collect them.
- `CANDIDATE-DEFECT`: deterministic failure reproduced only on the candidate.
- `LIVE-UNVERIFIED`: candidate exists, but the running process has not been
  shown to load it.

Never collapse `HARNESS-INVALID`, `BASELINE`, or `LIVE-UNVERIFIED` into a
single "tests failed" or "fixed" statement.

## Common trap

A process can keep old Python modules in memory after source files change. A
fresh import/isolated test may pass while the gateway still exhibits the old
behavior. Reload evidence is a separate boundary; do not restart an active
owner session merely to upgrade the status label.
