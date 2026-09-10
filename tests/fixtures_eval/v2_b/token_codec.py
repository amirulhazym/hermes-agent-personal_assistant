# Token Codec
def encode_session_token(user_id, timestamp):
    # Target function in isolation expects ISO string
    if not isinstance(timestamp, str):
        raise TypeError(f"Contract violation: timestamp must be ISO string, got {type(timestamp).__name__}")
    return f"token_{user_id}_{timestamp}"
