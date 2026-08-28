# Codex OAuth repair vs pooled-account add

## Trigger

A Hermes `openai-codex` request returns HTTP 401 with `error.code: token_invalidated` / `token_revoked`, while the stored JWT may still have a future `exp`.

## Key distinction

`hermes auth add openai-codex` is **not automatically a repair operation**. In the current implementation it runs a device-code login and adds a new independent pool entry with source `manual:device_code`; it intentionally does **not** overwrite `providers.openai-codex.tokens` or the existing `device_code` pool entry.

That is correct for adding a second ChatGPT account, but can leave the original singleton token active in runtime selection. Do not call it a re-auth fix without tracing which credential the gateway will select.

## Safe repair procedure

1. **Prove the failure** with a read-only probe to the exact Codex endpoint:
   `GET https://chatgpt.com/backend-api/codex/models?client_version=1.0.0`
   using the same Hermes-resolved credential. Capture HTTP status + sanitized error code.
2. **Inspect credential topology** (no tokens in output):
   - `providers.openai-codex.tokens` existence / `last_refresh`
   - `credential_pool.openai-codex` entry count, `source`, status/error metadata
   - existing session model overrides, which can persist an `api_key` in-memory.
3. **Choose the correct flow:**
   - Multi-account addition → `hermes auth add openai-codex`.
   - Repair the existing singleton-backed Codex runtime → use a verified login path that calls `_save_codex_tokens()` after device-code approval, so it updates `providers.openai-codex.tokens` and synchronizes the matching `device_code` pool entry.
4. **Do not assume a retry is enough.** Existing `/model --session` overrides retain resolved provider/api_key. After credential replacement, perform a fresh model switch or reset the affected channel session before testing.
5. **Verify all layers:**
   - auth store mtime / sanitized metadata changed;
   - direct `/models` returns 200 and record returned slugs;
   - one minimal Codex inference request returns 200;
   - test both Telegram and WhatsApp only when both are actually configured to `openai-codex`; a response from OpenCode Zen or `openai-api` proves nothing about Codex.

## Evidence boundaries

- JWT `exp` in future + `token_invalidated` = server-side invalidation, **not** normal expiry.
- A model picker listing is discovery/UI evidence only; it does not prove inference entitlement.
- A typed model ID accepted with a warning is not proof that the upstream Codex backend supports it.
- Do not claim the reason OpenAI revoked a token unless upstream returns it; `token_invalidated` alone does not identify the cause.

## Source paths (version-dependent; inspect before execution)

- `hermes_cli/auth_commands.py` — `auth add openai-codex` creates `manual:device_code` entries.
- `hermes_cli/auth.py` — `_save_codex_tokens()` updates the singleton and mirrors matching `device_code` pool entries.
- `gateway/run.py` — session model overrides can carry `provider`, `api_key`, and `base_url` across turns.
