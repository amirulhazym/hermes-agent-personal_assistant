# Dexa Taper Engine — Architecture & Usage

## Overview

The taper engine manages date-dependent dexamethasone dosing for the Tb Meningitis tapering regime. It reads `~/.hermes/dexa_taper.json` and provides dose information based on the current date.

## Tapering Schedule

**Rule:** Taper 1mg every 2 weeks, starting 0.3mg/kg (18mg for ~60kg patient)

**Three phases:**
1. **TDS (3x/day):** 8am, 12pm, 4pm — doses vary per slot
2. **BD (2x/day):** 8am, 2pm — slot D deactivated
3. **OD (1x/day):** 8am — slots C,D deactivated

**Current phase (as of 2026-07-05):** 14mg TDS (5/5/4)

## dexa_taper.json Format

```json
{
  "phases": [
    {
      "id": 5,
      "start": "2026-07-01",
      "end": "2026-07-14",
      "total_mg": 14,
      "freq": "TDS",
      "dose_morning": 5,
      "dose_midday": 5,
      "dose_afternoon": 4,
      "times": ["08:00", "12:00", "16:00"],
      "notes": "CURRENT PHASE"
    }
  ],
  "active_slots_by_freq": {
    "TDS": ["A", "B", "C", "D", "E"],
    "BD": ["A", "B", "C", "E"],
    "OD": ["A", "B", "E"],
    "STOP": ["A", "E"]
  }
}
```

**Key fields:**
- `dose_morning` → Slot B dose
- `dose_midday` → Slot C dose
- `dose_afternoon` → Slot D dose (TDS) or BD afternoon dose
- `active_slots_by_freq` → which slots are active per frequency

## chain_calc.py Integration

**Functions:**
- `load_taper()` → loads dexa_taper.json
- `get_current_phase(taper, date)` → returns phase dict for date
- `get_next_phase(taper, date)` → returns next phase
- `get_dexa_dose_for_slot(slot, phase)` → returns mg for B/C/D
- `get_dexa_total_mg(phase)` → returns total daily dose
- `get_dexa_freq(phase)` → returns TDS/BD/OD/STOP
- `get_days_until_next_phase(taper)` → days until dose change
- `is_slot_active_for_dexa(slot, taper)` → checks if slot is active

**CLI:**
```bash
python3 chain_calc.py --taper           # JSON taper info
python3 chain_calc.py --taper-display   # Human-readable status
```

## Dynamic Slot Management

When taper phase changes frequency, slots auto-deactivate:

| Phase | Active Slots | Deactivated |
|-------|--------------|-------------|
| TDS | A, B, C, D, E | None |
| BD | A, B, C, E | D |
| OD | A, B, E | C, D |
| STOP | A, E | B, C, D |

Inactive slots show as "—" in chain display and don't trigger reminders.

## Taper Alert Cron

`taper_alert.py` runs daily at 06:00 MYT via no_agent cron.

**Behavior:**
- Silent when no transition within 3 days
- Alerts when dose change is within 3 days
- Includes supply warnings if any drugs are low

**Alert format:**
```
📅 DEXA TAPER: 9 hari lagi tukar dose.

Dexa dose change in 9 days!
  Current: 14mg TDS (5+5+4)
  New:     13mg TDS (5+4+4)
  Dose changes:
  Slot C: 5mg → 4mg

Supply status:
  ❌ Pyridoxine (B6) — HABIS
```

## Reminder Templates

Templates now include actual mg values:
- Old: "Levetiracetam + Dexa #1"
- New: "Levetiracetam + Dexa #1 (5mg). Total Dexa hari ni: 14mg (TDS)."

## How to Extend for Other Medications

If another medication needs tapering:

1. Create a new taper JSON file (e.g., `levetiracetam_taper.json`)
2. Add taper functions to chain_calc.py (follow dexa pattern)
3. Update reminder templates to include taper info
4. Add taper alert cron if needed

## Verification

```bash
# Check current taper status
python3 chain_calc.py --taper-display

# Check dose for specific slot
python3 -c "from chain_calc import get_dexa_dose_for_slot; print(get_dexa_dose_for_slot('B'))"

# Simulate future date
python3 -c "from chain_calc import get_current_phase, load_taper; print(get_current_phase(load_taper(), '2026-09-15'))"
```
