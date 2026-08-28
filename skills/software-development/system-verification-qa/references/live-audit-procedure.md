# Live Audit Procedure — Empirical Verification of Hermes Behavior

Use this when the user asks to "test", "verify", "audit", or "check if it really works" and the topic touches runtime behavior (model switching, API calls, session state, provider behavior, picker display).

The procedure is **read code → probe live state → reproduce scenario → compare**. Code reading alone is preparation, not the answer.

## Step 1: Read the code path

Use the main SKILL.md procedures. Identify:
- Which handler is invoked (slash command → gateway handler → core function)
- What state it reads (config, session DB, in-memory dict, live API)
- What state it writes (config, session DB, in-memory dict, live API)
- What the upstream behavior is (provider API call, transport kwargs)

Stop and switch to live testing once you have a **concrete hypothesis** ("this should hit `/v1/chat/completions` with these kwargs and either succeed or fail with status N").

## Step 2: Check runtime state

### Config

```bash
cat ~/.hermes/config.yaml | head -30  # model section, agent section
```

### Per-provider env (loaded from ~/.hermes/.env)

```bash
grep -E '^[A-Z_]+=' ~/.hermes/.env | awk -F= '{print $1}' | sort -u
```

### Session DB (state.db)

```python
import sqlite3
conn = sqlite3.connect('/home/ubuntu/.hermes/state.db')
cur = conn.cursor()
cur.execute("""
    SELECT id, model, source, title, started_at
    FROM sessions
    WHERE id LIKE 'YYYYMMDD%'  -- today
    ORDER BY started_at DESC
    LIMIT 20
""")
for r in cur.fetchall():
    print(f"  {r[0]} | model={r[1]} | src={r[2]} | title={r[3]} | start={r[4]}")
```

The `model` column in `sessions` is the **last persisted model name** — but it can be `None` for new sessions, and it can be stale if the model was switched via picker (picker path may or may not persist depending on the platform).

### Picker cache

```bash
cat ~/.hermes/provider_models_cache.json | python3 -m json.tool | head -50
```

This is what `/model` picker shows. Note the `at` timestamp — when was it last refreshed?

### Cached agent state (NOT directly observable)

The gateway caches the `AIAgent` per session in `_agent_cache`. **You cannot inspect this from outside the running process** unless the gateway exposes an API endpoint. The dashboard API (`/api/model/info`) shows the config-level model only, not the cached agent's.

If the cached agent state matters (e.g. "user says /status shows X but /model says Y"), you have to reproduce by:
1. Reading the source for how `status` resolves the model
2. Inferring what the cached agent's `model` attribute is
3. The model is set when the agent is constructed — see `agent.model` and `agent.provider` in the cached entry

## Step 3: Probe live API for provider models

**Curated lists are NOT ground truth.** Always verify.

```python
import os, requests
api_key = os.getenv('OPENCODE_ZEN_API_KEY', '')  # or OPENCODE_GO_API_KEY, etc.

# 1. Get the live catalog
r = requests.get('https://opencode.ai/zen/v1/models',
                 headers={'Authorization': f'Bearer {api_key}'}, timeout=15)
live_ids = sorted([m['id'] for m in r.json()['data']])

# 2. Get the curated list from Hermes source
import sys
sys.path.insert(0, '/home/ubuntu/.hermes/hermes-agent')
from hermes_cli.models import _PROVIDER_MODELS
curated = _PROVIDER_MODELS.get('opencode-zen', [])

# 3. Diff
print("In curated but NOT in live:", set(curated) - set(live_ids))
print("In live but NOT in curated:", set(live_ids) - set(curated))

# 4. For each curated model, send a real chat to confirm it works
working, broken = [], []
for m in curated:
    r = requests.post('https://opencode.ai/zen/v1/chat/completions',
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={"model": m, "messages": [{"role": "user", "content": "hi"}],
              "max_tokens": 5}, timeout=15)
    if r.status_code == 200:
        working.append(m)
    else:
        broken.append((m, r.status_code))
        print(f"  ❌ {m}: {r.status_code} - {r.text[:200]}")
```

**Expected output (this session's finding):** 3 out of 6 curated `opencode-zen` models returned 401 "Model is not supported" — they were in the curated list but no longer in the live catalog.

## Step 4: Reproduce the user's scenario

If the user said "after /reset model is X" or "/model picker says Y but chat fails":
1. Set the same starting state (read config, identify which model is the "default" right now)
2. Run the same command (`/reset`, `/model <picker option>`)
3. Check the outcome state:
   - What does config say now? (file mtime, model.default value)
   - What does the session DB show?
   - Does the next chat completion succeed?

The point: the user observed runtime behavior, so we must observe runtime behavior. If the code says "this should happen" and the runtime shows "this didn't happen", that's a bug, not a misunderstanding.

## Step 5: Compare findings vs code

Build a table:

| Behavior observed | Code path | Match? |
|---|---|---|
| /new clears session override | `_handle_reset_command` line 118: `self._session_model_overrides.pop(...)` | ✅ Match |
| Picker accepts qwen3.6-plus-free | `validate_requested_model` returns accepted:True for curated-only | ✅ Match (the code is buggy) |
| Chat fails 401 on qwen3.6-plus-free | Live API rejects the model | ❌ Code accepted, but live API rejects — bug |
| /status shows deepseek after picker switch | `_handle_status_command` reads agent cache first | ✅ Code is doing this, but it surprises users |

The point: report both the code AND the live evidence. If they don't match, say so clearly.

## Pitfalls

- **Don't trust validate_requested_model "accepted" verdict** without sending a real chat completion. The accept logic is curated-list-only, not live-API-probed.
- **Don't trust the picker cache file's "at" timestamp** — even if recent, the curated list it was built from may be stale.
- **Don't conflate "model.default in config" with "the model the agent actually uses"**. The agent caches its own model in its constructor; only an `agent evict` or `/new`/`/reset` re-resolves.
- **Don't assume reasoning effort propagates uniformly**. Each provider profile has its own `build_api_kwargs_extras`; absence of that method = reasoning dropped silently. Check `plugins/model-providers/<name>/__init__.py` for each provider.
