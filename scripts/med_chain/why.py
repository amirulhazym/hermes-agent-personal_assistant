def why(slot, solver_result, rules):
    """Explain why a slot has its computed time.

    Looks up the rule that fired for the slot and builds a human-readable
    chain: Rule -> Because -> Therefore.
    """
    fired = solver_result.get("rules_fired", [])
    slots = solver_result.get("slots", {})
    rule = None
    for rid in fired:
        r = next((c for c in rules if c["id"] == rid), None)
        if r and r.get("to") == slot:
            rule = r
            break
    if rule is None:
        if slot in slots:
            return f"Slot {slot} = {slots[slot]} (user-set / independent, no rule fired)"
        return f"Slot {slot}: untouched (no rule derives it)"
    frm = rule["from"]
    frm_time = slots.get(frm)
    arrow = "fixed_offset" if rule["type"] == "fixed_offset" else "fixed_gap"
    because = f"{frm} shifted to {frm_time}" if frm_time else f"{frm} known"
    return (f"Rule: {arrow} {frm}→{slot} / "
            f"Because: {because} / "
            f"Therefore: {slot} = {slots[slot]}")
