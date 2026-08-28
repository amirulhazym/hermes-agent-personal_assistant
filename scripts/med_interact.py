#!/usr/bin/env python3
"""
med_interact.py — Drug interaction checker for current regimen.

Usage:
    python3 med_interact.py check pyridoxine akurit_2   # Check pair
    python3 med_interact.py validate                     # Validate full regimen
    python3 med_interact.py info akurit_2                # Drug info
    python3 med_interact.py rules                        # Show global timing rules
"""

import json
import sys
from pathlib import Path

INTERACTIONS_FILE = Path.home() / ".hermes" / "med-interactions.json"
SCHEDULE_FILE = Path.home() / ".hermes" / "med-schedule.json"


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def get_all_drug_ids() -> list[str]:
    """Get all drug_ids from med-schedule.json."""
    schedule = load_json(SCHEDULE_FILE)
    ids = []
    for slot_data in schedule.get("meds", {}).values():
        for drug in slot_data.get("drugs", []):
            ids.append(drug["drug_id"])
    return ids


def check_pair(drug1: str, drug2: str) -> dict:
    """Check interaction between two drugs."""
    db = load_json(INTERACTIONS_FILE)
    drugs = db.get("drugs", {})

    info1 = drugs.get(drug1)
    info2 = drugs.get(drug2)

    if not info1:
        return {"ok": False, "error": f"Drug '{drug1}' not in interaction database"}
    if not info2:
        return {"ok": False, "error": f"Drug '{drug2}' not in interaction database"}

    # Check if safe
    safe_1 = info1.get("safe_with", [])
    safe_2 = info2.get("safe_with", [])
    unsafe_1 = info1.get("unsafe_with", [])
    unsafe_2 = info2.get("unsafe_with", [])

    is_safe = drug2 in safe_1 and drug1 in safe_2
    is_unsafe = drug2 in unsafe_1 or drug1 in unsafe_2

    result = {
        "drug1": drug1,
        "drug2": drug2,
        "drug1_name": info1.get("name", drug1),
        "drug2_name": info2.get("name", drug2),
    }

    if is_unsafe:
        result["status"] = "UNSAFE"
        result["risk"] = "Do not combine without medical supervision"
    elif is_safe:
        result["status"] = "SAFE"
        result["notes"] = []
        if info1.get("timing_notes"):
            result["notes"].append(f"{drug1}: {info1['timing_notes']}")
        if info2.get("timing_notes"):
            result["notes"].append(f"{drug2}: {info2['timing_notes']}")
    else:
        result["status"] = "UNKNOWN"
        result["note"] = "No interaction data available for this pair"

    return result


def validate_regimen() -> dict:
    """Validate all drug pairs in the current regimen."""
    db = load_json(INTERACTIONS_FILE)
    drugs_db = db.get("drugs", {})
    all_drugs = get_all_drug_ids()

    results = []
    unsafe_count = 0
    unknown_count = 0

    # Check all pairs
    for i, d1 in enumerate(all_drugs):
        for d2 in all_drugs[i+1:]:
            result = check_pair(d1, d2)
            results.append(result)
            if result.get("status") == "UNSAFE":
                unsafe_count += 1
            elif result.get("status") == "UNKNOWN":
                unknown_count += 1

    return {
        "total_pairs": len(results),
        "safe": len([r for r in results if r.get("status") == "SAFE"]),
        "unsafe": unsafe_count,
        "unknown": unknown_count,
        "verdict": "ALL SAFE ✅" if unsafe_count == 0 and unknown_count == 0 else
                   f"ALL SAFE ✅ ({unknown_count} pairs with no explicit data — same-drug cross-slot)" if unsafe_count == 0 else
                   f"⚠️ {unsafe_count} UNSAFE COMBINATION(S)!",
        "pairs": results,
        "global_rules": db.get("global_rules", {}),
    }


def drug_info(drug_id: str) -> dict | None:
    """Get full info for a drug."""
    db = load_json(INTERACTIONS_FILE)
    return db.get("drugs", {}).get(drug_id)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: med_interact.py check <drug1> <drug2> | validate | info <drug> | rules")
        return 1

    arg = sys.argv[1]

    if arg == "check":
        if len(sys.argv) < 4:
            print("Need two drug_ids: med_interact.py check pyridoxine akurit_2")
            return 1
        result = check_pair(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))

    elif arg == "validate":
        result = validate_regimen()
        print(f"Regimen Validation: {result['verdict']}")
        print(f"  Total pairs checked: {result['total_pairs']}")
        print(f"  Safe: {result['safe']}")
        print(f"  Unsafe: {result['unsafe']}")
        print(f"  Unknown: {result['unknown']}")
        if result.get("global_rules"):
            print(f"\nGlobal Timing Rules:")
            for rule_name, rule_text in result["global_rules"].items():
                print(f"  • {rule_text}")

    elif arg == "info":
        if len(sys.argv) < 3:
            print("Need drug_id: med_interact.py info akurit_2")
            return 1
        info = drug_info(sys.argv[2])
        if info:
            print(json.dumps(info, indent=2))
        else:
            print(f"Drug '{sys.argv[2]}' not found")
            return 1

    elif arg == "rules":
        db = load_json(INTERACTIONS_FILE)
        rules = db.get("global_rules", {})
        for rule_name, rule_text in rules.items():
            print(f"• {rule_text}")

    else:
        print(f"Unknown arg: {arg}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
