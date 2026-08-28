# Hermes Runtime Architecture — Current State (Verified 2026-07-16)

> Source of truth: live codebase at `/home/ubuntu/hermes-snapshot-20260709/hermes-agent/`
> Core file: `hermes_cli/runtime_provider.py` (1,854 lines)
> This is a **verified snapshot** of the architecture BEFORE the RuntimeContext redesign.
>
> **Redesign status:** Architecture design doc at `~/.hermes/design/runtime-resolver-architecture.md` (v2, frozen 2026-07-16).
> Implementation plan at `~/.hermes/design/runtime-resolver-implementation.md` (6 epics, Task 1-3 done).
> New files: `hermes_cli/runtime_context.py`, `hermes_cli/runtime_resolver.py`.

## Key Finding: No Structured Context Objects

There is NO:
- `RuntimeContext` class
- `RequestContext` class  
- `CapabilityContext` class
- `ModelState` class (in userland; `SessionModelState` exists only in ACP protocol schema)

Everything is a flat `Dict[str, Any]` returned by `resolve_runtime_provider()`.

## resolve_runtime_provider() Return Shape

Returns a dict with these fields (varies by provider branch):

| Field | Example Values | Always Present? |
|-------|---------------|-----------------|
| `provider` | `"openrouter"`, `"nous"`, `"anthropic"`, `"openai-codex"`, `"custom"` | ✅ Always |
| `api_mode` | `"chat_completions"`, `"anthropic_messages"`, `"codex_responses"` | ✅ Always |
| `base_url` | URL string | ✅ Always |
| `api_key` | credential string (redacted) | ✅ Always |
| `source` | `"env"`, `"portal"`, `"oauth"`, `"azure-explicit"`, `"process"`, `"hermes-auth-store"` | ✅ Always |
| `requested_provider` | original requested value | ✅ Always |
| `expires_at` | timestamp (nous only) | ❌ Provider-specific |
| `last_refresh` | timestamp (openai-codex, xai-oauth only) | ❌ Provider-specific |
| `expires_at_ms` | millisecond timestamp (qwen-oauth, google-gemini-cli only) | ❌ Provider-specific |
| `email` | string (google-gemini-cli only) | ❌ Provider-specific |
| `project_id` | string (google-gemini-cli only) | ❌ Provider-specific |
| `command` | string (copilot-acp only) | ❌ Provider-specific |
| `args` | list (copilot-acp only) | ❌ Provider-specific |

## Resolution Chain (Implicit Priority)

Written as if-else chain in `resolve_runtime_provider()` (line 1388-1757+):

1. **Explicit args** (`requested`, `explicit_api_key`, `explicit_base_url`, `target_model`) — caller-supplied overrides
2. **Azure Anthropic shortcut** — if `provider=anthropic` + Azure endpoint in base_url, short-circuit with Azure key
3. **Azure Foundry** — `provider=azure-foundry`, read from config
4. **Named custom runtime** (`_resolve_named_custom_runtime`) — matches against `custom_providers` config
5. **Provider resolution** via `resolve_provider()` — maps aliases to canonical providers
6. **Explicit runtime** (`_resolve_explicit_runtime`) — direct env-var based resolution
7. **Credential pool** (`load_pool` + `pool.select()`) — for openrouter / multi-key providers
8. **Provider-specific auth** — nous / openai-codex / xai-oauth / qwen-oauth / minimax-oauth / google-gemini-cli / copilot-acp / anthropic / bedrock / openai / openrouter (fallback)

**IMPORTANT:** For `requested_provider="auto"`, failures in steps 5-8 fall through SILENTLY to the next provider (no error raised). For explicit providers, failures RAISE AuthError.

## What /model Currently Displays

**ACP adapter** (`server.py` _cmd_model, line 1760-1764):
```
Current model: {model}
Provider: {provider}
```
No traceability. No configured vs requested vs effective distinction.

**Gateway** (`slash_commands.py` _handle_model_command):
- With args: interactive picker (Telegram/Discord) or text list
- Shows `current_model`, `current_provider`, `current_base_url` read from config.yaml
- Reads session override dict (`_session_model_overrides`) which overlays on top of config
- No "requested state" tracking — user intent lost after resolution

### Post-Redesign Status

Since 2026-07-16, `/model --status` now shows the full runtime resolution chain (Configured, Requested, Primary, Source, Resolution, Fallback, and if agent context is available: Effective runtime and fallback reason). See `~/.hermes/design/runtime-resolver-architecture.md` §5 for the contract.

## ModelSwitchResult (model_switch.py, line 282-298)

```python
class ModelSwitchResult:
    success: bool
    new_model: str = ""
    target_provider: str = ""
    provider_changed: bool = False
    api_key: str = ""
    base_url: str = ""
    api_mode: str = ""
    error_message: str = ""
    warning_message: str = ""
    provider_label: str = ""
    resolved_via_alias: str = ""
    capabilities: Optional[ModelCapabilities] = None
    model_info: Optional[ModelInfo] = None
    is_global: bool = False
```

**Gap identified:** No `requested_raw` field. No `resolution_reason` field. No `configured_source` field.

## Consumers of resolve_runtime_provider() (Independent Re-resolution)

Each consumer calls `resolve_runtime_provider()` independently — there's no shared context:

| Consumer | File | Line | Notes |
|----------|------|------|-------|
| ACP auth | `acp_adapter/auth.py` | 21-22 | Reads runtime for provider detection |
| ACP session | `acp_adapter/session.py` | 573-604 | Resolves runtime per-session |
| Batch runner | `batch_runner.py` | 871 | Own resolution for batch jobs |
| Curator | `agent/curator.py` | 1697-1808 | Explicit note: must not reuse main chat runtime |
| Auxiliary client | `agent/auxiliary_client.py` | 1815-1817 | Own resolution with `requested="custom"` |
| Delegate tool | `tools/delegate_tool.py` | 2672-2755 | Reads configured_model + calls resolve + re-reads result |
| Web tools | `tools/web_tools.py` | 322-323 | AUXILIARY_WEB_EXTRACT_MODEL env var |
| Image gen tool | `tools/image_generation_tool.py` | 1289 | Own configured_model reader |
| Video gen tool | `tools/video_generation_tool.py` | 468-502 | Own configured_model reader |

**Migration plan:** These consumers should move from `resolve_runtime_provider()` → `RuntimeResolver.resolve()` per the 3-phase migration strategy in `~/.hermes/design/runtime-resolver-architecture.md` §10. Phase 1b (new consumers) and Phase 2 (old consumers).

## Key Safety Guards (Existing)

1. **Custom provider base_url isolation** (`_config_base_url_trustworthy_for_bare_custom`, line 61-88): prevents stale OpenRouter base_url from hijacking `custom` sessions. Guards loopback and known-custom aliases (ollama, vllm, llamacpp).

2. **Nous key TTL check** (line 1505-1514): `_agent_key_is_usable()` verifies min TTL before using pooled credentials; expired keys trigger refresh.

3. **Azure endpoint detection** (line 1667-1699): separates Azure Anthropic keys from Claude Code OAuth tokens to prevent 401 errors.

4. **Session model overrides** (gateway `_session_model_overrides` dict): per-session model persistence that survives across turns in the same conversation.

## Implicit Invariants (NOT Formalised — Need Explicit Definition)

Currently true by code structure but never stated as contracts:
- Resolver always returns `provider`, `api_mode`, `base_url`, `api_key`, `source`, `requested_provider`
- Resolver falls through silently for `auto` providers when credentials fail
- Resolver raises for explicit (non-auto) providers when credentials fail
- `api_mode` is derived from provider type + base URL host, not from user request
- Session overrides take precedence over config.yaml but are NOT persisted to config

## Hermes state.db persistence facts (verified 2026-08-07)

- **Declarative schema reconciliation = the migration mechanism.** `hermes_state.py` `SCHEMA_SQL` is the single source of truth for the `sessions`/`messages` schemas. `_init_schema()` runs `executescript(SCHEMA_SQL)` then `_reconcile_columns()` diffs live columns against SCHEMA_SQL and ADDs any missing ones. To add a column: add it to `SCHEMA_SQL` — reconcile auto-migrates every live DB on next `SessionDB` init (additive, idempotent, runs for write-mode connections; read-only skips it). Do NOT write a version-gated ALTER chain for column additions.
- **`sessions.billing_provider` / `billing_base_url` / `billing_mode` are first-route-wins.** `update_token_counts()` persisted them via `COALESCE(col, ?)`, so a mixed-provider session keeps the FIRST provider's billing metadata forever. `/status` falls back to these fields only after session override → cached agent, so DB fields can look contradictory to the runtime route. (Candidate fix on branch `fix/model-identity-attribution`: `CASE WHEN ? IS NOT NULL THEN ? ELSE col END`.)
- **`sessions.model` is COALESCE-filled** on the first successful API call with whatever `agent.model` is at that moment — silent fallback can make it differ from config.yaml `model.default`.
- **Model identity chain (requested vs canonical):** `agent.model` = requested ID; the provider returns `response.model` (streaming path already extracts first `chunk.model` in `chat_completion_helpers.py` ~1886-1895). Aliases may be remapped server-side (deepseek-chat → deepseek-v4-flash). Candidate branch adds `agent.response_model` capture in `conversation_loop.py` + a `sessions.canonical_model` column.
- **`provider_model_ids()` merge behavior:** live `/v1/models` results are merged with the static `_PROVIDER_MODELS` curated list (curated-first for most providers) — this can RE-INSERT model IDs that upstream removed from discovery (deepseek-chat/reasoner case). `cached_provider_model_ids()` prefers a stale same-fingerprint cache entry over an empty live result, so a pre-fix cache keeps serving removed IDs until TTL expiry.
- **Alias routing maps:** `hermes_cli/model_switch.py` `MODEL_ALIASES` (bare family → default model, e.g. `deepseek` → `deepseek-chat` pre-fix) and `DIRECT_ALIASES` (`_BUILTIN_DIRECT_ALIASES` + config `model_aliases:`). Bare-alias resolution against a provider whose catalog lacks the family silently falls through to OpenRouter or the provider's first curated model — a cost-escalation/reroute trap.

## Cross-Reference

- `hermes_cli/runtime_provider.py` — core resolver (1,854 lines)
- `hermes_cli/runtime_context.py` — NEW: RuntimeContext dataclass with invariants (2026-07-16)
- `hermes_cli/runtime_resolver.py` — NEW: RuntimeResolver wrapping old resolver (2026-07-16)
- `hermes_cli/model_switch.py` — `ModelSwitchResult` + flag parsing (2,223 lines)
- `gateway/slash_commands.py` — `_handle_model_command` (3,953 lines gateway file)
- `acp_adapter/server.py` — `_cmd_model` + `_build_model_state` (2,059 lines)
- `tools/delegate_tool.py` — independent resolve + model pass-through
- Design doc: `~/.hermes/design/runtime-resolver-architecture.md` (frozen v2)
- Implementation plan: `~/.hermes/design/runtime-resolver-implementation.md` (6 epics)
