# DeepSeek Pricing (verified from api-docs.deepseek.com, Jul 04 2026)

## DeepSeek V4 Flash

| Component | Rate per 1M tokens |
|-----------|-------------------|
| Input (Cache Hit) | **$0.0028** |
| Input (Cache Miss) | **$0.14** |
| Output | **$0.28** |

Maximum output: 384K tokens
Context window: 1M tokens

Features: JSON Output, Tool Calls, FIM (non-thinking only), Chat Prefix Completion.

## DeepSeek V4 Pro

| Component | Rate per 1M tokens |
|-----------|-------------------|
| Input (Cache Hit) | **$0.003625** |
| Input (Cache Miss) | **$0.435** |
| Output | **$0.87** |

Concurrency limit: 500 (vs 2500 for Flash)

## Deprecation Notice

`deepseek-chat` and `deepseek-reasoner` model names will be deprecated on **2026/07/24 15:59 UTC**. They correspond to non-thinking and thinking modes of deepseek-v4-flash respectively.

## Balance API

**Endpoint:** `GET https://api.deepseek.com/user/balance`
**Auth:** Bearer token (DEEPSEEK_API_KEY)

Response shape:
```json
{
  "is_available": true,
  "balance_infos": [
    {"currency": "USD", "total_balance": "0.00", "granted_balance": "0.00", "topped_up_balance": "0.00"},
    {"currency": "CNY", "total_balance": "18.94", "granted_balance": "0.00", "topped_up_balance": "18.94"}
  ]
}
```

**Billing deduction:** Expenses are deducted from topped-up or granted balance, preferring granted balance first.

## Models endpoint

**Endpoint:** `GET https://api.deepseek.com/v1/models`
Returns available model IDs (deepseek-v4-flash, deepseek-v4-pro).

## Credential Access

The API key is stored in the env file at `/home/ubuntu/.hermes/.env`:
```
DEEPSEEK_API_KEY=sk-ede...
```

Source it in shell:
```bash
source /home/ubuntu/.hermes/.env
echo $DEEPSEEK_API_KEY
```

Or use the auth.json credential pool reference, which shows `source: "env:DEEPSEEK_API_KEY"`.
