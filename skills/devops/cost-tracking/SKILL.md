---
name: cost-tracking
title: Cost Tracking
description: Monitor and track API usage costs across providers. Query session DB for token breakdowns, call provider balance APIs, calculate cost from pricing tiers, and project runway. Use when running daily/weekly cost reports or investigating spending.
trigger: user asks for cost report, usage summary, balance check, token tracking, budget projection, or any API spending question.
tags: [cost, billing, token-usage, deepseek, api-costs, burn-rate]
---

# Cost Tracking

Class-level methodology for tracking API usage costs across LLM providers used by Hermes Agent.

## Workflow

### 1. Quick Aggregate View

```bash
hermes insights --days N
```

This gives a high-level summary: sessions, messages, input/output tokens, tool calls, models used, platforms, and activity patterns. Good for a quick check but doesn't provide per-session granularity or specific cost calculations.

### 2. Granular Per-Session Data

Query the Hermes SQLite session DB directly for precise token breakdowns:

```python
import sqlite3, time

conn = sqlite3.connect('/home/ubuntu/.hermes/state.db')
cursor = conn.cursor()

# Sessions by date range (use Unix timestamps in MYT)
cursor.execute("""
    SELECT id, source, started_at, message_count, tool_call_count,
           input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
           reasoning_tokens, estimated_cost_usd, actual_cost_usd, model
    FROM sessions
    WHERE started_at >= ? AND started_at <= ?
    ORDER BY started_at
""", (start_ts, end_ts))
```

To get today's start in MYT: `TZ='Asia/Kuala_Lumpur' date -d 'YYYY-MM-DD 00:00:00 +08' '+%s'`

### 3. Subscription/OAuth Account Limits (ChatGPT Plus & Google AI Pro / Antigravity)

For subscription accounts using OAuth providers (e.g. `openai-codex` or `antigravity`), do not look for API key billing or treat local session tokens as the subscription quota meter. Use the gateway slash command:

```text
/usage
```

`/usage` combines two distinct evidence layers:

- **Current session telemetry:** input/output/cache/total tokens and API-call count recorded by Hermes.
- **Provider account limits (`AccountUsageSnapshot`):** live usage/quota metadata fetched through the authenticated OAuth credentials.

#### Antigravity (Google AI Pro Subscription)
Live quota is exposed per-model via Cloud Code Assist's `fetchAvailableModels` (`quotaInfo.remainingFraction` and `quotaInfo.resetTime`). When hooked to `fetch_account_usage()`, `/usage` natively reports remaining quota percentage and time until reset across active models (`gemini-3.7-flash`, `gemini-3.1-pro`, `claude-sonnet-4-6`, `claude-opus-4-6`).

#### OpenAI Codex (ChatGPT Plus/Pro)
The implementation resolves the Codex usage endpoint from the provider base URL (`/wham/usage`). The server may return only a primary session window; treat an omitted secondary window as a data gap rather than assuming no weekly limit exists.

For terminal-side historical activity, use:

```bash
hermes insights --days 1 --source telegram
```

or `/insights 1` in the gateway. This reads Hermes' local session database and reports sessions, models, messages, tools, and recorded token totals; it is not a direct ChatGPT Plus quota meter. On a populated database this can take longer than a 30-second shell timeout; retry with a longer timeout before concluding it is unavailable.

Interpret status carefully:

- `OpenAI API: ✗` means no API key is configured and is expected for the Plus OAuth route.
- `OpenAI Codex: ✓ logged in` is the relevant authentication evidence.
- `Model/Provider` in `/status` shows the selected/runtime-facing configuration; use `/usage` for account limits and `/insights` for historical model usage.

**Evidence boundary:** report the account snapshot's raw provider, plan, windows, percentages, and reset timestamps separately from Hermes-local token analytics. Never convert Hermes tokens into Plus quota/credits without a documented provider mapping.

### 4. Provider Balance Check

**DeepSeek:**
```bash
curl -s https://api.deepseek.com/user/balance -H "Authorization: Bearer ${DEEPSEEK_API_KEY}"
```
Returns balance by currency (USD, CNY) with granted vs topped-up breakdowns.

**Other providers:** Check their respective billing/balance API endpoints.

### 5. Cost Calculation

Use the provider's current pricing tiers. See `references/deepseek-pricing.md` for verified DeepSeek pricing.

```python
def deepseek_cost(input_tokens, output_tokens, cache_read_tokens):
    """Estimate cost for DeepSeek V4 Flash in USD."""
    return (
        input_tokens * 0.14 / 1_000_000 +      # cache miss input
        cache_read_tokens * 0.0028 / 1_000_000 + # cache hit input
        output_tokens * 0.28 / 1_000_000         # output
    )
```

> **NOTE:** `input_tokens` in state.db = cache MISS tokens. `cache_read_tokens` = cache HIT tokens. Bill at different rates — do not merge.

### 6. Burn Rate & Runway Projection

- Track cost per day over 3-7 days for a stable average
- Compare against remaining balance to estimate runway
- Free-tier models contribute $0 cost. See `references/free-tier-models.md` for the full list of
known free models (`deepseek-v4-flash-free`, `mimo-v2.5-free`, `nemotron-3-ultra-free`,
`qwen3.6-plus-free`). NULL-model sessions (unclassified) also count as free for cost purposes.

```python
daily_avg = total_cost_last_7d / 7
runway_days = remaining_balance_usd / daily_avg
```

### 7. Session DB Schema (relevant columns)

From `sessions` table in `/home/ubuntu/.hermes/state.db`:
- `input_tokens` — cache miss input tokens (billed at higher rate)
- `output_tokens` — output tokens
- `cache_read_tokens` — cache hit input tokens (billed at lower rate)
- `cache_write_tokens` — tokens written to cache (not directly billed)
- `reasoning_tokens` — thinking/reasoning tokens (included in output)
- `estimated_cost_usd` — Hermes' internal estimate (often 0 if unconfigured)
- `actual_cost_usd` — actual cost from provider (often 0 if not fed back)
- `cost_status` — 'unknown' if cost tracking not configured
- `model` — model name
- `billing_provider` — provider used for billing

### 8. Live 7-Day Cache Hit Rate (from agent.log, not state.db)

The session DB does NOT expose per-call cache ratios. The `cache=H/T` metric
only appears in agent.log API-call lines:

```
agent.conversation_loop: API call #11: model=deepseek-v4-flash-free provider=opencode-zen in=62352 out=412 total=62764 latency=5.4s cache=61184/62352 (98%)
```

Measure the 7-day window by parsing agent.log (rotated logs: agent.log.1,
agent.log.2... keep the newest plus prior files covering the window):

```python
import re
from datetime import datetime, timedelta

cutoff = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
pat = re.compile(r'cache=(\d+)/(\d+)')
hit = miss = n = 0
for logf in ['/home/ubuntu/.hermes/logs/agent.log']:
    with open(logf) as f:
        for line in f:
            if line[:10] < cutoff or 'cache=' not in line:
                continue
            m = pat.search(line)
            if m:
                h, t = int(m.group(1)), int(m.group(2))
                hit += h; miss += (t - h); n += 1
tot = hit + miss
print(f'7d: {n} calls, hit={hit:,} miss={miss:,} total={tot:,} rate={100*hit/tot:.1f}%')
```

**Pitfall — messages table column is `content`, not `body`**: querying
`SELECT body FROM messages` fails with `sqlite3.OperationalError: no such
column: body`. Use `content`. Cache ratios are NOT stored per-message in
state.db at all — agent.log is the only source for this metric. (2026-07-31)

## Pitfalls

- **cost_status = "unknown"**: Hermes does NOT auto-compute costs unless pricing is configured. Always calculate manually from raw token counts + provider pricing.
- **Time zone**: Session timestamps are Unix UTC. Convert to/from MYT (UTC+8) using `TZ='Asia/Kuala_Lumpur'`.
- **Cache token volume**: DeepSeek's cache_read_tokens can exceed input_tokens per session because the cache prefix (system prompt, tools, skills) is larger than individual requests. This is expected.
- **Free models have 0 cost**: Sessions via opencode-zen free tier store token counts in DB but incur no billing. See `references/free-tier-models.md` for the complete list.
- **NULL model in DB**: Sessions with `model IS NULL` or `model = ''` are unclassified. Do not include them in paid-cost aggregation — filter with `WHERE model IS NOT NULL AND model != ''`.
- **credential_pool lookup**: auth.json's `source` field (e.g. `env:DEEPSEEK_API_KEY`) tells where the key comes from, not the key itself. Source the `.env` file to load it: `source /home/ubuntu/.hermes/.env`.

## References

- `references/deepseek-pricing.md` — Confirmed DeepSeek pricing tiers (verified from live docs)
- `references/state-db-queries.md` — Reusable SQL queries for daily/weekly reporting
- `references/free-tier-models.md` — Known free-tier models that incur zero API cost
- `references/tavily-usage-check.md` — Tavily API usage endpoint (GET /usage), checking all 11 keys from .env, per-key vs account-level breakdown, pricing-per-call mapping
