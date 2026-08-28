# System-Resolution Debugging — Hermes Model/Picker Investigation Recipe

Condensed from a 2026-07-09 session where the agent wrongly concluded the MiniMax
provider was dead based on a shell `curl`/DNS test, while the user was actively
receiving minimax-m3 responses.

## The dual code-path trap

Hermes resolves a model/provider through TWO independent paths that can disagree:

| Path | Code entry | What it reads | Result for `minimax` |
|------|-----------|---------------|----------------------|
| **Picker** (`/model X --provider Y`) | `runtime_provider.resolve_runtime_provider()` | built-in plugin registry → `api.minimax.io/anthropic`, `anthropic_messages` | Shows correct metadata (1M ctx, cost) |
| **Gateway chat** (`run_agent`) | `gateway/run.py:_resolve_runtime_agent_kwargs()` → `resolve_runtime_provider()` with NO args → uses `config.yaml model.provider` | same plugin, BUT logs show `base_url=https://api.minimax.com/v1` when config has a stale `model.base_url` | Actual API call uses whatever the resolved runtime says |

Key: the `/model` command saves `model.default` + `model.provider` to config.yaml
(`cli.py:7608-7611`) but does NOT always rewrite `model.base_url`. If config.yaml
has a stale `model.base_url` from a custom `providers:` block, the gateway may use
it. The custom `providers.minimax` block is often **dead** — `_get_named_custom_provider("minimax")` returns `None` because the built-in plugin shadows it.

## Minimal reproducer (run inside hermes-agent dir)

```python
import sys, os
sys.path.insert(0, "/home/ubuntu/.hermes/hermes-agent")
# load .env
with open("/home/ubuntu/.hermes/.env") as f:
    for line in f:
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
os.environ["HERMES_HOME"] = "/home/ubuntu/.hermes"

from hermes_cli.runtime_provider import resolve_runtime_provider
from hermes_cli.models import curated_models_for_provider, normalize_provider

# Exact gateway call (no args -> reads config.yaml model.provider)
r = resolve_runtime_provider()
print(r.get("provider"), r.get("base_url"), r.get("api_mode"))

# Check if a model is in a provider's curated list
print("hy3-free" in [m for m, _ in curated_models_for_provider("opencode-zen")])
```

## Gateway log is ground truth

```bash
grep -E 'provider=|base_url=|Fallback activated' ~/.hermes/logs/agent.log | tail -30
```

Look for:
- `provider=X base_url=Y model=Z` → what was ACTUALLY called
- `Fallback activated: A → B` → primary failed, silently switched to B
- `APIConnectionError` / `401` / `404` → the real failure mode

If you see `Fallback activated: minimax-m3 → deepseek-v4-flash`, the user is talking
to deepseek, NOT minimax — even if `/status` says `Model: minimax-m3 (minimax)`.

## Symptoms this recipe catches

1. `/model hy3-free` (no --provider) resolves to wrong provider because the model
   isn't in that provider's `_PROVIDER_MODELS` curated list → picker falls back to
   current provider. Fix: add the model to `_PROVIDER_MODELS["opencode-zen"]` in
   `hermes_cli/models.py`.
2. Two picker entries with near-identical names ("MiniMax" capital M from
   `PROVIDER_GROUPS` display name, "minimax" lowercase from provider ID) — by design,
   not a bug, but confusing. Built-in plugin wins over custom config block.
3. Silent fallback hides the real provider — user thinks they're on model X but
   they're on the fallback.
