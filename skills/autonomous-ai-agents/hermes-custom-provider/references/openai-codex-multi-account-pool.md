# openai-codex Multi-Account Credential Pool (Verified 2026-08-07)

**Hermes version:** v0.17.0 (upstream 1dfe781e, +6 local carried commits)
**Context:** User's ChatGPT Plus account hit 100% weekly Codex usage limit; needed automatic fallback to other Plus accounts without manual re-login. User has several Plus accounts and plans to add more.

## Verdict

Native support — no wrapper scripts, no hacks. Hermes credential pools rotate between multiple ChatGPT accounts on the same `openai-codex` provider automatically. The "different auth approach per account" idea is unnecessary: all Plus accounts go through the same OAuth device flow, and the pool handles rotation.

## Mechanism (source evidence, ~/.hermes/hermes-agent/)

| Piece | Evidence |
|---|---|
| Pool per provider | `~/.hermes/auth.json` → `credential_pool.openai-codex` is a LIST of entries (id, label, auth_type=oauth, source, access_token, refresh_token, priority, last_status, last_error_code, last_error_reason, last_error_message, last_error_reset_at, request_count, base_url, last_refresh) |
| Add = append, not overwrite | `hermes_cli/auth_commands.py` (~line 310): builds `PooledCredential(..., source=SOURCE_MANUAL_DEVICE_CODE)` + `pool.add_entry(entry)`. Code comment: "Add a distinct, self-contained pool entry per account ... instead of routing through the singleton `_save_codex_tokens` save path" — fixes issue #39236 (a second `hermes auth add openai-codex` previously overwrote the first account's singleton-mirrored entry). `--label <name>` supported for naming accounts. |
| Failover pool core | `agent/credential_pool.py`: STATUS_OK / STATUS_EXHAUSTED / STATUS_DEAD; `_exhausted_ttl(error_code)` cooldown (401=5 min, 429=1 h, default=1 h) — but **provider-supplied `reset_at` OVERRIDES the TTL**: `_exhausted_until()` returns `last_error_reset_at` when set (parsed from the error body, supports epoch s/ms + ISO); terminal auth reasons excluded from rotation (`token_invalidated`, `token_revoked`, `invalid_token`, `invalid_grant`, `unauthorized_client`, `refresh_token_reused`); openai-codex entries sync from auth store + refresh via `refresh_codex_oauth_pure()` |
| Error → rotation | `agent/error_classifier.py`: `rate_limit` (429), `billing` (402 / "insufficient_quota" / "credits exhausted"), `auth` (401/403). Docs flow: ChatGPT/Codex "usage limit reached" → rotate to next pool key IMMEDIATELY, no retry (the cap won't clear on retry); generic transient 429 → retry once, second 429 → rotate; 402 → rotate immediately; 401 → OAuth refresh then rotate |
| Strategies | `credential_pool_strategies:` in config.yaml — `fill_first` (default), `round_robin`, `least_used`, `random` |
| Cross-provider layer | `fallback_providers:` list in config.yaml (each entry: provider + model); `hermes fallback` CLI manages it; activates only when ALL pool entries exhausted |

## Official docs

- https://hermes-agent.nousresearch.com/docs/user-guide/features/credential-pools
- https://hermes-agent.nousresearch.com/docs/user-guide/features/fallback-providers

## Setup recipe (headless VPS, no TTY)

1. Per account: ensure **"Device code authorization for Codex" is ON** in ChatGPT Security Settings (chatgpt.com/settings/security) BEFORE starting. A code generated before enabling is invalid — request a fresh one after enabling.
2. Run the native flow in background PTY — it prints URL + code then **auto-polls** (NO input() prompt; Ctrl+C cancels):
   ```
   terminal(command="hermes auth add openai-codex --label account2", background=true, pty=true, notify_on_complete=true)
   ```
3. Poll process output, relay `https://auth.openai.com/codex/device` + code to the user. **IMPORTANT:** user must log in with the NEW account, not the maxed one (same-account re-login creates a useless duplicate entry).
4. Process auto-completes on approval → `notify_on_complete` wakes you — no need to poll manually.
5. Verify: `hermes auth list openai-codex` → N entries. `active_provider` in auth.json is unchanged on subsequent adds (only the FIRST credential sets it).
6. Optional hardening: add a cheap provider to `fallback_providers` (e.g. deepseek-v4-flash-free) so an all-exhausted day still works.

Note: the usercode endpoint rate-limits login attempts (429) — backoff is built in (Retry-After honored, capped 60s).

## Caveats

- **reset_at override — the pool knows the real reset time (VERIFIED live 2026-08-07):** when the provider error body carries a reset timestamp, the pool stores `last_error_reset_at` (epoch) on the entry and `_exhausted_until()` returns THAT absolute time instead of the 1h TTL. ChatGPT's weekly-limit error includes the reset time; Hermes parses it. Live evidence: maxed account showed `last_error_reset_at = 2026-08-08 13:25:53` (MYT, ~16 h away) — cooldown ran until the ACTUAL weekly reset, **zero intermediate probes**, and every request went straight to account 2. So the answer to "will it keep probing account 1 every hour?" is NO — check `last_error_reset_at` per entry in auth.json to see exactly when an account wakes up.
- **fill_first flips back to primary on reset even if the standby still has quota:** after reset, the next request probes account 1 → success → it becomes primary again (first healthy entry). The standby account's quota is NOT burned while idle. Intended behaviour — the alternation is driven by the PRIMARY's exhaustion state, not by the standby's usage (user asked "tak tunggu acc 2 habis quota dulu?" — correct, it doesn't).
- **One failed turn when current account is already maxed:** `fill_first` tries account 1 first → 429 → marks exhausted → rotates. Next turn is on account 2. Self-heals after the weekly reset: cooldown expires, account 1 retried, succeeds, becomes primary again. No manual action needed.
- **Cache rotation penalty:** provider-side prompt caches are account-scoped. Rotating mid-conversation costs one full-price context re-read (docs warning).
- **Plus accounts cannot use API keys** (separate billing from ChatGPT subscription). All Plus accounts go through OAuth device flow.
- **Known stream bugs** (empty `response.output`, #5736/#5883/#5732) are unrelated to auth/quota — don't attribute rotation issues to them.
- The weekly-limit error body contains "usage limit" → classified as usage-limit → immediate rotation (not the generic-429 retry path).
