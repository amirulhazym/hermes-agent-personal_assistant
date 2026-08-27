import json
from datetime import datetime, time, timedelta


def load_rules(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _add(t: time, hours: int) -> time:
    dt = datetime.combine(datetime(2000, 1, 1), t) + timedelta(hours=hours)
    return dt.time()


def _parse_time(value: str) -> time:
    hour, minute = map(int, value.split(":"))
    return time(hour, minute)


def _anchors(constraints: list[dict]) -> dict[str, time]:
    return {
        c["slot"]: _parse_time(c["time"])
        for c in constraints
        if c.get("type") == "anchor"
    }


def _constraint(constraints: list[dict], rule_id: str) -> dict:
    return next(c for c in constraints if c["id"] == rule_id)


def solve(constraints, fixed_slots: dict):
    """Resolve medication timing from anchors, lower bounds, and actual Dexa times.

    `fixed_slots` contains user-confirmed actual times only. Derived values never
    become a reason to derive another future dose: C is created from actual B;
    D is created from actual C. This keeps pending doses from forming a cascade.
    """
    slots = dict(fixed_slots)
    anchors = _anchors(constraints)
    rules_fired: list[str] = []
    conflicts: list[str] = []

    # B: doctor anchor is default. Akurit sets a lower bound, never a cascade.
    a_to_b = _constraint(constraints, "rule_001")
    b_anchor = anchors["B"]
    if "B" in slots:
        if "A" in slots:
            earliest = _add(slots["A"], a_to_b["hours"])
            if slots["B"] < earliest:
                conflicts.append(
                    f"A→B unsafe: B {slots['B'].strftime('%H:%M')} is before "
                    f"minimum {earliest.strftime('%H:%M')}"
                )
    else:
        earliest = _add(slots["A"], a_to_b["hours"]) if "A" in slots else b_anchor
        slots["B"] = max(b_anchor, earliest)
        rules_fired.append("rule_004")
        if "A" in fixed_slots:
            rules_fired.append("rule_001")

    # Pending E is only a night anchor. It is not calculated from morning Letram.
    if "E" not in slots:
        slots["E"] = anchors["E"]
        rules_fired.append("rule_005")

    # Pending F (BD 2pm): doctor anchor is 14:00 default. Actual Dexa B sets
    # a min_gap lower bound (rule_009: min 6 hours from B) so delayed morning
    # Dexa pushes F safely without clashing.
    b_to_f = next((c for c in constraints if c.get("id") == "rule_009"), None)
    f_anchor = anchors.get("F")
    if "F" in slots:
        if "B" in slots and b_to_f:
            earliest_f = _add(slots["B"], b_to_f["hours"])
            if slots["F"] < earliest_f:
                conflicts.append(
                    f"B→F unsafe: F {slots['F'].strftime('%H:%M')} is before "
                    f"minimum {earliest_f.strftime('%H:%M')}"
                )
    elif f_anchor:
        if "B" in fixed_slots and b_to_f:
            earliest_f = _add(fixed_slots["B"], b_to_f["hours"])
            slots["F"] = max(f_anchor, earliest_f)
            rules_fired.append("rule_008")
            rules_fired.append("rule_009")
        else:
            slots["F"] = f_anchor
            rules_fired.append("rule_008")

    # Before actual Dexa B exists, C/D retain independent planned defaults
    # 12:00/16:00. Akurit may delay B for safety but never cascades later slots.
    # Once actual B exists, its exact minute drives C/D; actual C overrides D.
    b_to_c = _constraint(constraints, "rule_002")
    c_to_d = _constraint(constraints, "rule_003")
    dexa_origin = fixed_slots.get("B", b_anchor)
    if "C" not in slots:
        slots["C"] = _add(dexa_origin, b_to_c["hours"])
        rules_fired.append("rule_002")
    if "C" in fixed_slots:
        if "D" not in slots:
            slots["D"] = _add(fixed_slots["C"], c_to_d["hours"])
            rules_fired.append("rule_003")
    elif "D" not in slots:
        slots["D"] = _add(slots["C"], c_to_d["hours"])
        rules_fired.append("rule_003")

    known = set(slots)
    referenced = {
        x for c in constraints for x in (c.get("from"), c.get("to"), c.get("slot")) if x
    }
    untouched = sorted(referenced - known)
    return {
        "slots": slots,
        "untouched": untouched,
        "rules_fired": rules_fired,
        "conflicts": conflicts,
    }
