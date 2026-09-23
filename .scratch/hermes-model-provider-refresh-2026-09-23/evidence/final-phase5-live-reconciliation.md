# Final Phase 5 — live model-surface reconciliation

Date: 2026-09-24

## Why reconciliation was required

The full pre-refresh Hermes runtime tree (origin/main, 5 patches) differed from the current live Hermes source at 1,094 paths. A full-tree deployment would therefore overwrite unrelated live/upstream bytes and was rejected as unsafe.

Within the 16 core files intentionally changed by model-refresh patches 6–9:
- 10 files still matched the pre-refresh baseline.
- 6 files had newer live source-like bytes:
  - agent/model_metadata.py
  - agent/reasoning_effort.py
  - hermes_cli/model_normalize.py
  - hermes_cli/models.py
  - tests/agent/test_model_metadata.py
  - hermes_cli/model_switch.py

The six files had a common live mtime boundary of 2026-09-01 and contained substantive upstream/runtime changes. They were not overwritten.

## Reconciliation method

For overlapping files, a three-way merge used:
- base: reconstructed pre-refresh candidate (origin/main, 5 patches);
- current: exact live file;
- other: model-refresh candidate after patch 9.

Five overlapping files merged cleanly. hermes_cli/models.py had two true conflicts in provider-catalog/validation areas, so it was rebuilt from the exact live file and only the intended DeepSeek/Zen policy deltas were ported onto that live source.

Preserving current live hermes_cli/model_switch.py exposed three minimal transitive source dependencies that were also captured exactly:
- utils.py
- hermes_cli/config.py
- hermes_constants.py

These transitive files are unchanged relative to live after reconciliation; they are captured in source so the reconciled candidate is internally consistent.

## Result

New ordered runtime overlay:
- patches/upstream-hermes/2026-09-24_live_model_surface_reconciliation.patch
- SHA-256: afb474028bd55dea66cab13ef95f1c1ef505239fc5fa6f0ecf119d629e387601
- source-lock order: 10

Reconstructed 10-patch candidate:
- base: a9611f3c6f7ff287a4f10f71a77d7c5a808ea1c8
- files: 10,495
- tree SHA-256: ed72a03df8dc5c6d77b4e81b443ed20735c3874ca5712e7ad58f8dd287b3cc77
- patch-series digest: d249ea3fc90a59cfa6c73a48fee996e2905e90244304f9faff0a903de69812fa

Behavior evidence before commit:
- reconciled Python syntax: PASS;
- focused gateway/Zen transitive reconciliation: 12 passed;
- combined reconciled core matrix: 288 passed;
- actual Codex OAuth catalog includes gpt-6-astra / gpt-6-sol / gpt-6-luna;
- actual DeepSeek catalog is deepseek-flash + deepseek-v4-pro;
- OpenCode Zen chat catalog fails closed to [];
- no live runtime/config/cache/service files were modified.

## Release implication

The final release must use a selective core deployment payload for the model-refresh target files, not the full 10,495-file tree. Unrelated live drift remains outside this release and must not be overwritten.
