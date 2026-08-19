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
