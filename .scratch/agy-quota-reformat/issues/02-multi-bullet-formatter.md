# Issue 02: Multi-bullet Sectioned Markdown Formatter

- **Status**: ready-for-agent
- **Blocked by**: Issue 01
- **Target File**: `src/antigravity_provider/hermes_plugin.py`

## Description
Update `_format_quota_markdown(raw_models)` to emit the two sections (`🔹 Gemini Models` and `🔹 Other Models`).
- Number each model entry per section starting from 1: `N. **{Model Name}**:`.
- Render metrics as indented sub-bullets:
  ```text
     • {rem_str} baki ({used_str} used)
     • Reset: {reset_str}
  ```
- Omit inline backticks for percentages and reset timestamps.
- Insert blank lines between consecutive model blocks.
- Gracefully handle route variance and unavailable picker supplement models.

## Verification
- Unit test inspecting formatting string output against Telegram & WhatsApp compatibility requirements.
