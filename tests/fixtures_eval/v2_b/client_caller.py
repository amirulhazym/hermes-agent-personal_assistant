# Client Caller
from .token_codec import encode_session_token

def initiate_session(user_id):
    # Caller passes integer timestamp instead of ISO string
    token = encode_session_token(user_id, timestamp=1789041200)
    return token
