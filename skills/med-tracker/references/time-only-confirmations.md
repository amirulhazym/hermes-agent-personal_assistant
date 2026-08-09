# Time-Only Medication Confirmations

## Rule
A confirmation without a drug name or slot may be mapped only from the current medication schedule. Read the schedule and identify candidate intake windows.

- Exactly one candidate **and** the message is clearly a **med** confirmation (e.g. "dah ambil", "ubat 6.05am", "slot done"): log that slot with the user's exact stated time, not the agent's current time.
- Zero or multiple candidates: do not write state; ask which slot/drug was taken.
- After writing: read back the slot and report the raw date, slot, drug IDs, and recorded time.
- Label this as schedule-based disambiguation, not explicit drug-name evidence.

Example: "Dah ambil, 6.05am tadi" can map to A at 06:05 when the current schedule places A at 06:00 and no other slot is plausible.

## Malay "makan" override (2026-07-22)
Bare "dah makan [time]" / "thanks remind" is **food-vs-med ambiguous**. Do **not** auto-map from schedule alone and do **not** assume food. Ask once:

> "Boss 'makan' yg boss maksudkan tu makan ubat kan? Ke boss baru lepas makan makanan? Sorry boss, saya nak confirmkan sebab saya nak log accurately."

Then log only after clarification (or if the same message already names a drug/slot/alias).

Never infer drug identity from conversational habit alone, and never proceed when the schedule is stale, ambiguous, or unavailable.
