# Tavily API Usage Checking

## Endpoint

```
GET https://api.tavily.com/usage
Authorization: Bearer tvly-YOUR_KEY
```

## Response Shape

```json
{
  "key": {
    "usage": 616,
    "limit": null,
    "search_usage": 441,
    "extract_usage": 7,
    "crawl_usage": 5,
    "map_usage": 0,
    "research_usage": 163
  },
  "account": {
    "current_plan": "Researcher",
    "plan_usage": 616,
    "plan_limit": 1000,
    "search_usage": 441,
    "extract_usage": 7,
    "crawl_usage": 5,
    "map_usage": 0,
    "research_usage": 163,
    "paygo_usage": 0,
    "paygo_limit": null
  }
}
```

## Checking All Keys at Once

When `TAVILY_API_KEYS` (plural) contains a list in `.env`:

```bash
source ~/.hermes/.env
# Use Python to iterate through keys
python3 -c "
import os, json, urllib.request

with open(os.path.expanduser('~/.hermes/.env')) as f:
    content = f.read()

# Parse TAVILY_API_KEYS from .env
import re
match = re.search(r'^TAVILY_API_KEYS=(.*)$', content, re.MULTILINE)
if match:
    val = match.group(1).strip()
    try:
        keys = json.loads(val)
    except:
        keys = [p.strip().strip(chr(34)).strip(chr(39)) for p in val.split(',') if p.strip()]

    for key in keys:
        req = urllib.request.Request('https://api.tavily.com/usage')
        req.add_header('Authorization', f'Bearer {key}')
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            print(f'{key[:12]}...: key_total={data[\"key\"][\"usage\"]}  plan={data[\"account\"][\"plan_usage\"]}/{data[\"account\"][\"plan_limit\"]}')
"
```

## Key Structure in .env

- `TAVILY_API_KEY` — main working key
- `TAVILY_API_KEYS` — JSON array or comma-separated list of additional keys

## Pricing (as of July 2026)

| Plan | Credits/Month | Notes |
|------|--------------|-------|
| Free (Researcher) | 1,000 | Search, Extract, basic Research |
| Paid plans | Higher | Advanced Research, Crawl, higher rate limits |

Cost per call: Search=1 credit, Extract=1 credit/URL, Research=variable, Crawl=variable.

## Notes
- Usage API returns data for current billing cycle only — no reset date shown
- `key.limit` is usually `null` for Researcher plan (cap is at plan level)
- Rate limit: 20 req/min for Researcher plan
- Dashboard: https://app.tavily.com
- API docs: https://docs.tavily.com/documentation/api-reference/endpoint/usage.md
