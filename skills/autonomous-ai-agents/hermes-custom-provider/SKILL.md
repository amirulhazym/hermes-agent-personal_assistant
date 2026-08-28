---
name: hermes-custom-provider
description: "Set up custom LLM providers (OpenAI-compatible gateways like A6API and OpenRouter alternatives) in Hermes Agent. Covers plugin creation, config.yaml providers section, slash command visibility, and the dual-registration requirement."
version: 1.1.0
---

# Hermes Custom Provider Setup

## Route Selection: Config-Only First, Plugin Only When Needed

Do not assume every OpenAI-compatible endpoint needs a provider plugin or dual registration.

**For a plain OpenAI-compatible gateway, try the keyed `providers.<slug>` config path first.** In the live Hermes v0.20.0 source, `hermes_cli.config._normalize_custom_provider_entry()` / `get_compatible_custom_providers()` normalize the entry, and `hermes_cli.providers.resolve_provider_full()` resolves it to an `openai_chat` `ProviderDef`. This was live-tested for an APIMaster-style endpoint with the following raw result:

```text
RESOLVED= id=apimaster transport=openai_chat base_url=https://apimaster.ai/v1 api_key_env_vars=('APIMASTER_API_KEY',) source=user-config
```

Use a plugin only when the provider needs custom transport, authentication, request/response transformation, model metadata, or behavior that config cannot express. The old “plugin + `providers:` is always mandatory” rule applies to plugin-backed provider profiles, not to every new OpenAI-compatible URL.

### Current config-only shape

```yaml
providers:
  <slug>:
    name: "<Display Name>"
    base_url: "https://provider.example/v1"
    key_env: "<ENV_VAR>"
    default_model: "<model-id>"
    discover_models: true
```

`api_key_env` is accepted as a compatibility alias, but `key_env` is the canonical field in the current normalizer. Keep the key value in `.env`; never put it in `config.yaml` or a chat transcript.

**LIVE-VERIFIED PITFALL (2026-08-20): the `api_key_env` alias does NOT populate `api_key_env_vars` in `resolve_provider_full()`.** With `api_key_env: X` set, the resolver returns `api_key_env_vars=()`; switching the same provider to `key_env: X` flips it to `('X',)`. Any path that discovers keys through the resolver (e.g. `/model` picker discovery) can silently miss the credential when the alias is used. Always use `key_env`.

### Separate configuration, activation, and behavior evidence

- `hermes config set` proves only **CONFIGURED ON DISK**.
- A fresh process/config resolver proves **RESOLUTION**.
- `GET /v1/models` with the real key proves **KEY + MODEL DISCOVERY**.
- A minimal `POST /chat/completions` with an actually listed model proves **INFERENCE**.
- The running gateway must be restarted/reloaded separately before claiming **LIVE ACTIVATION**.

A provider setup is not complete if any of these boundaries is silently skipped. If a messaging session is active, defer the gateway restart until a safe window or explicit user approval; report the provider as configured-on-disk but not live.

## Why This Happens

The slash command handler (`gateway/slash_commands.py:1131-1142`) uses `resolve_provider_full()` from `hermes_cli/providers.py:664`. This function checks:

1. `user_providers` (from `providers:` in config.yaml) -- raw name FIRST
2. Built-in via `get_provider()` (CANONICAL_PROVIDERS + models.dev)
3. `user_providers` again with canonical name
4. Custom providers from `custom_providers:` config

The plugin's `providers.register_provider()` populates `_REGISTRY` and `CANONICAL_PROVIDERS` (step 2), but `resolve_provider_full()` checks `user_providers` FIRST (step 1). The gateway slash command uses `cfg.get("providers")` as `user_providers` -- an empty dict means `resolve_provider_full` skips the user-provider path entirely and only finds it via CANONICAL_PROVIDERS if discovery has run.

## Phase 0: Verify the API Key First

**DON'T** start building a provider plugin until the key is confirmed working. A dead or wrong-scope key will fail silently at step 4 (Live API) and waste time debugging the setup.

Run the systematic verification protocol before touching plugin files:

```bash
cat << 'VERIFYEOF' | python3
import urllib.request, urllib.error, json, datetime, re

# 1. Paste the RAW key as provided (newlines and all — the regex cleans it)
RAW = """sk-...paste the key exactly as the user gave it, messy lines included"""

KEY = re.sub(r'\s+', '', RAW)
print(f"Key length: {len(KEY)}  prefix: {KEY[:15]}...  suffix: ...{KEY[-8:]}")

BASE = "https://api.openai.com/v1"  # or the target provider's base

def call(method, url, data=None):
    r = urllib.request.Request(url, data=data, method=method)
    r.add_header("Authorization", f"Bearer {KEY}")
    if data: r.add_header("Content-Type", "application/json")
    try:
        resp = urllib.request.urlopen(r, timeout=20)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try: return e.code, json.loads(body)
        except: return e.code, body

# Level 1: Model list (cheapest — no tokens burned)
s, d = call("GET", f"{BASE}/models")
print(f"Level 1 (models list): HTTP {s} -> {'PASS' if s == 200 else 'FAIL'}")

# Level 2: Real chat completion (proves inference works)
payload = json.dumps({
    "model": "gpt-4o-mini",  # cheapest fallback
    "messages": [{"role": "user", "content": "Reply: ok"}],
    "max_tokens": 10
}).encode()
s, d = call("POST", f"{BASE}/chat/completions", payload)
print(f"Level 2 (inference): HTTP {s} -> {'PASS' if s == 200 else 'FAIL'}")

# Level 3: Usage/scope check (distinguishes project-key from admin-key)
today = datetime.date.today().strftime("%Y-%m-%d")
s, d = call("GET", f"{BASE}/usage?date={today}")
print(f"Level 3 (usage): HTTP {s} -> {'PASS if usage data visible' if s == 200 else f'FAIL — scope limited ({json.dumps(d, indent=2)[:100]})'}")
VERIFYEOF
```

Three levels tell you: (L1) key exists and is active, (L2) inference credits aren't exhausted, (L3) whether it's a project-scoped (`sk-proj-` — admin/billing endpoints return 401) or org-level key.

See `references/api-key-verification.md` for edge cases (rate limits, expired keys, key type fingerprinting, OpenAI secret-redaction awareness).

## ChatGPT Plus Subscription via Built-in OAuth

For a ChatGPT Plus/Pro subscription without an OpenAI API key, use the built-in `openai-codex` provider and its device-code OAuth flow. This is **not** a custom provider and does not require plugin + `providers:` dual registration.

Required workflow:

1. Run `hermes auth add openai-codex`.
2. If the device page reports that device-code authorization must be enabled, enable **device code authorization for Codex** in ChatGPT Security Settings and request a fresh code. Never reuse the failed/expired code.
3. Authenticate at `https://auth.openai.com/codex/device`.
4. Verify `hermes auth list` shows an `openai-codex` OAuth credential.
5. Fetch the account's live Codex model catalog before claiming model availability. A static model list is only fallback evidence.
6. Run one minimal inference per required model; avoid multi-turn/tool/stress tests until the user approves them because subscription limits apply.
7. Verify both `/model` discovery functions (`list_picker_providers` and `list_authenticated_providers`) without consuming generation tokens.
8. After config changes, restart the gateway and separately verify PID replacement, bridge/readiness, provider config loading, and actual user-visible `/model` delivery.

Use the complete endpoint/polling sequence and evidence boundaries in `references/chatgpt-plus-codex-oauth.md`.

### Multi-Account ChatGPT Plus Pool (Weekly Limit Rotation)

Multiple ChatGPT Plus accounts can share the `openai-codex` provider — Hermes rotates between them **automatically** when one hits its weekly usage cap. No hacks, no wrapper scripts.

- `hermes auth add openai-codex --label <name>` creates a **distinct pool entry per account** (source `manual:device_code`). A second login does NOT overwrite the first — the old #39236 overwrite bug is fixed (`hermes_cli/auth_commands.py` ~line 310, `pool.add_entry()`).
- Automatic rotation: `429 "usage limit reached"` (ChatGPT/Codex weekly limit) → rotate to next account immediately (no retry — the cap won't clear on retry). Cooldown TTL defaults: 401 = 5 min, 429/402 = 1 h — BUT when the error body carries a reset timestamp (ChatGPT weekly-limit errors do), the pool stores `last_error_reset_at` and sleeps until that ABSOLUTE time, no hourly probing (verified: maxed account slept until 13:25:53 next day). 402 billing → rotate immediately. 401 → OAuth refresh, rotate on failure.
- Strategy via `credential_pool_strategies:` in config.yaml: `fill_first` (default), `round_robin`, `least_used`, `random`.
- All accounts exhausted → `fallback_providers:` (cross-provider layer) activates.
- The device flow is headless-friendly: prints URL + code, then **auto-polls** (no input() prompt). Run `terminal(background=true, pty=true, notify_on_complete=true)` and relay the code to the user — the process completes itself on approval.
- Per-account prerequisite: "Device code authorization for Codex" ON in ChatGPT Security Settings before each login.

Full mechanism evidence, recipe, and caveats: `references/openai-codex-multi-account-pool.md`.

## Canonical Provider Collision and Model-Picker Discovery

Before adding a custom OpenAI-compatible provider, inspect Hermes's canonical provider registry and aliases. A provider key that looks natural (for example, `openai`) may already be an alias or may coexist with a built-in provider such as `openai-api`. Adding a custom block under a colliding key can produce duplicate picker rows and bypass the built-in discovery/filter path.

Required checks:

1. Inspect canonical aliases and provider profiles (`normalize_provider`, `get_provider_profile`, `resolve_provider_full`).
2. Run the actual picker functions (`list_picker_providers` and/or `list_authenticated_providers`) rather than trusting config appearance.
3. Compare model counts and IDs per provider. A raw OpenAI `/v1/models` response is heterogeneous and can contain embeddings, image, audio, TTS, moderation, and realtime products that are not valid Hermes agent models.
4. Prefer the built-in `openai-api` path for the real OpenAI API when it exists; reserve `providers.<name>` for genuinely custom OpenAI-compatible endpoints.
5. If discovery code changes, clear only the affected provider cache with `clear_provider_models_cache("openai-api")`, then re-run the picker in a fresh process. A stale `provider_models_cache.json` entry can make a correct discovery fix appear ineffective.
6. Separate live availability from agent compatibility: use the provider's live model endpoint as the availability source, intersect it with a dynamic capability catalog where available, and retain a safe curated fallback for offline/catalog failure.

Do not claim the picker is fixed until the fresh provider rows, duplicate-slug check, cache state, and model list have been captured. See `references/provider-picker-discovery.md` for the OpenAI collision reproduction and evidence pattern.

## Complete Setup Procedure

### 1. Create Plugin Directory

```bash
mkdir -p ~/.hermes/plugins/model-providers/<provider-name>/
```

### 2. Create `plugin.yaml`

```yaml
name: <provider-name>-provider
kind: model-provider
version: "1.0"
description: <description>
author: <your-name>
```

### 3. Create `__init__.py`

```python
"""Provider profile for <Provider Name>."""

from providers import register_provider
from providers.base import ProviderProfile

profile = ProviderProfile(
    name="<provider-name>",           # slug used in --provider flag
    aliases=("<alias1>",),            # optional alternative names
    display_name="<Display Name>",
    description="<description>",
    signup_url="<url>",
    env_vars=("<ENV_VAR>",),          # env var holding API key
    base_url="<base-url>",            # e.g. https://api.example.com/v1
    auth_type="api_key",              # or oauth_device_code, etc.
    default_aux_model="<model>",      # for compression/vision/etc.
    fallback_models=(                 # models available by default
        "<model1>",
        "<model2>",
    ),
)

register_provider(profile)
```

### 4. Add `providers:` Section to config.yaml

```bash
hermes config set providers.<name>.name "<Display Name>"
hermes config set providers.<name>.base_url "<base-url>"
hermes config set providers.<name>.key_env "<ENV_VAR>"
hermes config set providers.<name>.default_model "<model>"
```

Or manually in `~/.hermes/config.yaml`:

```yaml
providers:
  <name>:
    name: "<Display Name>"
    base_url: "<base-url>"
    key_env: "<ENV_VAR>"
    default_model: "<model>"
```

### 5. Set Default Provider + Base URL

```bash
hermes config set model.provider <name>
hermes config set model.base_url "<base-url>"
```

### 6. Restart Gateway

Use `clean-restart-gateway` skill. Do NOT ask user to restart manually.

### 7. Verify

After restart, verify in this order:

1. Plugin discovery: run `from providers import get_provider_profile; print(get_provider_profile('<name>'))` from hermes-agent directory. Should return ProviderProfile, not None.
2. Config: `grep "^model:" -A 5 ~/.hermes/config.yaml` -- provider should be `<name>`, base_url should match.
3. Resolution chain: simulate `resolve_provider_full('<name>', user_providers, None)` with the actual config providers dict.
4. Live API: `curl` to provider's `/chat/completions` endpoint with valid model.
5. Slash command: user tests `/model <valid-model> --provider <name>` in WhatsApp/Telegram.

## Pitfalls

- **Cloudflare-fronted providers return HTTP 403 "error code: 1010" to plain urllib** (default `Python-urllib` User-Agent). Retry the same call with a browser User-Agent header (e.g. Firefox UA) — observed a6api.com flipping 403 → 200 with 73 models. Hermes's own fetches are unaffected; this only bites ad-hoc curl/python probes.
- **Never claim "all providers" from a single source.** When the user asks to test/verify "semua" providers, enumerate every credential source first: config.yaml `providers:`, `auth.json` `credential_pool` (per-provider LIST of entry dicts — fields `active`, `label`, `base_url`, `access_token` for manual keys, `secret_fingerprint` for env-referenced keys), `auth.json` `providers.<name>.tokens` (OAuth), `.env` `*_API_KEY` vars, and plugin profiles under `~/.hermes/plugins/model-providers/` (plugin providers may NOT resolve via `resolve_provider_full` — e.g. a6api-gateway resolved `NONE` but its pool entry carries `base_url`). Presenting a config-only subset as "all" triggered an explicit user correction. Recipe: `references/all-provider-verification.md`; runnable probe: `scripts/zero-token-provider-probe.py`.
- **Zero-token verification preferred for provider API tests**: `GET {base}/v1/models` proves key + connectivity without burning tokens, so model selection is irrelevant. Only fall back to a tiny `max_tokens` completion when the models endpoint is unsupported. NOTE: the `openai-codex` Responses API (`/backend-api/codex/responses`) does NOT support `GET /models` or `max_output_tokens` — its required request shape differs from standard OpenAI Chat Completions. See `references/openai-codex-manual-refresh.md` for the exact format (`store=false`, `stream=true`, `input` as list).

- **Dotted model names in config**: `hermes config set model.models.gpt-5.6-sol.context_length 1050000` is SAFE -- the YAML parser treats dotted keys as string keys in the `models:` dict, NOT nested YAML keys. No corruption risk for model IDs.
- **Plugin imports**: Use `from providers import register_provider` and `from providers.base import ProviderProfile`. These are the correct paths. Do NOT import from `hermes_cli`.
- **Config not hot-reloaded**: `hermes config set` writes immediately to disk but the GATEWAY reads config at startup only. You MUST restart gateway after config changes.
- **Session overrides & stale SessionDB**: If user still gets "Unknown provider" or old provider usage in `/usage` after fix, check for stale session model overrides (`_session_model_overrides` in gateway) and check the `billing_provider` column in SQLite `sessions` table. `/usage` between turns falls back to `billing_provider` from SQLite if no agent is resident unless gateway fallback ladder includes config and session overrides. A `/reset` (new session) clears session overrides.
- **hermes model is interactive-only**: Cannot run `hermes model` via terminal/pipes. Use Python-level APIs to verify registration instead.
- **Gateway restart drains**: Set `agent.restart_drain_timeout: 0` in config.yaml BEFORE restart. Without this, the drain blocks 180s.
- **API key in .env, not config.yaml**: The `api_key_env` field references an env var name, not the key value itself. Set the actual key in `~/.hermes/.env`.
- **`openai-codex` is BUILT-IN, not custom**: If the user wants to use ChatGPT Plus subscription, `openai-codex` is a built-in OAuth provider (`hermes auth add openai-codex`) — it does NOT need the plugin + config dual registration. The custom-provider flow in this skill is for third-party OpenAI-compatible endpoints. If `openai-codex` has unresolved bugs (see `evidence-first-feasibility-assessment` → `references/openai-codex-known-bugs.md`), a custom provider alternative is **CatGPT-Gateway** — browser automation that exposes ChatGPT as an OpenAI-compatible Chat Completions API. See `references/catgpt-gateway-setup.md`.

## Reference Files

| File | Covers |
|------|--------|
| `references/a6api-setup.md` | Complete A6API provider setup (plugin + config + verification) |
| `references/antigravity-provider-setup.md` | Antigravity (Google AI Pro OAuth in-process plugin), live `fetchAvailableModels` catalog, wire-to-short model ID routing (`gemini-3.7-flash`), and WhatsApp-friendly short IDs |
| `references/api-key-verification.md` | Systematic protocol to validate any API key before building a provider around it |
| `references/chatgpt-plus-codex-oauth.md` | ChatGPT Plus/Pro subscription OAuth device-code flow, live Codex catalog discovery, token-conservative verification, `/model` evidence boundaries |
| `references/provider-picker-discovery.md` | Canonical-provider collision, raw `/v1/models` noise, cache invalidation, and evidence-first picker verification |
| `references/catgpt-gateway-setup.md` | CatGPT-Gateway: browser-automation custom provider for ChatGPT/Claude subscriptions — alternative when built-in `openai-codex` OAuth provider has unresolved bugs |
| `references/openai-codex-multi-account-pool.md` | Multi-account ChatGPT Plus pool: rotation, cooldown TTLs, strategies, `hermes auth add --label`, headless device flow |
| `references/openai-codex-manual-refresh.md` | Manual token refresh + raw Codex Responses API verification (client_id, JWT decode, 400-error progression, auth.json write-back, pool cleanup procedure) |
| `references/all-provider-verification.md` | Enumerate every credential source + zero-token `/v1/models` probe recipe (config, pool, OAuth, env, plugins) |
| `scripts/zero-token-provider-probe.py` | Runnable one-call-per-provider zero-token probe across config.yaml + auth.json + .env |
| `scripts/verify-codex-pool.py` | Runnable pool verification: decodes each JWT, refreshes tokens, makes a minimal API call, optionally writes live tokens back to auth.json |
