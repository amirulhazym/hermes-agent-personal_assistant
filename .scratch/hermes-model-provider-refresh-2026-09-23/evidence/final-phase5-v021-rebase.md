# Final Phase 5 — Hermes v0.21 live-base rebase

Date: 2026-09-24

## Why this supersedes the earlier candidate

After Task 6, release preflight proved that the current live Hermes runtime is based on official Hermes v0.21.0 commit `29112bef099274229cadff79cdff7bf7b99c4b77`, not the older `a9611f3...` reconstruction base used during Tasks 1–6.

The older candidate remained valid as task evidence, but it was not safe to deploy over the newer live source tree. Release approval for that older SHA must not be reused for this superseding candidate.

## Rebased authoritative runtime

Official/live-common base:
- `29112bef099274229cadff79cdff7bf7b99c4b77`

Active runtime overlays:
1. existing auxiliary middleware route
2. existing goal-resume counter reset
3. existing auxiliary middleware fail-closed hardening
4. v0.21-compatible bounded main-turn auto-continue
5. existing profile-routing fail-closed safety
6. consolidated v0.21 model-provider refresh

New v0.21 overlays:
- `2026-09-24_bounded-main-turn-auto-continue-v021.patch`
  - SHA-256 `d034d3ef302d870e24be933b3fe27300d727da506763d9b0644f5a01ab362699`
- `2026-09-24_model_provider_refresh_v021.patch`
  - SHA-256 `a8b114de926d7b948eb9b5de6238e3c0fab23e490288c8df1767993ce49d111a`

Provider-specific Task 2/3/4/6 overlays and the temporary stale-base live-surface bridge remain retained as historical/source-only evidence.

## Fresh verification before candidate commit

- v0.21 reconstruction: PASS
- files: 10,933
- tree SHA-256: `58a78e9a5d2b15afb39d012aa6dfe15849cafe2e80c522a4e6b7a8c07d9e9435`
- reconstruction contract tests after base correction: 5 passed
- Codex tests: 10 passed
- DeepSeek tests: 49 passed, 172 deselected
- Zen/shared gateway tests: 67 passed
- live read-only Codex catalog includes GPT-6 Astra/Sol/Luna
- live read-only DeepSeek catalog = deepseek-flash + deepseek-v4-pro
- OpenCode Zen chat catalog = []
- no live runtime/config/cache/service writes were performed

## Release boundary

This commit only creates a new release candidate. Protected main promotion and live deployment require a fresh exact-SHA owner release approval for the final candidate produced from this rebase.
