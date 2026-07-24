def route(intent: dict) -> str:
    """Low complexity -> 'send'; high (multi-change or conflicts) -> 'review'."""
    conflicts = intent.get("conflicts") or []
    slot_changes = intent.get("slot_changes", 0)
    if conflicts or slot_changes > 1:
        return "review"
    return "send"
