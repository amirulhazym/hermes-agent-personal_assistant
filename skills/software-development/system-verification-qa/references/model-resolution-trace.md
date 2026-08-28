# Gateway Model Resolution — Full Code Trace

Session: 2026-07-01 — Answering "model sync /new /reset behaviour after VPS migration"

## The Question

User noticed after VPS migration:
1. `/model` changes don't auto-sync between Telegram and WhatsApp
2. `/new` vs `/reset` seemed to behave differently (but they're aliases)
3. Default model reverted to `mimo-v2.5-free` after `/reset`

## Resolution Chain

### Step 1: `/model` command → `gateway/slash_commands.py`

Handler: `_handle_model_command()` at line 1032.

The flow:
1. `parse_model_flags(raw_args)` parses `--session`, `--global`, `--provider`, `--refresh` flags
2. `resolve_persist_behavior(is_global, is_session)` decides whether to write to config:
   - `--session` → False (session-only)
   - `--global` → True (explicit persist)
   - Neither → checks `config.yaml.model.persist_switch_by_default` (defaults to `True`)

3. `_switch_model()` resolves the model + provider + api_key + base_url + api_mode

4. `_finish_switch()`:
   ```
   self._session_model_overrides[session_key] = {
       "model": result.new_model,
       "provider": result.target_provider,
       "api_key": result.api_key,
       "base_url": result.base_url,
       "api_mode": result.api_mode,
   }
   ```
   This writes to `config.yaml` if `persist_global is True`:
   ```python
   model_cfg["default"] = result.new_model
   model_cfg["provider"] = result.target_provider
   ```

Key point: `/model` sets BOTH session override AND config.yaml by default.

### Step 2: Session override format

Each session has a unique key derived from platform + chat_id + user_id:
```
agent:main:telegram:dm:<chat_id>
```
vs
```
agent:main:whatsapp:dm:<chat_id>
```

So Telegram's override doesn't affect WhatsApp's override (or vice versa).

### Step 3: `/new` / `/reset` → `gateway/slash_commands.py`

Both resolve to `canonical == "new"` which calls `_handle_reset_command()`.

In `_handle_reset_command()` (line 64):
```python
# Clear any session-scoped model/reasoning overrides
self._session_model_overrides.pop(session_key, None)
self._set_session_reasoning_override(session_key, None)
```

This clears ONLY the calling session's override. Other platforms' overrides are untouched.

### Step 4: Model resolution on next turn → `gateway/run.py`

`_resolve_session_model()` at line 3195:

```python
model = _resolve_gateway_model(user_config)  # reads config.yaml model.default
override = self._session_model_overrides.get(resolved_session_key)

if override:
    override_model = override.get("model", model)
    if override.get("api_key"):
        return override_model, override_runtime  # fast path
    # fall through to env-based resolution

# ... resolve runtime kwargs from env ...

# Last resort: provider's default model
if not model and runtime_kwargs.get("provider"):
    model = get_default_model_for_provider(runtime_kwargs["provider"])
```

So if `/new` cleared the override, the next turn reads from `config.yaml.model.default`. If that's empty, it falls back to the provider's hardcoded default.

## Default Model Behaviour

The hardcoded model list per provider lives in `hermes_cli/models.py` → `_PROVIDER_MODELS`. For `opencode-zen`:

```python
"opencode-zen": [
    "deepseek-v4-flash-free",    # position 0 = default
    "minimax-m3-free",
    "mimo-v2.5-free",
    "qwen3.6-plus-free",
    "nemotron-3-ultra-free",
    "north-mini-code-free",
],
```

When `_resolve_session_model()` needs a fallback and `config.yaml.model.default` is empty:
```python
get_default_model_for_provider("opencode-zen")
   → _PROVIDER_SILENT_DEFAULT_OVERRIDES.get("opencode-zen")  # None — no override for opencode-zen
   → _PROVIDER_MODELS["opencode-zen"][0]                      # "deepseek-v4-flash-free"
```

**Note:** `_PROVIDER_SILENT_DEFAULT_OVERRIDES` (line 1230) exists so metered aggregators with most-expensive-first lists don't auto-select a flagship model silently. Currently only has `{"nous": "deepseek/deepseek-v4-flash"}`.

### Final safety net: `_last_resolved_model`

If resolution somehow produces an empty model (transient config cache miss, post-interrupt recovery), the gateway falls back to the last successfully-resolved model per session key (or process-wide):

```python
# gateway/run.py ~line 3281:
_last_good = getattr(self, "_last_resolved_model", None)
if _last_good is not None and not model:
    _recovered = _last_good.get(resolved_session_key) or _last_good.get("*")
    if _recovered:
        model = _recovered
```

This prevents the session from going silent with HTTP 400 "No models provided".

## Why "Previously" It Synced

Before the VPS migration, user was likely running an older Hermes version where:
1. No `_session_model_overrides` existed
2. `/model` directly wrote to `config.yaml` with no session-scoped caching
3. Every turn read from config, so all platforms immediately saw the change

With session overrides, the existing session caches its model choice — only `/new`/`/reset` (or a fresh process) picks up the global config change.

### CRITICAL: Picker vs typed `/model`

This was the root cause of the user's confusion. There are **two code paths** and they behave differently:

#### Path A (typed `/model deepseek-v4-flash`)
`_finish_switch()` at line 1315:
```python
persist_global = resolve_persist_behavior(is_global_flag, is_session)  # default True
...
if persist_global:
    model_cfg["default"] = result.new_model
    model_cfg["provider"] = result.target_provider
    save_config(cfg)
```
→ Session override + config.yaml persist ✓

#### Path B (Telegram inline model picker)
`_on_model_selected()` at line 1145:
```python
result = _switch_model(
    raw_input=model_id,
    ...
    is_global=False,  # ← HARDCODED! Never persists
    ...
)
# Stores session override but NEVER writes to config.yaml
```
→ Session override ONLY ✗

**Result:** If user switches model via the interactive picker (buttons), the change disappears after `/new`/`/reset`. Only typed `/model <name>` persists across resets. This also explains cross-platform sync gaps: picker only sets override for one platform's session key.

### Key Source Locations

| File | Lines | What |
|---|---|---|
| `gateway/run.py` | 2070-2083 | `_resolve_gateway_model()` — reads config.yaml |
| `gateway/run.py` | 3195-3299 | `_resolve_session_model()` — full resolution with overrides |
| `gateway/run.py` | 2380, 2508-2509 | `_session_model_overrides` dict declaration |
| `gateway/slash_commands.py` | 64-229 | `_handle_reset_command()` — clear overrides on `/new` |
| `gateway/slash_commands.py` | 1032-1506 | `_handle_model_command()` — model switch logic |
| `hermes_cli/model_switch.py` | 302-360 | `parse_model_flags()` — flag extraction |
| `hermes_cli/model_switch.py` | 363-390 | `resolve_persist_behavior()` — persist decision |
| `hermes_cli/commands.py` | 68-69 | `CommandDef("new", ..., aliases=("reset",))` — alias proof |
