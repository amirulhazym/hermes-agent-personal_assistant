# Session DB Queries for Cost Tracking

All queries target `/home/ubuntu/.hermes/state.db` (SQLite).

## Get today's sessions

```python
import sqlite3, time

conn = sqlite3.connect('/home/ubuntu/.hermes/state.db')
cursor = conn.cursor()

# Get MYT midnight timestamp
# 2026-07-04 00:00:00 +08:00 = 1783094400
today_start = 1783094400
now = int(time.time())

cursor.execute("""
    SELECT id, source, started_at, ended_at, message_count, tool_call_count,
           input_tokens, output_tokens, cache_read_tokens, cache_write_tokens,
           reasoning_tokens, estimated_cost_usd, actual_cost_usd, cost_status,
           model, billing_provider
    FROM sessions
    WHERE started_at >= ? AND started_at <= ?
    ORDER BY started_at
""", (today_start, now))
```

## Day-by-day aggregation (last 7 days)

```python
from collections import defaultdict

week_ago = today_start - 7 * 86400
cursor.execute("""
    SELECT id, started_at, message_count, tool_call_count,
           input_tokens, output_tokens, cache_read_tokens
    FROM sessions
    WHERE started_at >= ?
    ORDER BY started_at
""", (week_ago,))

day_stats = defaultdict(lambda: {'input':0, 'output':0, 'cacheread':0, 'msgs':0, 'sessions':0})
for row in cursor.fetchall():
    day_key = time.strftime('%a %b %d', time.localtime(row[1]))  # row[1] = started_at
    ds = day_stats[day_key]
    ds['input'] += row[3] or 0
    ds['output'] += row[4] or 0
    ds['cacheread'] += row[5] or 0
    ds['msgs'] += row[2] or 0
    ds['sessions'] += 1
```

## Cost breakdown by model (last N days)

Separates paid-model costs from free-tier, with per-model aggregation.

```python
from collections import defaultdict

FREE_MODELS = {
    'deepseek-v4-flash-free', 'mimo-v2.5-free',
    'nemotron-3-ultra-free', 'qwen3.6-plus-free',
}

# Pricing (per 1M tokens) — keep in sync with deepseek-pricing.md
PRICING = {
    'deepseek-v4-flash':  {'in': 0.14,   'out': 0.28,  'cache': 0.0028},
    'deepseek-v4-pro':    {'in': 0.435,  'out': 0.87,  'cache': 0.003625},
    'mimo-v2.5-pro':      {'in': 1.00,   'out': 4.00,  'cache': 0},      # unverified
    'minimax-m3':         {'in': 0.15,   'out': 0.60,  'cache': 0},      # unverified
}

# Default for unknown models — conservative (v4-flash rates)
DEFAULT_RATES = {'in': 0.14, 'out': 0.28, 'cache': 0.0028}

cursor.execute("""
    SELECT model,
           COUNT(*) as sessions,
           SUM(input_tokens) as total_in,
           SUM(output_tokens) as total_out,
           SUM(cache_read_tokens) as total_cache
    FROM sessions
    WHERE started_at >= ?
      AND model IS NOT NULL AND model != ''
    GROUP BY model
    ORDER BY COUNT(*) DESC
""", (week_ago,))

print(f"{'Model':<35} {'Sess':>4} {'InTok':>10} {'OutTok':>8} {'Cost(USD)':>10}")
print('-' * 72)
total_cost = 0.0
for row in cursor.fetchall():
    model = row[0]
    if model in FREE_MODELS:
        continue  # skip free models
    p = PRICING.get(model, DEFAULT_RATES)
    cost = ( (row[1] or 0) * p['in']
           + (row[2] or 0) * p['out']
           + (row[3] or 0) * p['cache'] ) / 1_000_000
    total_cost += cost
    print(f'{model:<35} {row[1]:>4} {row[2]:>10,} {row[3]:>8,} ${cost:>8.4f}')
print(f'{"TOTAL":<35} {"":>4} {"":>10} {"":>8} ${total_cost:>8.4f}')
```

> **NULL model rows**: Always filter `WHERE model IS NOT NULL AND model != ''` in paid-cost
> queries. NULL-model sessions are unclassified — treat as free-tier for cost purposes.

## Sessions table schema (key columns)

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT | Session identifier (e.g. cron_XXXX or datestamp) |
| source | TEXT | Platform: cron, telegram, whatsapp, subagent |
| started_at | REAL | Unix timestamp |
| ended_at | REAL | Unix timestamp (NULL if active) |
| message_count | INTEGER | Messages in session |
| tool_call_count | INTEGER | Total tool calls |
| input_tokens | INTEGER | Cache MISS input tokens |
| output_tokens | INTEGER | Output tokens |
| cache_read_tokens | INTEGER | Cache HIT input tokens |
| cache_write_tokens | INTEGER | Tokens written to cache |
| reasoning_tokens | INTEGER | Thinking/reasoning tokens |
| estimated_cost_usd | REAL | Hermes' internal estimate |
| actual_cost_usd | REAL | Actual cost from provider |
| cost_status | TEXT | 'unknown', 'estimated', 'actual' |
| model | TEXT | Model name |
| billing_provider | TEXT | Provider used for billing |

## Get credential source from auth.json

```bash
python3 -c "
import json
with open('/home/ubuntu/.hermes/auth.json') as f:
    d = json.load(f)
pool = d.get('credential_pool', {}).get('deepseek', [{}])[0]
print('Source:', pool.get('source'))
print('Base URL:', pool.get('base_url'))
print('Fingerprint:', pool.get('secret_fingerprint'))
"
```
