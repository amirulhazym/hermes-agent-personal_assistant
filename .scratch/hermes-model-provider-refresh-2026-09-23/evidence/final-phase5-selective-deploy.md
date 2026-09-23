# Final Phase 5 — selective deployment boundary

Date: 2026-09-24

## Why full-tree deployment is rejected

The final Hermes v0.21 candidate reconstructs successfully from official/live-common base
`29112bef099274229cadff79cdff7bf7b99c4b77`, but a full-tree deploy dry-run still
finds live byte differences outside the model-refresh scope.

Classification against the active runtime overlays found 49 raw live/candidate mismatches.
Thirteen mismatches were not touched by any active overlay and included unrelated Windows/
PowerShell installer/update files plus `pyproject.toml`. Those files are explicitly excluded
from this release.

The model-provider refresh itself is the consolidated order-6 overlay and owns exactly 16 files:
8 production files plus 8 tests. Live deployment is therefore constrained to the 8 production
files only.

## Core selective deployment manifest

Artifact:
- `docs/reconciliation/hermes-runtime-model-refresh-deploy-manifest.json`

Scope:
1. `agent/model_metadata.py`
2. `agent/reasoning_effort.py`
3. `agent/usage_pricing.py`
4. `hermes_cli/codex_models.py`
5. `hermes_cli/model_normalize.py`
6. `hermes_cli/model_switch.py`
7. `hermes_cli/models.py`
8. `plugins/model-providers/deepseek/__init__.py`

Manifest tree SHA-256:
- `d81c08a41d029196e533fe2db595a2570859396958da968ea6590b331e79f55c`

Read-only deploy dry-run:
- entries: 8
- current_hash_mismatches: 8
- writes: 0
- deletes: 0
- restart: 0

This proves the selective payload contains only files that actually need the approved
model-refresh write.

## Antigravity selective deployment manifest

Artifact:
- `docs/reconciliation/antigravity-model-refresh-deploy-manifest.json`

Production scope:
- `src/antigravity_provider/models.py`

Payload SHA-256:
- `be4e7a6c02f572265d75785477f550a7ca628b2ba226ec1a513d06b155a16339`

Target file SHA-256:
- `206c223ce82c36d5926e1ad382472e04642239cc8617a8ed813e96749b2f5428`

Current live file SHA-256 before release:
- `9232cece790a5831f4b7caef1925af59ec737b58a1d71e41c9dfb234b444e62b`

Only this Antigravity production file will be written. Test files, pycache, pytest cache,
marker files, Git metadata, credentials, and all other plugin source files are excluded.

## Safety boundary

Before owner release approval:
- no origin/main promotion;
- no live core write;
- no Antigravity live write;
- no model-cache clear;
- no gateway restart;
- no Telegram/WhatsApp send.

After exact-SHA approval, deployment must:
1. snapshot the 8 core destination files and the one Antigravity destination file;
2. deploy only those manifest entries;
3. verify exact post-write hashes;
4. invalidate only the affected provider-model cache;
5. restart/reload only the required gateway service;
6. run bounded provider and Telegram/WhatsApp post-deploy smoke;
7. retain rollback bytes and deployment receipt.
