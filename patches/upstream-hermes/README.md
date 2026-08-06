# Upstream Hermes Agent — VPS overlay patches

Source: `~/.hermes/hermes-agent` (nested upstream clone of NousResearch/Hermes-Agent).
**Never merge upstream Git history into this repository.** These patches document
source-worthy VPS customizations; upstream history stays in its own lane.

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
