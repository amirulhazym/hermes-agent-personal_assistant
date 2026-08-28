# Provider Model Identity Verification (requested vs canonical vs billing)

Proven 2026-08-07 on session `20260807_130033_1ef8c9` (the `deepseek-chat` audit).

## Core concept: three identities, never conflate

| Identity | Where it lives | Meaning |
|---|---|---|
| **Requested** | `agent.model`, `sessions.model`, `config.yaml model.default` | The model ID the user picked / Hermes sent. May be a legacy alias. |
| **Canonical (served)** | `response.model` / first stream `chunk.model` | What the provider ACTUALLY served. Can differ from requested when aliases are remapped server-side. |
| **Billing metadata** | `sessions.billing_provider` / `billing_base_url` | DB attribution fields. Frozen at FIRST provider via `COALESCE(col, ?)` in `hermes_state.update_token_counts()` — NOT a per-call routing ledger. |

A `/status` line like `deepseek-chat (deepseek)` proves only what was REQUESTED and the runtime route. It does not prove the canonical serving model, and the DB `billing_provider=opencode-zen` does not prove later traffic used OpenCode.

## Proven case (2026-08-07)

- DeepSeek removed `deepseek-chat`/`deepseek-reasoner` from live `/v1/models` discovery on 2026-07-24 (official changelog); before that they pointed at non-thinking/thinking modes of `deepseek-v4-flash`.
- Hermes picker STILL offered them: `provider_model_ids()` merges the static `_PROVIDER_MODELS` curated list back into the live result, re-inserting IDs upstream removed. `cached_provider_model_ids()` also prefers a stale same-fingerprint cache entry over an empty live result.
- Direct probe: `POST model=deepseek-chat` → HTTP 200, `response.model=deepseek-v4-flash`. Alias still works server-side but is no longer discoverable — "discontinued from discovery", not "rejected".
- First 7 API calls of the session used `deepseek-v4-flash-free/opencode-zen`; later calls used `deepseek-chat/deepseek`; DB `billing_provider` stayed `opencode-zen` (COALESCE freeze).
- `/status` model line is built from priority: session override → cached agent → DB row → config (`gateway/slash_commands.py` `_handle_status_command`). It prints the requested ID; it does not canonicalize against `response.model` (pre-fix).

## Verification procedure (do all, in order)

1. **Live catalog vs picker output:** `GET {base_url}/v1/models` (bearer auth) → compare against `provider_model_ids(provider)` / the picker. Extra static-only IDs = stale curated merge. Filter must be applied on final result AND cache reads, not just one merge path.
2. **Direct probe with the EXACT requested ID:** send one minimal `chat/completions` with `model=<requested>` and `max_tokens` small; record HTTP status AND `response.model` in the response body. A current probe is evidence for the current endpoint, NOT historical proof of past calls — label past-call canonical as HIGH CONFIDENCE, not PROVEN.
3. **Deprecation check:** consult the provider's official changelog for the model name (e.g. DeepSeek `/updates` page). "Discontinued" often means removed from discovery while the alias still works — never conclude rejection without a probe.
4. **Leak paths beyond the curated list:** provider profile `fallback_models` (used when live fetch fails — a stale list here can offer ONLY deprecated IDs), `default_aux_model` (compression/title calls), `MODEL_ALIASES`/`DIRECT_ALIASES` (`hermes_cli/model_switch.py`) — a bare alias resolving through these can silently reroute to the wrong provider (cost escalation) or to OpenRouter's stale catalog.
5. **Pricing check:** cost estimation is keyed on the model ID passed in — an alias priced at old rates while the canonical model has no entry (or different rates) makes session costs wrong. Check `agent/usage_pricing.py` for the canonical model.
6. **Thinking-mode wire shape:** provider profiles gate `build_api_kwargs_extras` on assumptions like "deepseek-chat = V3 no thinking". Server-side alias remapping makes those assumptions stale; probe with an explicit thinking flag and check whether `reasoning_content` comes back (echo-trap risk on multi-turn). A single-turn probe with no reasoning_content lowers the risk but does not fully prove the multi-turn echo contract — run the 2-turn echo probe (`scripts/probe-reasoning-echo.py`): turn 1 thinking-enabled captures `reasoning_content`, turn 2 replays it in the assistant message; HTTP 200 on turn 2 = echo contract VERIFIED. Proven 2026-08-07: `deepseek-v4-flash` thinking enabled, 2-turn echo → 200, no 400.
7. **Cross-check billing:** `SELECT model, billing_provider, billing_base_url, input_tokens, output_tokens, cache_read_tokens FROM sessions WHERE id LIKE '%<sid>%'` — token totals are aggregate across ALL providers in the session; the singular billing_provider column is first-route metadata. Per-provider attribution comes from `agent.log` `API call #N: model=... provider=...` lines, not the DB.

## Fix outcome (merged to main 2026-08-07; user decision = FULL PURGE)

User's definitive answer was **full purge**, not graceful alias routing:

- `_DEPRECATED_MODEL_ALIASES` map + `_filter_deprecated_aliases(provider, ids, live_ids=None)`: deprecated IDs dropped from picker unless live catalog still serves them; applied to final results AND cache reads (stale `provider_models_cache.json` entries can otherwise resurface aliases after upgrade — clear/refetch at deploy).
- **Typed aliases are DENIED, not routed.** `DIRECT_ALIASES` builtin entries and `_LEGACY_MODEL_ROUTES` were REMOVED. `detect_provider_for_model` returns None for any ID in the deny registry (before the OpenRouter lookup — otherwise a stale aggregator catalog hijacks the route = billing surprise). Typed `/model deepseek-chat` fails loud "no model detected".
- `agent.response_model` captured per call; `sessions.canonical_model` column (added via SCHEMA_SQL declarative reconcile — idempotent, no manual migration); billing fields switched to `CASE WHEN ? IS NOT NULL THEN ? ELSE col END` (last-write-wins, NULL-safe).
- Cost estimation canonical-first: `response_model or model`.
- Full-purge sweep: normalization fallback → `deepseek-v4-flash` (was `deepseek-chat`), profile `aliases=()`, aggregator/godmode fallback lists updated, pricing + context-metadata alias entries removed. Grep ALL file types (`*.py`, `*.json`, `*.yaml`) — 121 references found across curated lists, profiles, normalization, pricing, metadata, cache fixtures, tests. Categorize each: **guard** (deny-list/stale-cache filter — keep, it actively rejects), **fixtures** (bulk-replace mechanical), **history docs** (comments explaining the removal — keep). Guard tests assert aliases are rejected in every path (detect/resolve/normalize).

## Deployment notes (2026-08-07)

- Merged to main via **git worktree isolation**: branch in `/tmp/hermes-fix`, main working tree left untouched until merge. WIP in main (unrelated catalog/observability work, 39 files) preserved via `git stash push -u` → `git merge --ff-only` → `git stash pop`; no conflicts because hunks didn't overlap — ALWAYS verify BOTH sets of changes exist in overlapping files after pop (grep counts per marker string), don't trust the clean pop message.
- **Push to GitHub: `git ls-remote` succeeding does NOT mean push works.** ls-remote is anonymous for public repos; push requires stored credentials (SSH key / git-credentials / GITHUB_TOKEN / gh CLI). Check `~/.ssh/`, `~/.git-credentials`, `.env` for `GITHUB_*` BEFORE promising a push.
- **Deployed-to-disk ≠ live-verified.** After merge without gateway restart, the running gateway still executes pre-fix code in memory; files on disk are candidate-until-restart. Label it "deployed to disk, live verification pending restart" — do not claim live.

## Evidence grading

- Current live probe ≠ historical proof. Same-day probe + official mapping + request logs = HIGH CONFIDENCE for historical calls, not PROVEN.
- If `response.model` was not persisted historically, say so — that observability gap is itself a finding.
