# Upstream Hermes Agent — VPS overlay patches

Source: `~/.hermes/hermes-agent` (nested upstream clone of NousResearch/Hermes-Agent).
**Never merge upstream Git history into this repository.** These patches document
source-worthy VPS customizations; upstream history stays in its own lane.

> **Authority boundary:** The current Hermes runtime is reconstructed only by
> `docs/reconciliation/hermes-runtime-source-lock.json` and its explicitly
> hash-pinned `patch_series`. The overlays listed below are historical/source-only
> evidence unless they are added to that lock with an exact order and SHA-256.
> They are not deployment inputs merely because they exist in this directory.
> See `docs/reconciliation/hermes-runtime-source-authority.md`.

## Recorded upstream bases
- `2bd1977d8` — release v0.17.0 (base before local P1-C commits)
- `f94dff11e` — local `main` HEAD (merge of feat/selected-model-contract-vps); 6 local commits on top of upstream

## Patches (apply in order, each `git apply --check` validated)
1. `2026-08-06_p1c-selected-model-contract.patch` (base `2bd1977d8`)
   Purpose: curated model list (D8) + fail-closed `validate_selected_route()` gate
   + picker gating + tests. Files: hermes_cli/models.py, hermes_cli/model_switch.py,
   gateway/slash_commands.py, tests/selected_model_contract/*, test_opencode_zen_curated_list.py,
   test_validate_selected_route.py.
2. `2026-08-06_vps-runtime-overlays.patch` (base `f94dff11e`)
   Purpose: runtime resolver, execution/runtime context, observability, goals,
   turn finalizer, WhatsApp bridge reconnect controller, models/codex models,
   and their tests. Excludes: ui-tui/*, whatsapp-bridge.old/, .install_method,
   venv, node_modules, vendored deps.
3. `2026-08-11_a4-model-purge-and-test-stability.patch`
   (base `1620de974d2f84577b4afcc2d05e31f41f3ee1da`, extracted candidate
   `08a2cdb3d5ab7cb098e1a93940f30d4ff63ca66b`)
   Purpose: A4 DeepSeek legacy-alias purge/model-catalog updates plus the
   associated stale-test, launcher-harness, revert-fixture, and MCP mtime
   test corrections. This is an upstream overlay patch; it is not a merge of
   upstream Git history into this repository. SHA-256:
   `c79ab7b83790182fc997726a650868a5c3238a87bf407d485a4bcd64b96e8177`.

## Deterministic apply
```bash
cd <upstream clone>
git checkout 2bd1977d8        # or f94dff11e for overlay 2
git apply --check patches/upstream-hermes/2026-08-06_p1c-selected-model-contract.patch
git apply patches/upstream-hermes/2026-08-06_p1c-selected-model-contract.patch
git apply --check patches/upstream-hermes/2026-08-06_vps-runtime-overlays.patch
git apply patches/upstream-hermes/2026-08-06_vps-runtime-overlays.patch
```

## Provenance
Recorded 2026-08-06 during Gate 4 reconciliation. Overlay 1 = 6 local commits
(selected-model-contract P1-C); overlay 2 = working-tree modifications + untracked
source files vs HEAD f94dff11e. Secret values never included; env-var references only.

## Current source-lock closure — 2026-08-28

The authoritative current series is the seven-entry `patch_series` in
`docs/reconciliation/hermes-runtime-source-lock.json`, applied to official base
`a31be48030f60383bf4c1d96ba46bd4b48430218`.

4. `2026-08-28_live-core-usage-and-billing-route.patch` — incremental delta
   after the existing C2/C3/C4 stack. It contains the two backup-unique paths
   (`agent/account_usage.py`, `tests/agent/test_account_usage.py`) and the one
   auto-merged path (`gateway/slash_commands.py`).
5. `2026-08-28_live-auxiliary-middleware-route.patch` — selective capture of
   live commit `c39995e94d78abd33e21ecb6e47051b644d26640`, routing synchronous
   auxiliary completions through the execution middleware for in-process
   providers.
6. `2026-08-28_live-goal-resume-counter-reset.patch` — selective capture of
   live commit `a1a38baea746f90d551a278e85bd885c3fa0f117`, clearing both
   consecutive judge-failure counters on goal resume.
7. `2026-08-28_harden-auxiliary-middleware-fail-closed.patch` — candidate
   hardening added after independent review found that the live middleware
   overlay could retry a failed provider or bypass middleware exceptions.

The overlays preserve intentional live behavior plus the reviewed hardening; they
are not a byte-for-byte clone of the entire live upstream history. Therefore
whole-file SHA equality with the live checkout is not an acceptance criterion.
The materialized candidate is tested at the behavior seams instead.

The 16-path reconciliation evidence, post-snapshot live-only capture, source
hashes, test boundary, and historical-snapshot warning are recorded in
`docs/reconciliation/core-live-source-closure-20260828.md`. The raw backup is
not an active runtime input merely because it exists; only the hash-pinned lock
series is authoritative.

8. `2026-09-04_live_model_picker_refresh.patch` — live model picker refresh flag
   passthrough for interactive slash-commands and picker listings.
9. `2026-09-05_bounded-main-turn-auto-continue.patch` — candidate main
   CLI/gateway bounded progress-aware continuation after a 300-iteration window;
   max two additional windows; not live-applied. SHA-256:
   `dd6db0f5690297e236d23697cfa27e2b54c09ecc363f894a208446e1933165a8`.

10. `2026-09-23_codex_gpt6_fallback.patch` — active candidate overlay for the Codex OAuth model picker. It adds the live-verified `gpt-6-astra`, `gpt-6-sol`, and `gpt-6-luna` slugs to the offline fallback only; live OAuth discovery remains authoritative and no GPT-6 `-900k` variants are synthesized. SHA-256: `fc5cd55df7ec1d986b70a3feb971c92e3dd4acfd45c2f8560e8c3ece45d737c8`.

11. `2026-09-23_deepseek_v41_refresh.patch` — active candidate overlay for native DeepSeek. It moves the picker/normalizer to canonical `deepseek-flash`, retains `deepseek-v4-pro`, filters retired V4 Flash picker aliases, updates thinking-effort mapping and 1M context metadata, and snapshots current peak pricing. SHA-256: `28d77f0ddf1364adc261e269acedf103e26c29ed782325d7926f3107a3096d8d`.

12. `2026-09-23_opencode_zen_free_only.patch` — active candidate overlay for this installation's OpenCode Zen free-only policy. It fails closed for Zen chat models across live discovery, stale cache, typed validation, and shared interactive pickers; paid Zen remains excluded and Jev stays outside `/model` because it uses the System One endpoint. SHA-256: `0c77301186e3f6049d3a3e185dbc46b7b9cf606144ce4bb0e6047c99af3b8714`.

13. `2026-09-24_shared_model_catalog_integration.patch` — active integration overlay for shared `/model` behavior. It removes the dead OpenCode Zen row from the base authenticated provider list so WhatsApp Cloud text fallback and Telegram interactive picker consume the same free-only fail-closed catalog. SHA-256: `5755e7b77d4fcdbcdb3368f5aec55562c4f2bacb4a3e8d2329f937d6eb45311a`.

14. `2026-09-24_live_model_surface_reconciliation.patch` — active pre-release reconciliation overlay. It preserves current live upstream model-surface bytes and the minimal transitive live dependencies (`utils.py`, `hermes_cli/config.py`, `hermes_constants.py`) while retaining the Codex, DeepSeek, OpenCode Zen, and shared `/model` refresh changes. This avoids overwriting newer live source-like changes during selective deployment. SHA-256: `afb474028bd55dea66cab13ef95f1c1ef505239fc5fa6f0ecf119d629e387601`.

## 2026-09-24 v0.21 live-base reconciliation

The model-refresh release candidate now uses official Hermes v0.21.0 commit
`29112bef099274229cadff79cdff7bf7b99c4b77` as the live-common base. Direct
comparison proved 10,923 of 10,925 official source files byte-identical to the
current live runtime; the two remaining live differences are the existing
profile-routing overlay in `gateway/run.py` and a release-out-of-scope local
`pyproject.toml` line removal.

Active overlay replacements:
- `2026-09-24_bounded-main-turn-auto-continue-v021.patch` — v0.21-compatible
  rebase of the existing bounded auto-continue overlay. SHA-256:
  `d034d3ef302d870e24be933b3fe27300d727da506763d9b0644f5a01ab362699`.
- `2026-09-24_model_provider_refresh_v021.patch` — consolidated provider refresh
  for Codex, DeepSeek, OpenCode Zen and shared Telegram/WhatsApp `/model`
  catalog behavior. SHA-256:
  `a8b114de926d7b948eb9b5de6238e3c0fab23e490288c8df1767993ce49d111a`.

The earlier provider-specific overlays and the temporary stale-base live-surface
bridge are retained as historical/source-only evidence and are not active
deployment inputs.
