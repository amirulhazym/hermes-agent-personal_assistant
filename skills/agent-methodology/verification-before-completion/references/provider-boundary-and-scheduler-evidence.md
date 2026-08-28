# Provider Boundary and Scheduler Evidence

Use this reference when a scheduled reminder or notification depends on an external LLM/API provider.

## Failure pattern

A runtime config can contain an OpenAI-compatible origin or an already-versioned base:

- `https://host`
- `https://host/v1`

Blindly appending `/v1/chat/completions` to both creates either a valid URL or a duplicated path such as `https://host/v1/v1/chat/completions`. The latter may return HTTP 404 even though credentials and the provider itself work.

Provider name and credential mapping are also coupled runtime inputs. Adding a provider in config without adding its environment-variable mapping can select the wrong key or report a misleading missing-key failure.

## Minimal adapter contract

Normalize before constructing the endpoint:

```python
api_base = base_url.rstrip("/")
if not api_base.endswith("/v1"):
    api_base += "/v1"
url = f"{api_base}/chat/completions"
```

Test both base forms and test the provider-to-key mapping. Then call the configured model against the actual endpoint and capture the raw status/result.

## Scheduler evidence ladder

Do not treat these as equivalent:

1. `run request accepted` — request-layer evidence only.
2. `last_run_at` changed and status is `ok` — scheduler execution evidence.
3. Expected stdout/state accounting changed — script-path evidence.
4. Delivery log contains fresh destination success — transport evidence.
5. Destination-side message is observed — strongest user-facing evidence.

Report the lowest level actually proven. A successful provider call proves generation, not scheduler execution or WhatsApp delivery.

## Regression coverage

At minimum, include:

- origin base URL gets `/v1`;
- versioned base URL does not get duplicate `/v1`;
- provider has the correct credential environment variable;
- failed generation does not increment delivery accounting;
- successful generation increments accounting exactly once;
- real scheduler run has fresh metadata and delivery evidence before claiming delivery.
