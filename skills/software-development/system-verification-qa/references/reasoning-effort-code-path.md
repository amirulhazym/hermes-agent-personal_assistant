# Reasoning Effort — Full Code Path & Verification Protocol

## The Problem

User sets `/reasoning xhigh` (or `agent.reasoning_effort: xhigh` in config.yaml) but:
- Response feels fast, no visible thinking
- Same model on OpenCode/zcode with "Max" reasoning shows visible thinking
- User suspects the setting isn't actually being applied

**Root cause is almost NEVER "the config isn't being read."** It's one of:
1. Display suppression (hides reasoning from user)
2. Model not in provider's effort whitelist (effort silently dropped)
3. Silent fallback (actual model ≠ model user thinks is running)
4. `parse_reasoning_effort()` rejecting the value before it reaches the provider

## Full Code Path

```
config.yaml agent.reasoning_effort: xhigh
       │
       ▼
hermes_constants.py:794-812
  parse_reasoning_effort("xhigh")
  → VALID_REASONING_EFFORTS = ("minimal", "low", "medium", "high", "xhigh")
  → "xhigh" ACCEPTED → {"enabled": True, "effort": "xhigh"}
  ◆ "max" NOT in VALID_REASONING_EFFORTS → returns None → falls to default
       │
       ▼
run_agent.py → reasoning_config injected into agent loop state
       │
       ▼
chat_completions.py → _build_kwargs_from_profile()
  → calls provider_profile.build_api_kwargs_extras()
       │
       ▼
plugins/model-providers/<profile>/__init__.py
  → OpenCodeZenProfile.build_api_kwargs_extras()
     → checks _MODEL_EFFORT_WHITELIST.get(flat_model_name)
        ◆ NOT in whitelist → returns ({}, {}) — EMPTY. reasoning_effort NEVER sent.
        ◆ IN whitelist → calls _clamp_effort() → sends reasoning_effort in top_level
  → OpenCodeGoProfile.build_api_kwargs_extras()
     → checks model family (deepseek/kimi/glm/minimax)
        ◆ NOT in any family → returns ({}, {}) — EMPTY.
        ◆ IN family → calls _clamp_effort() → sends reasoning_effort
       │
       ▼
Wire format sent to API:
  {
    "model": "deepseek-v4-flash",
    "reasoning_effort": "xhigh",       ← Only present if whitelist match
    ...
  }
```

## The Two Gates

### Gate 1: `parse_reasoning_effort()` (hermes_constants.py)

```python
VALID_REASONING_EFFORTS = ("minimal", "low", "medium", "high", "xhigh")
```

**"max" is NOT in this set.** If user sets `/reasoning max`, `parse_reasoning_effort("max")` returns `None`, and the system falls back to the default effort (usually "medium" or "high" depending on model family).

**The value never reaches the provider's `_clamp_effort()`,** even if the provider whitelist DOES accept "max".

### Gate 2: `_MODEL_EFFORT_WHITELIST` (provider profile)

```python
# OpenCodeZenProfile
_MODEL_EFFORT_WHITELIST = {
    "deepseek-v4-flash-free": {"low", "medium", "high", "xhigh", "max"},
    "mimo-v2.5-free": {"none", "minimal", "low", "medium", "high", "xhigh", "max"},
    "nemotron-3-ultra-free": {"none", "minimal", "low", "medium", "high", "xhigh", "max"},
}
```

**hy3-free is NOT in this whitelist.** When hy3-free is the active model and `build_api_kwargs_extras()` is called, it returns `({}, {})` — **no reasoning_effort is sent to the API**. The model runs at its server-default thinking level.

## Silent Fallback Model Illusion

This is the most insidious failure mode because the user has NO visibility:

### Detection Protocol

Cross-reference THREE sources to find the actual serving model:

```
Source 1: User's configured model (what /status shows)
  → Check config.yaml model.default / model.provider
  → Check session DB: state.db sessions table (model column)

Source 2: Gateway fallback messages (if API failed)
  → grep "Fallback activated" ~/.hermes/logs/gateway.log
  → Shows the fallback chain: MODEL_A → MODEL_B → MODEL_C
  → Only present when primary model's API call FAILED

Source 3: Agent API call records (the REAL model serving)
  → grep "model=" ~/.hermes/logs/agent.log
  → Shows the actual model parameter sent to the API
  → This is the GROUND TRUTH for what's running
```

### Worked Example (2026-07-15)

```
Source 1 (config):    model.default=hy3-free, provider=opencode
Source 2 (gateway):   "Fallback activated: hy3-free → hy3-free (opencode-zen)"
                      "Fallback activated: hy3-free → deepseek-v4-flash-free (opencode-zen)"
Source 3 (agent):     model=deepseek-v4-flash-free provider=opencode-zen
```

**The user THINKS hy3-free is running. It's actually deepseek-v4-flash-free.**  
The first fallback was useless (same model, same provider). The SECOND fallback worked silently.  
The session DB model shows `deepseek-v4-flash-free` (filled by `COALESCE(model,?)` in `update_token_counts()` on first successful API call -- see `references/session-db-model-update-chain.md`), while config.yaml `model.default` still says `hy3-free`. /status reads the session DB model (showing fallback), but the user's config default is invisible. Every API call goes to deepseek-v4-flash-free.

### Root Causes for Fallback

1. **Balance gated models** (opencode-zen tier 2): hy3-free returns HTTP 403 with code 30001 "account balance insufficient" even though listed at $0.00/1M. The platform checks account balance and refuses if $0.

2. **`_is_payment_error()` doesn't catch all payment errors**: The function checks `status in {402, 404, 429, None}` — **hy3-free returns HTTP 403**, which is NOT in this set. So the fallback engine's payment detection FAILS to identify the real issue. The fallback still triggers because the exception is a generic APIError, but the PAYMENT-SPECIFIC branch (which would show a helpful message) is bypassed.

## Verification Protocol: "Is reasoning_effort actually working?"

### Step 1: Check display config (fastest — catches #1 cause)

```
grep -A2 'show_reasoning' ~/.hermes/config.yaml
```

If `display.show_reasoning: false` OR `display.platforms.whatsapp.show_reasoning: false`, the reasoning IS happening but being SUPPRESSED before delivery. The model thinks, the user just can't see it.

### Step 2: Check if the model is in the effort whitelist

Open the provider profile. If the model name is NOT in `_MODEL_EFFORT_WHITELIST` (for OpenCodeZen) or NOT matched by the model-family detection (for OpenCodeGo), reasoning_effort is silently dropped.

### Step 3: Live API probe (definitive)

Write a probe that calls the SAME API endpoint Hermes uses, with and without reasoning_effort=xhigh, and compares `reasoning_tokens` from the usage response. A significant difference (e.g., xhigh=180 vs none=101 for simple Qs) proves reasoning_effort IS being applied at the API level.

### Step 4: Learn the actual serving model (detect fallback)

Cross-reference session DB model (`state.db` sessions table) with agent.log to see if the actual API-call model differs from the stored session model.

## Summary Verification Checklist

| Check | Method | Finding |
|---|---|---|
| Display suppression | `grep show_reasoning config.yaml` | If false → reasoning hidden, not missing |
| Effort parsing | Trace `parse_reasoning_effort()` | If "max" → rejected; use "xhigh" |
| Model whitelist | Check `_MODEL_EFFORT_WHITELIST` | If model missing → effort silently dropped |
| Silent fallback | Cross-reference session DB vs agent.log | If they differ → user's model not actually running |
| API-level verification | Live probe with/without reasoning_effort | If xhigh produces more reasoning_tokens → effort IS working |
