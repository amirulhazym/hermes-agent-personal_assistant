# OpenCode API Quirks (Verified 2026-07-03)

## Endpoints

| Service | Correct Base URL | Notes |
|---|---|---|
| OpenCode Zen (free tier) | `https://opencode.ai/zen/v1/chat/completions` | API key = empty string (`api_key: ''`) |
| OpenCode Go (paid $10/mo) | `https://opencode.ai/zen/go/v1/chat/completions` | NOT `/go/v1/` — that returns 404 |
| OpenCode Go models list | `https://opencode.ai/zen/go/v1/models` | Returns available models |

## Rate Limit Headers

**Neither Zen nor Go return `x-ratelimit-*` headers.** Response headers are minimal:
```
date, content-type, content-length, cf-placement, server, cf-ray
```
Standard OpenAI-compatible rate limit headers are NOT present. This is unlike most OpenAI-compatible providers.

## Response Body

Response includes a `cost` field:
```json
{"cost": "0"}
```
For Zen (free tier), cost is always 0. For Go (flat subscription), cost is also 0 per request — the subscription covers usage.

## Undocumented Endpoints Tested (ALL 404)

| Endpoint | Result |
|---|---|
| `/zen/go/v1/usage` | 404 |
| `/zen/go/v1/quota` | 404 |
| `/zen/go/v1/rate-limit` | 404 |
| `/zen/v1/user/info` | 404 |
| `/api/workspace/{id}/usage` | 404 |
| `/api/workspace/{id}/billing` | 404 |

## Billing Dashboard

The ONLY way to view subscription usage is the web dashboard:
```
https://opencode.ai/workspace/{workspace_id}/go
```
Requires GitHub/Google OAuth login. No API key or programmatic access.

## Usage Limits (from docs, 2026-07-03)

- 5-hour limit: $12 of usage
- Weekly limit: $30 of usage
- Monthly limit: $60 of usage

## Go Pricing (from docs, verified 2026-07-03)

Full pricing table — source: https://opencode.ai/docs/usage/go

| Model | Input/1M | Output/1M | Cached Read/1M |
|---|---|---|---|
| DeepSeek V4 Flash | $0.27 | $1.10 | $0.027 |
| DeepSeek V4 Pro | $0.55 | $2.19 | $0.055 |
| MiMo V2.5 | $0.14 | $0.28 | $0.0028 |
| MiMo V2.5 Pro | $1.74 | $3.48 | $0.0145 |
| GLM-5.2 | $1.40 | $4.40 | $0.26 |
| GLM-5.1 | $1.40 | $4.40 | $0.26 |
| Kimi K2.7 Code | $0.95 | $4.00 | $0.19 |
| Kimi K2.6 | $0.95 | $4.00 | $0.16 |
| MiniMax M3 | $0.20 | $0.80 | $0.02 |
| MiniMax M2.7 | $0.15 | $0.60 | $0.015 |
| Qwen3.7 Max | $0.50 | $2.00 | $0.05 |
| Qwen3.7 Plus | $0.30 | $1.20 | $0.03 |
| Qwen3.6 Plus | $0.30 | $1.20 | $0.03 |

**Cost estimation formula:**
```python
cost_usd = (input_tokens / 1e6 * input_rate) + (output_tokens / 1e6 * output_rate) + (cache_read_tokens / 1e6 * cached_rate)
```

Implemented in `~/.hermes/scripts/billing.py` as `estimate_go_cost()`.

## Implications for Billing Monitoring

Since no API exposes usage data, billing monitoring must be:
1. **Self-tracked** — accumulate token counts from session DB (already implemented in billing.py)
2. **Manual check** — periodic dashboard check via desktop browser
3. **Cost estimation** — calculate from token counts × model pricing

## Mobile Browser Cookie Extraction (Dead End)

HttpOnly session cookies CANNOT be extracted from ANY mobile browser:
- `document.cookie` returns empty (HttpOnly flag blocks JS access)
- No mobile browser has full DevTools Application tab
- Firefox mobile does NOT have built-in cookie viewer for HttpOnly cookies
- HAR export requires desktop DevTools

**Only viable path:** Desktop browser DevTools (Application → Cookies) or desktop HAR export.

## User-Agent Sensitivity (Verified 2026-07-16)

The opencode-zen API returns **different error formats** depending on the `User-Agent` header sent with the request. This is critical when verifying model availability via direct API calls.

| User-Agent | Error Response | Notes |
|---|---|---|
| `curl/8.4.0` (or browser UA) | `{"code":30001,"message":"Sorry, your account balance is insufficient","data":null}` | Proper JSON, actionable error message |
| Python `urllib` default | `error code: 1010` (Content-Type: text/plain) | Opaque, hard to diagnose |

**Impact:** If you use Python `urllib.request` (or `requests` without setting User-Agent) to probe the API, you get the opaque `"error code: 1010"` response instead of the actionable JSON. Always set `User-Agent: curl/8.4.0` explicitly.

**Root cause:** Likely Cloudflare or the API gateway routes requests differently based on the `User-Agent` value — `curl` gets routed to the proper JSON error handler, while `urllib` default hits a generic text error page.

**Safe Python pattern:**
```python
req = urllib.request.Request(
    url, data=json.dumps(payload).encode(),
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "curl/8.4.0"  # REQUIRED for proper error format
    },
    method="POST"
)
```
