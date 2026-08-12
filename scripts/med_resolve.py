#!/usr/bin/env python3
"""
med_resolve.py — Resolve drug names/fragments/shorthand to drug_id + slot.

Use as a mandatory pre-flight check before med_confirm.py to prevent
agent fabrication of drug names (e.g. fabricating "Letrozole" for "letram").

Usage:
    python3 med_resolve.py letram --time 20:32
    → {"ok": true, "drug_id": "levetiracetam_e", "slot": "E", "drug": "Levetiracetam"}

    python3 med_resolve.py letrozole
    → {"ok": false, "error": "UNKNOWN: 'letrozole'", "suggestions": ["..."]}

    python3 med_resolve.py dexa --time 13:00
    → {"ok": true, "drug_id": "dexamethasone_2", "slot": "C", "drug": "Dexamethasone"}
"""
import json
import os
import sys
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
SCHEDULE_FILE = HERMES_HOME / "med-schedule.json"

# Compound aliases intentionally expand to several distinct medication records.
# A compound alias is never a synthetic drug and never completes an entire slot.
COMPOUND_ALIASES = {
    "cc": ["calcium", "calcitriol"],
}

# ── Alias table ────────────────────────────────────────────────────────────
# Map user shorthand → canonical drug name. The resolution engine matches
# against drug_id AND drug name in the schedule, using these aliases as
# expansion prefixes.
#
# Keep in sync with med-tracker skill's Drug-Level Confirmation Patterns.
ALIASES = {
    # Slot A
    "akurit": "akurit_2",
    "akurit-4": "akurit_2",
    "rifampicin": "akurit_2",
    "akurit-2": "akurit_2",
    "pyridoxine": "pyridoxine",
    "vitamin b6": "pyridoxine",
    "b6": "pyridoxine",
    # Slot B + E (time-dependent)
    "letram": "levetiracetam",          # → slot B (before 2pm) or E (after 2pm)
    "levetiracetam": "levetiracetam",
    "keppra": "levetiracetam",
    "levetiracetam pagi": "levetiracetam",  # → B
    "letram pagi": "levetiracetam",         # → B
    # Dexa all slots
    "dexa": "dexamethasone",
    "dexamethasone": "dexamethasone",
    "steroid": "dexamethasone",
    "dexamethasone pagi": "dexamethasone",  # → B (before 11am)
    "steroid pagi": "dexamethasone",        # → B
    "dexa pagi": "dexamethasone",           # → B
    "dexamethasone tengahari": "dexamethasone",  # → C (11am-2pm)
    "steroid tengahari": "dexamethasone",       # → C
    "dexa tengahari": "dexamethasone",          # → C
    "dexamethasone petang": "dexamethasone",    # → D (after 4pm)
    "steroid petang": "dexamethasone",          # → D
    "dexa petang": "dexamethasone",             # → D
    # Slot C
    "calcium": "calcium",
    "kalsium": "calcium",
    "calcitriol": "calcitriol",
    "vitamin d": "calcitriol",
    # PRN (as needed)
    "panto": "pantoprazole",
    "pantoprazole": "pantoprazole",
    "protonix": "pantoprazole",
    "gastro": "pantoprazole",
    "b-complex": "b_complex",
    "b complex": "b_complex",
    "swisse": "b_complex",
    "vitamin b": "b_complex",
    # Slot E only
    "letram mlm": "levetiracetam",        # → E (after 7pm)
    "levetiracetam mlm": "levetiracetam", # → E
    "levetiracetam malam": "levetiracetam", # → E
    "letram malam": "levetiracetam",       # → E
}

# ── Time-based slot disambiguation rules ───────────────────────────────────
# Applied when a drug matches multiple slots.
TIME_RULES = {
    "levetiracetam": {
        "B": (None, 14),    # Before 14:00 → B
        "E": (14, None),    # After 14:00 → E
    },
    "dexamethasone": {
        "B": (None, 10.5),  # Before 10:30 → B
        "C": (10.5, 16),    # 10:30-16:00 → C
        "D": (16, None),    # After 16:00 → D
    },
}


def load_schedule() -> dict:
    """Load med-schedule.json, return empty dict on failure."""
    try:
        with open(SCHEDULE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def all_drugs_flat(schedule: dict) -> list[dict]:
    """Return flat list of {drug_id, drug, slot, dosage} across all slots + extras."""
    result = []
    for slot_letter, slot_data in schedule.get("meds", {}).items():
        for drug in slot_data.get("drugs", []):
            result.append({
                "drug_id": drug["drug_id"],
                "drug": drug["drug"],
                "slot": slot_letter,
                "dosage": drug.get("dosage", ""),
            })
    # Also include PRN extras (no slot, just drug_id)
    for extra in schedule.get("extras", []):
        if extra.get("drug_id"):
            result.append({
                "drug_id": extra["drug_id"],
                "drug": extra.get("name", extra["drug_id"]),
                "slot": "",
                "dosage": extra.get("dosage", ""),
            })
    return result


def match_name(what: str, entry: dict) -> bool:
    """Check if `what` matches drug_id or drug name (substring or exact)."""
    what = what.lower()
    drug_id = entry["drug_id"].lower()
    drug_name = entry["drug"].lower()
    return what == drug_id or what in drug_id or what == drug_name or what in drug_name


def pick_slot_by_time(matches: list[dict], time_24h: str) -> list[dict]:
    """
    Apply time-based disambiguation for drugs in multiple slots.
    Returns the filtered list — only one slot's entries survive, or
    all if no time rule applies.
    """
    try:
        hour_f = float(time_24h.replace(":", ".").rstrip("0").rstrip("."))
        if ":" in time_24h and time_24h.endswith("00"):
            hour_f = float(time_24h.split(":")[0])
    except (ValueError, AttributeError):
        return matches  # Can't parse time — return all

    for m in matches:
        drug_id_short = m["drug_id"].rsplit("_", 1)[0]  # "dexamethasone" from "dexamethasone_1"
        rules = TIME_RULES.get(drug_id_short) or TIME_RULES.get(m["drug_id"])
        if not rules:
            continue
        for slot_letter, (lo, hi) in rules.items():
            if (lo is None or hour_f >= lo) and (hi is None or hour_f < hi):
                # Return ONLY entries matching this slot
                return [x for x in matches if x["slot"] == slot_letter]
    return matches


def _resolve_compound(fragment: str, schedule: dict, slot: str = None, time_24h: str = None) -> dict | None:
    """Expand an established multi-drug shorthand into its component records."""
    component_ids = COMPOUND_ALIASES.get(fragment.strip().lower())
    if component_ids is None:
        return None
    candidates = all_drugs_flat(schedule)
    if slot:
        candidates = [d for d in candidates if d["slot"] == slot.upper()]
    components = []
    for drug_id in component_ids:
        matches = [d for d in candidates if d["drug_id"] == drug_id]
        if len(matches) != 1:
            return {
                "ok": False,
                "error": f"COMPOUND_COMPONENT_UNAVAILABLE: '{fragment}' -> '{drug_id}'",
            }
        components.append(matches[0])
    slots = {d["slot"] for d in components}
    if len(slots) != 1:
        return {"ok": False, "error": f"COMPOUND_SPANS_SLOTS: '{fragment}'"}
    return {
        "ok": True,
        "compound": True,
        "compound_id": fragment.strip().lower(),
        "all_drug_ids": [d["drug_id"] for d in components],
        "components": components,
        "slot": components[0]["slot"],
        "drug": " + ".join(d["drug"] for d in components),
    }


def resolve(fragment: str, slot: str = None, time_24h: str = None) -> dict:
    """
    Resolve a drug name/fragment/shorthand to drug_id + slot.

    Returns:
        {"ok": True, "drug_id": "...", "slot": "A", "drug": "...", "dosage": "..."}
        or
        {"ok": False, "error": "UNKNOWN: '...'", "suggestions": [...]}
    """
    schedule = load_schedule()
    if not schedule or "meds" not in schedule:
        return {"ok": False, "error": "Schedule not found or invalid"}

    f = fragment.strip().lower()
    if not f:
        return {"ok": False, "error": "Empty fragment"}

    compound = _resolve_compound(f, schedule, slot=slot, time_24h=time_24h)
    if compound is not None:
        return compound

    # Step 1: Expand alias
    expanded = ALIASES.get(f, f)
    
    # Step 1.5: Word-based slot inference
    # If the fragment contains time words, use them to infer slot BEFORE matching
    WORD_TO_SLOT = {"pagi": "B", "tengahari": "C", "tengah": "C", "petang": "D", "mlm": "E", "malam": "E"}
    slot_hint = None
    words = f.split()
    for w in words:
        if w in WORD_TO_SLOT:
            slot_hint = WORD_TO_SLOT[w]
            break
    if slot_hint and not slot:
        slot = slot_hint  # Filter to hinted slot

    # Step 2: Search all (or specified) slots
    candidates = all_drugs_flat(schedule)
    if slot:
        candidates = [d for d in candidates if d["slot"] == slot.upper()]

    # Step 3: Find matches
    matches = [d for d in candidates if match_name(expanded, d)]

    if not matches:
        # No match — return suggestions
        suggestions = [
            f"{d['drug_id']} ({d['drug']}, slot {d['slot']})"
            for d in all_drugs_flat(schedule)
        ]
        return {
            "ok": False,
            "error": f"UNKNOWN: '{fragment}'",
            "suggestions": suggestions,
        }

    # Step 4: Time-based disambiguation
    if time_24h:
        matches = pick_slot_by_time(matches, time_24h)

    if not matches:
        return {"ok": False, "error": f"Time rules eliminated all matches for '{fragment}' at {time_24h}"}

    result = matches[0]
    ret = {"ok": True, "drug_id": result["drug_id"], "slot": result["slot"], "drug": result["drug"]}

    # ── Dexa dosage: ALWAYS override with taper engine (root-cause fix) ──
    # med-schedule.json dexa dosage is a STATIC snapshot that drifts every
    # 2-week taper phase. The authoritative mg comes from dexa_taper.json.
    from dexa_taper_lookup import get_dexa_dose, is_dexa_drug
    if is_dexa_drug(result["drug_id"]):
        taper_mg = get_dexa_dose(result["slot"], date_str=None)
        if taper_mg is not None:
            ret["dosage"] = f"{taper_mg}mg"
            ret["dosage_source"] = "dexa_taper.json"
        else:
            # Fallback to schedule if taper unavailable
            if result.get("dosage"):
                ret["dosage"] = result["dosage"]
                ret["dosage_source"] = "med-schedule.json (fallback)"
    else:
        if result.get("dosage"):
            ret["dosage"] = result["dosage"]

    # Flag ambiguity if time didn't resolve
    if len(matches) > 1:
        ret["ambiguous"] = True
        ret["all_matches"] = [{"drug_id": m["drug_id"], "slot": m["slot"], "drug": m["drug"]} for m in matches]

    return ret


# ── CLI entry point ────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("Usage: med_resolve.py <fragment> [--time HH:MM] [--slot LETTER]")
        print()
        print("Resolve a drug name/shorthand to the correct drug_id and slot.")
        print("Returns JSON. Exit code 0 = resolved, 1 = unknown.")
        sys.exit(0)

    fragment = sys.argv[1]
    slot = None
    time_24h = None

    args = sys.argv[2:]
    i = 0
    while i < len(args):
        if args[i] == "--time" and i + 1 < len(args):
            time_24h = args[i + 1]
            i += 2
        elif args[i] == "--slot" and i + 1 < len(args):
            slot = args[i + 1].upper()
            i += 2
        else:
            i += 1

    result = resolve(fragment, slot=slot, time_24h=time_24h)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result.get("ok") else 1)
