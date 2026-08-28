# Reasoning Tokens — Troubleshooting Guide

## Symptom

Daily usage report shows `Reasoning tokens | 0` even though `reasoning_effort: xhigh` is configured.

## Root Cause (verified 2026-07-03)

**Bug:** `normalize_usage()` in `agent/usage_pricing.py:763` reads from `output_tokens_details` but OpenCode/OpenAI-standard returns reasoning tokens under `completion_tokens_details`.

```python
# CURRENT (bug):
output_details = getattr(response_usage, "output_tokens_details", None)
if output_details:
    reasoning_tokens = _to_int(getattr(output_details, "reasoning_tokens", 0))

# FIX: check completion_tokens_details first, fallback to output_tokens_details
output_details = getattr(response_usage, "completion_tokens_details", None)
if not output_details:
    output_details = getattr(response_usage, "output_tokens_details", None)
if output_details:
    reasoning_tokens = _to_int(getattr(output_details, "reasoning_tokens", 0))
```

## What's ACTUALLY Working (confirmed by live test, 2026-07-03)

| Layer | Status | Evidence |
|---|---|---|
| Config `reasoning_effort: xhigh` | ✅ Correct | `config.yaml` |
| `parse_reasoning_effort("xhigh")` → `{enabled: true, effort: "xhigh"}` | ✅ Correct | `hermes_constants.py:797` |
| OpenCodeZenProfile accepts `deepseek-v4-flash-free` in whitelist | ✅ Correct | `plugins/model-providers/opencode-zen/__init__.py:121` |
| `_clamp_effort("xhigh", whitelist, "high")` → returns `"xhigh"` | ✅ Correct | `line 172` |
| API accepts `reasoning_effort: xhigh` (200 OK) | ✅ Confirmed | Live curl test |
| Model produces `reasoning_content` in response | ✅ Confirmed | Response had reasoning text |
| API counts reasoning tokens | ✅ Confirmed | `completion_tokens_details.reasoning_tokens: 30` |
| **Usage tracking reads reasoning_tokens** | ❌ **BROKEN** | Reads wrong field name |

## Full Trace Path

```
config.yaml: agent.reasoning_effort: xhigh
  → gateway/run.py:_load_reasoning_config() reads config
  → hermes_constants.py:parse_reasoning_effort("xhigh")
    → returns {"enabled": True, "effort": "xhigh"}
  → AIAgent stores as self.reasoning_config
  → agent/transports/chat_completions.py:529 calls profile.build_api_kwargs_extras()
  → plugins/model-providers/opencode-zen/__init__.py:130-172
    → checks _MODEL_EFFORT_WHITELIST["deepseek-v4-flash-free"] → {"low","medium","high","xhigh","max"}
    → _clamp_effort("xhigh", whitelist, "high") → "xhigh"
    → sets top_level["reasoning_effort"] = "xhigh" (line 172)
  → HTTP POST to OpenCode Zen API
    → Response includes:
      - choices[0].message.reasoning_content (the actual reasoning text)
      - usage.completion_tokens_details.reasoning_tokens (the count)
  → agent/usage_pricing.py:normalize_usage() reads response
    → line 763: getattr(response_usage, "output_tokens_details", None)
    → RETURNS None (field is "completion_tokens_details")
    → reasoning_tokens stays 0
```

## Comparative Test Results (confirmed 2026-07-03)

Same question ("How many R letters are in the word strawberry?"), three settings:

| Setting | Reasoning tokens | Completion tokens | Pattern |
|---|---|---|---|
| `reasoning_effort: xhigh` | **325 rt** | 392 total | Deepest reasoning |
| `reasoning_effort: low` | **230 rt** | 328 total | Moderate reasoning |
| No param (default) | **118 rt** | 165 total | Least reasoning |

**Finding:** The parameter directly controls reasoning depth — xhigh produces **2.8× more reasoning tokens** than default. Each effort level measurably changes how deeply the model thinks.

## Live Test Command

```bash
curl -s --max-time 30 -X POST "https://opencode.ai/zen/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v4-flash-free",
    "reasoning_effort": "xhigh",
    "messages": [{"role": "user", "content": "Return only the word hello"}],
    "max_tokens": 50
  }'
```

Check for these fields in response:
- `choices[0].message.reasoning_content` — reasoning text present?
- `usage.completion_tokens_details.reasoning_tokens` — token count present?
- Not `usage.reasoning_tokens` — that's not where OpenCode puts it

## Key Insight

This is a **Hermes core parsing bug** — not a config issue, not an OpenCode relay limitation. The `reasoning_effort` parameter IS being sent correctly and the model IS reasoning at max. Only the usage tracking/reporting is broken because it reads the wrong field name.

The fix is in `agent/usage_pricing.py` running in the `hermes-agent` repo, not in our local config or scripts.
