PRIORITY = {
    "doctor_prescription": 100,
    "medical_safety": 95,
    "user_request": 60,
    "preference": 20,
}


def resolve(user_value, rule_priority: int, user_source: str = "user_request"):
    """Return ('rule'|'user', explanation)."""
    user_priority = PRIORITY.get(user_source, 60)
    if rule_priority > user_priority:
        return ("rule", f"Medical wins. Keeps computed value, not user {user_value}.")
    return ("user", f"User {user_value} accepted over rule priority {rule_priority}.")
