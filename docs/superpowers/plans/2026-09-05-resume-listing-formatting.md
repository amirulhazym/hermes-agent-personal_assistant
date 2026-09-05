# Fix /resume Session Listing & Formatting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix `/resume` slash command so it displays the active session plus up to 10 past titled sessions ordered by most recent activity (`last_active DESC`), formatted into a clean 3-line per session layout on Telegram mobile with source platform tags (`[TG]`, `[WA]`).

**Architecture:** Update `_list_titled_sessions` and format rendering in `gateway/slash_commands.py` (`GatewaySlashCommandsMixin._handle_resume_command`). Over-fetch 50 sessions via `SessionDB.list_sessions_rich(order_by_last_active=True)`, extract the active session, append the top 10 past titled sessions, and render each session in 3 lines separated by newlines.

**Tech Stack:** Python 3.11, SQLite (`hermes_state.SessionDB`), `pytest`.

## Global Constraints
- Sole development repo SSOT: `/home/ubuntu/hermes-agent-personal_assistant-work`.
- All changes represented as patch in `patches/upstream-hermes/`.
- No regression to `/resume <number>` or `/resume <name>` resolution.
- Format layout strictly adheres to:
  Line 1: `{index}. {active_label}\`{session_id}\` {source_tag}`
  Line 2: `   🏷️ {title}`
  Line 3: `   > _{preview}_`
  (blank line separator)

---

### Task 1: Query Pipeline & Session Selection

**Files:**
- Modify: `/home/ubuntu/.hermes/hermes-agent/gateway/slash_commands.py:4928-4980`
- Test: `/home/ubuntu/.hermes/hermes-agent/tests/gateway/test_resume_formatting.py`

**Interfaces:**
- Consumes: `SessionDB.list_sessions_rich(source=..., session_key=..., limit=50, order_by_last_active=True, min_message_count=1)`
- Produces: `titled: list[dict]` where first element is active session (if present) followed by up to 10 past titled sessions.

- [ ] **Step 1: Write the failing test**
Create test ensuring `_list_titled_sessions` retrieves active session + 10 past titled sessions in `last_active DESC` order.

- [ ] **Step 2: Run test to verify it fails**
Run `pytest tests/gateway/test_resume_formatting.py -v`. Expected: FAIL.

- [ ] **Step 3: Implement query over-fetch and active session assembly**
Update `_list_titled_sessions` to query `limit=50`, `order_by_last_active=True`. Separate active session and past titled sessions.

- [ ] **Step 4: Run test to verify it passes**
Run `pytest tests/gateway/test_resume_formatting.py -v`. Expected: PASS.

---

### Task 2: 3-Line Mobile Layout & Platform Tag Formatter

**Files:**
- Modify: `/home/ubuntu/.hermes/hermes-agent/gateway/slash_commands.py:4940-4965`
- Test: `/home/ubuntu/.hermes/hermes-agent/tests/gateway/test_resume_formatting.py`

- [ ] **Step 1: Write tests for format rendering**
Assert Line 1 has `{index}. (active) \`session_id\` [TG]`, Line 2 has `🏷️ {title}`, Line 3 has `> _{preview}_`, with empty line spacing.

- [ ] **Step 2: Run test to verify it fails**
Run `pytest tests/gateway/test_resume_formatting.py -v`. Expected: FAIL.

- [ ] **Step 3: Implement 3-line format in `_handle_resume_command`**
Format lines array, include source platform mapping dictionary (`{"telegram": "[TG]", "whatsapp": "[WA]", ...}`).

- [ ] **Step 4: Run test to verify it passes**
Run `pytest tests/gateway/test_resume_formatting.py -v`. Expected: PASS.

---

### Task 3: Patch Generation & SSOT Synchronization

**Files:**
- Create: `/home/ubuntu/hermes-agent-personal_assistant-work/patches/upstream-hermes/2026-09-05_resume_listing_and_format.patch`
- Modify: `/home/ubuntu/hermes-agent-personal_assistant-work/docs/reconciliation/` (if needed)

- [ ] **Step 1: Generate git diff patch**
Run `git diff` on runtime hermes-agent to produce patch file.

- [ ] **Step 2: Verify patch applies cleanly to personal repo**
Run `patch --dry-run` or check against SSOT.

- [ ] **Step 3: Full test suite verification**
Run gateway resume tests to ensure 100% green.
