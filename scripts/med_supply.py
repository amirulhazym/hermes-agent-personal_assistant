#!/usr/bin/env python3
"""
med_supply.py — Medication supply tracking and warnings.

Usage:
    python3 med_supply.py --check                 # All drugs supply status
    python3 med_supply.py --check akurit_2        # Specific drug
    python3 med_supply.py --low                   # Only drugs below warning threshold
    python3 med_supply.py --decrement akurit_2    # Manually decrement (usually auto via med_confirm)
    python3 med_supply.py --refill akurit_2 90    # Set supply to 90
    python3 med_supply.py --set akurit_2 30       # Set supply to exact value
    python3 med_supply.py --upcoming              # Drugs with refill_date in next 7 days
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from med_state_lock import exclusive_state_lock, locked_mutation

HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
SUPPLY_FILE = HERMES_HOME / "med-supply.json"
MYT = ZoneInfo("Asia/Kuala_Lumpur")


def load_supply() -> dict:
    if not SUPPLY_FILE.exists():
        return {"drugs": {}}
    try:
        with open(SUPPLY_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"drugs": {}}


def save_supply(data: dict) -> None:
    data["last_updated"] = datetime.now(MYT).strftime("%Y-%m-%d")
    SUPPLY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SUPPLY_FILE, "w") as f:
        json.dump(data, f, indent=2, sort_keys=False)


def today_str() -> str:
    return datetime.now(MYT).strftime("%Y-%m-%d")


def get_drug(data: dict, drug_id: str) -> dict | None:
    return data.get("drugs", {}).get(drug_id)


@locked_mutation
def decrement(drug_id: str, amount: int = 1) -> dict:
    """Decrement supply for a drug. Returns updated drug info."""
    data = load_supply()
    drug = get_drug(data, drug_id)
    if not drug:
        return {"ok": False, "error": f"Drug '{drug_id}' not found in supply tracking"}
    
    current = drug.get("current")
    if current is None:
        return {"ok": True, "drug_id": drug_id, "current": None, "note": "Supply not tracked (null)"}
    
    new_val = max(0, current - amount)
    drug["current"] = new_val
    save_supply(data)
    
    warning = drug.get("warning_threshold", 7)
    result = {"ok": True, "drug_id": drug_id, "current": new_val, "decremented": amount}
    
    if new_val == 0:
        result["alert"] = "OUT OF STOCK"
    elif new_val <= warning:
        result["alert"] = f"LOW — {new_val} pills left (threshold: {warning})"
    
    return result


@locked_mutation
def refill(drug_id: str, amount: int) -> dict:
    """Set supply to amount (refill)."""
    data = load_supply()
    drug = get_drug(data, drug_id)
    if not drug:
        return {"ok": False, "error": f"Drug '{drug_id}' not found"}
    
    drug["current"] = amount
    drug["last_refill"] = today_str()
    save_supply(data)
    return {"ok": True, "drug_id": drug_id, "current": amount, "refilled": True}


@locked_mutation
def set_supply(drug_id: str, amount: int) -> dict:
    """Set supply to exact value (manual correction)."""
    data = load_supply()
    drug = get_drug(data, drug_id)
    if not drug:
        return {"ok": False, "error": f"Drug '{drug_id}' not found"}
    
    drug["current"] = amount
    save_supply(data)
    return {"ok": True, "drug_id": drug_id, "current": amount}


def check_all() -> list[dict]:
    """Get supply status for all drugs."""
    data = load_supply()
    results = []
    for drug_id, info in data.get("drugs", {}).items():
        current = info.get("current")
        threshold = info.get("warning_threshold", 7)
        status = "ok"
        
        if current is None:
            status = "unknown"
        elif current == 0:
            status = "out_of_stock"
        elif current <= threshold:
            status = "low"
        
        results.append({
            "drug_id": drug_id,
            "name": info.get("name", drug_id),
            "slot": info.get("slot", "?"),
            "current": current,
            "threshold": threshold,
            "status": status,
            "refill_date": info.get("refill_date"),
            "notes": info.get("notes", ""),
        })
    return results


def check_low() -> list[dict]:
    """Get only drugs that are low or out of stock."""
    all_drugs = check_all()
    return [d for d in all_drugs if d["status"] in ("low", "out_of_stock")]


def check_upcoming(days: int = 7) -> list[dict]:
    """Get drugs with refill_date in next N days."""
    all_drugs = check_all()
    today = datetime.now(MYT).date()
    cutoff = today + timedelta(days=days)
    
    results = []
    for d in all_drugs:
        refill_date = d.get("refill_date")
        if refill_date:
            try:
                rd = datetime.strptime(refill_date, "%Y-%m-%d").date()
                if today <= rd <= cutoff:
                    d["days_until_refill"] = (rd - today).days
                    results.append(d)
            except ValueError:
                pass
    return results


def generate_warnings() -> list[str]:
    """Generate warning messages for low/out-of-stock drugs."""
    warnings = []
    low = check_low()
    for d in low:
        if d["status"] == "out_of_stock":
            warnings.append(f"❌ {d['name']} — HABIS! Refill date: {d.get('refill_date', 'unknown')}")
        elif d["status"] == "low":
            warnings.append(f"⚠️ {d['name']} — tinggal {d['current']} pil (threshold: {d['threshold']})")
    
    upcoming = check_upcoming(3)
    for d in upcoming:
        days = d.get("days_until_refill", 0)
        if days == 0:
            warnings.append(f"📅 {d['name']} — refill HARI INI!")
        elif days <= 3:
            warnings.append(f"📅 {d['name']} — refill dalam {days} hari ({d.get('refill_date')})")
    
    return warnings


# ── CLI ─────────────────────────────────────────────────────────────────────

def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: med_supply.py --check | --low | --upcoming | --decrement | --refill | --set")
        return 1
    
    arg = sys.argv[1]
    
    if arg == "--check":
        if len(sys.argv) > 2:
            drug_id = sys.argv[2]
            data = load_supply()
            drug = get_drug(data, drug_id)
            if drug:
                print(json.dumps(drug, indent=2))
            else:
                print(f"Drug '{drug_id}' not found")
                return 1
        else:
            results = check_all()
            print(json.dumps(results, indent=2))
    
    elif arg == "--low":
        results = check_low()
        if results:
            print(json.dumps(results, indent=2))
        else:
            print("All drugs above warning threshold ✅")
    
    elif arg == "--upcoming":
        results = check_upcoming()
        if results:
            print(json.dumps(results, indent=2))
        else:
            print("No refills scheduled in next 7 days")
    
    elif arg == "--decrement":
        if len(sys.argv) < 3:
            print("Need drug_id: --decrement akurit_2 [amount]")
            return 1
        drug_id = sys.argv[2]
        amount = int(sys.argv[3]) if len(sys.argv) > 3 else 1
        result = decrement(drug_id, amount)
        print(json.dumps(result, indent=2))
    
    elif arg == "--refill":
        if len(sys.argv) < 4:
            print("Need drug_id and amount: --refill akurit_2 90")
            return 1
        drug_id = sys.argv[2]
        amount = int(sys.argv[3])
        result = refill(drug_id, amount)
        print(json.dumps(result, indent=2))
    
    elif arg == "--set":
        if len(sys.argv) < 4:
            print("Need drug_id and amount: --set akurit_2 30")
            return 1
        drug_id = sys.argv[2]
        amount = int(sys.argv[3])
        result = set_supply(drug_id, amount)
        print(json.dumps(result, indent=2))
    
    elif arg == "--warnings":
        warnings = generate_warnings()
        if warnings:
            for w in warnings:
                print(w)
        else:
            print("No supply warnings ✅")
    
    else:
        print(f"Unknown arg: {arg}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
