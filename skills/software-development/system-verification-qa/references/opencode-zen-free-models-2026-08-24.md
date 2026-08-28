# OpenCode Zen — Free Model Status (live-verified 2026-08-24)

Live probe of every `*-free` model under `https://opencode.ai/zen/v1` with the account's own `OPENCODE_ZEN_API_KEY`. Supersedes `opencode-zen-model-tiers.md` (2026-07-15) and `opencode-zen-audit-findings-2026-07-01.md`. **Catalog is volatile — always re-probe before recommending a model.** Re-runnable probe: `scripts/probe-zen-free.py`.

## TL;DR — currently working free models (2026-08-24)

| Model | Status | Notes |
|-------|--------|-------|
| `hy3-free` | ✅ 200 | **Was balance-gated (30001) in Jul — now works.** ~3s |
| `x-preview-f-free` | ✅ 200 | ~2.5s, returns `reasoning_content` |
| `nemotron-3.5-lightning-free` | ✅ 200 | ~1.2s, returns `reasoning` + `reasoning_details` |
| `laguna-s-2.1-free` | ✅ 200 | ~1.8s, returns `reasoning`, has `refusal` key |
| `nemotron-3-ultra-free` | ✅ 200 | slow (~18s) |
| `mimo-v2.5-free` | ⚠️ 429 | works but hit `FreeUsageLimitError` (daily quota) — retry later |

## Dead / avoid

| Model | Error | Meaning |
|-------|-------|---------|
| `deepseek-v4-flash-free` | ❌ 400 server_error "Model is unavailable" | Was the main Tier-1 default; **removed/down upstream**. Fails in EVERY request shape (non-stream, stream, `reasoning_effort=low`) — not a request problem |
| `muse-spark-1.2-contributor-free` | ❌ 500 Internal server error | Persistent relay failure; **this model caused the user's "semua error"** (see diagnostic note below) |
| `north-mini-code-free`, `minimax-m3-free`, `qwen3.6-plus-free` | ❌ 401 "Model is not supported" | Not in live catalog — stale curated entries |

## Error taxonomy (how to read a probe failure)

- **400 server_error "Upstream request failed: Model is unavailable"** → model removed/disabled upstream. Not fixable by changing request params — verify by trying non-stream, stream, and with/without `reasoning_effort`; if all 400, it's dead.
- **500 Internal server error** → relay/upstream broken for that model. Can persist for hours (observed 13:09–13:12, still 500 at 16:35). Treat as dead for now.
- **429 `FreeUsageLimitError` "Rate limit exceeded"** → daily free quota exhausted. Temporary; model is fine, retry after quota reset.
- **401 "Model is not supported"** → model ID not in the live catalog (stale curated/picker entry).
- **30001 "account balance is insufficient"** → Tier-2 balance gate (hy3-free in Jul). Recheck periodically — gates can lift.
- **200 but empty `content` with tiny `max_tokens`** → reasoning models burn the budget on `reasoning_content` first. Probe with `max_tokens >= 100` and inspect `message` keys.

## Wire shape of successful 200s (useful for Hermes interleaved-reasoning parsing)

- `x-preview-f-free`, `hy3-free`, `deepseek-*`: message keys `[role, content, reasoning_content]`
- `laguna-s-2.1-free`: `[role, content, refusal, reasoning]`
- `nemotron-3.5-lightning-free`: `[role, content, refusal, reasoning, reasoning_details]`
- `mimo-v2.5-free`: returns a reasoning *struct* (not `reasoning_content`) per earlier audits.

## Diagnostic: which model was actually active when the user reports errors

`config.yaml` default (`deepseek-v4-flash`) is NOT necessarily what a chat session used. When a user says "semua error", find the real culprit:

```bash
grep -E "ERROR.*API call failed after" ~/.hermes/logs/agent.log | tail -10
```

This session's answer: WhatsApp session was on `model=muse-spark-1.2-contributor-free provider=opencode-zen`, which failed 3 retries × 2 turns with HTTP 500 — the exact source of the user's errors.

## Key locations & method

- **API key**: `~/.hermes/.env` → `OPENCODE_ZEN_API_KEY=sk-MqTen...`. NOT in `~/.hermes/auth.json` (that holds `providers`/`credential_pool`/`active_provider` — no opencode-zen entry). Existing `scripts/probe-live-models.py` only reads `os.getenv`, so it silently finds no key — load from `.env` instead (see `scripts/probe-zen-free.py`).
- **Endpoints**: `GET /v1/models` (catalog), `POST /v1/chat/completions` (probe).
- **Catalog drift**: 25 models (early Jul) → 9 (mid-Jul) → **19 (2026-08-24)**. Never trust cached lists; always re-fetch.
- **HTTP client**: plain `requests` worked from this VPS (Singapore) on 2026-08-24. Older notes required `curl_cffi` with `impersonate="chrome120"` for Cloudflare — keep curl_cffi as fallback only if you hit 403.
- **Filter for free models**: `id` contains `free` or starts with `x-preview`. The `/v1/models` list is not tier-annotated — a model being listed does NOT mean it's callable.

## Timeline

- 2026-07-01 audit: 3/6 curated free dead (401); `hy3-free` worked early Jul then 403-gated.
- 2026-07-15 tiers doc: `deepseek-v4-flash-free` ✅ Tier 1, `hy3-free` ❌ balance-gated.
- **2026-08-24: `deepseek-v4-flash-free` ❌ down, `hy3-free` ✅ works, `muse-spark-1.2-contributor-free` ❌ 500, 3 new free models appeared.**
