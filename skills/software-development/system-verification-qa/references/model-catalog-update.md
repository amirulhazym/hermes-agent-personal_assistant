# Model Catalog Update Procedure

## When to use this

When a new model family is released by a provider (OpenAI, Anthropic, Google, etc.) and needs to be added to Hermes' model picker and available model lists. The catalog is spread across two files and five+ lists.

## Files to update

| File | Provider key / context |
|---|---|
| `hermes_cli/models.py` | `_PROVIDER_MODELS["openai"]` — Native OpenAI provider |
| `hermes_cli/models.py` | `_PROVIDER_MODELS["openai-api"]` — OpenAI API provider |
| `hermes_cli/models.py` | `_PROVIDER_MODELS["nous"]` — OpenRouter-style IDs (prefixed with `openai/`) |
| `hermes_cli/models.py` | `OPENROUTER_MODELS` — Fallback OpenRouter catalog with descriptions |
| `hermes_cli/codex_models.py` | `DEFAULT_CODEX_MODELS` — openai-codex provider models |

Each provider list may have a different model ID format:

| Format | Example | Where used |
|---|---|---|
| Bare model ID | `gpt-5.6-luna` | `openai`, `openai-api`, `openai-codex` providers |
| Prefixed OpenRouter ID | `openai/gpt-5.6-luna` | `nous` provider, `OPENROUTER_MODELS` |

## Procedure

### 1. Add to `_PROVIDER_MODELS["openai"]` (bare IDs)

File: `hermes_cli/models.py` — look for the `"openai": [` block. Add new models at the TOP (most recent/most capable first).

```python
"openai": [
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-5.4",
    ...
],
```

### 2. Add to `_PROVIDER_MODELS["openai-api"]` (bare IDs)

Same file, same pattern. Search for `"openai-api": [` block.

### 3. Add to `_PROVIDER_MODELS["nous"]` (prefixed IDs)

Same file. The nous provider uses `openai/gpt-5.6-*` format:

```python
# OpenAI
"openai/gpt-5.6-sol",
"openai/gpt-5.6-terra",
"openai/gpt-5.6-luna",
"openai/gpt-5.5",
```

### 4. Add to `OPENROUTER_MODELS` (prefixed IDs with descriptions)

Same file, near top. Entries are `(model_id, description)` tuples. Add descriptions that match the model tier:

```python
("openai/gpt-5.6-sol",            "frontier reasoning"),
("openai/gpt-5.6-terra",          "balanced everyday"),
("openai/gpt-5.6-luna",           "fast, cost-sensitive"),
```

### 5. Add to `DEFAULT_CODEX_MODELS` (bare IDs)

File: `hermes_cli/codex_models.py`. Add at the top of the list:

```python
DEFAULT_CODEX_MODELS: List[str] = [
    "gpt-5.6-sol",
    "gpt-5.6-terra",
    "gpt-5.6-luna",
    "gpt-5.5",
    ...
```

### 6. Reasoning efforts — usually handled automatically

The function `_github_reasoning_efforts_for_model_id()` in `models.py` maps model IDs to effort levels by prefix:

```python
def _github_reasoning_efforts_for_model_id(model_id: str) -> list[str]:
    raw = (model_id or "").strip().lower()
    if raw.startswith(("openai/o1", "openai/o3", "openai/o4", "o1", "o3", "o4")):
        return list(COPILOT_REASONING_EFFORTS_O_SERIES)
    normalized = normalize_copilot_model_id(model_id).lower()
    if normalized.startswith("gpt-5"):
        return list(COPILOT_REASONING_EFFORTS_GPT5)
    return []
```

So `gpt-5.6-*` and `openai/gpt-5.6-*` will both normalize to `gpt-5.6-*` → matches `gpt-5` prefix → returns `["minimal", "low", "medium", "high"]`. **No code change needed for reasoning efforts** as long as the model ID starts with `gpt-5`.

### 7. Verify everything works

Run this verification script:

```python
import sys
sys.path.insert(0, '/home/ubuntu/.hermes/hermes-agent')
from hermes_cli.models import (
    _PROVIDER_MODELS, github_model_reasoning_efforts,
    OPENROUTER_MODELS
)
from hermes_cli.codex_models import DEFAULT_CODEX_MODELS

# Check reasoning efforts auto-map
for m in ['gpt-5.6-sol', 'gpt-5.6-terra', 'gpt-5.6-luna']:
    efforts = github_model_reasoning_efforts(m)
    print(f'{m}: {efforts}')

# Check model presence per provider
for prov in ['openai', 'openai-api', 'openai-codex', 'nous']:
    models = _PROVIDER_MODELS.get(prov, DEFAULT_CODEX_MODELS)
    if prov == 'openai-codex':
        from hermes_cli.models import _codex_curated_models
        models = _codex_curated_models()
    gpt56 = [m for m in models if 'gpt-5.6' in m]
    print(f'{prov}: {len(models)} total, gpt-5.6: {gpt56}')

# Check OpenRouter catalog
gpt56_or = [m for m, d in OPENROUTER_MODELS if 'gpt-5.6' in m]
print(f'OpenRouter: {gpt56_or}')
```

## Pitfalls

- **Don't forget the `nous` provider and `OPENROUTER_MODELS`** — they use prefixed IDs (`openai/gpt-5.6-*`), not bare IDs.
- **Model ordering matters** — most capable / latest model first in the list. The picker often shows models in list order.
- **Don't skip `codex_models.py`** — the `openai-codex` provider is generated from `DEFAULT_CODEX_MODELS`, not from `_PROVIDER_MODELS`.
- **Don't add models that don't exist yet** — verify the model is actually released via API docs or live `/v1/models` response.
- **The model picker shows models from the CURRENT provider's curated list, not all providers** — `curated_models(provider)` returns the list for the active provider. Adding models to `openai` won't make them visible when using `opencode-zen`.
