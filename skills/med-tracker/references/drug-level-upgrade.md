# Drug-Level Tracking Upgrade (2026-07-03)

## Problem

Slot-level binary state (confirmed/not-confirmed) was too coarse. Slot B had 2 drugs (dexamethasone_1, levetiracetam_b), but marking B as "confirmed" after Dexa was taken incorrectly stopped reminders for Levetiracetam.

## Root Cause

The domain's actual granularity was **drug within a slot**, but the state model only tracked **slot**. This mismatch meant partial completion was invisible — the system saw only ✅ or ❌ for the entire slot, missing the ◐ intermediate state.

## Fix

### Schema change

Old med-status.json:
```json
"B": { "status": "taken", "time": "08:16" }
```

New med-status.json:
```json
"B": {
  "overall": "partial",
  "drugs": {
    "dexamethasone_1": { "status": "taken", "time": "08:16" },
    "levetiracetam_b": { "status": "pending" }
  }
}
```

### 3-tier status

Status | Meaning | Reminders fire? | Icon
--------|---------|-----------------|------
`pending` | No drugs taken in slot | ✅ | ⏳ / ~time
`partial` | Some but not all drugs taken | ✅ (for pending drugs) | ◐
`completed` | ALL required drugs taken | ❌ | ✅

### Drug ID convention

Format: `{drug_name}_{slot_letter_suffix}` for uniqueness across slots.

Drug ID | Slot | Common name | Notes
--------|------|-------------|------
`akurit_4` | A | Akurit-4 (Rifampicin-based) | 4 tablets
`pyridoxine` | A | Vitamin B6 | 3 tablets, taken with A
`dexamethasone_1` | B | Dexamethasone 5mg #1 | Morning dose
`levetiracetam_b` | B | Levetiracetam 500mg | Morning dose
`dexamethasone_2` | C | Dexamethasone 5mg #2 | Noon dose
`calcium` | C | Calcium 500mg | With C
`calcitriol` | C | Vitamin D analogue | With C
`b_complex` | C | Swisse B-Complex | Rabu/Sabtu only, required=false
`dexamethasone_3` | D | Dexamethasone 5mg #3 | Evening dose
`levetiracetam_e` | E | Levetiracetam 500mg | Night dose

### Fuzzy drug name matching

`med_confirm.py` matches partial drug names to full drug_id:

Input | Resolves to | Via
------|------------|-----
`dexa` | `dexamethasone_1` (or _2 / _3 based on slot letter) | Prefix match against all drug_ids in the given slot
`letram` | `levetiracetam_b` (or _e based on slot letter) | Prefix match
`akurit` | `akurit_4` | Prefix match
`b6` | `pyridoxine` | Alias
`b complex` | `b_complex` | Partial match
`cc` | `calcium` | Compound shorthand — must ALSO confirm calcitriol

### Chain timing logic

C ~12:16 comes from:
- `get_actual_time(B)` returns **earliest** drug time (08:16 from Dexa)
- `B_to_C gap = 4 hours`
- 08:16 + 4h = 12:16

Alternative considered but rejected: using latest drug time (08:40 + 4h = 12:40). Earliest time chosen because:
1. Dexa spacing is clinically critical (maintains consistent steroid levels)
2. User can always take later, but earliest possible time is the useful lower bound

### Migration (today's data)

Handled manually via `--reset` and re-confirmation commands:
```
med_confirm.py --reset B
med_confirm.py B dexamethasone_1 --at 08:16   # restore Dexa
med_confirm.py B levetiracetam_b --at 08:40   # later confirmed
```

### Script interface

```
med_confirm.py B                  → mark ALL drugs in B as taken (slot-level, backward compat)
med_confirm.py B dexa             → mark only dexamethasone_1 in B (drug-level, fuzzy match)
med_confirm.py B levetiracetam_b  → mark specific drug_id (drug-level, exact)
med_confirm.py --at B 08:16       → with specific time
med_confirm.py --reset B          → clear B's drugs
med_confirm.py --check B          → show B status
med_confirm.py --status           → show all slots
```

### Escalation behavior

Reminders fire when slot is `partial` — the reminder message lists which drugs are pending:
```
"B belum complete! Levetiracetam masih belum ambil. Baru 1/2 je."
```
Only when ALL drugs in the slot reach `taken` does the reminder stop.
