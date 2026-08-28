#!/usr/bin/env python3
"""
med_substitute.py — Query medication substitution database.

Usage:
    python3 med_substitute.py pyridoxine        # Query substitutes
    python3 med_substitute.py --all              # Show all substitutions
    python3 med_substitute.py --otc              # Show only OTC-available drugs
    python3 med_substitute.py --check akurit_2   # Check if substitute exists
"""

import json
import sys
from pathlib import Path

SUBSTITUTIONS_FILE = Path.home() / ".hermes" / "substitutions.json"


def load_db() -> dict:
    if not SUBSTITUTIONS_FILE.exists():
        return {"substitutions": {}}
    try:
        with open(SUBSTITUTIONS_FILE) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {"substitutions": {}}


def query(drug_id: str) -> dict | None:
    """Query substitutes for a drug_id."""
    db = load_db()
    entry = db.get("substitutions", {}).get(drug_id)
    if not entry:
        return None
    return entry


def has_substitute(drug_id: str) -> bool:
    """Check if a drug has any available substitute."""
    entry = query(drug_id)
    if not entry:
        return False
    return not entry.get("no_substitute_available", True)


def format_result(drug_id: str, entry: dict) -> str:
    """Format a substitution entry for display."""
    lines = [f"Drug: {entry.get('original', drug_id)}"]
    lines.append(f"Slot: {entry.get('slot', '?')}")

    if entry.get("no_substitute_available"):
        lines.append("Status: ❌ NO SUBSTITUTE AVAILABLE")
        lines.append(f"Notes: {entry.get('notes', '')}")
        return "\n".join(lines)

    alts = entry.get("alternatives", [])
    if not alts:
        lines.append("Status: ❌ No alternatives listed")
        return "\n".join(lines)

    lines.append(f"Status: ✅ {len(alts)} alternative(s) available")
    for i, alt in enumerate(alts, 1):
        lines.append(f"\n  Alternative {i}: {alt.get('drug', '?')}")
        lines.append(f"    Active: {alt.get('active_ingredient', '?')}")
        lines.append(f"    Dose: {alt.get('equivalent_dose', '?')}")
        lines.append(f"    Adequacy: {alt.get('adequacy', '?')}")
        lines.append(f"    Timing: {alt.get('timing', '?')}")
        if alt.get("interactions"):
            lines.append(f"    Interactions: {', '.join(alt['interactions'])}")
        else:
            lines.append(f"    Interactions: None known")
        if alt.get("notes"):
            lines.append(f"    Notes: {alt['notes']}")
        if alt.get("verified"):
            lines.append(f"    Verified: {alt['verified']}")

    return "\n".join(lines)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: med_substitute.py <drug_id> | --all | --otc | --check <drug_id>")
        return 1

    arg = sys.argv[1]
    db = load_db()

    if arg == "--all":
        for drug_id, entry in db.get("substitutions", {}).items():
            print(format_result(drug_id, entry))
            print("---")

    elif arg == "--otc":
        for drug_id, entry in db.get("substitutions", {}).items():
            if not entry.get("no_substitute_available"):
                print(format_result(drug_id, entry))
                print("---")

    elif arg == "--check":
        if len(sys.argv) < 3:
            print("Need drug_id")
            return 1
        drug_id = sys.argv[2]
        result = has_substitute(drug_id)
        print(json.dumps({"drug_id": drug_id, "has_substitute": result}))

    else:
        # Query specific drug
        drug_id = arg
        entry = query(drug_id)
        if entry:
            print(format_result(drug_id, entry))
        else:
            # Try fuzzy match
            all_drugs = list(db.get("substitutions", {}).keys())
            matches = [d for d in all_drugs if drug_id.lower() in d.lower()]
            if matches:
                print(f"Drug '{drug_id}' not found. Did you mean: {', '.join(matches)}?")
            else:
                print(f"Drug '{drug_id}' not found in substitution database.")
                print(f"Available drugs: {', '.join(all_drugs)}")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
