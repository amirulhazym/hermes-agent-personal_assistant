#!/usr/bin/env python3
"""
taper_alert.py — Check for upcoming tapering phase transitions.

Runs daily via cron. Silent when no transition is imminent.
Alerts when a phase transition is within 3 days.

Usage:
    python3 taper_alert.py           # Check and output alert if needed
    python3 taper_alert.py --force   # Always output (for testing)
    python3 taper_alert.py --status  # Show current taper status
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

HERMES_HOME = Path.home() / ".hermes"
TAPER_FILE = HERMES_HOME / "dexa_taper.json"
SUPPLY_FILE = HERMES_HOME / "med-supply.json"
MYT = ZoneInfo("Asia/Kuala_Lumpur")
ALERT_DAYS = 3  # Alert this many days before phase transition


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def now_myt() -> datetime:
    return datetime.now(MYT)


def today_str() -> str:
    return now_myt().strftime("%Y-%m-%d")


def get_current_phase(taper: dict) -> dict | None:
    # Delegates to dexa_taper_lookup (single source of truth)
    from dexa_taper_lookup import get_active_phase
    return get_active_phase(taper)


def get_next_phase(taper: dict) -> dict | None:
    # Delegates to dexa_taper_lookup (single source of truth)
    from dexa_taper_lookup import get_next_phase as _next
    return _next(taper)


def days_until(end_date_str: str) -> int:
    end = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    return (end - now_myt().date()).days


def format_dose_change(current: dict, next_p: dict, days: int = 0) -> str:
    """Format dose change description.
    
    When days==0: transition-day style (hari ni ← LAST DAY, esok ← NEW DOSE)
    When days>0:  countdown style (Current until X, New start Y)
    """
    curr_total = current.get("total_mg", 0)
    next_total = next_p.get("total_mg", 0)
    curr_freq = current.get("freq", "TDS")
    next_freq = next_p.get("freq", "TDS")
    
    # Build dose strings
    def dose_str(phase):
        freq = phase.get("freq", "TDS")
        m = phase.get("dose_morning", 0)
        mid = phase.get("dose_midday", 0)
        dose_2pm = phase.get("dose_2pm", 0)
        aft = dose_2pm or phase.get("dose_afternoon", 0)
        total = phase.get("total_mg", 0)
        
        if freq == "TDS":
            return f"{total}mg TDS ({m}+{mid}+{aft})"
        elif freq == "BD":
            return f"{total}mg BD ({m}+{dose_2pm})"
        elif freq == "OD":
            return f"{total}mg OD ({m})"
        elif freq == "STOP":
            return "STOP (0mg)"
        return f"{total}mg"
    
    lines = []
    
    if days == 0:
        # Transition day style
        lines.append(f"Hari ni ({current['end']}): {dose_str(current)} ← LAST DAY")
        lines.append(f"Esok  ({next_p['start']}): {dose_str(next_p)} ← NEW DOSE")
    else:
        # Countdown style
        lines.append(f"Current: {dose_str(current)} until {current['end']}")
        lines.append(f"New:     {dose_str(next_p)} start {next_p['start']}")
    
    # Frequency change
    if curr_freq != next_freq:
        lines.append(f"⚠️ Frequency change: {curr_freq} → {next_freq}")
        if next_freq == "BD":
            lines.append(f"→ Slot D will be DEACTIVATED")
            lines.append(f"→ Slot F (14:00) will be ACTIVATED — BD 2pm dose")
        elif next_freq == "OD":
            lines.append(f"→ Slots C,D,F will be DEACTIVATED")
        elif next_freq == "STOP":
            lines.append(f"→ ALL dexa slots will be DEACTIVATED")
    
    # Specific dose changes per slot
    changes = []
    for slot, key in [("B", "dose_morning"), ("C", "dose_midday"), ("D", "dose_afternoon")]:
        curr_dose = current.get(key, 0)
        next_dose = next_p.get(key, 0)
        if curr_dose != next_dose:
            changes.append(f"  Slot {slot}: {curr_dose}mg → {next_dose}mg")
    if changes:
        lines.append("")
        lines.append("Dose change:")
        lines.extend(changes)
    
    return "\n".join(lines)


def check_supply_warnings() -> list[str]:
    """Get supply warnings for display in taper alert."""
    warnings = []
    supply_data = load_json(SUPPLY_FILE)
    for drug_id, info in supply_data.get("drugs", {}).items():
        current = info.get("current")
        threshold = info.get("warning_threshold", 7)
        if current is not None and current <= threshold:
            if current == 0:
                warnings.append(f"  ❌ {info.get('name', drug_id)} — HABIS")
            elif current <= threshold:
                warnings.append(f"  ⚠️ {info.get('name', drug_id)} — tinggal {current}")
    return warnings


def main() -> int:
    force = "--force" in sys.argv
    status_only = "--status" in sys.argv
    
    taper = load_json(TAPER_FILE)
    if not taper or "phases" not in taper:
        if force or status_only:
            print("No taper data available")
        return 0
    
    current = get_current_phase(taper)
    next_p = get_next_phase(taper)
    
    if status_only:
        if current:
            total = current.get("total_mg", 0)
            freq = current.get("freq", "?")
            end = current.get("end", "?")
            days = days_until(end) if end else None
            print(f"Current: {total}mg {freq}")
            print(f"Phase ends: {end} ({days} days)")
            if next_p:
                print(f"Next: {next_p.get('total_mg')}mg {next_p.get('freq')}")
        else:
            print("No active taper phase found")
        return 0
    
    if not current or not next_p:
        if force:
            print("No upcoming phase transition")
        return 0
    
    end = current.get("end")
    if not end:
        return 0
    
    days = days_until(end)
    
    # Only alert within ALERT_DAYS window
    if days > ALERT_DAYS and not force:
        return 0  # Silent
    
    # Build alert message
    lines = []
    
    if days == 0:
        lines.append(f"⚠️ DEXA TAPER: Phase {current['id']} ends today — Phase {next_p['id']} starts tomorrow")
    else:
        lines.append(f"📅 DEXA TAPER: {days} hari lagi Phase {current['id']} → Phase {next_p['id']}")
    
    lines.append("")
    lines.append(format_dose_change(current, next_p, days))
    
    # Supply warnings
    supply_warnings = check_supply_warnings()
    if supply_warnings:
        lines.append("")
        lines.append("Supply status:")
        lines.extend(supply_warnings)
    
    output = "\n".join(lines)
    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
