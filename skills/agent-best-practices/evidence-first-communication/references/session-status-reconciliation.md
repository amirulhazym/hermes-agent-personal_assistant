# Historical Session Status Reconciliation

Use this reference when a user resumes a long investigation after inactivity, context compaction, model switching, or a fresh chat and asks where the work stopped.

## Evidence ledger

Record one row per claim, not one row per conversation:

- `claim`: what the user wants to know
- `session_id` / `parent_session_id`: exact lineage
- `message_id`: the user request and the last relevant evidence
- `historical_claim`: what the previous assistant said
- `last_tool_evidence`: final raw output or artifact observation
- `current_check`: fresh filesystem/VCS/runtime check, if performed
- `status`: `DONE/PROVEN`, `PARTIAL`, `OPEN`, `ON HOLD/BLOCKED`, `UNVERIFIED`, `INCOMPLETE`, or `NOT FOUND IN CHECKED PATHS`
- `boundary`: candidate, commit, pushed ref, live disk, active memory, E2E, or delivery
- `next_gate`: the one missing proof or explicit approval

## Reconstruction sequence

1. Search session history with the user's literal terms and a few technical anchors.
2. Select sessions by exact message evidence, not title/display labels alone.
3. Read the bookends, then scroll from the matched message to the session's true end.
4. If the end is tool output or an assistant tool-call with no final user-facing message, classify the work as incomplete at that boundary.
5. Check whether an artifact exists separately from whether it was attached, sent, or consumed by the user.
6. Check whether a candidate exists separately from whether it was committed, pushed, deployed, loaded into memory, or exercised end-to-end.
7. Only call a status “current” after a fresh check. Otherwise say “last historically evidenced status; not re-audited now.”

## Minimum status lanes

For recovery/reconciliation/repair work, report these independently:

1. Diagnosis/finding
2. Candidate working tree
3. Commit identity and cleanliness
4. Test evidence and scope
5. Pushed/remote state
6. Live-on-disk state
7. Active process/reload state
8. End-to-end behavior
9. Evidence artifact creation
10. Evidence artifact delivery
11. Owner approval, hold, or scope lock

A positive result in one lane must not upgrade another lane. In particular:

- audit complete ≠ repair complete;
- report file exists ≠ report delivered;
- local commit ≠ pushed release;
- live file ≠ loaded process;
- generated reminder ≠ handset delivery;
- broad regression timing ≠ exact causal commit proven.

## Owner-facing WhatsApp shape

Start with the verdict:

```text
[Day/date/time MYT]

Short answer: [resolved / not resolved / partial].

What was resolved:
- ...

What was not resolved:
- ...

Last stopping point:
- ...

Current evidence horizon:
- Last historical proof: ...
- Fresh check now: ... / not run

Next gate:
- ...
```

Use session links inline when useful. Avoid a large narrative before the verdict. Do not reopen implementation or execute a repair merely because the user asked for a recap.

## Failure pattern to avoid

A prior investigation created a substantial live-audit report and later created forensic matrix/ledger files. The final session ended while reading those files, without a final delivery response. The correct classification was:

- live audit artifact: created and historically delivered;
- forensic package: files created, final delivery unproven;
- candidate repair: local only;
- live repair/deployment: not done.

The existence of more files must not be rounded up into “the whole task was completed.”
