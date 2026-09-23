# Hermes Model Provider Refresh — 2026-09-23

## Goal

Refresh only these Hermes provider catalogs and compatibility rules: `openai-codex`, `opencode-zen` (free-tier policy only), `deepseek`, and `antigravity`, so the shared `/model` flow exposes choices that are current and actually callable from the VPS.

## Verified current state

- OpenAI Codex OAuth live discovery returns: `gpt-6-astra`, `gpt-6-sol`, `gpt-6-luna`, GPT-5.6 family/context variants, and `gpt-5.5`.
- Hermes Codex offline fallback has no GPT-6 entries, so transient discovery failure would regress the picker.
- DeepSeek live `/v1/models` returns `deepseek-flash` plus legacy/current V4 entries; official canonical V4.1 Flash ID is `deepseek-flash`.
- Hermes DeepSeek fallback/default still prefers retired `deepseek-v4-flash`, and the thinking detector does not match canonical `deepseek-flash`.
- OpenCode Zen official free list now has 8 free SKUs, but `jev-1.13-free` is System One (`/systemone`), not a chat/generative model.
- All 7 official Zen free generative/chat models returned HTTP 403 from this VPS: `OpenCode's free tier can only be used from within OpenCode`.
- Current Zen picker exposes 84 entries including paid, stale, deprecated, test, and free IDs; this violates the requested free-only boundary and callable-only intent.
- Antigravity live catalog returns 14 logical chat models and already includes `gemini-3.8-flash`; plugin `DEFAULT_MODEL` remains `gemini-3.7-flash`.
- Google managed-agent ID `antigravity-preview-09-2026` is not a model ID for this custom Cloud Code bridge and must not be added to Hermes `/model`.
## Locked implementation direction pending owner gate

1. `openai-codex`: keep live OAuth discovery authoritative; add GPT-6 Astra/Sol/Luna to the offline fallback and test live/fallback parity. Do not invent `-900k` GPT-6 aliases unless current metadata explicitly marks them eligible.
2. `deepseek`: make `deepseek-flash` the canonical selectable/default Flash ID; retain V4 Pro while official service remains available; hide retired V4 Flash/Vision IDs from the picker while preserving an explicit backward-compatible normalization path to `deepseek-flash`.
3. DeepSeek reasoning: treat `deepseek-flash` as thinking-capable and align effort mapping with the current official API contract.
4. `opencode-zen` free-only: fail closed. Do not expose paid Zen models, stale free IDs, or Jev in the normal chat `/model` picker. Because direct Hermes calls to every official free generative SKU are currently 403, expose no Zen-free selectable model until a legitimate callable path is verified.
5. Do not spoof OpenCode client identity or headers to bypass its free-tier restriction.
6. `antigravity`: preserve the existing live entitlement catalog; update only the plugin fallback/default from Gemini 3.7 Flash to Gemini 3.8 Flash, with regression tests. Do not add managed-agent IDs.
7. Shared gateway contract: one catalog/selection source for Telegram and WhatsApp; no channel-specific model lists.
8. Source-first only: no direct edits under `~/.hermes/hermes-agent` or `~/.hermes/plugins/antigravity-provider`.

## Acceptance criteria

- Interactive `/model` on Telegram and WhatsApp reads the same refreshed provider state.
- Codex GPT-6 models remain visible even when live discovery is unavailable.
- DeepSeek picker shows canonical current IDs and `deepseek-flash` receives correct thinking controls.
- Zen cannot accidentally select paid models under the free-only policy and cannot offer known-403 free SKUs as working choices.
- Antigravity default/fallback resolves to `gemini-3.8-flash` without disturbing its existing custom live patch set.
- Provider model cache is invalidated during deployment so stale entries cannot resurrect removed choices.
- Tests, reconstruction checks, secret scan, PII review, and runtime smoke checks pass before any release claim.
