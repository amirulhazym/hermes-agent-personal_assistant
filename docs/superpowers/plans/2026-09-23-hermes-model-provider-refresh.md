# Hermes Model Provider Refresh Implementation Plan

> **For execution agent:** follow `/xcute`; no implementation/deployment before owner approval. Execute TDD, source-first, and preserve exact runtime provenance.

**Goal:** Refresh `openai-codex`, `opencode-zen` free-only policy, `deepseek`, and `antigravity` so shared `/model` output on Telegram and WhatsApp is current, callable, and fail-closed against stale/paid choices.

**Architecture:** Keep provider discovery centralized in Hermes model catalog + provider profiles. Live provider catalogs stay authoritative where trustworthy; curated fallbacks protect outages. Provider-specific compatibility rules normalize canonical IDs and wire behavior. Runtime changes are represented as hash-pinned SSOT patch artifacts and deployed only through reconstruction/deployment scripts.

**Evidence date:** 2026-09-23 MYT.

## Task 1 — Red tests: current provider contracts

**Files**
- Modify/add targeted tests under `tests/hermes_cli/`, `tests/agent/`, and provider-profile tests as appropriate.
- Do not modify live runtime tests in place.

**Tests first**
1. Codex fallback must include `gpt-6-astra`, `gpt-6-sol`, `gpt-6-luna`.
2. Live Codex discovery must remain authoritative and must not synthesize unverified GPT-6 context aliases.
3. DeepSeek picker must prefer `deepseek-flash` and `deepseek-v4-pro`, not retired Flash/Vision aliases.
4. `deepseek-flash` must enter DeepSeek thinking-mode handling with current effort semantics.
5. Zen free-only picker must never expose paid/test/deprecated models or Jev as chat.
6. Zen must fail closed when no legitimate free chat SKU is callable externally.
7. Antigravity fallback/default must be `gemini-3.8-flash`; live catalog remains intact.

Run the smallest affected pytest files and prove expected failures before production changes.
## Task 2 — Codex and DeepSeek implementation

**Core targets in reconstructed upstream candidate**
- `hermes_cli/codex_models.py`
- `hermes_cli/models.py`
- `hermes_cli/model_normalize.py` if legacy canonicalization belongs there
- `plugins/model-providers/deepseek/__init__.py`
- relevant model metadata/reasoning helper only if tests prove required

**Codex**
- Add GPT-6 Astra/Sol/Luna to offline fallback in current live priority order.
- Extend forward-compat logic only where a real compatible template exists.
- Keep OAuth `/backend-api/codex/models` discovery first.

**DeepSeek**
- Make `deepseek-flash` the canonical V4.1 Flash entry/default.
- Keep `deepseek-v4-pro` while official API continues serving it.
- Remove retired V4 Flash/Vision names from picker-facing lists; normalize old selections to `deepseek-flash`.
- Make `deepseek-flash` thinking-capable; map Hermes effort to official `none/low/high/max` behavior without sending invalid combinations.

Re-run Task 1 tests until green.
## Task 3 — OpenCode Zen free-only fail-closed policy

**Targets**
- `hermes_cli/models.py`
- `hermes_cli/model_switch.py` only if picker filtering cannot live in provider catalog/profile
- `plugins/model-providers/opencode-zen/__init__.py`
- targeted tests

Implementation rules:
- Current official free SKUs are discovery inputs, not automatic selectable models.
- Exclude `jev-1.13-free` from chat because its documented endpoint is `/systemone`.
- Exclude all paid Zen models under this owner's free-only policy.
- Exclude stale/undocumented free IDs unless explicitly re-verified as legitimate and callable.
- Because live Hermes-origin calls to all official free generative SKUs returned 403 on 2026-09-23, the free-only selectable set must currently resolve empty/fail-closed.
- Never spoof OpenCode identity, proprietary headers, or client behavior to bypass the service-side restriction.
- Preserve a clear path for future refresh: once direct external use becomes legitimately callable, the same verified-free filter can surface models without enabling paid choices.

Re-run Zen catalog, selection, and typed-switch tests.
## Task 4 — Antigravity fallback/default refresh

**Dependency source:** `~/.hermes/plugins/antigravity-provider` is runtime-only; do not edit it directly.

- Reconstruct the plugin source state represented by the existing SSOT Antigravity patch.
- Add a new source-represented delta that changes `DEFAULT_MODEL` to `gemini-3.8-flash`.
- Preserve live `fetchAvailableModels` discovery, `VERIFIED_PICKER_SUPPLEMENTS`, wire profiles, and custom Gemini R6-B3 behavior.
- Update parity/reconstruction tests so the new patch series is deterministic.
- Do not add `antigravity-preview-09-2026` to model IDs.

## Task 5 — Build authoritative upstream patch + reconstruction candidate

1. Reconstruct current runtime candidate:
   `python3 scripts/reconstruct_hermes_runtime.py --lock docs/reconciliation/hermes-runtime-source-lock.json --tree-manifest docs/reconciliation/hermes-runtime-tree-manifest.json --output <candidate-dir> --validate`
2. Apply only the tested Task 2/3 source deltas to that candidate.
3. Generate one incremental `patches/upstream-hermes/2026-09-23_model_provider_refresh.patch`.
4. Add its SHA-256 and order to `docs/reconciliation/hermes-runtime-source-lock.json`.
5. Regenerate/validate the runtime tree manifest as required by the reconstruction tool.
6. Keep historical patches unchanged; do not activate the old 2026-09-04 picker-refresh patch implicitly.

Run `git apply --check`, reconstruction validation, targeted pytest, reconciliation tests, secret scan, and PII review.
## Task 6 — Candidate verification, owner release gate, deployment

Before deploy:
- Capture exact candidate SHA and clean working-tree evidence.
- Dry-run the supported deploy command with the reconstructed candidate, authoritative manifest/lock, and exact release SHA.
- Stop if any unmanaged live drift, secret/PII issue, or reconstruction mismatch appears.
- Protected publication/deployment requires the repository's exact-SHA owner approval flow.

After approved deploy:
- Invalidate only affected provider-model cache entries, or the whole picker cache if the supported command only offers whole-cache refresh.
- Restart/reload only the required Hermes gateway service through the existing approved procedure.
- Re-run live provider discovery with force refresh plus the shared picker builder.
- Expected: Codex GPT-6 visible; DeepSeek canonical IDs; Zen free-only unavailable/fail-closed while 403 persists; Antigravity 3.8 default plus live catalog intact.
- Exercise /model on Telegram and WhatsApp and confirm both are backed by the same refreshed shared catalog.
- Use no paid Zen generation. Any DeepSeek generation smoke must be explicitly bounded and reported as billable before execution.

## Rollback

- Preserve pre-deploy runtime bytes via the deployment system's rollback protection.
- If smoke checks fail, restore the prior exact runtime manifest/bytes; do not patch live by hand.
- Restore prior source-lock/tree-manifest only through a new source commit, never by rewriting published history.

## Status

Plan only — ready for the mandatory /xcute owner approval gate. No production code/config/runtime change has been made by this work item.
