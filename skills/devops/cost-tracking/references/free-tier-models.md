# Free-Tier Models (zero-cost billing)

All known models that incur no API cost. Token counts are still recorded in the session DB but
`estimated_cost_usd` / `actual_cost_usd` are always 0.

## Known Free Models

| Model | Provider / Source | Notes |
|-------|-------------------|-------|
| `deepseek-v4-flash-free` | opencode-zen | DeepSeek V4 Flash via subsidized tier |
| `mimo-v2.5-free` | opencode-zen | Mimo via subsidized tier |
| `nemotron-3-ultra-free` | opencode-zen | Nemotron via subsidized tier |
| `qwen3.6-plus-free` | opencode-zen | Qwen 3.6 Plus via subsidized tier |
| `hy3-free` | opencode-zen | Hermes 3 (hy3) via subsidized tier |

All these are served through the `opencode-zen` provider — a free/subsidized routing layer.
The `-free` suffix in the model name distinguishes them from paid variants (e.g.
`deepseek-v4-flash` vs `deepseek-v4-flash-free`).

## NULL / Empty Model Field

Sessions with `model IS NULL` OR `model = ''` in the session DB are unclassified — they were
created before model tracking was enabled or by integrations that don't report a model name.

**Recommendation:** Treat NULL-model sessions as free for cost-reporting purposes (their token
counts contribute to usage metrics but cannot be priced reliably). When aggregating cost by model,
filter them out explicitly:

```sql
WHERE model IS NOT NULL AND model != ''
```

## Checking Which Models Are Free vs Paid

Query the session DB for all distinct model values seen recently:

```sql
SELECT model, COUNT(*) as sessions
FROM sessions
WHERE started_at >= ?
GROUP BY model
ORDER BY sessions DESC;
```

Compare against the free-models table above. Any model NOT in the free list is assumed paid at its
provider's published rates. Unknown models (not in either list) should default to `deepseek-v4-flash`
pricing as a conservative estimate.

## Updating This List

New free-tier models appear when opencode-zen or other subsidized providers add them. Re-verify by:

1. Querying distinct models from session DB
2. Checking the `billing_provider` column
3. Adding any new `*-free` model seen to this table
