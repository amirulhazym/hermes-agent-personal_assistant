# Cross-Check Completion Audit

Reusable pattern for rechecking a previous model/agent's "done" report.

## Trigger

Use when:

- the user switches models and asks for an independent recheck;
- a previous completion claim is being challenged;
- a task has multiple components, external services, or live/runtime state;
- the report says "all done" but the evidence was produced by the same agent that made the claim.

## Evidence matrix

For each item, capture these separately:

| Layer | Question | Example proof |
|---|---|---|
| Acceptance | What exactly had to be true? | spec, SCHEMA, runbook, task text |
| Artifact | Is the file/code present and structurally correct? | read-back, syntax check |
| Negative behavior | Does invalid input fail safely? | bogus model, missing source, empty field |
| Runtime | Did the active process/API execute the new path? | live command, API status, fresh PID |
| Persistence | Will it survive the session? | VCS status, commit, tracked file, remote |
| Source integrity | Does the documentation still match reality? | compare note claim with live probe |
| External side effect | Did the remote artifact really exist in final state? | fetch/read-back, ID/URL, trashed test artifact |

The final status is the lowest proven layer, not the highest claimed layer.

## Minimum audit sequence

1. Read the current acceptance criteria and relevant local rules.
2. Inspect the exact files and current VCS state.
3. Run the positive path.
4. Run adversarial/negative probes: invalid input, missing fields, stale source, alternate path, and empty/zero data.
5. Exercise the actual live boundary for API, service, or user-facing behavior.
6. Verify persistence and cleanup independently.
7. Reconcile documentation/status notes against the live result.
8. Report every failed first attempt, even if a corrected retry passes.

## Common findings this pattern should catch

- Linter passes current files but does not enforce all advertised rules (`--strict` is a no-op, invalid calendar dates accepted, empty provenance accepted).
- A migrated note says a feature is deployed/fixed while the live command still returns the old failure.
- An external-source migration has no local snapshot and cannot be independently compared without violating source-of-truth rules.
- A pipeline passes only when an undocumented environment variable points to the correct credential root.
- A manifest declares fields that the verifier never checks.
- A fixture formula passes, but the real database has excluded rows, nonzero counters, open sessions, or semantic ambiguity.
- A script works in the working tree but is untracked/uncommitted, so rollback and provenance are not proven.

## Fixture versus live evidence

A fixture proves control flow or arithmetic only. It cannot prove:

- that a metric is the correct production metric;
- that all provider/session rows are included;
- that a deployment was loaded by the active runtime;
- that a historical baseline is reproducible;
- that a remote document was published and remains accessible.

Conversely, a live positive test does not prove negative-path completeness, backward compatibility, or full manifest enforcement. Both boundaries are required.

## Status vocabulary

- **PROVEN** — direct current evidence satisfies the acceptance criterion.
- **CONDITIONAL** — the main path works, but a documented prerequisite or known limitation remains.
- **PARTIAL** — some components work; at least one acceptance criterion is not met.
- **UNVERIFIED** — the claim may be true, but the required evidence is unavailable or prohibited by source-of-truth rules.
- **CONTRADICTED** — current live behavior directly disagrees with the artifact/report.
- **BLOCKED** — a dependency prevents the required verification.

Never replace these with a binary "done" when the item has unresolved sub-components.
