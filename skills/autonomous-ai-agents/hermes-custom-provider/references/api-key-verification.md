# API Key Verification Protocol

Systematic validation of an API key before integrating it as a Hermes provider.
Prevents wasting time building a provider plugin around a dead, expired, or wrong-scope key.

## Three-Level Validation

| Level | What | Endpoint | Token cost | Tells you |
|-------|------|----------|------------|-----------|
| L1 | Model list | `GET /v1/models` | 0 | Key exists, is active, not revoked |
| L2 | Chat completion | `POST /v1/chat/completions` | ~10 | Inference credits aren't exhausted |
| L3 | Usage/scope | `GET /v1/usage?date=<today>` | 0 | Key type (project vs org), scope limits |

## Procedure

### 1. Load the key without exposing it

Never ask the user to paste an API key into chat, a transcript, a ticket, or a command line. The user should place it in the provider's secret store (`$HERMES_HOME/.env`, normally `~/.hermes/.env`) and tell the agent only that it is present.

Use a hidden-input shell flow when the owner is operating the VPS directly:

```bash
umask 077
read -r -s -p 'Provider API key: ' KEY
printf '\n'
printf 'PROVIDER_API_KEY=%s\n' "$KEY" >> "$HERMES_HOME/.env"
unset KEY
chmod 600 "$HERMES_HOME/.env"
```

Before testing, check only presence and length/prefix metadata—not the value:

```python
from pathlib import Path
import os

home = Path(os.environ.get('HERMES_HOME', Path.home() / '.hermes'))
key = next(
    (line.split('=', 1)[1] for line in (home / '.env').read_text().splitlines()
     if line.startswith('PROVIDER_API_KEY=')),
    '',
)
print({'present': bool(key), 'length': len(key), 'prefix': key[:8] + '...' if key else ''})
```

Do not rely on redacted tool output to reconstruct a secret. Redaction is evidence that a value was hidden, not a reason to print or copy it elsewhere. For a user-owned secret, the agent may read it inside the process for an HTTP test, but must never print, persist, or return it.

### 2. Three-level test script

Run one bounded script against the provider's real base URL. Load the secret from the process environment or the provider secret scope; never embed it in source, heredoc text, shell history, or output.

```python
import json, os, urllib.error, urllib.request

BASE = os.environ["PROVIDER_BASE_URL"].rstrip("/")
KEY = os.environ["PROVIDER_API_KEY"]
MODEL = os.environ["PROVIDER_MODEL_ID"]
if not KEY:
    raise SystemExit("provider key is missing")

def call(method, path, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(f"{BASE}/{path.lstrip('/')}", data=data, method=method)
    req.add_header("Authorization", f"Bearer {KEY}")
    if data:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = json.loads(resp.read())
            return resp.status, body
    except urllib.error.HTTPError as exc:
        # Do not print the raw body: providers sometimes echo request/key fragments.
        try:
            body = json.loads(exc.read())
        except Exception:
            body = {}
        err = body.get("error") if isinstance(body, dict) else {}
        return exc.code, {"error_type": err.get("type"), "error_code": err.get("code")}

# L1: zero-token model discovery.
status, body = call("GET", "/models")
ids = [x.get("id") for x in body.get("data", []) if isinstance(x, dict)] if status == 200 else []
print({"L1_models": status, "model_count": len(ids), "model_ids": ids})
if status != 200:
    raise SystemExit("L1 failed; do not spend inference tokens")
if MODEL not in ids:
    raise SystemExit(f"configured model is not listed: {MODEL}")

# L2: minimal real inference against the listed model.
status, body = call("POST", "/chat/completions", {
    "model": MODEL,
    "messages": [{"role": "user", "content": "Reply with exactly: ok"}],
    "max_completion_tokens": 10,
})
choice = (body.get("choices") or [{}])[0] if isinstance(body, dict) else {}
print({"L2_chat": status, "response_model": body.get("model") if isinstance(body, dict) else None,
       "finish_reason": choice.get("finish_reason")})

# L3: optional provider-specific usage/scope probe. 404/405 is expected for many proxies.
status, body = call("GET", "/usage")
print({"L3_usage": status, "scope_evidence": "available" if status == 200 else "not_exposed"})
```

For a proxy whose environment is not already loaded, load only the owner-controlled `.env` into the process using the platform's secret manager or an equivalent protected mechanism. Do not add a generic `source .env` step to documentation unless the file format and permissions have been checked.

### 3. Interpret results

| L1 | L2 | L3 | Meaning |
|----|----|----|---------|
| 200 | 200 | 200 | Full access — any model, org-level dashboard |
| 200 | 200 | 200 ∅data | Project-scoped key (`sk-proj-`), no historical usage |
| 200 | 200 | 401 | **Normal for `sk-proj-` keys** — admin/billing endpoints blocked |
| 200 | 4xx | — | Key is live but inference is blocked (quota exhausted, rate-limited, model access restricted) |
| 401 | — | — | **Key is dead** — revoked, expired, or mistyped |
| 429 | — | — | Rate limited — wait and retry |

**`sk-proj-` key fingerprint**: If L1+L2 pass but admin endpoints (`/organizations`, `/me`, `/dashboard/billing/*`) return 401, the key is **project-scoped**. This is the modern OpenAI key format. It can call inference but cannot manage accounts, list API keys, or view billing. This is expected — not a failure.

### 4. Edge cases

- **Expired key**: Returns `401 {"error": {"code": "invalid_api_key", "message": "Incorrect API key provided: ..."}}`. Same error as a typo — no way to distinguish from the API alone.
- **Revoked key**: Same 401 response. The user can check their OpenAI dashboard to confirm.
- **Rate limit**: HTTP 429 with `Retry-After` header. Wait and retry.
- **Model not available**: Even if L1 passes, a specific model may return `404 The model `gpt-5.6-sol` does not exist`. The model list is the source of truth — always check `gpt-5.6-sol in model_ids` before testing.
- **Reasoning model gotcha**: Models like `o1`, `o3`, `gpt-5.6-sol` require `max_completion_tokens` instead of `max_tokens`. Using the wrong param returns `400 Unsupported parameter: 'max_tokens' is not supported with this model`.

## Provider-specific notes

### OpenAI
- Base URL: `https://api.openai.com/v1`
- Key prefix `sk-proj-` = project-scoped (most common for new keys)
- Key prefix `sk-` = org-level (legacy, can access admin endpoints)
- Usage API: `GET /v1/usage?date=YYYY-MM-DD` — returns per-project usage
- No programmatic way to identify the account/org from just the key

### OpenAI-compatible proxies (A6API, OpenRouter, etc.)
- Use the same three-level protocol
- Model list may include models from multiple providers
- Usage API may not exist — expect 404 or 501
- Billing identification impossible via API alone

## Pitfalls

- **Don't truncate the key in the script**: The `...` in tool output is Hermes' secret redaction, not the real key. Write the full raw paste into the heredoc and let the regex clean it.
- **Don't assume 401 means "key is dead" on admin endpoints**: For `sk-proj-` keys, 401 on `/organizations` or `/billing` is expected and normal.
- **Don't skip L2 if L1 passes**: L1 only proves the key format is valid and the key hasn't been deleted. L2 proves inference quotas aren't exhausted.
- **Don't test with a model the user won't use**: Test with the actual target model if feasible, or the cheapest fallback (`gpt-4o-mini` for OpenAI).
