# Verifying a pasted Hermes `/status` block (field-source map + anomalies)

When a user pastes a `/status` output (e.g. the `📊 **Hermes Gateway Status**` block) and asks "verify betul² / ada aku suspect apa-apa GG" — do NOT trust the text. The block is genuine generator output, but several fields can mislead. Trace EVERY field to its source of truth. Proven 2026-08-07 on session `20260807_130033_1ef8c9`.

## Confirming the block is genuine output (not fabrication)

The exact cosmetic strings come from `locales/en.yaml` → `gateway.status.*`. Real labels:
- `header` = `📊 **Hermes Gateway Status**`
- `tokens` = `**Cumulative API tokens (re-sent each call):** {tokens}`  ← literal label
- `context` = `**Context:** {used} / {total} ({pct}%)`
- `agent_running`, `platforms`, `created`, `last_activity`, `model` (`{model} ({provider})`)

The generator is `gateway/slash_commands.py` `_handle_status_command()`. If the pasted block's wording matches these strings exactly, it is genuine `/status`.

## Field → source of truth map

| `/status` field | Real source | Notes |
|---|---|---|
| `Created` | `sessions_store` metadata `created_at` | **NOT** the DB session birth. Store entry can be RE-created hours later (see Anomaly A). |
| `Last Activity` | `sessions_store` metadata `updated_at` | Both from `~/.hermes/sessions/sessions.json` key `agent:main:<plat>:<type>:<id>`. |
| `Session ID` | DB `sessions.id` | The ID embeds a timestamp: `20260807_130033` = 13:00:33. |
| `Title` | DB `sessions.title` | |
| `Model: X (provider)` | session override → cached agent → DB row → config | Provider shown is runtime; DB `billing_provider` may differ (e.g. runtime `deepseek` vs DB `billing_provider=opencode-zen`). |
| `Context: {used}` | compressor `last_prompt_tokens` | Matches DB/sessions-store `last_prompt_tokens`. |
| `Context: {total}` | compressor `context_length` | **TWO sources fight**: `config.yaml model.context_length` vs built-in `agent/model_metadata.py` CONTEXT_LENGTH table. Shown value = whichever won resolution (see Pitfall B). |
| `Cumulative API tokens ({tokens})` | `db_total_tokens` = `input+output+cache_read+cache_write+reasoning` from DB `sessions` row | Verified by re-summing the columns. Label is misleading — see Pitfall C. |
| `Agent Running` | `active_agents` count at query time | |
| `Connected Platforms` | configured transports | |

## Pitfall A — `Created` can lag true session birth by hours

Session ID timestamp and DB `started_at` = TRUE birth. `/status` shows the sessions-store `created_at`, which is when the CURRENT store entry was written. Reality:
- A session split (context compression) creates a new session ID in the DB: log line `Session split detected: <parent> → <child> (compression)`.
- A later `Session expiry: 1 sessions to finalize (telegram:1)` can finalize/clear the store entry.
- The next turn then writes a NEW store entry → `created_at` jumps to that moment.

Proven (2026-08-07): session born 13:00:51 (split log) and ID `..._130033` = 13:00:33, but `/status` said `Created: 19:46`. Store re-created after a 19:36:50 expiry-finalize, first new turn ~19:45-19:46. So a user querying "when was this session created?" gets the STORE-ENTRY time, ~6h46m late. Not a data-integrity bug — a "created_at means store-entry creation" semantics gap.

**Cross-check:** confirm true birth via the session ID's embedded timestamp OR `SELECT started_at FROM sessions WHERE id=...`.

## Pitfall B — requested alias is not necessarily the canonical serving model

`/status` prints the requested/session model ID from the override or cached agent; it does not canonicalize against `response.model`. This matters for provider aliases.

Proven on 2026-08-07: DeepSeek's live `/v1/models` listed only `deepseek-v4-flash` and `deepseek-v4-pro`, while Hermes's picker still exposed `deepseek-chat` and `deepseek-reasoner`. Root cause: `hermes_cli/models.py` merges the static curated list into the live API result, re-inserting legacy IDs that upstream discovery omitted. A direct request with `model=deepseek-chat` returned HTTP 200 with `response.model=deepseek-v4-flash`. Thus the status label `deepseek-chat (deepseek)` described the requested compatibility alias and route, not the canonical model returned by the provider.

For historical calls, do not promote a current probe into direct historical proof. If the exact call's `response.model` was not persisted, label the canonical model as high-confidence/inferred from same-day direct probing and official mapping, not historically proven.

## Pitfall C — context denominator must follow the serving capability, not a similarly named old model

`/status` uses the cached compressor's `context_length` when an agent/override exists. Resolution priority is explicit global `model.context_length` → provider/model-specific lookup → built-in metadata.

For the 2026-08-07 DeepSeek case, `1,000,000` was correct for the canonical `deepseek-v4-flash`: DeepSeek's official pricing page states a 1M context, the live alias probe returned `deepseek-v4-flash`, and Hermes resolves both `deepseek-chat` and `deepseek-v4-flash` to 1,000,000. The earlier claim that per-model 128K entries for unrelated configured models imposed an operator-wide 128K cap was wrong. Only an explicit applicable `model.context_length` or selected-model/custom-provider override governs that route.

Never infer context from an old alias's historical capability. Resolve the actual provider route and canonical serving model first, then compare against an explicit applicable config override.

## Pitfall D — a singular DB billing provider can be stale after a mid-session switch

`hermes_state.py::update_token_counts()` writes `billing_provider = COALESCE(billing_provider, ?)` and likewise for `billing_base_url`. Once non-null, later calls through another provider do not replace those fields via this path. In the proven session, the first seven API calls used `deepseek-v4-flash-free/opencode-zen`; later calls used `deepseek-chat/deepseek`, while the DB row retained `billing_provider=opencode-zen`.

This does NOT prove later traffic used OpenCode. `/status` prioritizes override/cached-agent provider and only falls back to DB billing fields. Treat the DB's singular billing provider as first-route metadata, not a per-call routing ledger. Use `agent.log` or persisted request events to reconstruct mixed-provider sessions.

## Pitfall E — "Cumulative API tokens (re-sent each call)" is a misleading label

The VALUE is faithful and reproducible: `db_total_tokens = input + output + cache_read + cache_write + reasoning` from the `sessions` row. But the LABEL "re-sent each call" oversells it — it is the SUM over the whole session, NOT re-sent per call. On this session `2,340,333` = 345,283 input + 27,050 output + **1,968,000 cache_read** + 0 + 0: 84% of it is prompt-cache reads. Report the value as *cumulative session bucket sum*, not as re-sent token count.

## Verification procedure (do this before answering)

1. Match block wording to `locales/en.yaml` `gateway.status.*` → confirms format provenance.
2. Query the DB `sessions` row and re-sum token buckets, but do not treat `model` or `billing_provider` as the whole runtime truth.
3. Read `sessions/sessions.json` for store-side timestamps and `last_prompt_tokens`.
4. Trace `agent.log` for the exact session ID: model, provider, base URL, switch boundary, and every API-call route.
5. Probe the provider's live `/models` endpoint. Compare it against `provider_model_ids()` / picker output; static-only extras may be stale aliases.
6. If model identity is ambiguous, send a minimal direct request to the exact provider/model route and inspect `response.model`. State clearly that a current probe is not historical call capture.
7. Resolve context length for the canonical serving model, then check only explicit config overrides applicable to that route. Do not apply unrelated per-model entries.
8. Inspect `/status` source priority (override → cached agent → DB → config) and DB update semantics such as `COALESCE` before calling fields contradictory.
9. Trace gateway birth/expiry events for timestamp anomalies.
10. Present separate verdicts for requested model ID, canonical response model, runtime provider, DB billing metadata, and context capability; attach evidence and confidence to each.