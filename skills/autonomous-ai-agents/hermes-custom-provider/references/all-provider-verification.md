# All-Provider Zero-Token Verification

## Trigger

User says "test semua provider", "verify every provider", or "one API call per provider, jangan burn token". The deliverable is connectivity proof for EVERY provider identity that holds a credential — not just the config-level ones.

## Enumeration: every credential source (structure verified 2026-08-20)

1. **config.yaml `providers:`** — keyed custom providers; resolvable via `resolve_provider_full(slug, user_providers=..., custom_providers=...)`.
2. **auth.json `credential_pool`** — rotation pools. Shape: dict `provider -> LIST of entry dicts` (NOT wrapped in an `entries` key). Observed entry fields:
   - env-referenced pools (a6api, deepseek, openai-api, opencode-zen/go): `label`, `source`, `secret_fingerprint`, `base_url` — the actual key lives in `.env`; the pool entry has NO token field.
   - manual pools (custom:ftf): `access_token` + per-entry `base_url` + `active` flag + `label` (e.g. main-ftf / ftf-ml / ftf-rr / ftf-dev).
   - OAuth pool (openai-codex): `access_token`/`refresh_token` per entry.
3. **auth.json `providers.<name>`** — OAuth token storage, e.g. `providers.openai-codex.tokens.{access_token, refresh_token}`.
4. **.env `*_API_KEY` vars** — scan NAMES only; a pool entry may reference an env key that is the real credential.
5. **Plugin profiles** `~/.hermes/plugins/model-providers/*` — plugin-registered providers may NOT resolve via `resolve_provider_full` (observed: `a6api-gateway` → `NONE`), but their pool entries carry `base_url` so probing still works.

`hermes auth list` gives a fast inventory of credential groups per provider (labels, counts, source types) without touching secrets.

## Probe rule

One `GET {base}/v1/models` per provider identity, `Authorization: Bearer`, browser User-Agent MANDATORY (see Cloudflare pitfall), timeout ~25s. Zero tokens burned — model selection is irrelevant for this test. Print only status / model count / first-3 IDs / latency. NEVER print key values (names + lengths only).

## Endpoint quirks (observed)

- **a6api.com**: 403 "error code: 1010" to plain urllib default UA → 200 with Firefox UA.
- **chatgpt.com/backend-api/me** with codex OAuth token from a VPS: 403 HTML edge block — zero-token proof NOT possible for `openai-codex`; report UNVERIFIED and offer one tiny inference (burns subscription quota) if the user approves.
- **minimax** (`api.minimax.io/anthropic/v1`, Anthropic-style): pool may be empty with no env key → nothing to test; say so, don't fabricate.
- A pool key can duplicate an env key (a6api + a6api-gateway share `A6API_API_KEY`); probe each provider identity separately anyway — different base URLs.

## Session snapshot (2026-08-20, all HTTP 200 /v1/models — WILL GO STALE, re-probe)

a6api 73 · a6api-gateway 73 · apimaster 46 · fiq 9 · ftf 19 (env key) + 19 (pool main-ftf) · deepseek 2 · openai-api 124 · opencode-go 28 · opencode-zen 18. `openai-codex`: UNVERIFIED (edge 403). `minimax`: no credentials.

## Caveats

- `.env` keys may exist that NO provider references (e.g. `FTF_API_KEY` env while the ftf provider actually uses the manual pool) — report the fact, don't silently "fix" it.
- A 403 Cloudflare block is NOT a key problem; a 401 IS. Label failures by cause.
