# Medication out-of-window confirmation exception

Use when an owner reports a medication intake whose resolved slot is valid but whose stated time falls outside the active schedule window.

## Evidence boundary

`med_resolve.py` answers *which canonical drug and slot* the phrase maps to. A successful resolver result is not an `ALLOW` decision. Run the deterministic safety gate separately; it may return `HOLD / SCHEDULE_TIME_WINDOW` for the same drug and time.

Capture:

- the owner's exact raw statement and exact stated `HH:MM`;
- resolver output (`drug_id`, slot);
- date-specific taper/dose source;
- safety-gate decision, active schedule version/window, taper phase/digests;
- pre-write state read-back.

Do not infer that a late time is safe merely because the chain display predicts a nearby time, and do not treat a stale-looking window as permission to bypass the gate silently.

## One-off exception protocol

1. Resolve the drug and slot.
2. Run a pure/read-only safety-gate evaluation at the reported time.
3. If the gate returns `HOLD / SCHEDULE_TIME_WINDOW`, ask one targeted question: whether this exact late intake is allowed by the doctor's/protocol's existing rule.
4. Treat an explicit owner answer such as "yes, log 5:30pm" as approval to record *that one event*, not approval to change the schedule, window, taper, or routine.
5. Re-run dry-run with the exact source-backed text and exact time.
6. Write through the native *drug-level* confirmation path using the canonical `drug_id`; never use bare slot confirmation for a partial/multi-drug slot.
7. Read back the drug status, exact time, slot overall state, and chain output.
8. Report the exception as one-off unless the owner separately approves a versioned regimen/schedule update.

## Failure boundaries

- No explicit late-intake approval: HOLD; do not write.
- Explicit approval but resolver is unknown/ambiguous: ask for drug clarification; do not write.
- Dry-run fails or read-back disagrees: stop and report; do not retry blindly.
- A successful write does not prove the gateway hook/runtime has been repaired; it proves only the native writer path recorded the event.
