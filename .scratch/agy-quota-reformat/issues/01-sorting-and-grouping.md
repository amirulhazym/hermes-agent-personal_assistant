# Issue 01: Sorting and Grouping Partition Engine

- **Status**: ready-for-agent
- **Blocked by**: none
- **Target File**: `src/antigravity_provider/hermes_plugin.py`

## Description
Implement model classification and descending version sort helpers for `_format_quota_markdown`.
- Partition logical model IDs into `gemini` and `other` sets.
- Order `gemini` models descending by release version (e.g. 3.8, 3.7, 3.6, 3.5, 3.1, 3.0, 2.5) with stable tier tie-breaking (`flash` before `pro` before `lite`).
- Order `other` models descending by family/version (Claude 4.6 Sonnet/Opus, GPT-OSS 120B).

## Verification
- Unit test verifying sort order and group categorization with mock catalog models.
