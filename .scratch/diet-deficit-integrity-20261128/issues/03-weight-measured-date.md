# 03 — Weight always carries measured_date

Blocked by: none

## Why
`latest_weight_kg = 59.0` is a 2026-11-15 sample. A 2026-11-28 report called it
"berat terkini kekal 59.0 kg" with no date - stale data presented as current.

## Slice
1. `render_weight(kg, measured_date)` -> `"59.0 kg (timbang 2026-11-15)"`.
2. If `measured_date` missing -> `"59.0 kg (tarikh tiada - jangan anggap semasa)"`.
3. Replace every bare weight print in compact and eod modes.

## Done
- Unit test covers both branches.
- Live 2026-11-28 render shows the date.
