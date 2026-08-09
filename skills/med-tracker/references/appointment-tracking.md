# Appointment Tracking System

## Overview

`med_appointments.py` tracks medical appointments and links them to tapering phases. Designed for IPR (Institut Perubatan Respiratori) follow-up appointments for TB Meningitis treatment.

## Architecture

```
appointments.json    → Appointment data (date, location, purpose, notes)
med_appointments.py  → CLI: add/list/complete/check
Cron (20:00 daily)   → Alerts if appointment tomorrow
taper_alert.py       → Can include appointment context in taper alerts
```

## Data Format

```json
{
  "appointments": [
    {
      "id": 1,
      "date": "2026-07-06",
      "time": null,
      "location": "IPR (Institut Perubatan Respiratori)",
      "purpose": "TB Meningitis follow-up + medication refill",
      "notes": "Pyridoxine habis — need refill. Also discuss tapering progress.",
      "linked_taper_phase": 5,
      "status": "upcoming",
      "reminder_sent": false
    }
  ]
}
```

**Fields:**
- `id` — unique identifier (auto-increment)
- `date` — YYYY-MM-DD format
- `time` — HH:MM or null if unknown
- `location` — where the appointment is
- `purpose` — why the appointment
- `notes` — additional context (what to bring up, what to ask for)
- `linked_taper_phase` — which taper phase this appointment falls in (auto-detected from date)
- `status` — "upcoming" or "completed"
- `reminder_sent` — whether the day-before reminder was sent

## CLI Usage

```bash
# Show upcoming appointments
python3 med_appointments.py --upcoming

# Show all appointments
python3 med_appointments.py --all

# Add new appointment
python3 med_appointments.py --add "2026-08-06" "IPR" "Follow-up" "Discuss taper progress"

# Mark as completed
python3 med_appointments.py --complete 1

# Check if appointment tomorrow (for cron)
python3 med_appointments.py --check-tomorrow

# Check if appointment today
python3 med_appointments.py --check-today
```

## Cron Integration

**Appointment reminder cron:** Runs daily at 20:00 MYT via no_agent cron.
- Script: `med_appointments.py --check-tomorrow`
- Silent when no appointment tomorrow
- Alerts with appointment details when appointment is next day

**Alert format:**
```
📅 TEMUJANJI ESOK!
  Tarikh: 2026-07-06
  Lokasi: IPR (Institut Perubatan Respiratori)
  Tujuan: TB Meningitis follow-up + medication refill
  Nota: Pyridoxine habis — need refill. Also discuss tapering progress.
```

## IPR Appointment Workflow

IPR (Institut Perubatan Respiratori) is the national TB referral center in Malaysia. Appointments typically involve:

1. **Doctor consultation** — tapering progress, side effects, general health
2. **Medication refill** — prescription renewal at IPR pharmacy
3. **Lab tests** — if needed (liver function, blood counts)

**Key points:**
- Must see doctor FIRST before getting medication from pharmacy
- Can't just walk into pharmacy without doctor's prescription
- Travel from Puchong Jaya to IPR is tiring — minimize trips
- If supply runs out before appointment, it's IPR's miscalculation (not system fault)

## Linking to Tapering Schedule

When adding appointments, the system auto-detects which taper phase the appointment falls in. This helps:
- Know what dose to discuss with doctor
- Track if dose changes align with appointments
- Provide context in taper alerts

## Future Enhancements

- Auto-add appointments from IPR visit dates
- Pre-appointment checklist (what to ask, what to bring)
- Post-appointment notes (what doctor said, new prescriptions)
- Integration with supply tracking (refill after appointment)
