# Runtime Reload + Configuration Contract Reconciliation

Use this reference when a post-update/live daemon behaves differently from the current files, especially when a schedule or safety gate rejects an owner-stated value.

## Evidence sequence

1. **Live process boundary**
   - PID, start time, command, cwd.
   - Hook/module load timestamp from the service log.
   - Current on-disk file hash and mtime.
   - Commit/change timestamp that produced the file.

2. **Direct-vs-live probe**
   - Run the smallest deterministic probe against the current file.
   - Capture the exact live audit output for the same input.
   - If current code returns the corrected value but live logs show the old value, classify `LIVE-STALE-LOADED-CODE`; do not patch the parser again.
   - A restart/reload is an operational gate, not proof that the fix is live. Re-run the active-path probe after reload.

3. **Configuration provenance**
   - Check whether the config path is tracked, ignored, generated, or private mutable state.
   - Compare current hash with preserved backups and source copies.
   - A value present in an ignored JSON file cannot be attributed to a Git merge without separate write evidence.

4. **Contract data-flow trace**

```text
config field -> resolver -> validation/gate predicate -> HOLD/ALLOW -> write/audit/state
```

Capture the raw value at each boundary. Do not stop at “the config says X.”

## Schedule semantics guard

Never collapse these into one `window` field:

- doctor/prescription target or scheduled anchor;
- earliest-safe lower bound;
- reminder/display window;
- retrospective actual-intake acceptance.

A broad reminder window may be suitable for notification timing but unsafe as a hard clinical acceptance rule. A stale window can become newly visible after a gate is deployed even though the value predates the merge. Repair the consumer contract and add tests for the anchor, lower bound, boundary, and late actual intake; do not silently edit the JSON to make one report pass.

## Minimum regression corpus

Include at least:

- exact envelope-wrapped inbound message;
- explicit actual time at the scheduled anchor;
- one minute before/after the configured boundary;
- a late but owner-confirmed retrospective intake;
- a complaint/correction mentioning “doctor”, “start”, or “prescribed” that is not a regimen change;
- a true clinician instruction to change dose/timing.

Assert separately:

- parsed intake time;
- intent classification;
- resolved drug/slot;
- gate decision and finding;
- whether the write subprocess was called;
- persisted audit/state read-back.
