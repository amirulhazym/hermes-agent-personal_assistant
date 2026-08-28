# Background Suite Status and Baseline Attribution

Use this reference when a long test run is reported through process notifications or progress logs.

## Status protocol

1. Map the exact process/session ID, command, working directory, candidate HEAD, `git status`, interpreter, worker count, `HOME`, `HERMES_HOME`, and log path.
2. Treat progress counters (`N passed`, `M failed`, percentage) as **INTERIM** only. They are not a verdict.
3. When the process exits, read the final aggregate and exit code. A late exit notification supersedes every earlier `running` or interim report.
4. Keep the tested bytes separate from the commit identity. If the worktree is dirty, the HEAD SHA does not represent the bytes tested; report `HEAD + dirty working tree`, not an exact candidate SHA.
5. Report the final state in this order: overall suite result, raw failed-node count, root-cause classification, candidate identity/cleanliness, release/live status, next gate, owner action required.

## Failure attribution

For every failed node, rerun the same node or file in fresh isolated environments against both the clean baseline and candidate. Use equivalent interpreter and environment settings.

Classify only with evidence:

- `BASELINE`: same failure on clean baseline;
- `CANDIDATE-DEFECT`: deterministic candidate-only failure and the changed code is causally relevant;
- `CONTRACT-CHANGE / STALE-TEST`: intended policy changed but the test asserts retired behavior;
- `HARNESS/FIXTURE`: missing isolated state, fixture, dependency, or patch materialization prevents a valid exercise;
- `ORDER-SENSITIVE/FLAKY`: full suite fails but isolated equivalent runs do not reproduce deterministically;
- `UNRESOLVED`: evidence is insufficient.

A targeted pass can show that a path works in that isolated invocation; it cannot convert the authoritative full-suite exit code into PASS. Conversely, a full-suite failure is not automatically a candidate defect when the clean baseline fails the same node or the runner's fixture boundary is invalid.

## Owner-facing format

Keep the report short and status-first:

```text
Goal: ...
What ran: ...
Final evidence: ...
What is proven: ...
What is partial/blocked: ...
Candidate identity: ...
Next gate: ...
Owner action: none / exact approval needed
```

Do not leave the user with a stale `running` or `0 failed` status after an exit notification. Explicitly correct the earlier interim status and preserve the raw final evidence.