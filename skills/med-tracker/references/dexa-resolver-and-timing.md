# Dexa resolver and timing verification

## Trigger

Use this reference whenever a user reports a Dexa dose with a time, asks whether a delayed lunch compresses the next dose, or the resolver returns a dosage that may conflict with the taper schedule.

## Safe workflow

1. Resolve the alias to obtain only the canonical drug_id and slot:
   `python3 ~/.hermes/scripts/med_resolve.py <alias> --time HH:MM --slot <slot>`
2. Treat the resolver's `dosage` field as non-authoritative for Dexa. It can come from the static `med-schedule.json` snapshot.
3. Read the current date-specific dose from:
   `python3 ~/.hermes/scripts/chain_calc.py --taper-display`
   or the matching date range in `~/.hermes/dexa_taper.json`.
4. Dry-run, then log the exact confirmed intake time with the canonical drug_id.
5. Recalculate the chain from the actual intake time; do not leave downstream reminders at the old time when the regimen requires spacing.

## Verified 2026-08-04 example

- `med_resolve.py dexamethasone_2 --time 12:58 --slot C` returned `dosage: 5mg`.
- The date-specific taper engine returned Phase TDS, 12mg/day: 4mg at 08:00 + 4mg at 12:00 + 4mg at 16:00.
- Therefore the resolver dosage was stale; current dose was 4mg, not 5mg.
- Slot C intake at 12:58 makes a strict 4-hour schedule-consistent Slot D time approximately 16:58. This is a calculation based on the tracked IPR 8/12/4 pattern, not independent authorization to change a prescriber's instruction.

## Food guidance evidence

For oral dexamethasone, NHS says not to take it on an empty stomach and to take it with or immediately after breakfast. MedlinePlus says to take it with food or milk to reduce stomach upset. If a dose was already taken empty-stomach, do not repeat or compensate; eat when practical and monitor for severe stomach pain, persistent vomiting, blood in vomit, or black/tarry stool.

Sources:

- https://www.nhs.uk/medicines/dexamethasone-tablets-and-liquid/how-and-when-to-take-dexamethasone-tablets-and-liquid
- https://medlineplus.gov/druginfo/meds/a682792.html
- https://www.medicines.org.uk/emc/files/pil.15923.pdf
