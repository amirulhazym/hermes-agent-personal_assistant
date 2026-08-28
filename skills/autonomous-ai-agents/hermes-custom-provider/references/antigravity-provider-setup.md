# Antigravity Provider Setup (jaeyeopme/antigravity-provider)

Google AI Pro / Antigravity subscription usage in Hermes Agent via the
jaeyeopme/antigravity-provider community plugin. This is an **OAuth-based
in-process provider** — not an OpenAI-compatible gateway, not a config-only
provider. It calls Google's Cloud Code Assist API directly with OAuth tokens.

## Account Risk

> ⚠️ This is an unofficial integration. It uses Antigravity access from outside
> Google's documented client surface. The Google account may be restricted,
> suspended, or lose access. Use a disposable/separate account if possible.

## Components

| Component | Path | Purpose |
|-----------|------|---------|
| agy CLI binary | `~/.local/bin/agy` | Official Google Antigravity CLI (v1.1.20+). Not used for inference, but useful for keychain auth on macOS. |
| Plugin (standalone) | `~/.hermes/plugins/antigravity-provider/` | Main plugin: OAuth, API client, request transform, `hermes agy` CLI commands. `kind: standalone`. |
| Model-provider profile | `~/.hermes/plugins/model-providers/antigravity/` | Tiny profile that registers the provider in Hermes's model picker. `kind: model-provider`. |
| OAuth credentials | `~/.hermes/.antigravity_oauth.json` | access_token, refresh_token, expires_at, email, project_id. |
| Config entry | `config.yaml → model.provider: antigravity` | Sets antigravity as default provider. |
| Config providers entry | `config.yaml → providers.antigravity` | Declares base_url, key_env, default_model, and model catalog for CLI resolver. |
| Plugin enable | `config.yaml → plugins.enabled: [antigravity-provider, model-providers/antigravity]` | BOTH entries required. |

## Installation

```bash
# 1. Install agy CLI (official Google installer)
curl -fsSL https://antigravity.google/cli/install.sh | bash

# 2. Install plugin
hermes plugins install jaeyeopme/antigravity-provider --enable

# 3. Login (OAuth)
hermes agy login --no-keychain

# 4. Set as default model (short ID supported)
hermes agy select gemini-3.7-flash
```

## OAuth Login from Phone (No SSH Tunnel)

When the user can only access via phone (no SSH tunnel to VPS), use manual
code exchange:

1. Generate PKCE pair + auth URL, save verifier to `/tmp/agy_oauth_session.json`.
2. User opens auth URL in phone browser → logs in → grants permission.
3. Google redirects to `http://127.0.0.1:51121/oauth-callback?code=XXX&state=XXX`.
4. Page won't load (127.0.0.1 = phone localhost, not VPS) — **this is expected**.
5. User copies the full URL from browser address bar.
6. Agent parses `code` from the URL, exchanges it for tokens using the saved
   PKCE verifier.
7. Agent fetches user email + onboards Cloud Code Assist project.
8. Agent saves credentials to `~/.hermes/.antigravity_oauth.json`.

### Code Exchange Implementation

```python
import json, sys, urllib.parse
sys.path.insert(0, '/home/ubuntu/.hermes/plugins/antigravity-provider/src')
from antigravity_provider.oauth import exchange_code_for_tokens, fetch_user_email
from antigravity_provider.cloudcode import load_or_onboard_project
from antigravity_provider.credentials import CredentialStore

# Load saved PKCE session
with open('/tmp/agy_oauth_session.json') as f:
    session = json.load(f)

# Parse redirect URL from user
parsed = urllib.parse.urlparse(redirect_url)
code = urllib.parse.parse_qs(parsed.query)['code'][0]

# Exchange
creds = exchange_code_for_tokens(code, code_verifier=session['verifier'],
                                   redirect_uri=session['redirect_uri'])
creds['email'] = fetch_user_email(creds['access_token'])
creds['project_id'] = load_or_onboard_project(creds['access_token'])

# Save
CredentialStore.default().save(creds)
```

### Auth Code Expiry

Google OAuth authorization codes expire in ~10 minutes. If the user was AFK
between URL generation and login, generate a fresh PKCE pair + URL. The
refresh_token (once obtained) does not expire unless explicitly revoked.

## Dynamic Model Catalog & Short Model IDs

Do NOT rely on static hardcoded lists. The plugin queries Antigravity's live
`POST https://cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels`
catalog and normalizes wire variant names into clean, short model IDs.

### Standard Short IDs (tested & active):
- `gemini-3.7-flash` (routes to wire ID `gemini-3.7-flash-tiered`)
- `gemini-3.6-flash` (routes to wire ID `gemini-3.6-flash-tiered`)
- `gemini-3.1-pro` (routes to wire ID `gemini-3.1-pro-low` / `gemini-pro-agent`)
- `gemini-3.5-flash`
- `claude-sonnet-4-6`
- `claude-opus-4-6`
- `gpt-oss-120b`

### Why Short IDs Matter for Messaging (WhatsApp / Telegram / CLI)
Prefixed IDs like `google-antigravity/gemini-3.7-flash` are tedious and error-prone
to type manually in messaging interfaces like WhatsApp. The plugin supports short
names directly:
- `/model gemini-3.7-flash`
- `hermes agy select gemini-3.7-flash`

### Wire ID vs Public ID Trap
Sending raw `gemini-3.7-flash` directly to the Cloud Code Assist API returns
`HTTP 404 NOT_FOUND`. The endpoint expects tiered wire names such as
`gemini-3.7-flash-tiered`. Always verify wire mappings when onboarding new model releases.

## API Quirks

- API endpoint: `https://daily-cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse`
- Auth: `Authorization: Bearer <access_token>` (Google OAuth, not API key)
- User-Agent must be `antigravity/hub/<version> <os>/<arch>` — the plugin builds this.
- Project onboarding required: `load_or_onboard_project()` calls Cloud Code Assist
  `loadCodeAssist` + `onboardUser` to get a `project_id`.
- Token refresh: `refresh_access_token()` via `oauth2.googleapis.com/token` with
  client_id + client_secret (hardcoded in plugin's `oauth.py`).

## Plugin Architecture

```
Hermes chat request
  → Plugin middleware intercepts requests to 127.0.0.1:8765/v1
  → transform.build_generate_content_request(): OpenAI → Gemini format (maps short ID to wire ID)
  → AntigravityClient.stream_generate(): calls Cloud Code Assist API
  → openai_compat.to_openai_completion(): Gemini → OpenAI format
  → Hermes receives standard chat completion
```

The plugin registers as middleware via `antigravity_llm_execution()` in
`hermes_plugin.py`. It checks if the request targets the `antigravity` provider;
if yes, it transforms and routes to Cloud Code Assist. Non-antigravity requests
pass through unchanged.

## Model-Picker & CLI Resolver Visibility (Two-Layer Requirement)

1. **Model Provider Profile**: `~/.hermes/plugins/model-providers/antigravity/__init__.py`
   registers `ProviderProfile` in `CANONICAL_PROVIDERS`.
2. **Config Providers Entry**: `providers.antigravity` in `config.yaml` must be present
   with `base_url: http://127.0.0.1:8765/v1`, `key_env: ANTIGRAVITY_HERMES_API_KEY`,
   `default_model`, and `models` list so that `resolve_provider_full()` in CLI/gateway
   resolves it cleanly without "Unknown provider".

## Commands

```bash
hermes agy status                    # Check credential state
hermes agy quota                     # Check live account quota & reset times
hermes agy login --no-keychain       # Browser OAuth (force, skip keychain)
hermes agy select [model-id]         # Set default model (e.g. gemini-3.7-flash)
hermes agy logout                    # Remove saved OAuth credentials
hermes model --refresh               # Refresh live model picker cache
```

## Re-login (Token Expired)

Access tokens expire in ~1 hour but auto-refresh via refresh_token. If
refresh_token is revoked or login session ends:

1. `hermes agy login --no-keychain`
2. Opens browser OAuth → user logs in → redirect to 127.0.0.1:51121
3. From VPS (SSH): `ssh -L 51121:127.0.0.1:51121 user@vps`
4. From phone: use manual code exchange (see above)

## Quota Tracking & Account Usage

Contrary to older assumptions, Antigravity **does expose live remaining quota and reset timestamps** via the `POST /v1internal:fetchAvailableModels` endpoint.

Each model entry in the returned payload carries a `quotaInfo` object:
```json
"quotaInfo": {
  "remainingFraction": 0.9433,
  "resetTime": "2026-08-25T11:43:18Z"
}
```

- `remainingFraction`: Float fraction of remaining quota (e.g. `0.9433` = 94.3% remaining / 5.7% used).
- `resetTime`: ISO 8601 UTC timestamp when the quota resets.

### Integration with Hermes `/usage`
Hermes uses `AccountUsageSnapshot` from `agent/account_usage.py` to display account-level rate limits and quota in messaging platforms (Telegram/WhatsApp) and CLI.

#### Pitfall: Stale `billing_provider` in Session DB after `/restart`
When `/usage` is run between turns (e.g. immediately after `/restart`), the gateway handler may look up `billing_provider` from the SQLite session database (`sessions` table). If the session was created under a previous provider (e.g. `openai-codex`) before switching to `antigravity`, `/usage` would query the old provider's quota instead of Antigravity unless:
1. `_handle_model_command` persists the new billing route via `update_session_billing_route()`.
2. `_handle_usage_command` falls back to `_session_model_overrides` and `config.yaml` `model.provider` when no live agent is resident.
3. The session DB row is updated.

When integrated into `fetch_account_usage()`, typing `/usage` in WhatsApp/Telegram natively renders:
```text
📈 **Antigravity Quota**
Provider: antigravity (Google AI Pro (Subscription))
gemini-3.7-flash: 94% remaining (6% used) • resets in 3h 10m (2026-08-25 19:43 +08)
gemini-3.1-pro: 94% remaining (6% used) • resets in 3h 10m (2026-08-25 19:43 +08)
claude-sonnet-4-6: 100% remaining (0% used) • resets in 4h 59m (2026-08-25 21:32 +08)
```

## Limitations

- **Auxiliary Task Incompatibility (`auxiliary.<task>.provider: antigravity` FAILS)**: `antigravity-provider` is an in-process middleware plugin that intercepts main conversation LLM calls via `llm_execution`. Background auxiliary tasks (`goal_judge`, `compression`, `title_generation`, `curator`, `vision`) are handled by `auxiliary_client.py`, which makes direct HTTP requests to `base_url` (`127.0.0.1:8765/v1`) rather than passing through `llm_execution` middleware. Setting `auxiliary.<task>.provider: antigravity` results in `httpcore.ConnectError: [Errno 111] Connection refused` and causes goal judge loops or aux failures. Always route `auxiliary.*` tasks to native HTTP OpenAI-compatible providers with valid API keys (e.g. `a6api`, `openrouter`) or leave as `auto`.
- **No streaming to Hermes**: Plugin collects all chunks then returns complete
  response (non-streaming from Hermes's perspective, despite SSE from API).
- **Thinking Budget**: Gemini models require sufficient `max_tokens` (e.g. 2048+)
  when reasoning is enabled to avoid `finish_reason=length` with empty content.
- **Gateway restart required** after config/plugin code changes — cannot restart from
  within an active agent session.
