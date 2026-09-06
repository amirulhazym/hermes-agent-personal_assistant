# Feature Specification: Antigravity Quota Display Re-formatting

- **Author**: Amirulhazym & Jane (AI Specialist / Operator)
- **Status**: Draft / Pending Approval
- **Feature Slug**: `agy-quota-reformat`
- **SSOT Location**: `patches/antigravity-provider/2026-09-04_custom_antigravity_features.patch`

## Problem Statement
When running `/usage agy` or `/agy quota` on Telegram and WhatsApp, the output from `_format_quota_markdown()` in `antigravity_provider/hermes_plugin.py` renders as a flat, un-separated list of single-line bullet points. All models (Gemini, Claude, GPT-OSS) are grouped together in alphabetical order, making scanning and reading on mobile devices tedious.

## Solution
Reformat the markdown output of `_format_quota_markdown()` into two distinct sections:
1. `🔹 Gemini Models` (sorted by version descending: e.g. 3.8 Flash, 3.7 Flash down to 2.5)
2. `🔹 Other Models` (Claude Opus/Sonnet, GPT-OSS, sorted by version/name descending)

Each model entry will be rendered using numbered list headers per section with indented bullet points for quota metrics and reset schedules, separated by blank lines for visual clarity:
```text
1. **Gemini 3.8 Flash**:
   • 98.1% baki (1.9% used)
   • Reset: 07/09 12:18 PM MYT
```

## User Stories
1. *As a mobile operator on Telegram*, I want `/usage agy` to display Gemini models grouped first and ordered newest-to-oldest, so that I can instantly check my primary daily driver quotas without scrolling past legacy or non-Gemini models.
2. *As a mobile operator on WhatsApp*, I want the quota and reset time displayed on structured sub-bullet points without code-block wrapping, so that the message renders cleanly without awkward monospace line breaks.
3. *As an automated system guardian*, I want the formatting changes backed by deterministic unit tests and contract tests, so that zero regressions or drift occur across runtime and SSOT patch layers.

## Implementation Decisions
- **Sectioning**:
  - `🔹 Gemini Models` for models where `logical_id.startswith("gemini-")`.
  - `🔹 Other Models` for all other models (e.g. `claude-*`, `gpt-oss-*`).
- **Sorting Logic**:
  - Sort versions in descending order using parsed numeric version components. If versions are identical or absent, secondary sort maintains predictable hierarchy (e.g. `flash` before `pro` before `lite`, or alphabetical).
- **Display Typography**:
  - Model Item Header: `N. **{display_name}**:` (1-indexed per section).
  - Metrics Sub-bullets:
    - `   • {rem_str} baki{used_part}`
    - `   • Reset: {reset_str}`
  - No backticks on numbers or dates for clean mobile typography.
  - One blank line between model blocks.
- **Route Variance & Supplement Fallbacks**:
  - If a model's quota varies by route, list route sub-bullets indented cleanly.
  - If a verified picker supplement model is missing from live catalog, show clearly labeled notice under its appropriate section.

## Testing Decisions
- Update unit tests in `~/.hermes/plugins/antigravity-provider/tests/test_hermes_plugin.py` to assert new section headers, numbering, and sub-bullet structure.
- Re-run full test suite of `antigravity-provider` (56/56 passing).
- Update SSOT patch in `/home/ubuntu/hermes-agent-personal_assistant-work/patches/antigravity-provider/2026-09-04_custom_antigravity_features.patch`.
- Execute contract tests `bash scripts/run_contract_tests.sh` to confirm runtime parity and zero drift.

## Out of Scope
- Modifying quota calculation arithmetic or reset time timezone (remains MYT).
- Changing `/usage` routing hooks or model picker logic.
