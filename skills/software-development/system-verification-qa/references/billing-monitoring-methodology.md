# Billing Monitoring Methodology

## Overview

Pattern for investigating API billing/usage monitoring when a provider doesn't expose usage data via public API. Developed during OpenCode Go integration (2026-07-03).

## Investigation Steps

### 1. Check Response Headers for Rate Limit Info

Most OpenAI-compatible providers return `x-ratelimit-*` headers. Test with:

```bash
curl -s --max-time 15 -D - -X POST "{base_url}/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer {key}" \
  -d '{"model":"...","messages":[{"role":"user","content":"hi"}],"max_tokens":10}' 2>&1 | head -30
```

Look for: `x-ratelimit-limit-tokens`, `x-ratelimit-remaining-tokens`, `x-ratelimit-reset-tokens`

**If absent:** Provider doesn't expose rate limits via headers. Move to step 2.

### 2. Probe Candidate Undocumented Endpoints

Try common patterns:
```
/zen/v1/usage, /zen/v1/quota, /zen/v1/rate-limit
/api/v1/usage, /api/workspace/{id}/usage
/auth/api/usage, /zen/go/v1/usage
```

Use `curl -sL -w "\nHTTP_CODE:%{http_code}"` to follow redirects and capture status.

**If all 404:** Provider has no public usage API. Move to step 3.

### 3. Check if Dashboard Uses Internal API

The web dashboard must fetch usage data from SOME endpoint. But without OAuth login, we can't inspect network calls.

**Only viable if:** User can provide session cookie from desktop browser DevTools.

### 4. Self-Tracked Usage (Fallback)

If no API exposure, track usage ourselves:

1. **Session DB** — Hermes stores `input_tokens`, `output_tokens`, `cache_read_tokens`, `reasoning_tokens` per session in `state.db`
2. **Query pattern** — Aggregate by provider, model, time window:
   ```sql
   SELECT billing_provider, model,
          SUM(input_tokens) as in_tok,
          SUM(output_tokens) as out_tok
   FROM sessions
   WHERE started_at >= ? AND billing_provider IS NOT NULL
   GROUP BY billing_provider, model
   ```
3. **Cost estimation** — Multiply token counts by model pricing (from docs):
   ```python
   cost = (input_tokens / 1e6 * input_rate) + (output_tokens / 1e6 * output_rate)
   ```

### 5. Cost Estimation from Token Counts

When per-request cost is always 0 (flat subscription), estimate from:
- Token counts from session DB
- Model pricing from provider docs
- Formula: `cost_usd = (input/1M * rate) + (output/1M * rate) + (cached/1M * rate)`

Implemented in `~/.hermes/scripts/billing.py` as `estimate_go_cost()`.

## OpenCode-Specific Findings

| Item | Finding |
|---|---|
| Zen endpoint | `https://opencode.ai/zen/v1/chat/completions` (free, api_key='') |
| Go endpoint | `https://opencode.ai/zen/go/v1/chat/completions` (NOT `/go/v1/`) |
| Rate limit headers | None (neither Zen nor Go) |
| Usage API | None (all 6 candidate endpoints returned 404) |
| Dashboard access | OAuth login required (GitHub/Google) — no programmatic access |
| Mobile cookie extraction | Dead end — HttpOnly blocks JS access on all mobile browsers |
| Usage limits | $12/5h, $30/week, $60/month |
| Self-tracked | Implemented in billing.py — queries state.db, estimates cost from pricing table |

## Billing.py Architecture

```
billing.py
├── check_deepseek()        — API balance check (curl → /v1/user/balance)
├── check_opencode_go()     — Key validity check (minimal test call)
├── check_self_tracked()    — Session DB aggregation (today/week/month/model)
├── estimate_go_cost()      — Token count → USD cost estimation
├── GO_MODEL_PRICING        — Full pricing table (13 models)
├── fetch_rates()           — CNY→MYR/USD/SGD conversion
└── main()                  — Orchestrates all checks, formats output
```

## Pivot Discipline (from evidence-first-feasibility-assessment)

When browser-based approach fails on mobile:
- **Don't** try Chrome → Brave → Firefox (same approach, different browser)
- **Do** recognize the class-level limitation (HttpOnly cookies are inaccessible from ALL mobile browsers)
- **Do** pivot to fundamentally different approach (API-level workarounds, self-tracking, desktop browser)
