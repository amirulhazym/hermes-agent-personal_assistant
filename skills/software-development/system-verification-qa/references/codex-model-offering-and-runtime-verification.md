# Codex Model Offering vs Runtime Verification

## Purpose

Reusable protocol for answering: “Is this model/provider pairing genuinely allowed and offered, or is Hermes using a wrong setup?” Applies especially to `openai-codex` OAuth, but the evidence boundaries generalize to other providers.

## Verdict boundaries

Keep these separate in the final report:

- **Configured:** `config.yaml` selects `model.default`, `model.provider`, and any explicit endpoint.
- **Catalog-listed:** the authenticated provider model endpoint returns the exact slug with non-hidden visibility.
- **Callable:** a successful request using the same provider credential accepts the slug.
- **Serving:** the exact target session’s `API call #N` log lines show the provider and model sent for that turn.
- **Provider-internal execution:** Hermes cannot prove whether a provider internally substitutes another model after accepting the request. State this blind spot explicitly.

A picker entry, static catalog entry, or typed model ID is not proof of catalog availability or inference entitlement.

## Minimal Codex procedure

1. Read active `~/.hermes/config.yaml` and capture only:
   - `model.provider`
   - `model.default`
   - `model.base_url`
   - `fallback_providers`
   - `agent.reasoning_effort`
   - global/per-platform reasoning display flags
2. Identify the exact session ID from the matching `agent.turn_context` line in `~/.hermes/logs/agent.log`.
3. Query the authenticated Codex catalog endpoint used by Hermes:

   `GET https://chatgpt.com/backend-api/codex/models?client_version=1.0.0`

   Use the same Hermes-resolved OAuth credential, but print no token. Record HTTP status and only sanitized target metadata: `slug`, `visibility`, `supported_in_api`, supported reasoning levels, and plan metadata.
4. Correlate only that session ID in `agent.log`:
   - `OpenAI client created ... provider=... model=...`
   - `API call #N: model=... provider=...`
   - `API call failed ...` if present
   - `Turn ended ... model=...`
   - `Fallback activated ...` if present
5. Query `state.db.sessions` for the same/current session: `model`, `billing_provider`, `billing_base_url`, `model_config`, `reasoning_tokens`, `api_call_count`, and `end_reason`.
6. If recent successful API calls for the exact model/provider already exist, classify runtime callable as proven and do not burn another inference request. If there are no successful calls, use a single minimal inference only if catalog evidence alone cannot answer the user's question.
7. Report four labels separately: CONFIGURED, CATALOG-LISTED, CALLABLE, ACTUALLY SERVING. Include any unproven provider-side substitution or account-entitlement boundary.

## Reasoning verification

Reasoning must be checked at multiple layers:

1. Hermes config: `agent.reasoning_effort`.
2. Provider/model metadata: accepted effort values for the exact slug.
3. Session DB: `model_config.reasoning_config` (`enabled`, `effort`).
4. Session DB: non-zero `reasoning_tokens` proves generation occurred for that session.
5. Display: `display.show_reasoning` and `display.platforms.<platform>.show_reasoning` control visibility, not generation.

Do not infer “reasoning is off” from a short response or missing visible thinking. Conversely, do not infer that a config value reached the wire without checking provider-specific transport logic or runtime/session evidence.

## Broad-audit correlation pitfall

A broad parser over the last N log lines can select an auxiliary compression, title-generation, cron, or background call from another provider and label it as the main turn's “first API call.” This creates a false configured-vs-serving divergence.

Correct handling:

- anchor on the exact `turn_context` session ID;
- filter every API-call line by that session ID where the log format supports it;
- distinguish main-turn calls from auxiliary/background calls;
- if the automated result conflicts with targeted evidence, mark the automated result `MIS-CORRELATED` and inspect its selection logic;
- do not silently average or discard the contradiction.

## Worked evidence pattern (2026-08-04)

Observed on a live Hermes install:

- Active config selected `openai-codex` + `gpt-5.6-luna`, with Codex backend base URL and empty fallback chain.
- The authenticated Codex `/models` request returned HTTP 200; the target record had `visibility=list`, `supported_in_api=true`, and included `xhigh` in supported reasoning levels.
- The exact WhatsApp session's `turn_context` and subsequent `API call #N` records were tagged `model=gpt-5.6-luna provider=openai-codex`.
- The session row recorded the same billing provider/base URL, `reasoning_config.enabled=true`, `effort=xhigh`, and non-zero `reasoning_tokens`.
- A bundled broad-window audit reported a DeepSeek first call. Targeted session evidence showed that this was not the main Codex turn; the result was treated as a correlation error, not a fallback finding.

This pattern proves the configuration and current route without requiring an additional inference probe when successful calls are already present.

## Authoritative references

- OpenAI Codex model selection: https://developers.openai.com/codex/models
- OpenAI API model catalog: https://developers.openai.com/api/docs/models
- OpenAI Codex authentication: https://developers.openai.com/codex/auth
- Hermes Codex live catalog endpoint (authentication required): https://chatgpt.com/backend-api/codex/models?client_version=1.0.0
