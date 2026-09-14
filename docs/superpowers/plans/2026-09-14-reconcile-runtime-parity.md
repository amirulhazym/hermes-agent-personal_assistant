# `hermes-agent` Reconstruction Contract Integrity & Pytest Retention Hardening Implementation Plan

> **Scope Boundary:** PR #40 is strictly scoped to repository-side reconstruction contract verification, stale picker test cleanup, and native pytest retention hardening. Live runtime drift monitoring remains separately owned by `scripts/drift_check.sh`.

**Goal:** Remove the stale historical requirement for `2026-09-04_live_model_picker_refresh.patch`, validate repository-side reconstruction contract integrity (`hermes-runtime-source-lock.json` + `hermes-runtime-tree-manifest.json`), keep synthetic managed drift detection, configure native pytest retention (`tmp_path_retention_count = 1`, `tmp_path_retention_policy = failed`), and maintain clean ancestry based directly on remote `origin/main`.

**Tech Stack:** Python 3.11, pytest 9.1.1, Git, GitHub REST API, `hermes-runtime-source-lock.json`, `hermes-runtime-tree-manifest.json`.

---

## Tasks

- [x] **Task 1: Repository Reconstruction Contract Verification in `test_runtime_dependency_drift.py`**
  - Verify official base commit resolvable in Git object store.
  - Verify active patch series existence, hashes, and monotonic order.
  - Enforce that historical out-of-series 2026-09-04 patch is not an active requirement.
  - Verify tree-manifest base SHA, destination root, and entry structure.
  - Keep synthetic negative test proving managed byte drift is caught while unmanaged owner customizations are ignored.
  - Focused test: 3/3 passed.

- [x] **Task 2: Native Pytest Retention Configuration in `pytest.ini`**
  - Set `tmp_path_retention_count = 1` and `tmp_path_retention_policy = failed`.
  - Validate clean removal on pass and exact diagnostic retention on fail.

- [x] **Task 3: PR #40 Clean Ancestry on `origin/main`**
  - Rebuild branch `reconciliation/runtime-parity-and-pytest-retention` directly on remote `origin/main` (`1fb941397ece3d20e3d24be675a3ccbcfa028126`).
  - Zero ancestry overlap with PR #39 (`614ab69606`).
  - Push with lease and verify GitHub CI status: `test` (success), `guards` (success).
