# Tracing Parameter Flow Through Hermes Agent Stack

When a model/runtime parameter (reasoning_effort, max_tokens, temperature, etc.) doesn't produce the expected behaviour, the root cause is often in one of the intermediate transformation layers. Trace the full path: don't stop at config.yaml.

## The 7-Layer Stack

Every model parameter flows through these layers. A break at any layer produces a silent failure (parameter sent but ignored, clamped, or dropped).

```
config.yaml                   ← Layer 1: User-facing config
    ↓
hermes_constants.py           ← Layer 2: Parse/validate/normalise
    ↓
gateway/run.py                ← Layer 3: Agent construction
    ↓
agent/agent_init.py           ← Layer 4: AIAgent init
    ↓
transports/chat_completions.py ← Layer 5: Transport layer (build kwargs)
    ↓
plugins/model-providers/<name>/__init__.py ← Layer 6: Provider profile
    ↓
HTTP request to API            ← Layer 7: Wire
```

## Step-by-Step Procedure

### Layer 1: Read config.yaml

```bash
grep -A5 -B5 "reasoning_effort\|max_tokens\|temperature" ~/.hermes/config.yaml
```

What to check: Is the parameter present? Is it spelled correctly? Is it under the right YAML path?

### Layer 2: Find the parsing/normalisation function

Search Hermes source for how the config value is parsed:

```bash
cd ~/.hermes/hermes-agent
grep -rn "def parse_\|VALID_\|_load_\|_parse_config" hermes_constants.py | head -10
```

**Examples found:**
- `parse_reasoning_effort()` in `hermes_constants.py:797` — maps string to `{"enabled": bool, "effort": str}`
- `VALID_REASONING_EFFORTS` in `hermes_constants.py:794` — `("minimal", "low", "medium", "high", "xhigh")`

What to check: Does the parser accept your value? Does it normalise/transform it in a way that changes semantics?

### Layer 3: Gateway/agent construction

Find how the parsed value is stored:

```bash
grep -n "reasoning_config\|_load_reasoning" gateway/run.py | head -10
```

Look for `self._reasoning_config` or similar — this is stored on the gateway object and passed to the AIAgent constructor.

What to check: Is the value being passed correctly? Any feature-gating logic that might skip it?

### Layer 4: AIAgent init

```bash
grep -n "reasoning_config" run_agent.py | head -10
```

The AIAgent stores `self.reasoning_config = reasoning_config` — this is then available when building API kwargs.

What to check: Is the value preserved through the constructor? Any defaulting logic that overrides it?

### Layer 5: Transport layer

```bash
grep -n "reasoning_config\|build_api_kwargs_extras" agent/transports/chat_completions.py
```

The transport calls `profile.build_api_kwargs_extras(kwargs, reasoning_config=reasoning_config)`. This is the critical bridge layer.

**Important: Check for feature gates BEFORE the provider profile.**

Look for `_supports_reasoning_extra_body()` or similar in the transport — these can silently block the parameter:

```python
# Example from run_agent.py (~line 4829):
def _supports_reasoning_extra_body(self) -> bool:
    # Returns True ONLY for openrouter.com, nousresearch.com,
    # api.githubcopilot.com, or localhost/LMStudio
    # All other hosts (opencode.ai, etc.) → returns False
```

If this gate returns False, `extra_body` reasoning params are dropped **before** reaching the provider profile. Note: top-level params like `reasoning_effort` bypass this gate — it only blocks `extra_body`.

What to check: Does a feature gate exist in the transport that blocks your parameter before it reaches the provider?

### Layer 6: Provider profile

Read the actual provider plugin:

```bash
cat ~/.hermes/hermes-agent/plugins/model-providers/<name>/__init__.py
```

Find the `build_api_kwargs_extras()` method. This is where the profile maps Hermes' internal parameter names to the actual API's field names.

**Key verification points:**
- Does the profile implement `build_api_kwargs_extras()` at all? **Missing entirely** → no per-profile customisation (relies on transport defaults)
- Does it have a model whitelist? If a model isn't whitelisted, the parameter may be silently dropped or defaulted
- Does it use `_clamp_effort()` or similar? This maps Hermes effort levels to the model's accepted subset — may silently downgrade `xhigh` to `high` if `xhigh` isn't in the whitelist
- Does it handle the specific parameter name correctly? OpenCode API uses `reasoning_effort` (top-level string), DeepSeek API uses `thinking` or `reasoning_config` (extra_body)

**Common pitfalls at this layer:**

| Profile | What we found |
|---|---|
| DeepSeek | Reads `reasoning_config` from kwargs, maps to DeepSeek's own effort levels, sets `extra_body` |
| OpenCode Zen | Reads `reasoning_config`, clamps to model whitelist, sets top-level `reasoning_effort` string |
| OpenCode Go | Only wires reasoning for `kimi-k2` and `deepseek-thinking` models — other models silently dropped |
| OpenRouter | Uses `_supports_reasoning_extra_body` gate — if base_url isn't openrouter/nousresearch, extra_body blocked |

### Layer 7: Wire (actual API call)

With the transport and profile confirmed, check how the response is parsed:

```bash
grep -rn "reasoning_tokens\|reasoning_content" agent/usage_pricing.py | head -10
```

The response parser reads `output_details.reasoning_tokens` — if the API response doesn't include this field (e.g., OpenCode relay strips it), the value stays 0 regardless of what was sent.

What to check: Does the upstream API actually return this field in its response format? Is there a relay/proxy in between that might strip it?

## Liveness Check

If possible, send a minimal real API call and capture the raw response to check what's actually returned:

```python
# Minimal probe for reasoning effort
import requests, json
resp = requests.post(
    f"{base_url}/chat/completions",
    headers={"Authorization": f"Bearer {api_key}"},
    json={
        "model": model_name,
        "messages": [{"role": "user", "content": "Say hello"}],
        "max_tokens": 20,
        "reasoning_effort": "xhigh",  # or whichever param name the profile uses
    }
)
print(json.dumps(resp.json(), indent=2))
```

Compare the `usage` object in the response — does `reasoning_tokens` exist?

## Summary

| Layer | File | What to check |
|---|---|---|
| 1 | config.yaml | Parameter present, correct spelling |
| 2 | hermes_constants.py | Parse function accepts your value |
| 3 | gateway/run.py | Value stored correctly |
| 4 | run_agent.py | Passed to AIAgent constructor |
| 5 | transports/chat_completions.py | Feature gates before provider; `build_api_kwargs_extras` called |
| 6 | plugins/model-providers/<name>/__init__.py | Model whitelist, clamping logic, field name mapping |
| 7 | API response | Field actually returned by upstream |

## Quick Command Cheatsheet

```bash
# Find all reasoning-related code
grep -rn "reasoning" ~/.hermes/hermes-agent/ --include="*.py" | grep -v venv | grep -v __pycache__

# Check provider profile
cat ~/.hermes/hermes-agent/plugins/model-providers/<name>/__init__.py

# Check transport reasoning gate
grep -A20 "_supports_reasoning_extra_body" ~/.hermes/hermes-agent/run_agent.py

# Check usage parser
grep -A10 "reasoning_tokens" ~/.hermes/hermes-agent/agent/usage_pricing.py

# Check config value
grep "reasoning_effort" ~/.hermes/config.yaml
```
