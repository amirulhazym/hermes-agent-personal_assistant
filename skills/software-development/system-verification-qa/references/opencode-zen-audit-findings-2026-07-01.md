# OpenCode Zen Audit — Findings 2026-07-01

> ⚠️ **STATUS CLAIMS SUPERSEDED 2026-08-24** — the *code-structure* findings below (picker cache stale, `/status` vs `/model` divergence, opencode-zen lacking `build_api_kwargs_extras`) remain valid, but the *model availability* claims are outdated. Live re-probe 2026-08-24: `deepseek-v4-flash-free` (marked ✅ here) is now **DOWN** (HTTP 400 "Model is unavailable"); `hy3-free` (balance-gated in Jul) now **WORKS** (HTTP 200); `muse-spark-1.2-contributor-free` is **DOWN** (HTTP 500, caused user-facing errors); 3 new free models appeared. Current verified snapshot: `references/opencode-zen-free-models-2026-08-24.md`; re-runnable probe: `scripts/probe-zen-free.py`.

> **Re-confirmed: 2026-07-01 (second audit session).** All 3 dead models still dead.  
> Live API now returns only 3 free models (was ~25 including paid in prior check — the `/v1/models` endpoint may have been scoped down or the paid tier moved to Go-only).  
> Picker cache (`provider_models_cache.json`) is still stale — shows all 6 curated models including the dead ones.  
> **New finding:** OpenCode Go reasoning gap extends beyond the opencode-zen issue — only kimi-k2 and deepseek-thinking models get reasoning on opencode-go; mimo/minimax/qwen/glm are silently dropped.  
> A reusable probe script is now at `scripts/probe-live-models.py`.

Session: Amirul noticed `/status` and `/model` showing different models, `/reset`/`/new` behaviour felt inconsistent, `qwen3.6-plus-free` was failing with 401, reasoning effort setting (`xhigh`) seemed to do nothing.

Method: Full end-to-end audit per `live-audit-procedure.md` — read code, probe live API, reproduce the scenario, compare.

## Finding 1 (CRITICAL): 3/6 curated opencode-zen models are dead

The curated list at `hermes_cli/models.py:376-384`:
```python
"opencode-zen": [
    "deepseek-v4-flash-free",  # ✅ works
    "minimax-m3-free",         # ❌ 401 "Model is not supported"
    "mimo-v2.5-free",          # ✅ works
    "qwen3.6-plus-free",       # ❌ 401 "Model is not supported"
    "nemotron-3-ultra-free",   # ✅ works
    "north-mini-code-free",    # ❌ 401 "Model is not supported"
],
```

**Live API catalog at the time of audit: 25 models**, including paid Claude/GPT/Gemini/Kimi/GLM. Among free-tier entries, only 3 of the 6 curated entries actually work.

**Root cause:** `validate_requested_model()` in `hermes_cli/models.py:3629` accepts curated-only models with a warning ("not found in live /v1/models listing but exists in curated catalog — accepted") instead of probing the live API. So `/model` and the picker happily accept models that the upstream provider has removed.

**Fix path (do not execute without user approval):**
- Remove the 3 dead entries from `_PROVIDER_MODELS["opencode-zen"]`
- Or add live-API-probe to `validate_requested_model` with a `--force` override
- Or fetch a fresh picker cache from live API (the cache file already has a `models_dev_cache.json` infrastructure that could be repurposed)

## Finding 2: `/status` source priority is different from `/model`

`/status` reads (in order, `_handle_status_command` line 395):
1. Cached AIAgent's `agent.model` attribute
2. Session DB `sessions.model` column
3. Config `model.default`

`/model` reads (in order, `_handle_model_command` line 1032):
1. `model_cfg.get("default")` from current config snapshot
2. Override: `_session_model_overrides[session_key]`
3. (sets both when switching)

**So when user picks a model via Telegram picker:**
- Picker writes `_session_model_overrides[tg_key] = {model: qwen3.6-plus-free, ...}`
- Picker does NOT persist to config.yaml (`is_global=False` hardcoded in callback)
- Cached agent still has its previous `model` attribute (e.g. `deepseek-v4-flash-free`)
- `/status` reports `deepseek-v4-flash-free` (from cached agent)
- `/model` reports `qwen3.6-plus-free` (from session override)

User sees: "Why does /status say X and /model say Y?" — the answer is they're reading from different in-memory state.

### Proposed fix: add session override as `/status` first priority

Change `_handle_status_command()` to check `_session_model_overrides[session_key]` **before** the cached agent:

```python
# CURRENT (line 484+):
model_name = model_name or _clean_str(session_row.get("model"))
...

# PROPOSED:
override = self._session_model_overrides.get(session_key)
if override:
    model_name = override.get("model", model_name)
    provider_name = provider_name or override.get("provider", "")
    base_url = base_url or override.get("base_url", "")
```

Effect: `/status` instantly reflects the model's the user just picked (whether via picker or typed). When the user runs `/new`/`/reset`, the override is cleared and `/status` reverts to the cached agent / config — which is the *correct* behavior since the session has been reset.

This change is purely a source-priority rearrangement in the read chain — no behavior change for sessions that don't have an override, and no persistence change.

## Finding 3: `opencode-zen` provider profile is missing reasoning wiring

`plugins/model-providers/opencode-zen/__init__.py` defines a plain `ProviderProfile` with **no `build_api_kwargs_extras` method**. By contrast, `opencode_go = OpenCodeGoProfile(...)` has the method and properly maps `xhigh` → `max` for DeepSeek thinking models.

**Effect:** Setting `agent.reasoning_effort: xhigh` (or `/reasoning xhigh`) does nothing for any opencode-zen model. No `reasoning_effort` or `extra_body.reasoning` is sent to the API. The model's default behaviour applies.

**Live verification:** Direct `POST /v1/chat/completions` calls to OpenCode Zen with `reasoning_effort: "xhigh"` returned 200 but the response did not include a `reasoning` token — i.e. the upstream accepts the param but ignores it for these models anyway. So the "no profile" code path is consistent with the upstream behaviour, but the configuration knob is still useless.

**Fix path:** Add `build_api_kwargs_extras` to `opencode_zen` profile mirroring `OpenCodeGoProfile` for the relevant model families (currently just `deepseek-v[3-9]*, deepseek-reasoner`).

## Finding 4: `/reasoning` is a per-provider-and-model mechanism, not universal

The reasoning effort knob (`agent.reasoning_effort` in config or `/reasoning` slash command) is **not universal**. Whether it reaches the API depends on both the provider profile AND the specific model:

### opencode-go (`OpenCodeGoProfile` — has `build_api_kwargs_extras`)

| Model family | Reasoning support | Detail |
|---|---|---|
| `kimi-k2.*` | ✅ Works | `xhigh` → `high`, sent as top-level `reasoning_effort` |
| `deepseek-v4*`, `deepseek-reasoner` | ✅ Works | `xhigh` → `max`, sent via `extra_body.thinking` |
| `mimo-v2.5*` | ❌ Silent drop | Not kimi, not deepseek — no branch matches |
| `minimax-m3`, `minimax-m2.7` | ❌ Silent drop | Not kimi, not deepseek — no branch matches |
| `qwen3.*` | ❌ Silent drop | Not kimi, not deepseek — no branch matches |
| `glm-5.*` | ❌ Silent drop | Not kimi, not deepseek — no branch matches |

### opencode-zen (plain `ProviderProfile` — NO `build_api_kwargs_extras`)

| All models | ❌ Silent drop | No method exists — reasoning never sent |

### Other providers

- Gemini 2.5/3/3.1 (via `_build_gemini_thinking_config`): mapped to `thinkingLevel` or `includeThoughts`
- LM Studio (when `supports_reasoning` is True): top-level `reasoning_effort`

**Impact:** Setting `/reasoning xhigh` is silently ignored for the majority of models Amirul uses daily (mimo, minimax, qwen, glm on opencode-go; ALL models on opencode-zen). The `/reasoning` command is not a no-op — it stores the value, evicts the cached agent — but the value never reaches the API.

### Per-model reasoning effort values (2026-07-01 live probe)

For the user's actual models, what effort values does the upstream API accept (vs. 400-reject)?

| Model | low | medium | high | xhigh | max | minimal | Wire format |
|---|---|---|---|---|---|---|---|
| `deepseek-v4-flash-free` (opencode-zen) | 200 | 200 | 200 | 200 | 200 | **400** | top-level `reasoning_effort` |
| `mimo-v2.5-free` (opencode-zen) | 200 | 200 | 200 | 200 | 200 | 200 | top-level (no-op server-side per #17314) |
| `deepseek-v4-pro` (opencode-go) | 200 | 200 | 200 | 200 | 200 | **400** | top-level `reasoning_effort` |
| `minimax-m3` (opencode-go) | 200 | 200 | 200 | 200 | 200 | 200 | top-level |
| `kimi-k2.6` (opencode-go) | 200 | 200 | 200 | 200 | 200 | 200 | top-level + `extra_body.thinking` |
| `glm-5.2` (opencode-go) | 200 | 200 | 200 | 200 | 200 | **400** | top-level only |

**Implication for the opencode-zen fix:** even after adding `build_api_kwargs_extras`, the effort value needs to be clamped per model family. `minimal` 400s on DeepSeek and GLM; `xhigh`/`max` need to be passed through (not clamped) for DeepSeek. The full per-model clamping table is in `references/reasoning-effort-per-model.md`.

## Finding 5: Picking model via Telegram inline picker ≠ typed `/model`

This was already known from earlier session, but it bears repeating as the root of many "model not syncing" complaints:

- **Picker** (`gateway/slash_commands.py:1149`, `_on_model_selected`): `is_global=False` hardcoded → session override only → does NOT write to config.yaml → does NOT sync to other platforms → lost on `/new`/`/reset`
- **Typed** (`gateway/slash_commands.py:1306`, `is_global=persist_global`): session override + config.yaml persist → syncs on `/new`/`/reset` for all platforms

This is by design (so users can try a model without committing), but the visual indicator in the picker output ("session only — add --global to persist") is easy to miss.

## Finding 6: Picker cache is stale — still shows dead models

The picker cache file (`~/.hermes/provider_models_cache.json`) is built from the curated `_PROVIDER_MODELS` list, NOT from live API. As of 2026-07-01 (second audit), it still shows all 6 opencode-zen models including the 3 dead ones:

```
opencode-zen (at=1782874125.6005554):
  deepseek-v4-flash-free
  minimax-m3-free       ← DEAD (401)
  mimo-v2.5-free
  qwen3.6-plus-free     ← DEAD (401)
  nemotron-3-ultra-free
  north-mini-code-free  ← DEAD (401)
```

The `provider_model_ids("opencode-zen")` function (line 2216-2218) has a custom override that **skips live API entirely** and returns only the static curated list. So even if the cache were refreshed, it would still show dead models — because the refresh pipeline never probes the live API for opencode-zen.

**Fix path:** Either remove the custom override to allow live API refresh, or remove dead models from the curated list so the static path is at least correct.

- Dashboard API not on default port (9090) — likely a different port, not investigated
- `MCP server 'cua-driver' failed initial connection` warning in logs (Windows path leak from WSL `/mnt/f/hermes/cua-driver/cua-driver.exe`) — env cleanup issue, separate
- `agent.title_generator: Title generation failed: ... deepseek-v4-flash-free not supported` — the title generator uses a different model (deepseek-v4-flash, no `-free`) but reports the user's current model name in the error, which is misleading

## Key takeaways for future audits

1. **Always probe live API for curated model lists** — drift is real.
2. **`/status` is not a reliable indicator of "current model"** — it shows cached agent state, not session override state.
3. **Reasoning effort is provider-and-model-specific** — `agent.reasoning_effort: xhigh` is a config knob that does nothing for most providers' free models.
4. **Picker and typed `/model` are different mechanisms with different persistence semantics.**
