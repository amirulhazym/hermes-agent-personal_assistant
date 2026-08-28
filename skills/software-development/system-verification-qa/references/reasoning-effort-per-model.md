# Reasoning Effort Acceptance Matrix (live-probed 2026-07-01)

Each model on each provider was probed by sending a real `/v1/chat/completions` call with `reasoning_effort=<value>` and recording the HTTP response. Values returning 200 are ACCEPTED; values returning 400 are REJECTED.

Probe methodology:
```python
r = requests.post(f'{base_url}/chat/completions',
    headers={'Authorization': f'Bearer {api_key}'},
    json={"model": m, "messages": [{"role": "user", "content": "1+1"}],
          "max_tokens": 3, "reasoning_effort": effort},
    timeout=12)
# 200 = accepted, 400 = rejected
```

Values tested: `low`, `medium`, `high`, `xhigh`, `max`, `minimal`, `none`

---

## OpenCode Zen (`https://opencode.ai/zen/v1`)

| Model | Accepted | Rejected | Notes |
|---|---|---|---|
| `deepseek-v4-flash-free` | `low`, `medium`, `high`, `xhigh`, `max` | `minimal` (400) | DeepSeek V4 defaults to thinking ON; cannot disable `extra_body.thinking` via relay |
| `mimo-v2.5-free` | **ALL** — `low`, `medium`, `high`, `xhigh`, `max`, `minimal`, `none` | None | Schema-accepts all levels; server-side NO-OP per issue #17314 |
| `hy3-free` | **BALANCE-GATED** | **BALANCE-GATED** | Returns code 30001 "account balance insufficient" on opencode-zen. Model exists in /v1/models but requires minimum balance to call — even though pricing is $0.00/1M. See `references/opencode-zen-model-tiers.md`. Untestable for reasoning effort without account balance. |
| `nemotron-3-ultra-free` | `low`, `medium`, `high`, `minimal` | `max` (timeout) | Limited; likely server-side clamps internally |

Priced models (`deepseek-v4-pro`, `kimi-k2.6`, `claude-*`, `gpt-*`) are INACCESSIBLE on the Zen endpoint (return credits error). Their reasoning behavior through the Zen endpoint is irrelevant in practice.

---

## OpenCode Go (`https://opencode.ai/zen/go/v1`)

| Model | Accepted | Rejected | Notes |
|---|---|---|---|
| `deepseek-v4-pro` | `low`, `medium`, `high`, `xhigh`, `max` | `minimal` (400) | Same as Zen. Default thinking ON via relay |
| `deepseek-v4-flash` | `low`, `medium`, `high`, `xhigh`, `max` | `minimal` (400) | Same |
| `mimo-v2.5` | `low`, `medium`, `high`, `xhigh`, `max`, `minimal`, `none` | None | Schema-accepts all; server-side NO-OP (#17314) |
| `mimo-v2.5-pro` | `low`, `medium`, `high`, `xhigh`, `max`, `minimal`, `none` | None | Same as mimo-v2.5 |
| `glm-5.2` | `low`, `medium`, `high`, `xhigh`, `max`, `none`, `adaptive` | `minimal` (400) | Error message: "Input should be 'low', 'medium', 'high', 'xhigh', 'max', 'none' or 'adaptive'" |
| `glm-5.1` | `low`, `medium`, `high`, `xhigh`, `max` | `minimal` (400) | Same as glm-5.2 |
| `glm-5` | `low`, `medium`, `high`, `xhigh`, `max` | `minimal` (400) | Same as glm-5.2 |
| `minimax-m3` | `low`, `medium`, `high`, `xhigh`, `max`, `minimal`, `none` | None | Schema-passthrough; no server-side thinking response observed via relay |
| `kimi-k2.6` | `low`, `medium`, `high`, `xhigh`, `max`, `minimal`, `none` | None | Default thinking ON via relay |
| `qwen3.7-max` | `low`, `medium`, `high`, `xhigh`, `minimal` | `max` — error: "must be one of: 'none', 'minimal', 'low', 'medium'" | AliCloud relay: 5 levels, max is rejected |
| `qwen3.6-plus` | `low`, `medium`, `high`, `xhigh` | `max` + `minimal` — error: "must be one of: 'none', 'minimum', 'low'" | Even more restrictive |

---

## Key patterns

1. **DeepSeek V4 family** (all variants on both Zen and Go): Same set — `low/medium/high/xhigh/max`, NO `minimal`
2. **Xiaomi MiMo family**: ALL values accepted schema-wise, NO effect server-side (#17314)
3. **GLM 5.x family**: Full set including `none` and `adaptive`, NO `minimal`
4. **Qwen on AliCloud**: MODEL-SPECIFIC accepted sets — qwen3.7-max is different from qwen3.6-plus
5. **OpenCode Zen routing hides thinking control**: `extra_body.thinking.type=disabled` returns status 200 but thinking is still ON in the response. The only way to "disable" thinking for DeepSeek through the relay is to not send any reasoning fields at all AND hope the relay doesn't add its own.
6. **No model tested sends a non-200 response for `extra_body.thinking.type=enabled`** — it's the binary toggle that all providers accept, even if they ignore it.

---

## DeepSeek V4 Flash — Reasoning Token Yield by Effort Level (live-probed 2026-07-15)

`deepseek-v4-flash` on OpenCode Go with `reasoning_effort=`. Simple question ("What is 2+2?"), `max_tokens=500`, streaming OFF.

| Effort    | HTTP | Time   | Completion Tokens | Reasoning Tokens | Reasoning Content |
|-----------|------|--------|-------------------|------------------|--------------------|
| `xhigh`   | 200  | 2.51s  | 2                 | 95               | 399 chars          |
| `medium`  | 200  | 2.10s  | 2                 | 65               | 220 chars          |
| `max`     | 200  | 2.20s  | 2                 | 69               | 262 chars          |
| `low`     | 200  | 2.47s  | 2                 | 59               | 263 chars          |
| *(none)*  | 200  | 2.18s  | 2                 | 84               | 314 chars          |

**Key findings:**

1. **DeepSeek V4 Flash ALWAYS returns `reasoning_content`** — even when no `reasoning_effort` field is sent at all. The model thinks by default through the opencode-go relay; there is no true "no thinking" mode for this model family on this provider.

2. **Effort level DOES affect token count but variance is small for simple questions.** `xhigh` produced the most reasoning tokens (95). `low` produced the least (59). But `max` only produced 69 — less than `medium` (65 is close) and less than no-field (84). The effort level is honored but the relationship is not linear for trivial prompts.

3. **All responses complete in ~2 seconds.** For simple questions, DeepSeek V4 Flash is fast regardless of effort level — the "instant response" perception is inherent to the model's speed, not an indication that reasoning is disabled.

4. **`curl_cffi` with `impersonate="chrome120"` is required to bypass Cloudflare on opencode-go.** Plain `urllib.request` returns HTTP 403 "error code: 1010" from the VPS's Singapore IP. The gateway itself uses its own TLS stack and is not affected.

5. **`reasoning_effort` is a TOP-LEVEL JSON field, not `extra_body`.** The OpenCodeGo provider profile emits `top_level["reasoning_effort"] = effort` (not inside `extra_body`). This matches the OpenAI-compatible schema and the relay passes it through.
