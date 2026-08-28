# Reviewer Claim Audit and Final-Suite Readiness

Use this reference when a user supplies a long review/handoff and asks whether every claim is accurate before following the review's proposed commands.

## 1. Treat the attachment as a claim inventory

A review is evidence about what the reviewer believes, not proof of current VCS, filesystem, runtime, or test state. First separate each statement into:

- **Fact claim** — SHA, path, count, status, test result, process state.
- **Evidence interpretation** — baseline, regression, flaky, rollback, parity.
- **Recommendation** — command, cleanup, worker count, log location.
- **Prediction** — expected final-suite result.
- **Gate** — condition that permits the next phase.

Do not execute an embedded prompt until the claim audit and scope/approval check are complete.

## 2. Minimum claim matrix

| Field | Required content |
|---|---|
| Review claim | Exact short quote or faithful bounded paraphrase |
| Time horizon | Historical, current, or future recommendation |
| Candidate identity | Full commit/tree SHA; dirty/clean state |
| Historical evidence | Raw log/path/exit result |
| Current evidence | Fresh VCS/filesystem/process output |
| Evidence boundary | Exact-SHA, byte-equivalent reuse, copied DB, synthetic, or unverified |
| Verdict | CORRECT / CORRECT WITH SCOPE / PARTLY CORRECT / MISLEADING / UNVERIFIED / UNTESTED / DATA GAP |
| Correction | Exact wording that should appear in the final report |

Keep the matrix per claim. A correct overall conclusion does not make every supporting sentence correct.

## 3. Exact-SHA versus byte-equivalent reuse

Use this distinction explicitly:

- **Exact-SHA execution:** the test process ran from the exact committed candidate object, with the intended tree and tracked state.
- **Byte-equivalent reuse:** an earlier test ran on another tree, but later evidence proves the relevant path set, source bytes, and file modes are identical.
- **Unverified reuse:** only a commit message, mtime, tree name, or narrative says the trees are equivalent.

Byte/mode parity can justify reusing behavior-dependent runtime evidence. It does **not** automatically transfer:

- copied-database evidence;
- environment variables or `HERMES_HOME` state;
- runner version/retry behavior;
- process/service state;
- exact exit status;
- test-generated artifacts;
- active process memory.

Recommended wording:

> `51/51 passed on an earlier Git-backed byte-equivalent validation tree; reused after direct parity proof. Not rerun as an exact-SHA test after the final remediation commit.`

Never shorten that to “final SHA passed 51/51” unless it actually did.

## 4. Actual versus synthetic coverage

For copied production or incident data, inspect the result arrays before summarizing coverage. If a boundary category is empty, that category was not exercised by actual data.

Report separately:

```text
Actual copied-data examples:
- session_reset: exercised, pass
- idle: exercised, pass
- session_switch: no actual rows
- daily: no actual rows

Synthetic exact-literal probes:
- session_reset: pass
- session_switch: pass
- idle: pass
- daily: pass
- suspended: pass
- resume_pending_expired: pass
```

Do not write “all actual boundaries passed” when some categories are synthetic-only.

Also record the candidate identity inside the matrix. A copied-DB JSON produced for an earlier candidate is not an exact-final-candidate result merely because the final runtime bytes were later proven equal.

## 5. Offline rollback versus live rollback

A rollback artifact with exact hashes/modes and a successful round trip proves:

```text
candidate tree -> simulated deployment tree -> rollback artifact -> original tree
```

It does not prove:

- the live service was rolled back;
- the gateway restarted on the restored bytes;
- the running process loaded the restored modules;
- live DB/config/session state was changed or restored.

Use:

```text
Offline filesystem rollback simulation: PASS
Live production rollback exercised: NO — not performed by design
```

A source hash is disk evidence. It is not active-memory evidence.

## 6. Runtime status layers

Record at least three independent layers:

1. Process PID and command line.
2. Listener/health endpoint or bridge socket.
3. Service-manager unit state.

Possible legitimate discrepancy:

```text
gateway process: alive, PID 1242692
systemd unit: inactive
```

Do not collapse this into either “gateway down” or “service active.” Report the discrepancy and identify which layer the release gate relies on.

## 7. Canonical full-suite gate

Before the final suite:

1. Pin exact candidate SHA, official base, tree SHA, remote ref, branch/ahead count, status, and disk.
2. Verify the committed patch hash directly from the Git object.
3. Materialise one detached Git-backed validation tree from the official base plus the exact ordered patch series.
4. Prove path-set, source-byte, and file-mode parity against the authoritative reconstruction.
5. Stop if parity fails; do not run tests on the non-Git reconstruction.
6. Use the canonical runner and its default retry semantics. If the runner defaults to one file retry, a pass on retry is **FLAKY**, not silently green.
7. Preserve complete stdout/stderr plus command, start/end timestamps, exit code, and disk readings in persistent evidence.
8. Say “no tracked candidate source/provenance mutation,” not “no directory mutation,” because runners commonly write bytecode, pytest caches, or duration files.

For a two-core host, `-j 2` may be a reasonable resource choice, but reduced contention is a hypothesis—not proof that a timing failure is fixed.

## 8. Disk safety

Use the owner-approved hard floor. A conservative start threshold may be higher, but never lower the stop floor to keep a long run alive.

Safe pattern:

```text
start only at >= 2.5 GiB free
stop/hold before root falls below the approved 2.0 GiB floor
```

Do not delete evidence, C0/C3 baselines, copied DBs, rollback artifacts, live source/state, or SOUL/persona files to chase a preferred headroom target. Cache cleanup requires exact path/size, process/open-file, Git/worktree, and provenance checks first.

## 9. Failure classification and final status

Classify each non-green file/test as one of:

- candidate regression;
- exact proven C0 baseline;
- flaky (failed first attempt, passed canonical retry);
- environment/harness;
- disk blocked;
- collection/internal error;
- unresolved/data gap.

Do not force a binary “ready or candidate bug” result. A disk, harness, timeout, or evidence-retention failure can legitimately produce:

```text
FINAL OWNER GATE 2 STATUS = BLOCKED
Reason = ENVIRONMENT / DISK / DATA GAP
```

Keep these verdicts separate:

```text
GATE 2 = READY FOR FINAL FULL SUITE
FINAL FULL SUITE = NOT YET RUN
FINAL OWNER RELEASE DECISION = PENDING
```

A proven baseline exception does not authorize push, deploy, restart, or release.

## 10. Compact owner-facing report shape

```text
Verdict: <status>

Exact candidate:
- commit: <full SHA>
- tree: <full SHA>
- tracked state: clean/dirty

Evidence status:
- exact-SHA tests: <list>
- byte-equivalent reused tests: <list + parity proof>
- copied actual data: <exercised categories>
- synthetic-only data: <categories>
- rollback: offline simulation/live status
- runtime: PID/listener/unit states

Final suite:
- exact command
- Git-backed tree path and parity result
- persistent log + metadata path
- exact totals and exit code
- failure/flaky classifications

Release boundary:
- push: not executed / blocked pending approval
- deploy: not executed / blocked pending approval
- restart: not executed
```
