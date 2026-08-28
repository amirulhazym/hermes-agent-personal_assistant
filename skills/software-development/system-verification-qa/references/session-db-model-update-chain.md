# Session DB Model Update Chain

## The Complete End-to-End Evidence Chain

This document traces the FULL path from gateway session creation to session DB model persistence, with code evidence at every link.

## Chain Summary

```
Gateway create_session (no model)
  → INSERT OR IGNORE → model=NULL in DB
       ↓
First API call → 403 (hy3-free)
       ↓
FALLBACK mutates agent.model = "deepseek-v4-flash-free"  (chat_completion_helpers.py:1176)
       ↓
Retry API call with fallback model → SUCCESS
       ↓
update_token_counts(model=agent.model)                    (conversation_loop.py:1877)
  → COALESCE(model, 'deepseek-v4-flash-free')             (hermes_state.py:1650)
  → model=NULL → SET to 'deepseek-v4-flash-free'
       ↓
/status reads session DB → model=deepseek-v4-flash-free
```

## Link 1: Gateway creates session WITHOUT model

**File:** `gateway/session.py` lines 1025-1040

```python
db_create_kwargs = {
    "session_id": session_id,
    "source": source.platform.value,
    "user_id": source.user_id,
    # !!! NO model key — model NOT passed !!!
}
...
self._db.create_session(**db_create_kwargs)
```

The gateway's `get_or_create_session()` creates a SQLite session row but does NOT include `model` in the kwargs dict. The `create_session()` call will default `model=None`.

## Link 2: `_insert_session_row()` uses INSERT OR IGNORE

**File:** `hermes_state.py` lines 1338-1367

```python
def _insert_session_row(
    self,
    session_id: str,
    source: str,
    model: str = None,        # ← None by default (gateway doesn't pass it)
    model_config: Dict[str, Any] = None,
    system_prompt: str = None,
    user_id: str = None,
    parent_session_id: str = None,
    cwd: str = None,
) -> None:
    """Shared INSERT OR IGNORE for session rows."""
    def _do(conn):
        conn.execute(
            """INSERT OR IGNORE INTO sessions (id, source, user_id, model, model_config,
               system_prompt, parent_session_id, cwd, started_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                session_id,
                source,
                user_id,
                model,                # ← NULL (gateway didn't provide it)
                json.dumps(model_config) if model_config else None,
                system_prompt,
                parent_session_id,
                cwd,
                time.time(),
            ),
        )
    self._execute_write(_do)
```

Key: `INSERT OR IGNORE` means the FIRST `create_session` call wins. The gateway runs first (model=NULL), so even though the agent later tries to `create_session` with model=hy3-free, it's IGNORED.

## Link 3: Agent tries to create same row → IGNORED

**File:** `run_agent.py` lines 511-527

```python
def _ensure_db_session(self) -> None:
    """Create session DB row on first use. Disables _session_db on failure."""
    if self._session_db_created or not self._session_db:
        return
    source = self.platform or os.environ.get("HERMES_SESSION_SOURCE", "cli")
    try:
        self._session_db.create_session(
            session_id=self.session_id,
            source=source,
            model=self.model,              # ← Would be "hy3-free" at agent init
            model_config=self._session_init_model_config,
            system_prompt=self._cached_system_prompt,
            user_id=None,
            parent_session_id=self._parent_session_id,
            cwd=_launch_cwd_for_session(source),
        )
        self._session_db_created = True
    except Exception as e:
        logger.warning("Session DB creation failed (will retry next turn): %s", e)
```

`INSERT OR IGNORE` → session_id already exists → row unchanged → model stays NULL.
The exception handler does NOT set `_session_db_created = True`, so it retries on every turn — and keeps getting IGNORED.

## Link 4: hy3-free API call fails (403)

Error body:
```json
{"code": 30001, "message": "Sorry, your account balance is insufficient"}
```

This triggers the fallback chain in `chat_completion_helpers.py`.

## Link 5: Fallback mutates `agent.model`

**File:** `chat_completion_helpers.py` lines 1170-1182

```python
old_model = agent.model

agent._config_context_length = None
agent.model = fb_model          # ← LINE 1176: mutated to fallback model
agent.provider = fb_provider    # ← LINE 1177
agent.base_url = fb_base_url    # ← LINE 1178
agent.api_mode = fb_api_mode    # ← LINE 1179
if hasattr(agent, "_transport_cache"):
    agent._transport_cache.clear()
agent._fallback_activated = True
```

Where `fb_model` comes from `config.yaml` `fallback_providers` list. For this session:
```
fallback_providers:
  - model: hy3-free          # ← first entry: skip (same endpoint as primary)
    provider: opencode-zen
  - model: deepseek-v4-flash-free    # ← second entry: WORKS → agent.model set here
    provider: opencode-zen
```

**Log evidence:**
```
2026-07-15 22:19:42,642 INFO [...] agent.chat_completion_helpers:
  Fallback activated: hy3-free → deepseek-v4-flash-free (opencode-zen)
```

## Link 6: Successful API call triggers `update_token_counts()`

**File:** `conversation_loop.py` lines 1862-1879

```python
agent._session_db.update_token_counts(
    agent.session_id,
    input_tokens=canonical_usage.input_tokens,
    output_tokens=canonical_usage.output_tokens,
    cache_read_tokens=canonical_usage.cache_read_tokens,
    cache_write_tokens=canonical_usage.cache_write_tokens,
    reasoning_tokens=canonical_usage.reasoning_tokens,
    estimated_cost_usd=float(cost_result.amount_usd)
    if cost_result.amount_usd is not None else None,
    cost_status=cost_result.status,
    cost_source=cost_result.source,
    billing_provider=agent.provider,      # ← "opencode-zen" (after fallback)
    billing_base_url=agent.base_url,      # ← "https://opencode.ai/zen/v1/"
    billing_mode="subscription_included"
    if cost_result.status == "included" else None,
    model=agent.model,                    # ← "deepseek-v4-flash-free" (after fallback!)
    api_call_count=1,
)
```

Note: There's also a safety `INSERT OR IGNORE` at line 1610 of `hermes_state.py` before the UPDATE:
```python
self._insert_session_row(session_id, "unknown", model=model)
```

This ensures the row exists even if `_ensure_db_session()` failed earlier. With INSERT OR IGNORE, it's a harmless no-op if the row already exists.

## Link 7: `COALESCE(model, ?)` fills the NULL

**File:** `hermes_state.py` lines 1611-1651

```python
if absolute:
    sql = """UPDATE sessions SET
            ...
            model = COALESCE(model, ?),          # ← Only fills if NULL (first time)
            api_call_count = ?
            WHERE id = ?"""
else:
    sql = """UPDATE sessions SET
            ...
            model = COALESCE(model, ?),          # ← LINE 1650
            api_call_count = COALESCE(api_call_count, 0) + ?
            WHERE id = ?"""
```

**`COALESCE(model, ?)` means:**
- If model is NULL (gateway created it without model) → SET to `?` (which is `"deepseek-v4-flash-free"`)
- If model is already set (from a previous successful API call) → UNCHANGED (COALESCE prevents overwrite)

**This is the mechanism that actually writes the model to the session DB.**

## Link 8: `update_session_model()` — ONLY for /model command

**File:** `hermes_state.py` lines 1563-1575

```python
def update_session_model(self, session_id: str, model: str) -> None:
    """Update the model for a session after a mid-session switch.

    Unlike ``update_token_counts`` which uses ``COALESCE(model, ?)``
    (only filling in NULL), this unconditionally sets the model column
    so that the dashboard reflects the user's latest /model choice.
    """
    def _do(conn):
        conn.execute(
            "UPDATE sessions SET model = ? WHERE id = ?",
            (model, session_id),
        )
    self._execute_write(_do)
```

Called ONLY from `gateway/slash_commands.py` lines 1222-1232 (the `/model` handler):
```python
# Persist the new model to the session DB so the
# dashboard shows the updated model (#34850).
_sess_db.update_session_model(
    _sess_entry.session_id, result.new_model
)
```

**The fallback code does NOT call `update_session_model()`**. Only the `/model` command does.

## Implications

| Claim | Previous Belief | Correct Fact |
|---|---|---|
| "Session DB NOT updated by fallback" | Session DB model stays at config default | **FALSE** — `COALESCE(model, ?)` in `update_token_counts()` fills with fallback model on first successful API call |
| "Session DB shows hy3-free" | True for session created before fallback | **PARTIALLY TRUE** — only for sessions that existed before fallback. New sessions (from context compression) show the fallback model |
| "/status shows config model" | Always shows config default | **WRONG** — /status reads session DB model which is filled by COALESCE with fallback model |
| "model=NULL sessions = 0" | Assumed all sessions have model | **FALSE** — 26/432 sessions have NULL model (sessions where no API call succeeded) |
| "update_session_model() fixes model" | Assumed it's used broadly | **FALSE** — only called by `/model` command, not by fallback |

## Verification Query

```sql
-- Check how model gets populated in current sessions
SELECT id, source, model, billing_provider, billing_base_url
FROM sessions
ORDER BY started_at DESC
LIMIT 5;

-- Count NULL vs set model sessions
SELECT
  COUNT(*) FILTER (WHERE model IS NULL) AS null_model,
  COUNT(*) FILTER (WHERE model IS NOT NULL) AS set_model,
  COUNT(*) AS total
FROM sessions;
```

## Cross-Reference Protocol (updated)

To find the ACTUAL serving model when there's a mismatch suspicion:

1. **Session DB** — `state.db` sessions table `model` column. Shows the fallback model (from COALESCE), NOT the configured model.
2. **Gateway log** — `grep "Fallback activated" ~/.hermes/logs/gateway.log`. Shows the fallback chain. Only present when primary model failed.
3. **Agent log** — `grep "API call #N: model=" ~/.hermes/logs/agent.log`. The definitive ground truth.

**Why session DB ≠ config:** The session DB model shows what `agent.model` was at the time of the first successful API call (after fallback). The config.yaml still shows the user's default. To see the configured model, read `config.yaml` `model.default` directly — the session DB won't show it.

**Diagnostic value of NULL model count:** 26/432 NULL model sessions (from this VPS). Possible interpretation: sessions where the first API call never succeeded (all fallbacks also failed, or session was created but no agent ran). A rising NULL count may indicate a degraded provider endpoint.
