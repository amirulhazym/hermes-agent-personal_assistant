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

## BD phase handling (added 2026-08-25)

- **BD phase** = 2x/day: 8am (Slot B) + 2pm (Slot F). Slot D (4pm) deactivated.
- **Slot F (14:00)** carries the 2pm dexa dose. Drug ID: `dexamethasone_f`. Auto-deactivated on OD/STOP phases.
- Time-based disambiguation window: F = 14:00-16:00 (overlaps with old C window 10:30-16:00 — narrow C to 10:30-14:00).
- Word-based slot hint: "2pm" → F.
- BD active: 2026-08-26 to 2026-11-17 (12 weeks, 6 BD phases + 1 transition day).

## Pending pharmacist confirmation

- **Phase 13 (2026-10-21 to 2026-11-03):** chart shows 6mg BD only, no split. Dose values NULL until boss confirms with pharmacist (early Sep 2026).
- **Phase 14 (2026-11-04 to 2026-11-17):** chart shows 5mg BD only, no split. Dose values NULL until boss confirms.
- See `dexa_taper.json` → `pending_pharmacist_confirm` array for fillable template. Do NOT fill in numbers preemptively.

## Food guidance evidence

For oral dexamethasone, NHS says not to take it on an empty stomach and to take it with or immediately after breakfast. MedlinePlus says to take it with food or milk to reduce stomach upset. If a dose was already taken empty-stomach, do not repeat or compensate; eat when practical and monitor for severe stomach pain, persistent vomiting, blood in vomit, or black/tarry stool.

Sources:

- https://www.nhs.uk/medicines/dexamethasone-tablets-and-liquid/how-and-when-to-take-dexamethasone-tablets-and-liquid
- https://medlineplus.gov/druginfo/meds/a682792.html
- https://www.medicines.org.uk/emc/files/pil.15923.pdf
