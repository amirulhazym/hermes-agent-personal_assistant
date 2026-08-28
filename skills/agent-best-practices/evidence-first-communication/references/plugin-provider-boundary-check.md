# Plugin Provider Boundary Check

Use when a Hermes/provider plugin appears installed or an API probe succeeds, but `/model`, `--provider`, or the gateway still reports an unknown/missing provider.

## Failure model

Provider integrations commonly cross independent layers:

```text
plugin/profile registration
  → canonical picker inventory
  → CLI/provider resolver
  → model-switch persistence
  → model catalog/discovery
  → plugin middleware/transport
  → gateway reload
  → channel/UI E2E
```

A pass at one layer does not promote the others to pass.

## Read-only probe matrix

Run in a fresh Hermes Python process with the active `HERMES_HOME`:

```python
from hermes_cli.config import load_config
from providers import list_providers
from hermes_cli.models import CANONICAL_PROVIDERS
from hermes_cli.providers import get_provider, resolve_provider_full

cfg = load_config()
slug = "<provider>"
print([(p.name, p.display_name) for p in list_providers() if p.name == slug])
print([p for p in CANONICAL_PROVIDERS if p.slug == slug])
print("built_in", get_provider(slug, allow_network=False))
print("resolved", resolve_provider_full(
    slug, cfg.get("providers") or {}, cfg.get("custom_providers") or []
))
```

Interpretation:

- profile/canonical present + `resolve_provider_full is None`: registration exists, but CLI routing metadata is missing. `model.provider` alone is insufficient; add a supported `providers.<slug>` definition.
- resolved provider has the wrong base URL/API mode/key mapping: configuration boundary is wrong; do not re-auth first.
- resolved provider is correct but picker row is absent: inspect authenticated-provider filtering and credential visibility.

## Picker inventory proof

Use the same function that backs the picker, not only the static cache:

```python
from hermes_cli.model_switch import list_authenticated_providers
rows = list_authenticated_providers(
    current_provider=slug,
    current_model="<exact-model>",
    user_providers=cfg.get("providers") or {},
    custom_providers=cfg.get("custom_providers") or [],
    for_picker=True,
    probe_custom_providers=False,
)
print([r for r in rows if r.get("slug") == slug])
```

Require both:

- a row for the expected slug; and
- `total_models > 0` with the expected exact model IDs.

A row with zero models is not picker success.

## In-process provider catalog rule

If the plugin intercepts LLM execution in-process and its configured base URL is only a dummy loopback URL, the picker must not depend on normal `/v1/models` discovery. Persist an explicit provider catalog:

```yaml
providers:
  <provider>:
    name: <display name>
    base_url: http://127.0.0.1:<port>/v1
    key_env: <placeholder-or-real-credential-env>
    default_model: <provider/model>
    models:
      - <provider/model-a>
      - <provider/model-b>
    discover_models: false
```

The plugin's setup/select path should preserve this mapping so a later selection does not recreate the same failure. Do not put real tokens in the provider mapping or in diagnostic output.

## Switch and inference proof

Exercise the actual switch path with live config:

```python
from hermes_cli.model_switch import switch_model
result = switch_model(
    raw_input="<provider/model>",
    current_provider="<current-provider>",
    current_model="<current-model>",
    explicit_provider="<provider>",
    user_providers=cfg.get("providers") or {},
    custom_providers=cfg.get("custom_providers") or [],
)
print(result)
```

Then make one minimal live request through the plugin's real middleware/transport. Keep these outcomes separate:

- `switch_model success=True`: resolver/switch contract proven;
- `AGY_OK`/equivalent completion: provider inference proven;
- picker row with models: picker substrate proven;
- fresh gateway/channel `/model` response with buttons: user-facing E2E proven.

For reasoning models, a tiny `max_tokens` value can be invalid even when auth is correct: thinking tokens may consume the budget, and some models reject reasoning-off entirely. If a short probe returns empty content with `finish_reason=length`, inspect the request transform and retry only with the model's valid reasoning/budget contract. Preserve the first failure; do not replace it with a success narrative.

## Status ledger

Report one status per boundary:

```text
REGISTRATION: PROVEN / UNVERIFIED
RESOLUTION: PROVEN / FAILED
PICKER INVENTORY: PROVEN / EMPTY / UNVERIFIED
SWITCH PATH: PROVEN / FAILED
LIVE INFERENCE: PROVEN / FAILED
GATEWAY RELOAD: PROVEN / PRE-CHANGE / UNVERIFIED
CHANNEL/UI E2E: PROVEN / UNVERIFIED
```

A restart before the config/plugin edit is `PRE-CHANGE`, not proof of the new runtime. A direct API pass never upgrades channel/UI E2E.
