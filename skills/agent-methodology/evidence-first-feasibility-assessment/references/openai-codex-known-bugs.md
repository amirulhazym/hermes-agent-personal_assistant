# openai-codex Known Bugs (Verified 2026-07-28)

**Provider:** Built-in `openai-codex` OAuth provider in Hermes Agent  
**Hermes version tested:** v0.17.0 (2026.6.19)  
**API:** Codex Responses API (not standard OpenAI Chat Completions)

## Root Cause Pattern

The Codex Responses API stream delivers text via `output_text.delta` events, but the **final `response.output[]` is empty**. Hermes' response validator checks `response.output` → finds empty list → triggers "Invalid API response" → falls back to backup model.

This is a **stream backfill bug** in `run_agent.py` (line ~7476-7478): the stream event parser fails to convert Codex stream events into output items for the final response object.

## Verified Issues

| Issue | Title | Status | Severity | Key Detail |
|-------|-------|--------|----------|------------|
| [#5736](https://github.com/NousResearch/hermes-agent/issues/5736) | GPT-5.x returns empty `response.output` — agent loop falls back | 🔴 OPEN (Apr 7) | Medium | Affects all tested gpt-5.x models. Fallback recovers but primary model is useless. |
| [#5883](https://github.com/NousResearch/hermes-agent/issues/5883) | GPT-5.4 fails normal mode, works verbose mode | 🔴 OPEN (Apr 7) | Medium | `-v` flag bypasses stream backfill bug. Stream event parser timing issue. |
| [#5732](https://github.com/NousResearch/hermes-agent/issues/5732) | Codex stream completes with empty output → classified malformed | 🔴 OPEN (Apr 7) | Medium | Intermittent. Tool-call-only or partially materialized final responses. |
| [#5678](https://github.com/NousResearch/hermes-agent/issues/5678) | "Responses API returned no output items" — stream delivers text but output[] empty | 🟡 CLOSED | Medium | Still referenced in newer bugs as same pattern. |
| [#61850](https://github.com/NousResearch/hermes-agent/issues/61850) | Ollama codex_responses loses terminal response after tool calls | 🔴 OPEN | Low | Ollama-specific variant of the empty-output pattern. |
| [#72915](https://github.com/NousResearch/hermes-agent/pull/72915) | Fix: classify Codex account token failures properly | 🟡 PR open | P2 | Prevents retrying token failures as unknown errors. |
| [#72690](https://github.com/NousResearch/hermes-agent/pull/72690) | Fix: harden Codex quota probe token refresh | 🟡 PR open | P2 | Security-sensitive — affects auth/sandboxing. |

## Workarounds (from issue #5883)

1. **Verbose mode** — `hermes chat -v` or `hermes chat --verbose`. The `-v` flag changes stream event timing, which sometimes lets the backfill complete before validation.
2. **Retry** — The fallback chain automatically retries 3 times. Some responses succeed on retry 2 or 3.
3. **Fallback model** — Configure a reliable backup model in config.yaml. When openai-codex fails, Hermes silently falls back.

## Detection

If user reports "Empty/malformed response" or "falling back to backup model" when using openai-codex:
1. Check gateway logs: `grep -i "empty\|malformed\|fallback\|response.output" ~/.hermes/logs/gateway.log | tail -20`
2. Try same query with `-v` flag
3. Check if specific model is affected (gpt-5.4 is worst; gpt-5.5 may be more stable)

## Alternative

If openai-codex is unreliable for production use, consider **CatGPT-Gateway** as a custom provider alternative. See `hermes-custom-provider` → `references/catgpt-gateway-setup.md`. It uses browser automation to drive the ChatGPT web UI, exposing a standard Chat Completions endpoint — bypassing the Codex Responses API entirely.

## Architecture Note

`openai-codex` is NOT a standalone provider plugin. It is embedded directly in `run_agent.py` (5525 lines) — the core agent loop. Provider-specific branches check `self.provider == "openai-codex"` and `self.api_mode == "codex_responses"` inline. This means:
- Bugs in the stream handler can affect the entire agent loop
- Fixes require touching core agent code, not a plugin
- The 6036-commit gap between v0.17.0 and main may include fixes — but `hermes update` carries risk of breaking other providers
