import os
from datetime import time

from solve import solve, load_rules

_RULES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules.json")


def _to_time(s):
    h, m = str(s).split(":")
    return time(int(h), int(m))


def _to_str(t):
    return f"{t.hour:02d}:{t.minute:02d}"


def _solve(fixed_slots: dict):
    rules = load_rules(_RULES_PATH)["constraints"]
    parsed = {k: _to_time(v) for k, v in fixed_slots.items() if v}
    return solve(rules, parsed)


def consistency_warnings(slot: str, time_str, known_slots: dict) -> list:
    """Check a stated slot time against the deterministic chain.

    Returns a list of human-readable warning strings (empty = consistent).
    Fail-open: callers must treat any exception as 'no warning'.

    Two checks:
      1. PRIMARY: given the OTHER known slots, does the engine derive a
         different time for this slot than the user stated?
      2. DOWNSTREAM: propagating THIS slot forward, does it clash with another
         already-known slot (e.g. B=07 implies C=11 but C is confirmed 12)?
    """
    warnings = []
    if not time_str:
        return warnings
    known = {k: v for k, v in known_slots.items() if v}
    others = {k: v for k, v in known.items() if k != slot}

    det_others = _solve(others).get("slots", {})
    expected = det_others.get(slot)
    # E=20:00 is a pending reminder target, not a validity constraint on an
    # actual user-confirmed intake.
    if slot != "E" and expected and _to_str(expected) != time_str:
        warnings.append(
            f"{slot} time {time_str} contradicts chain (expected {_to_str(expected)})"
        )

    det_from_new = _solve({slot: time_str}).get("slots", {})
    for s, t in det_from_new.items():
        if s != slot and s in known and _to_str(t) != known[s]:
            warnings.append(
                f"chain conflict: {s} shifts from {known[s]} to {_to_str(t)}"
            )
    return warnings
