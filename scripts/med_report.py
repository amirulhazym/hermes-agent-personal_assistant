#!/usr/bin/env python3
"""
med_report.py — Weekly medication compliance report.

Usage:
    python3 med_report.py               # Generate report for past 7 days
    python3 med_report.py --today       # Today's status only
    python3 med_report.py --range 14    # Last N days
"""

import json
import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

HERMES_HOME = Path.home() / ".hermes"
STATUS_FILE = HERMES_HOME / "med-status.json"
SCHEDULE_FILE = HERMES_HOME / "med-schedule.json"
SUPPLY_FILE = HERMES_HOME / "med-supply.json"
TAPER_FILE = HERMES_HOME / "dexa_taper.json"
MYT = ZoneInfo("Asia/Kuala_Lumpur")

SLOTS = ["A", "B", "C", "D", "E", "F"]
SLOT_NAMES = {
    "A": "Akurit-4 + Pyridoxine",
    "B": "Levetiracetam + Dexa #1",
    "C": "Dexa #2 + Calcium + Calcitriol",
    "D": "Dexamethasone #3",
    "E": "Levetiracetam (malam)",
    "F": "Dexamethasone #2 (BD 2pm)",
}


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


def get_slot_status(status_data: dict, slot: str, date: str) -> str:
    """Get overall status for a slot on a given date."""
    entry = status_data.get("meds", {}).get(slot, {}).get(date)
    if entry is None:
        return "no_data"
    if isinstance(entry, str):
        return "completed" if entry == "confirmed" else "pending"
    if isinstance(entry, dict):
        if "drugs" in entry:
            return entry.get("overall", "pending")
        if entry.get("status") == "confirmed":
            return "completed"
    return "pending"


def get_slot_time(status_data: dict, slot: str, date: str) -> str | None:
    """Get actual intake time for a slot on a given date."""
    entry = status_data.get("meds", {}).get(slot, {}).get(date)
    if entry is None:
        return None
    if isinstance(entry, dict):
        if "drugs" in entry:
            # Get latest taken time
            times = [d.get("time") for d in entry.get("drugs", {}).values()
                     if d.get("status") == "taken" and d.get("time")]
            return sorted(times)[-1] if times else None
        if "time" in entry:
            return entry["time"]
    return None


TRACKING_START = datetime.strptime("2026-07-02", "%Y-%m-%d").date()


def get_complete_dates(days: int) -> tuple[list[str], date]:
    """Get N complete days ending yesterday (today is never complete when report runs)."""
    today = now_myt().date()
    end = today - timedelta(days=1)  # Last complete day
    dates = [(end - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
    dates.reverse()
    return dates, end


def get_today_status(status_data: dict) -> dict:
    """Get today's intake progress so far."""
    today = now_myt().strftime("%Y-%m-%d")
    result = {}
    for slot in SLOTS:
        status = get_slot_status(status_data, slot, today)
        time = get_slot_time(status_data, slot, today)
        result[slot] = {
            "status": status,
            "time": time,
        }
    return result


def generate_report(days: int = 7) -> dict:
    """Generate compliance report for the past N complete days (excluding today)."""
    status_data = load_json(STATUS_FILE)
    supply_data = load_json(SUPPLY_FILE)
    taper_data = load_json(TAPER_FILE)
    
    dates, end_date = get_complete_dates(days)
    
    # Per-slot compliance
    slot_stats = {}
    for slot in SLOTS:
        taken = 0
        partial = 0
        missed = 0
        
        for date in dates:
            status = get_slot_status(status_data, slot, date)
            if status == "completed":
                taken += 1
            elif status == "partial":
                partial += 1
            elif status in ("pending", "no_data"):
                date_obj = datetime.strptime(date, "%Y-%m-%d").date()
                if date_obj < TRACKING_START:
                    continue  # Before tracking started
                missed += 1
        
        applicable_days = taken + partial + missed
        compliance = (taken / applicable_days * 100) if applicable_days > 0 else 0
        
        slot_stats[slot] = {
            "taken": taken,
            "partial": partial,
            "missed": missed,
            "compliance": round(compliance, 1),
        }
    
    # Overall compliance
    total_taken = sum(s["taken"] for s in slot_stats.values())
    total_applicable = sum(s["taken"] + s["partial"] + s["missed"] for s in slot_stats.values())
    overall_compliance = (total_taken / total_applicable * 100) if total_applicable > 0 else 0
    
    # Supply warnings
    supply_warnings = []
    for drug_id, info in supply_data.get("drugs", {}).items():
        current = info.get("current")
        threshold = info.get("warning_threshold", 7)
        if current is not None and current <= threshold:
            if current == 0:
                supply_warnings.append(f"❌ {info.get('name', drug_id)} — HABIS")
            else:
                supply_warnings.append(f"⚠️ {info.get('name', drug_id)} — tinggal {current}")
    
    # Taper info
    taper_info = None
    taper_phases = taper_data.get("phases", [])
    for phase in taper_phases:
        start = phase.get("start")
        end = phase.get("end")
        if not start:
            continue
        if end is None:
            if today_str() >= start:
                taper_info = phase
        else:
            if start <= today_str() <= end:
                taper_info = phase
    
    # Today snapshot
    today_snapshot = get_today_status(status_data)
    
    return {
        "period_start": dates[0],
        "period_end": dates[-1],
        "days": days,
        "overall_compliance": round(overall_compliance, 1),
        "slot_stats": slot_stats,
        "supply_warnings": supply_warnings,
        "taper": {
            "total_mg": taper_info.get("total_mg") if taper_info else None,
            "freq": taper_info.get("freq") if taper_info else None,
            "phase_end": taper_info.get("end") if taper_info else None,
        } if taper_info else None,
        "today": today_snapshot,
    }


def format_report(report: dict) -> str:
    """Format report for WhatsApp delivery."""
    now = now_myt()
    
    lines = []
    lines.append("📊 MED COMPLIANCE REPORT")
    lines.append("")
    
    # Period
    start = datetime.strptime(report["period_start"], "%Y-%m-%d")
    end = datetime.strptime(report["period_end"], "%Y-%m-%d")
    lines.append(f"🔅 {report['days']} complete days: {start.strftime('%d/%m/%Y')} - {end.strftime('%d/%m/%Y')}")
    lines.append("")
    lines.append(f"Date-to-Date (%): {report['overall_compliance']}%")
    lines.append("")
    
    # Per-slot
    for slot in SLOTS:
        stats = report["slot_stats"].get(slot, {})
        taken = stats.get("taken", 0)
        partial = stats.get("partial", 0)
        missed = stats.get("missed", 0)
        compliance = stats.get("compliance", 0)
        total = taken + partial + missed
        if total == 0:
            continue
        
        icon = "✅" if compliance >= 90 else "⚠️" if compliance >= 70 else "❌"
        line = f"{slot} — {taken}/{total} {icon}"
        if partial > 0:
            line += f" (◐{partial})"
        if missed > 0:
            line += f" (✗{missed})"
        lines.append(line)
    
    # Today
    if report.get("today"):
        today_str = now.strftime("%d/%m/%Y")
        parts = []
        t = report["today"]
        for slot in SLOTS:
            s = t.get(slot, {}).get("status", "")
            if s == "completed":
                emoji = "✅"
            elif s == "partial":
                emoji = "🟡"
            else:
                emoji = "🟡"  # pending
            parts.append(f"{slot}{emoji}")
        
        lines.append("")
        lines.append(f"🔅Today, {today_str}:")
        lines.append(" ".join(parts))
    
    # Taper note
    if report.get("taper"):
        t = report["taper"]
        taper_line = f"Note: Dexa {t['total_mg']}mg {t['freq']}"
        if t.get("phase_end"):
            end = datetime.strptime(t["phase_end"], "%Y-%m-%d")
            days_left = (end.date() - now.date()).days
            taper_line += f", Phase ends {end.strftime('%d/%m/%Y')} ({days_left} days)"
        lines.append("")
        lines.append(f"`{taper_line}`")
    
    # Supply warnings
    if report.get("supply_warnings"):
        lines.append("")
        for w in report["supply_warnings"]:
            lines.append(w)
    
    return "\n".join(lines)


def main() -> int:
    days = 7
    
    if "--today" in sys.argv:
        days = 1
    elif "--range" in sys.argv:
        idx = sys.argv.index("--range")
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])
    
    report = generate_report(days)
    print(format_report(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
