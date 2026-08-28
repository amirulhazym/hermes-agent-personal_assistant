# Antigravity Live Catalog and Wire Routing

## Purpose

Use this reference when an OAuth-backed provider's picker appears stale, a public model ID is rejected by the provider, or a model is visible in one layer but not usable in another.

This is a provider-specific example of the class-level rule in the parent skill: separate public/logical IDs, live entitlement IDs, wire route IDs, config/cache IDs, and loaded-runtime state.

## Proven reproduction (25 Aug 2026)

The installed plugin had a static five-model catalog in `models.py` and returned that same list from `hermes_provider.fetch_models()`. The active account's live Cloud Code Assist catalog was queried with the authenticated OAuth/project context:

```text
POST https://cloudcode-pa.googleapis.com/v1internal:fetchAvailableModels
body: {"project": "<project_id>"}
header: X-Goog-Api-Client: google-cloud-sdk vscode_cloudshelleditor/0.1

HTTP 200
raw model entries: 25
```

The raw catalog contained:

```text
gemini-3.7-flash-tiered
gemini-3.6-flash-low
gemini-3.6-flash-medium
gemini-3.6-flash-high
```

It did not contain bare `gemini-3.7-flash`. The public Google model page confirms the public logical ID, but that does not prove the private Cloud Code Assist route.

Control/target tests through the same plugin transport:

```text
gemini-3.1-pro             -> success
 gemini-3.5-flash           -> success
gemini-3.7-flash            -> HTTP 404 NOT_FOUND
gemini-3.7-flash-tiered     -> success, finish_reason=stop
```

The durable mapping was therefore:

```text
picker/logical: google-antigravity/gemini-3.7-flash
wire/request:   gemini-3.7-flash-tiered
```

A picker-only addition would have produced a selectable but broken model.

## Reusable implementation pattern

1. Inspect the provider source to determine whether discovery is static, `/v1/models`, or a private entitlement RPC.
2. Call the live catalog with the credential/project actually used by the runtime. Do not assume the provider CLI and plugin read the same OAuth store.
3. Preserve raw catalog IDs and response status in a secret-free diagnostic output.
4. Implement wire-to-logical normalization for picker display. Deduplicate route variants such as `-low`, `-medium`, `-high`, `-tiered`, `-thinking`, and `-agent` into one logical family where the provider contract supports it.
5. Implement logical-to-wire mapping for inference. Keep the mapping in the request transformation path, not only in config or picker code.
6. Merge the live list with a bounded static fallback. The fallback is for catalog outages only; it is not evidence that the provider is current.
7. Add regression tests for: raw catalog parsing, route normalization, target wire ID, invalid/internal-only entries, and a live target request.
8. Re-run all boundaries independently:

```text
CATALOG DISCOVERY
PROFILE REGISTRATION
CLI RESOLUTION
PICKER INVENTORY
MODEL SWITCH
LIVE INFERENCE
GATEWAY/PLUGIN RELOAD
CHANNEL OR UI E2E
```

Do not report the last boundary as proven from an earlier one.

## Cache and reload gate

Hermes can cache provider model IDs. After changing discovery or model mappings:

```bash
hermes model --refresh
```

A running gateway may still have the old plugin module in memory. Restart it using the supported external/operator path, then re-run the actual picker/channel check. The sequence `source changed -> unit tests pass -> picker inventory passes in a fresh process` is not yet Telegram/UI E2E.

## Endpoint caution

Test alternate catalog and inference endpoints separately. In the reproduction above, production catalog discovery returned current model entitlements, but a production inference probe returned:

```text
HTTP 429 RESOURCE_EXHAUSTED
```

The existing daily inference route accepted the mapped 3.7 request. This is evidence to preserve the working route while investigating quota/capacity—not permission to switch endpoints based on documentation or a third-party recommendation alone.

## Evidence ledger template

```text
public model documentation:      CAPABILITY only
live entitlement catalog:        CATALOG-PROVEN / raw IDs attached
logical-to-wire mapping:         SOURCE + unit-test proven
existing-model control:          LIVE-PROVEN
new-model inference:             LIVE-PROVEN or HTTP-ERROR with exact status
picker inventory:                FRESH-PROVEN / CACHE-STALE / UNVERIFIED
gateway/plugin reload:           PROVEN only after restart + fresh check
Telegram/WhatsApp/UI E2E:        UNVERIFIED until observed
```

## Sources

- Official public model ID: https://ai.google.dev/gemini-api/docs/models/gemini-3.7-flash
- Provider source/catalog implementation: https://github.com/jaeyeopme/antigravity-provider/blob/main/src/antigravity_provider/models.py
- Provider repository: https://github.com/jaeyeopme/antigravity-provider
- Private catalog request shape (secondary reference; live response remains the authority): https://docs.picoclaw.io/docs/providers/antigravity
