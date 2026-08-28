# openai-codex OAuth Device Code Flow (Verified 2026-07-28)

**Provider:** Built-in `openai-codex` in Hermes Agent  
**Auth type:** `oauth_external` — delegates to device-code flow against OpenAI auth

## Prerequisites

1. ChatGPT Plus/Pro subscription active on the OpenAI account
2. **"Device code authorization for Codex" MUST be enabled** in ChatGPT Security Settings (`https://chatgpt.com/settings/security`) — toggle ON before starting
3. Hermes v0.17.0+ (tested on v0.17.0)

## Flow (3 Steps)

### Step 1: Request Device Code

```
POST https://auth.openai.com/api/accounts/deviceauth/usercode
Content-Type: application/json
{"client_id": CODEX_OAUTH_CLIENT_ID}
```

Response (200):
```json
{
  "device_auth_id": "deviceauth_...",
  "user_code": "XXXX-XXXXX",
  "interval": "5",
  "expires_at": "2026-07-28T12:46:03+00:00"
}
```

### Step 2: User Authorizes

User opens `https://auth.openai.com/codex/device` in browser, enters `user_code`, logs in with email+password+2FA, approves device access.

**Known pitfall:** If user gets error "Enable device code authorization for Codex in ChatGPT Security Settings" — they need to toggle the setting ON first, then generate a NEW code. The old code is invalid after enabling.

### Step 3: Poll + Exchange

**Poll for authorization code:**
```
POST https://auth.openai.com/api/accounts/deviceauth/token
Content-Type: application/json
{"device_auth_id": "<id>", "user_code": "<code>"}
```
→ Returns `authorization_code` + `code_verifier` when user approves  
→ Status 403/404 = user hasn't completed yet (poll every 5s, max 15 min)

**Exchange for tokens:**
```
POST https://auth.openai.com/oauth/token
Content-Type: application/x-www-form-urlencoded
grant_type=authorization_code
&code=<authorization_code>
&redirect_uri=https://auth.openai.com/deviceauth/callback
&client_id=<CODEX_OAUTH_CLIENT_ID>
&code_verifier=<code_verifier>
```

Response (200):
```json
{
  "access_token": "eyJ...",
  "refresh_token": "...",
  "scope": "openid profile email offline_access",
  "token_type": "Bearer"
}
```

## CLI vs Programmatic

The `hermes auth add openai-codex` CLI command is **interactive** — it uses `input()` prompts and `print()` for output. This fails in headless/non-TTY environments (including the `terminal()` tool).

**Workaround:** Import `CODEX_OAUTH_CLIENT_ID` and `CODEX_OAUTH_TOKEN_URL` from `hermes_cli.auth` and drive the flow manually via `execute_code`. The `_save_codex_tokens()` function writes to `~/.hermes/auth.json`.

```python
import sys
sys.path.insert(0, '/home/ubuntu/.hermes/hermes-agent')
from hermes_cli.auth import CODEX_OAUTH_CLIENT_ID, CODEX_OAUTH_TOKEN_URL, _save_codex_tokens
import httpx

# Step 1: Get device code
resp = httpx.post("https://auth.openai.com/api/accounts/deviceauth/usercode",
    json={"client_id": CODEX_OAUTH_CLIENT_ID})
data = resp.json()
# Forward data['user_code'] and URL to user

# Step 2: User approves in browser

# Step 3: Poll
poll = httpx.post("https://auth.openai.com/api/accounts/deviceauth/token",
    json={"device_auth_id": data['device_auth_id'], "user_code": data['user_code']})
code_resp = poll.json()

# Step 4: Exchange
token_resp = httpx.post(CODEX_OAUTH_TOKEN_URL, data={
    "grant_type": "authorization_code",
    "code": code_resp['authorization_code'],
    "redirect_uri": "https://auth.openai.com/deviceauth/callback",
    "client_id": CODEX_OAUTH_CLIENT_ID,
    "code_verifier": code_resp['code_verifier'],
})
tokens = token_resp.json()
_save_codex_tokens(tokens)
```

## Token Storage

Tokens saved by `_save_codex_tokens()` go to `~/.hermes/auth.json` under `openai-codex` key:
```json
{
  "openai-codex": {
    "access_token": "...",
    "refresh_token": "...",
    "expires_at": "...",
    "source": "device_code"
  }
}
```

Token refresh is automatic — `refresh_codex_oauth_pure()` uses the refresh token against `CODEX_OAUTH_TOKEN_URL`.

## Security Notes

- **Zero credential exposure to VPS** — email, password, 2FA code NEVER touch the VPS. Only the OAuth tokens (access + refresh) are stored.
- Tokens can be revoked anytime from OpenAI account settings
- The `scope` includes `offline_access` — refresh token can obtain new access tokens without re-auth
- If token expires/revoked: `hermes auth add openai-codex` (or re-run manual flow)
