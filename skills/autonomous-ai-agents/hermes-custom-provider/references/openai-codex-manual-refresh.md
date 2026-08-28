# Manual Token Refresh & Raw API Verification

Session-derived reference: 2026-08-25. Verified against two pool entries (one dead, one live).

## When to use this

- The Hermes CLI (`hermes auth add`) is unavailable or you need to test existing pool credentials without going through the full device-code flow.
- You need to identify which entries in a multi-account `openai-codex` credential pool are dead vs live.
- You need to verify that a refreshed token actually works against the Codex Responses API before writing it back to `auth.json`.

## Auth.json structure for openai-codex

The OAuth tokens live in two places in `~/.hermes/auth.json`:

```python
import json
d = json.load(open("/home/ubuntu/.hermes/auth.json"))

# 1. Primary provider tokens (used by the gateway for active sessions)
d["providers"]["openai-codex"]["tokens"]["access_token"]   # JWT
d["providers"]["openai-codex"]["tokens"]["refresh_token"]   # rt.1....
d["providers"]["openai-codex"]["last_refresh"]              # ISO timestamp
d["providers"]["openai-codex"]["auth_mode"]                 # "oauth"

# 2. Credential pool entries (rotated by the gateway on failure)
for entry in d["credential_pool"]["openai-codex"]:
    entry["id"]               # short hash, e.g. "fa8a37"
    entry["label"]            # human name, e.g. "device_code", "account3"
    entry["auth_type"]        # "oauth"
    entry["source"]           # "device_code" or "manual:device_code"
    entry["priority"]        # int, lower = tried first
    entry["access_token"]     # JWT
    entry["refresh_token"]    # rt.1....
    entry["last_status"]      # "dead" / None
    entry["last_error_code"]  # 401 / None
    entry["last_error_reason"]# "token_revoked" / None
    entry["base_url"]         # "https://chatgpt.com/backend-api/codex"
    entry["last_refresh"]     # ISO timestamp
    entry["request_count"]    # int
```

## Decoding the access token JWT

The access token is a JWT. Decode it to check expiry and extract the `client_id` (needed for manual refresh):

```python
import json, base64, time

token = "eyJhbG..."  # the access_token
payload_b64 = token.split(".")[1]
payload_b64 += "=" * (4 - len(payload_b64) % 4)  # fix padding
payload = json.loads(base64.urlsafe_b64decode(payload_b64))

now = int(time.time())
exp = payload.get("exp", 0)
print(f"client_id: {payload.get('client_id')}")
print(f"sub: {payload.get('sub')}")  # account identifier
print(f"Expired: {now > exp} ({(now - exp) if now > exp else (exp - now)}s {'ago' if now > exp else 'remaining'})")
```

The `client_id` in the JWT payload is the OAuth client ID Hermes uses for Codex: `app_EMoamEEZ73f0CkXaXp7hrann`. **Do not guess or try other client IDs** — an earlier attempt with `app_EMoamXZYFn1c5Lm0ORvHx00k` returned `invalid_client`.

## Manual token refresh

```python
import json, urllib.request

CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
refresh_token = "rt.1...."  # from auth.json

data = json.dumps({
    "grant_type": "refresh_token",
    "refresh_token": refresh_token,
    "client_id": CLIENT_ID,
    "redirect_uri": "https://chatgpt.com/backend-api/codex/auth/callback"
}).encode()

req = urllib.request.Request(
    "https://auth.openai.com/oauth/token",
    data=data,
    headers={
        "Content-Type": "application/json",
        "User-Agent": "codex/1.0.0"
    },
    method="POST"
)

resp = urllib.request.urlopen(req, timeout=15)
result = json.loads(resp.read())
# result["access_token"]  — new JWT
# result["refresh_token"] — new refresh token (rotates!)
# result["expires_in"]    — 864000 (~10 days)
```

**Failure modes:**
- `401` + `"refresh_token_invalidated"` → session ended, account revoked. This entry is permanently dead. Remove it.
- `401` + `"Invalid client specified"` → wrong `client_id`. Extract it from the JWT payload instead.

## Codex Responses API — required request shape

The API endpoint is `https://chatgpt.com/backend-api/codex/responses`. Unlike standard OpenAI Chat Completions, this endpoint has strict requirements discovered through iterative 400 errors:

| Parameter | Value | Notes |
|-----------|-------|-------|
| `model` | e.g. `"gpt-5.6-luna"` | Codex-specific model slugs |
| `input` | **Must be a list** of message dicts | `[{role: "user", content: "..."}]` — a plain string returns `400: Input must be a list` |
| `store` | **`false`** (required) | Omitting returns `400: Store must be set to false` |
| `stream` | **`true`** (required) | Omitting returns `400: Stream must be set to true` |
| `max_output_tokens` | **Do not include** | Returns `400: Unsupported parameter: max_output_tokens` |

### Minimal working request

```python
import json, urllib.request

api_data = json.dumps({
    "model": "gpt-5.6-luna",
    "input": [{"role": "user", "content": "Say hello in one word."}],
    "store": False,
    "stream": True
}).encode()

api_req = urllib.request.Request(
    "https://chatgpt.com/backend-api/codex/responses",
    data=api_data,
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
        "User-Agent": "codex/1.0.0",
        "Accept": "text/event-stream"
    },
    method="POST"
)

resp = urllib.request.urlopen(api_req, timeout=60)
raw = resp.read().decode()
```

### Parsing the SSE stream

The response is Server-Sent Events. Extract text from `response.output_text.delta` events:

```python
text_parts = []
for line in raw.split("\n"):
    if line.startswith("data: "):
        data_str = line[6:].strip()
        if data_str and data_str != "[DONE]":
            event = json.loads(data_str)
            if event.get("type") == "response.output_text.delta":
                text_parts.append(event.get("delta", ""))
            elif event.get("type") == "response.created":
                print(f"Model: {event['response']['model']}")
            elif event.get("type") == "response.completed":
                usage = event["response"].get("usage", {})
                print(f"Status: {event['response']['status']}")
                print(f"Tokens: in={usage.get('input_tokens')}, out={usage.get('output_tokens')}")

full_text = "".join(text_parts)
print(f"Response: {full_text}")
```

## Pool cleanup procedure (verified 2026-08-25)

When the user says "re-auth with the working account, delete the dead one":

1. **Inventory** all pool entries (snippet above). Do NOT assume which is dead from labels alone.
2. **Test each entry** by attempting a token refresh (snippet above). `401 refresh_token_invalidated` = dead. Successful refresh = live.
3. **Refresh the live entry's token** and make a test API call (minimal request above). This proves end-to-end functionality.
4. **Write the refreshed tokens back** to `auth.json`:
   - Update `credential_pool.openai-codex[i]` with new `access_token`, `refresh_token`, clear all `last_error_*` fields, set `priority: 1`, set `last_refresh` to now.
   - Update `providers.openai-codex.tokens` with the same new tokens.
   - Update `providers.openai-codex.last_refresh` and `updated_at` at top level.
5. **Remove dead entries** from `credential_pool.openai-codex` (filter out by `id`).
6. **Verify** by reading `auth.json` back and making one more API call using the stored token.

### auth.json field reset checklist for a recovered entry

```python
entry["access_token"] = new_access
entry["refresh_token"] = new_refresh
entry["priority"] = 1
entry["last_status"] = None
entry["last_status_at"] = None
entry["last_error_code"] = None
entry["last_error_reason"] = None
entry["last_error_message"] = None
entry["last_error_reset_at"] = None
entry["last_refresh"] = timestamp
entry["request_count"] = 0
entry["failure_reason"] = None
```

Failing to clear `last_status: "dead"` and the `last_error_*` fields will cause the gateway to skip this entry even after the token is refreshed — it reads the cached failure state.

## Error progression (the 400-series discovery path)

This is the exact sequence of 400 errors encountered when building the request shape from scratch. Each error narrows the required shape:

1. `{"detail": "Input must be a list"}` → wrap input in a list of message dicts
2. `{"detail": "Store must be set to false"}` → add `"store": false`
3. `{"detail": "Stream must be set to true"}` → add `"stream": true`
4. `{"detail": "Unsupported parameter: max_output_tokens"}` → remove `max_output_tokens`

After all four are resolved, the API returns a valid SSE stream. This progression is stable — the same sequence will reproduce if starting from a standard OpenAI Chat Completions payload.
