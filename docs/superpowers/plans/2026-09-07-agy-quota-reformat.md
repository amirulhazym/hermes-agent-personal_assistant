# Implementation Plan: Antigravity Quota Display Re-formatting

- **Date**: 2026-09-07
- **Feature**: `agy-quota-reformat`
- **Spec**: `.scratch/agy-quota-reformat/spec.md`

## Proposed Changes

### 1. `~/.hermes/plugins/antigravity-provider/src/antigravity_provider/hermes_plugin.py`
- Add helper `_model_sort_key(logical_id: str)` to sort Gemini models descending by version (e.g. 3.8 down to 2.5) with tier priority (`flash` -> `pro` -> `lite`), and Claude / GPT models descending.
- Update `_format_quota_markdown(raw_models)`:
  - Partition models into `gemini_models` and `other_models`.
  - Add section headers:
    - `🔹 **Gemini Models**`
    - `🔹 **Other Models**`
  - Number models 1-N per section: `N. **{display_name}**:`
  - Render sub-bullets without backticks:
    - `   • {rem_str} baki{used_part}`
    - `   • Reset: {reset_str}`
  - Add blank line between model entries.

### 2. `~/.hermes/plugins/antigravity-provider/tests/test_hermes_plugin.py`
- Update test cases:
  - `test_format_quota_markdown`
  - `test_format_quota_markdown_renders_live_catalog_models`
  - `test_format_quota_markdown_marks_unreported_picker_supplement`
  - `test_format_quota_markdown_preserves_variant_quota_truth`
  - `test_format_quota_markdown_tolerates_noncanonical_quota_values`
- Assert new section headers, numbering (`1. **...**:`), indented sub-bullet lines, and absence of backticks around metrics.

### 3. Patch & Parity Verification
- Recompute and overwrite `patches/antigravity-provider/2026-09-04_custom_antigravity_features.patch` in SSOT repo.
- Run `PYTHONPATH=src pytest tests/` in `~/.hermes/plugins/antigravity-provider`.
- Run `bash scripts/run_contract_tests.sh` in personal dev repo.

## Verification Plan
1. TDD unit tests pass in `antigravity-provider`.
2. Contract tests pass in personal dev repo.
3. Smoke test output of `_handle_chat_command("")` matches exact requested format.
