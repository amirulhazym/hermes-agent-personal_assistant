# Screenshot vs Live-State Reconciliation

## Trigger

Use when a screenshot shows a user-visible contradiction: a reminder continues after the user says they completed an action, a UI shows stale data, or a delivery appears to ignore a confirmation.

## Evidence ledger

Record four separate facts instead of one blended verdict:

1. **Visible sequence** — exact screenshot timestamps, text, counters/IDs, and whether reported times are exact or approximate.
2. **Producer evidence** — scheduler/cron output, generated payload, delivery destination, adapter acceptance, and delivery timestamp.
3. **Backend state** — state file/database contents and reminder counters at the relevant time.
4. **Inbound transition evidence** — bridge/adapter receive event, application inbound log, parser/validator/safety-gate audit, and final state write.

## Classification

- **Stale state / producer path:** producer delivery is proven, but backend state lacks the expected completion.
- **Parser/validation/write failure:** inbound event exists, but the parser rejects it, the safety gate holds it, or the state write fails.
- **Ingestion/routing gap:** screenshot shows the input, but no application inbound event exists. The exact lower-level drop point remains UNVERIFIED; do not claim the bridge itself dropped it without bridge evidence.
- **Wrong destination/identity:** producer delivery target differs from the chat/account shown in the screenshot.

## Deterministic probe

For a cron-driven reminder system:

```text
1. Read the exact cron output file for each visible reminder.
2. Read scheduler/gateway delivery logs and compare destination IDs.
3. Read the live state and reminder-counter files.
4. Search inbound application logs for the screenshot messages and target chat.
5. Search parser/safety/state-write audit logs.
6. If no inbound event exists, run one controlled unique test message in the same chat and correlate its message ID across bridge → gateway → state audit.
```

Inspect the live schema and sample timestamp values before applying time filters. Different stores or versions may use epoch seconds or milliseconds; a filtered empty result is not evidence of missing events until the unit is established.

## Safety rule for stateful workflows

A screenshot is evidence of what the user saw or typed, but is not by itself a source-backed state transition. Do not manually re-log, reset counters, or replay a confirmation from the screenshot alone. Use the normal idempotent confirmation path, preserve safety/window checks, and check for an existing write first to avoid double logging.

## Reporting shape

```text
PROVEN: visible contradiction; producer delivery; current stale state
PARTIAL: inbound path checked only through application logs
UNVERIFIED: exact bridge/filter/drop point
NOT DONE: state mutation or workaround
NEXT: controlled correlation test or targeted path fix
```

The correct fix for frequent reminders is normally to repair the missing inbound/state transition, not to reduce reminder frequency or cap escalation, unless the owner explicitly changes that product requirement.
