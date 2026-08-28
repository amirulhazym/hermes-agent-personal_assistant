# Provider Picker Discovery: OpenAI-Compatible Endpoints

## Trigger

Use this procedure when a newly configured OpenAI-compatible provider appears duplicated, unorganized, or contains non-chat products in `/model`.

## Root-cause pattern

Hermes may have both:

- A built-in canonical provider (for direct OpenAI API, commonly `openai-api`), and
- A user-configured `providers.<slug>` entry.

A natural-looking slug such as `openai` can collide with an alias or coexist with the built-in provider. The custom-provider picker path may fetch the raw `/v1/models` catalog, while the canonical path applies agent-compatibility filtering. The result is duplicate provider rows plus embeddings, image, audio, TTS, moderation, or realtime IDs.

## Reproduction/evidence recipe

Run from the Hermes source environment. Load `.env` only in-process and never print secret values:

```python
from hermes_cli.inventory import load_picker_context
from hermes_cli.model_switch import list_picker_providers

ctx = load_picker_context()
rows = list_picker_providers(
    current_provider=ctx.current_provider,
    current_base_url=ctx.current_base_url,
    current_model=ctx.current_model,
    user_providers=ctx.user_providers,
    custom_providers=ctx.custom_providers,
)
for row in rows:
    print({k: row.get(k) for k in ("slug", "name", "source", "total_models", "models")})
```

Capture these facts:

- all OpenAI-related slugs;
- whether the custom slug appears alongside the canonical slug;
- model count per row;
- whether non-agent product families are present;
- whether the user config contains an unnecessary custom block.

## Safe correction

If the user intends the real OpenAI API and Hermes already has `openai-api`:

1. Remove only the colliding custom `providers.openai` block.
2. Leave `OPENAI_API_KEY` in `.env`; keep the secret out of `config.yaml` and output.
3. Preserve unrelated `model.provider` and `model.default` values.
4. Clear only the affected cache:

```python
from hermes_cli.models import clear_provider_models_cache
clear_provider_models_cache("openai-api")
```

5. Re-run the picker functions in a fresh process.

## Discovery design

For the canonical direct OpenAI endpoint:

```text
live /v1/models availability
    intersected with
agent-capability catalog
    with curated safety fallback
```

Do not blindly expose every ID from `/v1/models`; that endpoint is a product catalog, not a Hermes-agent compatibility catalog. Do not replace live discovery with a manually maintained model list unless it is explicitly documented as an offline fallback.

For custom OpenAI-compatible gateways, preserve their provider-specific live discovery behavior because their `/models` endpoint may already expose only usable chat/tool models.

## Verification boundary

A cache clear plus source patch is not sufficient evidence. The final report must distinguish:

- configuration correction;
- candidate source change;
- targeted test result;
- fresh live provider-model output;
- fresh picker output;
- stale-cache behavior, if observed;
- full-suite status, if not run.

Never report `DONE` when the final patch has not been re-tested or when the picker was only inspected through a lower-level function rather than the actual picker path.
