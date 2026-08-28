# A6API Provider Setup (July 2026)

Complete working configuration for A6API (a6api.com) as a custom Hermes provider.

## A6API Details

- Type: OpenAI-compatible routing proxy/gateway
- Base URL: `https://a6api.com/v1`
- Auth: Bearer token (API key)
- Model discovery: `GET /v1/models` returns 52 models (as of July 2026)
- Key models confirmed working: gpt-5.6-sol, gpt-5.6-terra, gpt-5.6-luna, claude-sonnet-5, claude-opus-4-8, grok-4.5, gpt-5.4-mini

## Plugin: `__init__.py`

```python
"""A6API provider profile - OpenAI-compatible routing proxy/gateway.

A6API (a6api.com) is a model aggregator/router similar to OpenRouter.
OpenAI-compatible API, multi-vendor auto-routing.
Base URL: https://a6api.com/v1
"""

from providers import register_provider
from providers.base import ProviderProfile

a6api = ProviderProfile(
    name="a6api",
    aliases=("a6api-gateway",),
    display_name="A6API",
    description="A6API model gateway - multi-vendor routing proxy",
    signup_url="https://a6api.com",
    env_vars=("A6API_API_KEY",),
    base_url="https://a6api.com/v1",
    auth_type="api_key",
    default_aux_model="gpt-5.4-mini",
    fallback_models=(
        "gpt-5.6-sol",
        "gpt-5.6-terra",
        "gpt-5.6-luna",
        "claude-sonnet-5",
        "claude-opus-4-8",
        "grok-4.5",
    ),
)

register_provider(a6api)
```

## Plugin: `plugin.yaml`

```yaml
name: a6api-provider
kind: model-provider
version: "1.0"
description: A6API model gateway - routing proxy with multi-vendor channels
author: amirulhazym
```

## Config: `config.yaml` additions

```yaml
model:
  provider: a6api
  base_url: https://a6api.com/v1
  default: deepseek-v4-pro
  models:
    claude-opus-4-8:
      context_length: 1000000
    claude-sonnet-5:
      context_length: 1000000
    gpt-5.6-luna:
      context_length: 1050000
    gpt-5.6-sol:
      context_length: 1050000
    gpt-5.6-terra:
      context_length: 1050000
    grok-4.5:
      context_length: 500000

providers:
  a6api:
    name: A6API
    base_url: https://a6api.com/v1
    api_key_env: A6API_API_KEY
    default_model: gpt-5.6-sol
```

## Config commands used

```bash
hermes config set model.provider a6api
hermes config set model.base_url https://a6api.com/v1
hermes config set providers.a6api.name A6API
hermes config set providers.a6api.base_url https://a6api.com/v1
hermes config set providers.a6api.api_key_env A6API_API_KEY
hermes config set providers.a6api.default_model gpt-5.6-sol
```

## .env

```
A6API_API_KEY=<key>
```

## Verification commands

```bash
# 1. Plugin discovery
cd ~/.hermes/hermes-agent && python3 -c "
import sys; sys.path.insert(0, '.')
from providers import get_provider_profile, _discover_providers
import providers
providers._discovered = False
providers._discover_providers()
p = get_provider_profile('a6api')
print(f'Found: {p is not None}')
print(f'base_url: {p.base_url if p else \"N/A\"}')
"

# 2. Resolution chain
cd ~/.hermes/hermes-agent && python3 -c "
import sys; sys.path.insert(0, '.')
import yaml
from hermes_cli.providers import resolve_provider_full
with open('/home/ubuntu/.hermes/config.yaml') as f:
    cfg = yaml.safe_load(f) or {}
result = resolve_provider_full('a6api', cfg.get('providers'), None)
print(f'Found: {result is not None}')
print(f'id: {result.id if result else \"N/A\"}')
"

# 3. Live API test
A6KEY=$(grep A6API_API_KEY ~/.hermes/.env | cut -d= -f2)
curl -s https://a6api.com/v1/chat/completions \
  -H "Authorization: Bearer $A6KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"claude-sonnet-5","messages":[{"role":"user","content":"Reply: a6api works"}],"max_tokens":20}'
```

## Reasoning/Extended Thinking Notes

- `reasoning_effort` is set to `xhigh` globally in config.yaml
- GPT-5.6-sol/terra/luna: Native OpenAI reasoning support - should work
- Claude models (sonnet-5, opus-4-8): Use extended thinking (different API mechanism). May not translate through A6API's OpenAI-compatible proxy layer
- Grok-4.5: Unknown - needs testing

## Timeline of July 18 Fix

1. Plugin files existed but `model.provider` was `opencode-go`, not `a6api`
2. `hermes config set model.provider a6api` + restart - config persisted
3. Plugin registered correctly (`providers._REGISTRY` had `a6api`)
4. `/model --provider a6api` still failed: "Unknown provider 'a6api'"
5. Root cause: `resolve_provider_full()` in slash command handler checks `providers:` config section first. Plugin registration in `_REGISTRY` doesn't suffice
6. Fix: Added `providers.a6api.*` entries to config.yaml
7. After restart: `resolve_provider_full('a6api', user_providers, None)` returns valid ProviderDef
8. Live API test: claude-sonnet-5 via A6API responds correctly
