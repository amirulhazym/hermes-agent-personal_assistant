# Medication stale-state reconciliation

Use this reference when a reminder says a medication is pending but the owner says it was already taken, especially when a quoted reminder is included in the reply.

## Failure class

A reminder is a projection of persisted state. It is not proof that the medication was not taken. Reconcile these boundaries separately:

```text
owner statement
  -> inbound receipt / quoted-text classification
  -> time parsing and drug resolution
  -> safety decision (ALLOW / HOLD / REJECT)
  -> native state writer
  -> live state read-back
  -> reminder producer
```

A stale reminder can be caused by:

- parser rejection or misparse of an earlier confirmation;
- a safety HOLD caused by a legacy window;
- the owner taking the drug before reporting it, so the reminder was accurate at generation time;
- quoted reminder/history being mistaken for a fresh event;
- a successful write that the reminder producer has not re-read yet.

Do not collapse these into “the reminder system is wrong” without checking the path.

## Owner-facing first response

Lead with the result, not the report:

```text
I understand: [drug/compound] was already taken.
The reminder was stale because [one evidence-backed cause].
I am checking/resolving [exact IDs], then I will read back the live state.
```

If the owner has already answered the same medication question, do not ask again. Use the latest explicit correction as the current source statement, while preserving any earlier conflicting literal separately.

## Exact-time handling

- Exact user-stated time wins and must be preserved verbatim in the evidence ledger.
- For `~15 minutes ago`, fetch the live clock, derive an approximate minute, and store/report it as approximate. Do not call the derived value exact.
- Keep processing time separate from intake time.
- If the user corrects `12:43` to `12:44`, use `12:44` as the latest owner correction but retain the earlier inbound literal for provenance; do not silently rewrite the original inbound record.

## Resolve before write

Run the actual resolver for each item:

```bash
python3 med_resolve.py dexa --time 12:44 --slot C
python3 med_resolve.py CC --time 13:20 --slot C
```

Expected shape:

- Dexa → one `drug_id`, e.g. `dexamethasone_2`, with slot and dose source.
- `CC` → `compound: true`, `compound_id: cc`, and both required component IDs (`calcium`, `calcitriol`).

Never interpret `CC` as Calcium alone, and never overwrite the whole slot to force a complete status.

## Native write preflight

Use the supported writer with the exact source text. Dry-run first:

```bash
python3 med_confirm.py C --compound cc --at 13:20 \
  --source-text 'Cc dah makan ~15min lepas' --dry-run

python3 med_confirm.py C dexamethasone_2 --at 12:44 \
  --source-text 'Dah makan dexa siang jam 12.44pm' --dry-run
```

A compound command is atomic for its components. Distinct same-slot events at distinct times may need separate native writes; read back after each one. If the first succeeds and the second fails, report the partial state and do not silently retry with a slot-level overwrite.

Then perform the same commands without `--dry-run`, only when the source-backed dry-run returns `ok: true`.

## Read-back contract

Read the actual slot state and require all of:

```text
expected drug IDs present
status = taken for every expected drug
stored times match the stated/derived provenance
slot overall = completed (only when all required drugs are present)
```

Example read-back shape:

```json
{
  "med": "C",
  "date": "YYYY-MM-DD",
  "overall": "completed",
  "confirmed": true,
  "drugs": {
    "calcium": {"status": "taken", "time": "13:20"},
    "calcitriol": {"status": "taken", "time": "13:20"},
    "dexamethasone_2": {"status": "taken", "time": "12:44"}
  }
}
```

Some query subcommands may return a nonzero process code because the generic CLI main expects an `ok` key that the query payload does not include. Do not turn that into a failed-state conclusion: inspect and report the JSON read-back itself.

## Legacy-window diagnostic

If an owner-stated intake is outside a configured reminder window:

1. classify the window as `LIVE CONFIGURED VALUE — NOT VERIFIED CLINICAL RULE` until its authority is proven;
2. trace whether the live safety gate converts it into `SCHEDULE_TIME_WINDOW` HOLD;
3. compare the live consumer with the current design/candidate contract;
4. never present the HOLD as proof that the medication timing was clinically invalid;
5. use the native source-backed writer only for the explicit owner statement, not as a silent regimen/config repair.

## Completion wording

After successful read-back, keep the reply short:

```text
C is now complete in live state:
- [drug] — [time]
- [compound component] — [time]
- [drug] — [time]

The previous reminder was stale because [cause].
```

Do not claim “future reminders are fixed/suppressed” until a subsequent reminder producer read or controlled tick has been observed. Separate “state corrected” from “producer behavior live-tested.”
