# Compact Medication Time Confirmation — 2026-08-19

## Proven trigger and interpretation

Raw inbound statement:

> `Dexa siang done 127pm`

The message contained all three required signals: a named drug (`Dexa`), a completion signal (`done`), and an explicit compact time (`127pm`). In this context, `127pm` was normalized to `13:27`; the original text remained the provenance/source quote. No current system time was substituted.

This is contextual normalization, not proof that every compact numeric token is unambiguous. A token without AM/PM, or one with multiple plausible parses, requires a clarification instead of a guess.

## Live resolution evidence

Command:

```bash
python3 /home/ubuntu/.hermes/scripts/med_resolve.py dexa --time 13:27 --slot C
```

Raw result:

```json
{
  "ok": true,
  "drug_id": "dexamethasone_2",
  "slot": "C",
  "drug": "Dexamethasone",
  "dosage": "4mg",
  "dosage_source": "dexa_taper.json"
}
```

The live resolver, not a static alias table, supplied the canonical drug ID and current taper dose.

## Safe single-drug write sequence

Because the message named only Dexa while Slot C contains multiple drugs, do not confirm the whole slot.

1. Pre-read showed Slot C for `2026-08-19` was pending.
2. Dry-run:

   ```bash
   python3 /home/ubuntu/.hermes/scripts/med_confirm.py C dexamethasone_2 --at 13:27 --source-text "Dexa siang done 127pm" --dry-run
   ```

   Result: only `dexamethasone_2` would change from pending to taken at `13:27`.

3. Real write used the same drug ID, explicit time, and exact source text. The write returned `overall: partial` and only the Dexa child.
4. Direct live read-back showed:

   ```json
   {
     "drugs": {
       "dexamethasone_2": {"status": "taken", "time": "13:27"}
     },
     "overall": "partial"
   }
   ```

5. `calcium`, `calcitriol`, and `b_complex` were absent from the entry; they were not auto-marked.
6. `chain_calc.py --update C` returned `{"ok": true, "state_reset": true}`. The resulting display was `A ✅ 08:05 → B ✅ 09:05 → C ◐ 13:27 → D ~17:27 → E ~20:00`.

## CLI evidence-handling pitfall

`med_confirm.py --check` returned valid JSON plus process exit code `1` for pending/partial states. Preserve and classify the JSON payload (`status`, `time`, `overall`, `confirmed`) before interpreting the exit code; do not blindly retry or double-write. The attempted `med_confirm.py --help` probe returned `Unknown option: --help`; use the documented invocation/read-back commands instead of treating that probe as a state failure.

## Reusable rule

Exact source text → canonical live ID → normalized explicit time → no-write dry-run → serialized single-drug write → child/aggregate/chain read-back. Never widen a one-drug statement to an entire multi-drug slot merely because the slot is known.
