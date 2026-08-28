# Auxiliary Vision Config Pitfalls

## The `base_url` → "custom" provider override trap

**Root cause location:** `agent/auxiliary_client.py`, function `_resolve_task_provider_model()`, line 4850:

```python
if base_url:
    return "custom", resolved_model, base_url, api_key, resolved_api_mode
```

When `base_url` is passed as an explicit argument (even from config), this function ALWAYS returns "custom" as the provider — discarding the actual configured provider (e.g. "opencode-zen", "opencode-go").

### How the cascade happens

```
async_call_llm(task='vision')
  → _resolve_task_provider_model('vision')        # provider=opencode-zen, base_url=False (reads from config FIRST)
  → resolve_vision_provider_client(provider=opencode-zen, base_url=url)
     → _resolve_task_provider_model('vision', provider='opencode-zen', base_url=url)
        → IF base_url is truthy: return "custom", ...  ← OVERRIDE!
  → resolve_provider_client("custom", ..., explicit_base_url=url, explicit_api_key=None)
     → custom_key = (explicit_api_key or "") or OPENAI_API_KEY or "no-key-required"
     → All empty → "no-key-required" placeholder → 401 AuthError
```

### The `api_key: ''` (empty string) trap

Setting `api_key: ''` in config YAML creates a YAML key with empty string value. The code handles this:

```python
cfg_api_key = str(task_config.get("api_key", "")).strip() or None  # → None (correct)
cfg_base_url = str(task_config.get("base_url", "")).strip() or None  # → None (correct)
```

But the EMPTY BASE URL check at line 4850:

```python
if base_url:  # ← this is the ARGUMENT base_url, not cfg_base_url
```

When `async_call_llm` passes `base_url=resolved_base_url or base_url`, and `resolved_base_url` is the config value (empty string = falsy) while `base_url` argument is None, the result is None — so it doesn't trigger. BUT if config has a REAL base_url (like `https://opencode.ai/zen/v1`), it WILL be truthy and trigger the override.

### The safe pattern

For built-in providers (opencode-zen, opencode-go, deepseek, etc.), do NOT set `base_url` in `auxiliary.*` config. The provider's base URL is already defined in `PROVIDER_REGISTRY` (`hermes_cli/auth.py`):

```python
"opencode-zen": ProviderConfig(
    id="opencode-zen",
    inference_base_url="https://opencode.ai/zen/v1",
    api_key_env_vars=("OPENCODE_ZEN_API_KEY",),
    ...
)
```

Removing `base_url` from config means:
1. `_resolve_task_provider_model` returns the original provider (not "custom")
2. The api_key is resolved via `resolve_api_key_provider_credentials` which checks env vars
3. The base_url is resolved from the provider registry

### Minimal working config for auxiliary vision with opencode-zen

```yaml
auxiliary:
  vision:
    provider: opencode-zen
    model: mimo-v2.5-free
    # NO base_url — provider knows its own endpoint
    # NO api_key — resolved from env via PROVIDER_REGISTRY
```

### Verification checklist

When debugging auxiliary vision 401:

1. **Check config** — does `auxiliary.vision` have `base_url`? Remove it for built-in providers.
2. **Check config** — does `auxiliary.vision` have `api_key` with empty string? Remove the line entirely (not set to '').
3. **Check env** — is the provider's env var set? `OPENCODE_ZEN_API_KEY` for opencode-zen.
4. **Check process lifetime** — did gateway restart after config change? `stat` .env mtime vs gateway PID lstart.
5. **Verify resolution** — run Python test:
   ```python
   from agent.auxiliary_client import resolve_vision_provider_client, async_call_llm, extract_content_or_reasoning
   # Test without explicit base_url (simulating clean config)
   p, c, m = resolve_vision_provider_client(async_mode=True)
   print(f'Provider: {p}, Key loaded: {bool(c.api_key)}')
   ```
6. **Bypass Hermes resolution entirely** — test raw API call:
   ```python
   import httpx
   from dotenv import load_dotenv; load_dotenv()
   import os
   resp = httpx.get('https://opencode.ai/zen/v1/models',
       headers={'Authorization': f'Bearer {os.environ["OPENCODE_ZEN_API_KEY"]}'})
   print(f'API health: {resp.status_code}')
   ```

### Resolution chain summary

```
_resolve_task_provider_model(task, provider, model, base_url, api_key)
  │
  ├─ IF explicit api_key + base_url → "custom" endpoint
  ├─ IF explicit base_url → **OVERRIDES to "custom" provider** ← TRAP
  ├─ IF cfg_base_url + cfg_api_key → "custom" endpoint
  ├─ IF cfg_base_url + cfg_provider (!= auto) → use provider (cfg_api_key=None)
  ├─ IF cfg_provider (!= auto) → use provider (cfg_base_url=None, cfg_api_key=None)
  └─ ELSE → "auto" (full auto-detection chain)

resolve_vision_provider_client
  └─ _resolve_task_provider_model resolves config
  └─ IF resolved_base_url is set:
       → provider_for_base_override = requested or "custom"
       → resolve_provider_client(provider_for_base_override, explicit_base_url, explicit_api_key)
  └─ IF requested == "auto":
       → auto-detection chain (main provider → OpenRouter → Nous → stop)
  └─ ELSE:
       → resolve_provider_client(requested_provider, ...)  # falls through PROVIDER_REGISTRY
```

## DeepSeek V4 Flash vision: Responses API ONLY (2026-08-13, live-verified)

DeepSeek V4 Flash (0731) rejects `image_url` blocks in `/chat/completions`
with `400 unknown variant 'image_url', expected 'text'` (Rust serde schema
error). This exact string is what surfaces from the Hermes vision tool too —
**it is a transport problem, NOT a base_url problem**. Vision works ONLY via
the Responses API:

| Endpoint | Image format | Result (live-tested) |
|---|---|---|
| `api.deepseek.com/v1/chat/completions` | `{"type":"image_url",...}` | ❌ 400 unknown variant |
| `api.deepseek.com/v1/responses` | `{"type":"input_image","image_url":...}` | ✅ 200 |

### Two reasons `auto` silently fails for DeepSeek

1. **Vision auto-detect skips DeepSeek**: `auxiliary_client.py`
   (`_main_model_supports_vision` comment) still labels DeepSeek text-only —
   `auto` falls through to OpenRouter/Nous/DeepInfra and never tries the main
   provider.
2. **URL auto-detect does not route DeepSeek to Responses**:
   `hermes_cli/runtime_provider.py::_detect_api_mode_for_url` only knows
   api.x.ai / api.openai.com / anthropic / kimi hosts; `api.deepseek.com`
   defaults to `chat_completions`.

### Working config (explicit provider bypasses both)

```yaml
auxiliary:
  vision:
    provider: deepseek            # bypass text-only catalog skip
    model: deepseek-v4-flash
    api_mode: codex_responses     # force Responses transport
    # base_url/api_key empty — registry resolves https://api.deepseek.com/v1
    # + DEEPSEEK_API_KEY from env
```

Notes:
- `api_mode` is NOT in the official docs auxiliary reference and
  `hermes config set` warns "not a recognized config key" — the warning is
  cosmetic; `_resolve_task_provider_model` reads `task_config.get("api_mode")`
  directly and it works. Verify with a read-only probe:
  `_resolve_task_provider_model('vision')` → expect
  `('deepseek', 'deepseek-v4-flash', None, None, 'codex_responses')`.
- `reasoning_effort: "none"` is a documented per-task knob for vision (cuts
  latency/cost) — optional.
- Config edits: `patch`/`write_file` REFUSE `~/.hermes/config.yaml`
  ("Refusing to write to Hermes config file") — use `hermes config set K V`
  (backup `cp config.yaml config.yaml.pre-<fix>` first).

### Diagnosis recipe (ground truth before touching config)

1. **Which provider is the SESSION actually using?** Check the system prompt
   header (`Model:`/`Provider:` lines) — `config.yaml` `model:` block can
   point elsewhere (e.g. opencode-zen) while the live session runs deepseek.
   Trust the session header; config may be stale or user-switched.
2. **Live-probe DeepSeek directly** (needs `DEEPSEEK_API_KEY` from
   `~/.hermes/.env`): POST `/v1/chat/completions` with an `image_url` block →
   expect 400 unknown variant; POST `/v1/responses` with `input_image` →
   expect 200. That pair alone proves transport requirement without touching
   Hermes.
3. Free-tier gateways (opencode-zen etc.) may return 429 FreeUsageLimitError
   during probes — that means the request was accepted and is rate-limited,
   NOT a format rejection. Do not conclude "no vision" from 429.

## Pitfall: session model ≠ config.yaml `model:` block

The system prompt's `Model:`/`Provider:` lines are authoritative for what the
live session runs. `config.yaml` `model:` may show a different provider
(e.g. `opencode-zen` / `deepseek-v4-flash-free`) because the user switched
models mid-session. Before debugging an auxiliary/model symptom, confirm the
session's declared provider first — do NOT chase the config.yaml provider.
User correction (2026-08-13): chasing config.yaml's opencode-zen while the
session ran deepseek wasted investigation time ("kau dah sesat ni, stop").
