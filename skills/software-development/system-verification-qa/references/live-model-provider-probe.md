# Live Model Provider Probe (opencode-zen / opencode-go class)

Reusable method for "test why models error" requests: enumerate the live
catalog, probe every free model with real calls, then attribute failures to
upstream vs local setup. Proven 2026-08-24 on opencode-zen (11 free models;
cleanly attributed a Hermes session-wide 500 storm to one dead upstream model
while the config default was unrelated).

## Workflow

1. **Load key locally, never echo it.** `~/.hermes/.env` holds
   `OPENCODE_ZEN_API_KEY` (auth.json may show None for it). Read with
   `line.startswith('VAR=')`; keep in memory only.
2. **Fetch live catalog**: `GET {base}/v1/models`. Filter free tier by
   substring (`free`) plus an explicit known-free list — catalog names drift,
   and the curated source tuple drifts independently. Check BOTH.
3. **Probe each model** with minimal `POST /v1/chat/completions`
   `{model, messages:[{role:user,content:'Reply with exactly: OK'}],
   max_tokens: 100}`. Use `max_tokens>=100`: reasoning models burn budget on
   thinking and return empty content at max_tokens=5 — empty content on a
   first pass is a FALSE NEGATIVE until retested larger.
4. **Classify by exact wire shape**, not status alone:
   - `FreeUsageLimitError` "Rate limit exceeded" → transient quota gate; do
     NOT claim daily reset window unless verified.
   - 401 `"Model ... is not supported"` AND absent from live catalog → dead;
     if still listed in catalog → outage, not deprecation.
   - 500 Internal server error → upstream down; retest twice before reporting.
5. **Attribute before diagnosing Hermes**: grep agent.log for the failing
   turns' actual `model=` / `provider=`. Session errors often come from a
   model that is neither the config default nor in the curated list.
6. **Prove recovery claims with repeat calls** (hy3-free balance gate lifted:
   two consecutive 200s before reporting "now working").

## Report format

One row per model: id | HTTP | evidence quote | verdict
(✅ working / ⚠️ rate-limited-transient / ❌ dead / ❌ down-upstream).
Note producing region/IP (VPS = Singapore). Label unverified mechanisms
(quota reset windows) UNVERIFIED — never infer them.

## Pitfalls

- Curated source tuple ≠ live catalog ≠ picker cache; all three drift apart.
- curl_cffi absent is fine: plain requests worked 2026-08-24 where a
  2026-07-01 audit recorded Cloudflare 403. Re-verify anti-bot era each time;
  do not hardcode either outcome.
- `scripts/probe-live-models.py` here imports hermes_cli by path and may not
  resolve outside its expected layout; standalone inline scripts are more
  reliable.

## Related

- `references/opencode-zen-model-tiers.md` — dated status snapshots
  (2026-07-15 legacy + 2026-08-24 live re-verification).
- `operator/hermes-git-pr-flow` — promoting curated-list changes through
  protected main (branch → 4 gates → PR → squash).
