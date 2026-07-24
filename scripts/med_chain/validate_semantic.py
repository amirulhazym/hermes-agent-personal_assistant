def validate(llm_slots: dict, solver_result: dict):
    """Compare parsed LLM slot times against solver truth.

    Returns (ok: bool, messages: list[str]). A slot the LLM asserts must match
    the solver's computed time; otherwise it is a factual mismatch (likely the
    old auto-linearization bug).
    """
    messages = []
    solver_slots = solver_result.get("slots", {})
    for slot, t in llm_slots.items():
        if slot in solver_slots:
            if solver_slots[slot] != t:
                messages.append(
                    f"{slot}: LLM={t} but solver={solver_slots[slot]} (mismatch)"
                )
        else:
            messages.append(
                f"{slot}: LLM asserted {t} but solver leaves it untouched/unknown"
            )
    return (len(messages) == 0, messages)
