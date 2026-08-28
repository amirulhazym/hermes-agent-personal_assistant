# Fallback Verification Protocol — Temporarily Disable Fallback for Model Testing

## When to use

- You need to prove whether a specific model (`hy3-free`, any other) can actually serve requests on the current account
- You want a single, clean attempt — no automatic fallback masking the failure
- The user explicitly wants honest failure (not reliability)
- After verification, you must restore the original fallback configuration exactly

## Approach Selection

There are two approaches depending on what you need to verify:

| Approach | Use when | Impact |
|---|---|---|
| **Phase 0 — Direct API call** | You just want to know if the model is callable (not a full session test) | Zero config changes, works mid-session |
| **Phase 1–5 — Config modification** | You need to verify a full session (with tools, reasoning, etc.) on the target model without fallback interference | Requires backup/restore of config.yaml, new session needed |

Start with Phase 0. Only proceed to Phase 1–5 if the user explicitly asks for a full-session test.

---

## Phase 0 — Direct API Call (Lighter, Mid-Session)

Send exactly ONE API request to the target provider endpoint using Python `urllib.request` (avoids shell-quoting issues and secret-redaction). This proves whether the model is callable without modifying any config or starting a new session.

```python
import urllib.request, json, os

# Read API key from .env directly (NOT via shell env var)
env = open(os.path.expanduser("~/.hermes/.env")).read()
api_key = None
for line in env.splitlines():
    if "OPENCODE_ZEN_API_KEY" in line:  # adjust for target provider
        api_key = line.split("=", 1)[1].strip().strip('"').strip("'").strip('\r')
        break

url = "https://opencode.ai/zen/v1/chat/completions"  # adjust for target
payload = {
    "model": "hy3-free",  # the model to test
    "messages": [{"role": "user", "content": "Reply with only the single word: OK"}],
    "max_tokens": 8,
    "temperature": 0
}

# CRITICAL: Set User-Agent to "curl/8.4.0". The opencode-zen API
# returns different error formats based on User-Agent:
#   - urllib default → "error code: 1010" (opaque)
#   - curl/8.4.0    → {"code": 30001, "message": "..."} (proper JSON)
req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode(),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "curl/8.4.0"
    },
    method="POST"
)

try:
    with urllib.request.urlopen(req, timeout=60) as resp:
        print(f"HTTP {resp.status}")
        print(f"Body: {resp.read().decode()}")
except urllib.error.HTTPError as e:
    print(f"HTTP {e.code}")
    body = e.read().decode()
    print(f"Body: {body}")
    # Check for CF-RAY for traceability
    for k, v in e.headers.items():
        if k in ('CF-RAY', 'Date', 'Server'):
            print(f"  {k}: {v}")
```

### Evidence to capture

| Piece | How |
|---|---|
| HTTP status code | From response |
| Provider error code | From JSON body (e.g. `code: 30001`) |
| Error message | From JSON body (e.g. `"balance insufficient"`) |
| Model sent | Confirmed from payload `"model"` field |
| Provider endpoint | Confirmed from URL used |
| Request ID / trace ID | CF-RAY header (Cloudflare ray ID) |
| Reasoning request? | Check whether `reasoning_effort` was in payload |
| Control test | Same endpoint with a KNOWN-WORKING model (e.g. deepseek-v4-flash-free) to prove the API key and balance are valid |

### Verdict classification

| Label | Criteria |
|---|---|
| ✅ Genuinely works | HTTP 200, response contains valid chat completion |
| ❌ Genuinely fails | HTTP 403/401/400 with error body, or connection timeout (after 60s) |
| ⚠️ Inconclusive | Explain why (e.g. "DNS resolution failed, endpoint may be down") |

If the model works via direct API call but fails in Hermes sessions, the issue is NOT model availability — it's Hermes configuration (wrong base_url, auth mismatch, provider profile stripping params).

### Why Python over curl

| Concern | curl | Python `urllib.request` |
|---|---|---|
| Secret redaction | API key gets `***`'d in tool output, breaking the command | Key passed programmatically, no shell exposure |
| Shell quoting | JSON with nested quotes requires escaping | Python dict → `json.dumps()` handles cleanly |
| User-Agent control | Explicit `-H "User-Agent: ..."` works | Must set explicitly — default triggers different error format |
| Header capture | `-v` needed, verbose output | Direct `e.headers` access |

---

## Config modification approach (full session test)

**Do NOT modify running agent state** (`agent._fallback_chain = []`, etc.). The running agent may have internal state that overrides or re-populates the chain mid-turn. The gateway is a separate process and reads config per-session.

Instead, modify the config file that the gateway reads when creating new sessions. Only needed when Phase 0 (direct API call) is insufficient.

## Protocol

### Phase 1 — Backup

```python
import yaml, shutil
from pathlib import Path

cfg_path = Path.home() / ".hermes" / "config.yaml"
bak_path  = Path.home() / ".hermes" / "config.yaml.fallback.bak"

with open(cfg_path) as f:
    cfg = yaml.safe_load(f)

original_fallback = cfg.get("fallback_providers", [])

# Save to backup file
shutil.copy2(cfg_path, bak_path)

# Also store in memory for the restore step
# original_fallback is a list of dicts like:
# [{"model": "hy3-free", "provider": "opencode-zen"},
#  {"model": "deepseek-v4-flash-free", "provider": "opencode-zen"}]
```

### Phase 2 — Disable

```python
cfg["fallback_providers"] = []
with open(cfg_path, "w") as f:
    yaml.safe_dump(cfg, f, default_flow_style=False)
```

This ensures `_load_fallback_model()` in `gateway/run.py:3911` returns an empty list for the NEXT session creation.

### Phase 3 — Verify

Start a fresh session with the target model (e.g. `/model hy3-free` or a `/new` command targeting the model). The gateway will create a new `AIAgent` with `agent._fallback_chain = []` (from `agent_init.py:950` — empty list branch).

### Phase 4 — Collect evidence

From agent.log, capture:

1. First API call attempt: `API call #1: model=<model> provider=<provider>`
2. If success: latency, tokens, cache stats
3. If failure: `API call failed (attempt N/M) error_type=<type> summary=<reason>`
4. **Verify NO fallback events** — confirm `grep "Fallback activated" ~/.hermes/logs/agent.log` has NO new entries for this session

### Phase 5 — Restore

```python
with open(bak_path) as f:
    cfg = yaml.safe_load(f)
with open(cfg_path, "w") as f:
    yaml.safe_dump(cfg, f, default_flow_style=False)
bak_path.unlink()
```

## Code Paths Reference

### Where `_fallback_chain` is built

`agent/agent_init.py:942-950`:

```python
if isinstance(fallback_model, list):
    agent._fallback_chain = [
        f for f in fallback_model
        if isinstance(f, dict) and f.get("provider") and f.get("model")
    ]
elif isinstance(fallback_model, dict) and fallback_model.get("provider") and fallback_model.get("model"):
    agent._fallback_chain = [fallback_model]
else:
    agent._fallback_chain = []
agent._fallback_index = 0
```

When `fallback_model=[]` (list), the condition passes `isinstance([], list)`, the list comprehension yields `[]`, so `agent._fallback_chain = []`. Then `_try_activate_fallback()` at line 1066 checks `agent._fallback_index >= len(agent._fallback_chain)` → `0 >= 0` → True → returns False immediately. No fallback ever activates.

### Where `_try_activate_fallback()` is triggered

`agent/chat_completion_helpers.py:1060-1306` — called from `conversation_loop.py` at 8+ call sites (lines 942, 1267, 1338, 1481, 2785, 3188, 3335, 4281). All triggered when an API call fails with a non-retryable error.

### Where `model` is set in the request body

`run_agent.py:4824` — `_build_api_kwargs()` builds the kwargs dict that eventually becomes `stream_kwargs` in `chat_completion_helpers.py:1813-1828`. The `model` field is set from `agent.model` at this point:

```python
def _build_api_kwargs(self, api_messages: list) -> dict:
    ...
    api_kwargs["model"] = agent.model
    ...
```

This is consumed by `interruptible_streaming_api_call()` at `chat_completion_helpers.py:1575+`, which passes `**api_kwargs` to `request_client.chat.completions.create()`.

### Where gateway reads fallback config

`gateway/run.py:3911-3929`:

```python
def _load_fallback_model() -> list | None:
    ...
    cfg = yaml.safe_load(f) or {}
    fb = get_fallback_chain(cfg)
    ...
```

Uses `hermes_cli/fallback_config.py:51` `get_fallback_chain()` which reads `config.yaml` → `fallback_providers` key → returns as list of dicts.

## hy3-free Specific Failure Mode

hy3-free on opencode-zen has been verified (2026-07-16) as balance-gated. The error:

- **HTTP 403**
- **Error code**: 30001
- **Message**: "Sorry, your account balance is insufficient"
- **Model priced at**: $0.00/1M tokens (free per-token, but requires minimum balance to pass the gate)
- **Root cause**: opencode-zen enforces a minimum account balance even for $0/1M models (likely anti-abuse)
- **Fix**: Add minimum balance to the opencode-zen workspace

This is NOT a "model doesn't exist" error. hy3-free IS in the `/v1/models` response. It IS callable — if the account has sufficient balance.

The same pattern affects `gpt-5.6-*` and `grok-4.5` models (CreditsError with billing URL instead of code 30001).

## Restore Safety

The backup file (`config.yaml.fallback.bak`) is ALWAYS created before modification. The restore command must:
1. Verify the backup exists (stat it)
2. Write it back (yaml.safe_dump ensures structure preservation)
3. Remove the backup (clean slate)
4. Verify the restored config matches the original (yaml.diff or manual compare)

Do NOT skip the verification step. A corrupted config file will silently break all subsequent sessions.
