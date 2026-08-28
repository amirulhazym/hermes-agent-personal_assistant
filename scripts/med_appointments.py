#!/usr/bin/env python3
"""
med_appointments.py — Medical appointment tracker.

Usage:
    python3 med_appointments.py --upcoming           # Next appointment
    python3 med_appointments.py --all                # All appointments
    python3 med_appointments.py --add "2026-08-06" "IPR" "Follow-up"  # Add new
    python3 med_appointments.py --check-tomorrow     # Alert if appointment tomorrow
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

HERMES_HOME = Path.home() / ".hermes"
APPOINTMENTS_FILE = HERMES_HOME / "appointments.json"
TAPER_FILE = HERMES_HOME / "dexa_taper.json"
MYT = ZoneInfo("Asia/Kuala_Lumpur")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_json(path: Path, data: dict) -> None:
    data["last_updated"] = datetime.now(MYT).strftime("%Y-%m-%d")
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def now_myt() -> datetime:
    return datetime.now(MYT)


def today_str() -> str:
    return now_myt().strftime("%Y-%m-%d")


def get_upcoming(data: dict) -> list[dict]:
    """Get upcoming appointments (today or future)."""
    today = today_str()
    upcoming = []
    for appt in data.get("appointments", []):
        if appt.get("status") == "completed":
            continue
        appt_date = appt.get("date", "")
        if appt_date >= today:
            days_until = (datetime.strptime(appt_date, "%Y-%m-%d").date() - now_myt().date()).days
            appt["days_until"] = days_until
            upcoming.append(appt)
    return sorted(upcoming, key=lambda x: x.get("date", ""))


def get_taper_phase_id(date_str: str) -> int | None:
    """Get taper phase ID for a given date."""
    taper = load_json(TAPER_FILE)
    for phase in taper.get("phases", []):
        start = phase.get("start")
        end = phase.get("end")
        if not start:
            continue
        if end is None:
            if date_str >= start:
                return phase.get("id")
        else:
            if start <= date_str <= end:
                return phase.get("id")
    return None


def add_appointment(date: str, location: str, purpose: str, notes: str = "") -> dict:
    """Add a new appointment."""
    data = load_json(APPOINTMENTS_FILE)
    appts = data.get("appointments", [])

    new_id = max([a.get("id", 0) for a in appts], default=0) + 1
    phase_id = get_taper_phase_id(date)

    new_appt = {
        "id": new_id,
        "date": date,
        "time": None,
        "location": location,
        "purpose": purpose,
        "notes": notes,
        "linked_taper_phase": phase_id,
        "status": "upcoming",
        "reminder_sent": False,
    }

    appts.append(new_appt)
    data["appointments"] = appts
    save_json(APPOINTMENTS_FILE, data)

    return {"ok": True, "appointment": new_appt}


def mark_completed(appt_id: int) -> dict:
    """Mark an appointment as completed."""
    data = load_json(APPOINTMENTS_FILE)
    for appt in data.get("appointments", []):
        if appt.get("id") == appt_id:
            appt["status"] = "completed"
            save_json(APPOINTMENTS_FILE, data)
            return {"ok": True, "appointment": appt}
    return {"ok": False, "error": f"Appointment #{appt_id} not found"}


def check_tomorrow() -> dict | None:
    """Check if there's an appointment tomorrow. Returns alert message if yes."""
    data = load_json(APPOINTMENTS_FILE)
    tomorrow = (now_myt().date() + timedelta(days=1)).strftime("%Y-%m-%d")

    for appt in data.get("appointments", []):
        if appt.get("date") == tomorrow and appt.get("status") != "completed":
            return {
                "alert": True,
                "appointment": appt,
                "message": format_appointment(appt, days_until=1),
            }
    return None


def check_today() -> dict | None:
    """Check if there's an appointment today."""
    data = load_json(APPOINTMENTS_FILE)
    today = today_str()

    for appt in data.get("appointments", []):
        if appt.get("date") == today and appt.get("status") != "completed":
            return {
                "alert": True,
                "appointment": appt,
                "message": format_appointment(appt, days_until=0),
            }
    return None


def format_appointment(appt: dict, days_until: int = None) -> str:
    """Format appointment for display."""
    lines = []

    if days_until == 0:
        lines.append("📅 TEMUJANJI HARI INI!")
    elif days_until == 1:
        lines.append("📅 TEMUJANJI ESOK!")
    elif days_until is not None:
        lines.append(f"📅 Temujani dalam {days_until} hari")
    else:
        lines.append("📅 Temujani:")

    lines.append(f"  Tarikh: {appt.get('date', '?')}")
    if appt.get("time"):
        lines.append(f"  Masa: {appt['time']}")
    lines.append(f"  Lokasi: {appt.get('location', '?')}")
    lines.append(f"  Tujuan: {appt.get('purpose', '?')}")
    if appt.get("notes"):
        lines.append(f"  Nota: {appt['notes']}")

    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: med_appointments.py --upcoming | --all | --add | --check-tomorrow | --check-today | --complete <id>")
        return 1

    arg = sys.argv[1]
    data = load_json(APPOINTMENTS_FILE)

    if arg == "--upcoming":
        upcoming = get_upcoming(data)
        if upcoming:
            for appt in upcoming:
                print(format_appointment(appt, appt.get("days_until")))
                print()
        else:
            print("Tiada temujani akan datang")

    elif arg == "--all":
        for appt in data.get("appointments", []):
            status = "✅" if appt.get("status") == "completed" else "📅"
            print(f"{status} #{appt.get('id')}: {appt.get('date')} — {appt.get('purpose')}")
            if appt.get("location"):
                print(f"   Lokasi: {appt['location']}")
            if appt.get("notes"):
                print(f"   Nota: {appt['notes']}")
            print()

    elif arg == "--add":
        if len(sys.argv) < 5:
            print("Usage: --add <date> <location> <purpose> [notes]")
            return 1
        date = sys.argv[2]
        location = sys.argv[3]
        purpose = sys.argv[4]
        notes = sys.argv[5] if len(sys.argv) > 5 else ""
        result = add_appointment(date, location, purpose, notes)
        print(json.dumps(result, indent=2))

    elif arg == "--complete":
        if len(sys.argv) < 3:
            print("Need appointment ID: --complete 1")
            return 1
        result = mark_completed(int(sys.argv[2]))
        print(json.dumps(result, indent=2))

    elif arg == "--check-tomorrow":
        result = check_tomorrow()
        if result:
            print(result["message"])
        # Silent when no appointment tomorrow — no stdout = no delivery for no_agent cron

    elif arg == "--check-today":
        result = check_today()
        if result:
            print(result["message"])
        else:
            print("Tiada temujani hari ini")

    else:
        print(f"Unknown arg: {arg}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
