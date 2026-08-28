# Reasoning Effort Forensic Audit — 2026-07-15

## Context

User set `/reasoning xhigh` on `/model deepseek-v4-flash --provider opencode-go`. Response felt fast with no visible thinking tokens. Suspected reasoning_effort wasn't applied.

## Final Verdict: reasoning_effort=xhigh WAS working correctly

- Code path verified: config → parse_reasoning_effort("xhigh") → build_api_kwargs_extras() → _clamp_effort("xhigh", whitelist) → top_level["reasoning_effort"] = "xhigh" ✓
- Live probes confirmed: xhigh produces 1.5-1.8x more reasoning tokens than default for simple prompts
- But reasoning content stripped before WhatsApp delivery (display.show_reasoning: false)

## Root cause of "feels like no thinking"

4 layers, each independently sufficient to cause the perception:

### Layer 1: Display suppression
- `display.show_reasoning: false` globally
- `display.platforms.whatsapp.show_reasoning: false` (explicit override)
- `agent_output_handler.py:1030-1040` strips `reasoning_content` when `show_reasoning` is false
- Model IS thinking; content never reaches user

### Layer 2: Model whitelist gap
- `OpenCodeZenProfile` has `_MODEL_EFFORT_WHITELIST` covering only 3 models:
  - deepseek-v4-flash-free ✓
  - mimo-v2.5-free ✓
  - nemotron-3-ultra-free ✓
- hy3-free NOT whitelisted → reasoning_effort silently dropped
- If user was on hy3-free, xhigh would never be sent (no error)

### Layer 3: Silent fallback
- Current session DB shows deepseek-v4-flash-free (the fallback model)
- user's config says hy3-free → 403'd → fallback to deepseek-v4-flash-free
- Session DB never updated after fallback; `/status` shows stale model
- Context compression re-reads config (hy3-free) → re-triggers fallback cycle

### Layer 4: Model speed
- deepseek-v4-flash-free is genuinely fast: xhigh completes in <40s
- Without visible tokens, fast response = no thinking in user's perception

## Provider Profile Architecture (opencode-zen and opencode-go)

Both profiles live in a single file: `plugins/model-providers/opencode-zen/__init__.py`:

- `OpenCodeZenProfile` (aliases: "opencode", "opencode_zen", "zen") — base_url=https://opencode.ai/zen/v1
- `OpenCodeGoProfile` (aliases: "opencode_go", "go", "opencode-go-sub") — base_url=https://opencode.ai/zen/go/v1

### OpenCodeZen reasoning wiring
```python
_MODEL_EFFORT_WHITELIST = {
    "deepseek-v4-flash-free": {"low", "medium", "high", "xhigh", "max"},
    "mimo-v2.5-free": {"none", "minimal", "low", "medium", "high", "xhigh", "max"},
    "nemotron-3-ultra-free": {"none", "minimal", "low", "medium", "high", "xhigh", "max"},
}
```
Models NOT in this list (like hy3-free) get no reasoning_effort sent → silent drop.

### OpenCodeGo reasoning wiring
Per-model-family whitelists with outward-walking clamp:
```python
_DEEPSEEK_GO_WHITELIST = {"low", "medium", "high", "xhigh", "max"}  # deepseek-v4-flash, deepseek-v4-pro
_KIMI_GO_WHITELIST = {"low", "medium", "high", "xhigh", "max"}
_GLM_GO_WHITELIST = {"low", "medium", "high", "xhigh", "max"}
_MINIMAX_GO_WHITELIST = {"low", "medium", "high", "xhigh", "max", "nothinking", "thinking"}
```
Models NOT in a recognised family (mimo, qwen on opencode-go) get empty extra_body → no reasoning_effort.

## Fallback Lifecycle

1. Config: model.default=hy3-free, provider=opencode (→ opencode-zen via alias)
2. Agent init creates client for hy3-free → 403 "balance insufficient" (code 30001)
3. `_classify_by_status(403)` matches "insufficient balance" in billing patterns → `FailoverReason.billing`
4. `_try_activate_fallback()` increments `_fallback_index`:
   - First fallback entry: hy3-free (opencode-zen) — dedup check catches same model+base_url → skips
   - Second entry: deepseek-v4-flash-free (opencode-zen) — works
5. `agent.model = "deepseek-v4-flash-free"` — permanently mutated in-place
6. Session DB NOT updated — still shows hy3-free
7. Context compression → new agent init → re-reads config → hy3-free → 403 → fallback cycle repeats

## Billing Error Classification

Error: HTTP 403, body: `{"code": 30001, "message": "Sorry, your account balance is insufficient"}`

**Main agent loop:** `_classify_by_status(403)` matches `"insufficient balance"` in `_BILLING_PATTERNS` → `FailoverReason.billing` → triggers fallback ✓

**Auxiliary client** (compression, title-gen, vision): `_is_payment_error()` only checks `status in {402, 404, 429, None}` — **403 is NOT in this set** → returns False → no fallback triggered → fails permanently.

## Key code files

| File | What |
|------|------|
| `plugins/model-providers/opencode-zen/__init__.py` | Both provider profiles, whitelists, build_api_kwargs_extras |
| `agent/error_classifier.py:746-792` | `_classify_by_status()` for 403 |
| `agent/auxiliary_client.py:2353-2440` | `_is_payment_error()` — 403 gap |
| `agent/chat_completion_helpers.py:720-811` | Provider profile vs legacy path routing |
| `agent/transports/chat_completions.py:416-424` | extra_body["reasoning"] assembly (legacy path) |
| `hermes_constants.py:794-812` | `parse_reasoning_effort()` — VALID_REASONING_EFFORTS gate |
| `agent/agent_output_handler.py:1030-1040` | reasoning_content stripping for display |
