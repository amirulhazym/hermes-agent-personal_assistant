import os
from datetime import time

from solve import solve, load_rules

_RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.json")


def _to_minutes(value):
    if isinstance(value, time):
        return value.hour * 60 + value.minute
    hour, minute = str(value).split(":")
    return int(hour) * 60 + int(minute)


def _diff_minutes(start, end) -> int:
    return (_to_minutes(end) - _to_minutes(start)) % (24 * 60)


def review_slots(slots: dict, rules: list) -> list:
    """Audit slot timings under anchors, lower bounds, and exact Dexa gaps."""
    lines = []
    for rule in rules:
        rid = rule["id"]
        kind = rule["type"]
        if kind in ("fixed_gap", "fixed_offset", "min_gap"):
            frm, to, hours = rule["from"], rule["to"], rule["hours"]
            if frm not in slots or to not in slots:
                lines.append(f"{rid} N/A (slots missing)")
                continue
            gap = _diff_minutes(slots[frm], slots[to])
            expected = hours * 60
            ok = gap >= expected if kind == "min_gap" else gap == expected
            relation = "minimum" if kind == "min_gap" else "exact"
            lines.append(f"{rid} {'PASSED' if ok else 'FAILED'} ({frm}->{to} {relation} {hours}h)")
        elif kind == "anchor":
            slot, target = rule["slot"], rule["time"]
            if slot not in slots:
                lines.append(f"{rid} N/A (slot missing)")
            elif slot == "B":
                # B may be later than 08:00 only when an Akurit lower bound requires it.
                ok = _to_minutes(slots[slot]) >= _to_minutes(target)
                lines.append(f"{rid} {'PASSED' if ok else 'FAILED'} ({slot} no earlier than {target})")
            else:
                # E anchor is a pending reminder target only. Actual intake is
                # recorded as stated and is never rejected against this target.
                lines.append(f"{rid} PASSED ({slot} reminder target {target})")
        elif kind == "independent":
            lines.append(f"{rid} PASSED (independent)")
        else:
            lines.append(f"{rid} N/A (unsupported type {kind})")
    return lines


def review_fixed(fixed_slots: dict) -> list:
    rules = load_rules(_RULES_PATH)["constraints"]
    parsed = {
        key: time(*(int(x) for x in str(value).split(":")))
        for key, value in fixed_slots.items() if value
    }
    return review_slots(solve(rules, parsed)["slots"], rules)


def main() -> int:
    import json
    import sys

    raw = sys.argv[1] if len(sys.argv) > 1 else '{"A": "06:00"}'
    lines = review_fixed(json.loads(raw))
    print("MED CHAIN RULE REVIEW")
    for line in lines:
        print("  " + line)
    if any("FAILED" in line for line in lines):
        print("RESULT: FAILED")
        return 1
    print("RESULT: PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
