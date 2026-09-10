# Config Resolver
import json
from pathlib import Path

def resolve_route(req):
    policy_file = Path(__file__).parent / "auth_policy.json"
    with open(policy_file) as f:
        policy = json.load(f)
    if policy.get("enforce_strict_mtls"):
        return {"error": "AUTH_CERT_REJECTED", "reason": "Client certificate missing in strict mTLS mode"}
    return {"route": "/api/v1/stream"}
