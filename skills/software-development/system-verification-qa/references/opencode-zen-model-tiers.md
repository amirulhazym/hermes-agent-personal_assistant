# OpenCode Zen — Model Access Tiers

OpenCode Zen (`https://opencode.ai/zen/v1`) classifies models into three access tiers.

## 🌐 COMMUNITY EVIDENCE 2026-08-24 (evening)

- deepseek-v4-flash-free 400: LIKELY NOT transient. r/opencode threads (titles, via search): "Free promotion has ended for DeepSeek V4 Flash Free." + "deepseek v4 flash free not work anymore in zen" (~9d before 24 Aug) + DeepSeek price hike ×16 ("Bye bye OpenCode Go" thread). Interpretation: free promo ended upstream; catalog still lists it. CAVEAT: thread bodies unreadable (Reddit blocks bots) — title/snippet-level evidence only.
- muse-spark-1.2-contributor-free 500: NO community reports found; cause unknown (overload vs broken deploy both possible). Owner theory: per-model request pool exhausted ("hot"). UNVERIFIED either way.
- Lesson logged by owner: HTTP failure ≠ model removed; NEVER propose picker removal without cross-checking website/socials first. Status-check approach (flag down/recovery) replaces purge approach.

## 🔴 LIVE RE-VERIFIED 2026-08-24 (supersedes everything below)

Full free-model sweep via direct `POST /v1/chat/completions` (plain requests, VPS Singapore IP):

| Model | Status | Evidence |
|-------|--------|----------|
| `x-preview-f-free` | ✅ 200 | content `'OK'` + reasoning_content present |
| `hy3-free` | ✅ 200 | **NOW WORKING** — balance gate lifted since ~Aug 2026 |
| `nemotron-3-ultra-free` | ✅ 200 | slow (~18s) |
| `nemotron-3.5-lightning-free` | ✅ 200 | fast (~1–2s), NEW model |
| `laguna-s-2.1-free` | ✅ 200 | fast (~2–3s), NEW model |
| `mimo-v2.5-free` | ⚠️ 429 FreeUsageLimitError | 200 at 16:36 MYT, rate-limited at 16:37 — reset window UNKNOWN (UNVERIFIED daily vs hourly) |
| `deepseek-v4-flash-free` | ❌ 400 "Model is unavailable" | upstream down; failed ALL request shapes (non-stream / stream=true / reasoning_effort) |
| `muse-spark-1.2-contributor-free` | ❌ 500 Internal server error | down; caused Hermes session API failures 13:09–13:12 MYT 2026-08-24 |
| `north-mini-code-free`, `minimax-m3-free`, `qwen3.6-plus-free` | ❌ 401 not supported | long dead |

Environment notes (2026-08-24):
- `/v1/models` now returns **19 models** total.
- `curl_cffi` no longer installed; plain `requests` succeeded (no Cloudflare 403) — anti-bot behaviour changed vs the July audit below.
- Everything below this section = 2026-07-15/2026-07-01 snapshots, kept for history only.

### Picker architecture — why purging the source tuple does NOT change `/model` (verified 2026-08-24)

- The `/model` picker's PRIMARY source is the live catalog (`GET /v1/models`), cached ~1 hour in `~/.hermes/provider_models_cache.json`.
- `D8_OPENCODE_ZEN_FREE_MODELS` in `hermes_cli/models.py` is fallback/selectability gate only — editing it changes no visible picker entry while the catalog still advertises the models.
- Proven 2026-08-24: tuple purge merged to repo main (PR #4, squash `bc4ad6a8e`) yet picker still shows `muse-spark-1.2-contributor-free` / `deepseek-v4-flash-free` because they remain in the live catalog. To drop a down model from the picker: refresh/clear the cache file (regenerable, safe) or wait out TTL — not a tuple edit.
- ⚠️ Deploy trap: runtime copy `~/.hermes/hermes-agent/hermes_cli/models.py` (~5.5k lines) ≠ source clone version (~4.3k lines). Direct file-copy deploy would REGRESS runtime code. Deployment here requires reconciliation, not `cp`.

### "Dead" = completions fail, NOT absence from catalog

Evening retest (~18:20 MYT, hours after afternoon sweep):

| Model | Afternoon | Evening retest | In live catalog? |
|---|---|---|---|
| `deepseek-v4-flash-free` | ❌ 400 | ❌ 400 "Upstream request failed: Model is unavailable" | YES — still advertised |
| `muse-spark-1.2-contributor-free` | ❌ 500 | ❌ 500 "Internal server error" | YES — still advertised |
| `big-pickle` | ⚠️ 429 | — | listed, non-`-free` name, quota-gated like mimo |
| `ling-3.0-flash-free` | ❌ 401 | — | NO (absent) → genuinely removed; purged from tuple |

Rules: classify model health by probe result, never by catalog membership (providers keep advertising down models). Re-probe hours later before declaring permanent death — identical error shape across sessions = persistent upstream outage; single failure = transient.

### Catalog enumeration without token burn

- `GET https://opencode.ai/zen/v1/models` + `Authorization: Bearer $OPENCODE_ZEN_API_KEY` → full list, zero completion cost. 2026-08-24: 19 models, 8 `-free` (x-preview-f, hy3, laguna-s-2.1, mimo-v2.5, muse-spark-1.2-contributor, nemotron-3-ultra, nemotron-3.5-lightning, deepseek-v4-flash); non-free: big-pickle + paid tier (claude/gemini/gpt/grok/kimi).
- Webpage cross-check limits hit 2026-08-24: workspace URLs (`opencode.ai/workspace/<id>`) sit behind an OpenAuth login wall — extraction returns only "Continue with GitHub"; docs pages intermittently fail crawler extraction. The API catalog endpoint is the authoritative public surface; do NOT treat webpage-extraction failure as evidence about model status, and say plainly which surfaces were walled when reporting.

---

[Legacy Context — verified 2026-07-15] The `/model` picker in Hermes shows curated models without tier awareness — a model appearing in the picker does NOT guarantee it's callable.

## Tier 1 — Actually Free (no balance required)

| Model | Status | Notes |
|-------|--------|-------|
| `deepseek-v4-flash-free` | ✅ Working | Returns reasoning_content by default |
| `mimo-v2.5-free` | ✅ Working | Returns reasoning struct (not reasoning_content) |
| `nemotron-3-ultra-free` | ✅ Working | Limited reasoning effort support |

These models work immediately with any valid API key. No credits needed.

## Tier 2 — "Free" but Balance-Gated

| Model | Status | Error |
|-------|--------|-------|
| `hy3-free` | ❌ Code 30001 | `{"code":30001,"message":"Sorry, your account balance is insufficient","data":null}` |

**This is the confusing category.** Pricing is $0.00/1M tokens (verified via TypingMind, OpenRouter), but the opencode-zen platform gates it behind a minimum balance check — likely anti-abuse. Even $1 credit may satisfy the gate.

### hy3-free timeline (from agent.log)

| Period | Status | Evidence |
|---|---|---|
| Jul 13 22:37–23:33 | ✅ **Working** | 8+ successful API calls with `model=hy3-free`, latency 12–124s |
| Jul 14 01:50+ | ❌ **Failed** | `HTTP 403: Sorry, your account balance is insufficient` — FIRST failure |
| Jul 14 06:54+ | ❌ Failed | Same 403 on every attempt |
| Jul 16 07:07–13:26 | ❌ Failed | Same 403 on every attempt across cron + Telegram + WhatsApp |

The transition happened BETWEEN Jul 13 23:33 (last success) and Jul 14 01:50 (first failure). Possible causes:
- Daily/periodic free quota exhausted
- opencode-zen policy change (started gating previously-ungated models)
- Account balance change (depleted below minimum threshold)

**Diagnostic pattern:** To detect whether a model *used to work*, grep agent.log for successful API calls:
```bash
grep "model=hy3-free" ~/.hermes/logs/agent.log | grep "latency=" | tail -5
```
If the most recent successful call is older than the most recent 403 failure, the model was gated between those two timestamps.

Note: `hy3-preview` exists on opencode-go's `/v1/models` but returns "not supported on lite model list" when called — different issue, likely subscription tier restriction.

## Tier 3 — Paid (requires credits)

| Model | Status | Error |
|-------|--------|-------|
| `gpt-5.6-luna` | ❌ CreditsError | `{"type":"error","error":{"type":"CreditsError","message":"Insufficient balance. Manage your billing here: https://opencode.ai/workspace/<id>/billing"}}` |
| `gpt-5.6-sol` | ❌ CreditsError | Same format |
| `gpt-5.6-terra` | ❌ CreditsError | Same format |
| `grok-4.5` | ❌ CreditsError | Same format |

These return a `CreditsError` (not code 30001) with a billing URL pointing to the workspace billing page.

## Workspace Info

- Workspace ID: `wrk_01KTG0K2G2EWXRN2JYJX44E7QZ` (extracted from CreditsError response 2026-07-15)
- Billing URL: `https://opencode.ai/workspace/wrk_01KTG0K2G2EWXRN2JYJX44E7QZ/billing`
- Login: GitHub or Google OAuth (same account used to create API key)

## Impact on Hermes

The curated model list in `hermes_cli/models.py` includes `hy3-free` under `opencode-zen` (line 370). The picker's runtime filter cross-checks against `/v1/models` — and `hy3-free` IS in that response — so the picker shows it as available. But it's not callable without balance.

**Removed models** (commented out at lines 361-363): `minimax-m3-free`, `qwen3.6-plus-free`, `north-mini-code-free` — these returned 401 "not supported" and were correctly pruned. `hy3-free` returns a different error class (balance gate, not "not supported") and remains listed but broken.

## Alternatives for hy3-free

1. **Add balance** to opencode-zen account (even $1 may unlock Tier 2)
2. **OpenRouter**: `tencent/hy3:free` at $0.00/1M — genuinely free. Route through Hermes OpenRouter provider.
3. **Remove from curated list** if neither option works (mirrors treatment of other broken free models)

## Provenance

- Live-probed 2026-07-15: all 9 models from `/v1/models` tested individually
- curl_cffi with impersonate=chrome120 required (plain urllib gets Cloudflare 403 from VPS Singapore IP)
- Account: single `OPENCODE_ZEN_API_KEY` (sk-MqTen...)
