# Spec: /resume Listing Accuracy & Clean Telegram Mobile Formatting

## Problem Statement

When the user runs `/resume` on Telegram, the command only returns 5 named sessions instead of 10, does not sort strictly by most recent activity (`last_active DESC`), and displays items in a single dense paragraph that wraps poorly on mobile screens. Furthermore, the active session is missing its explicit active indicator, and untitled sessions lack clear placeholder cues.

## Solution

1. **Over-fetch & Titled Extraction**: Over-fetch candidate sessions (`limit=50`, `order_by_last_active=True`, `min_message_count=1`) via `SessionDB.list_sessions_rich` so that untitled/reset artifacts do not starve the list. Extract the active session (labeled `(active)`) plus up to 10 past titled sessions sorted by most recent activity.
2. **Clean 3-Line Mobile Layout**:
   - Line 1: `{index}. {active_label}\`{session_id}\` {source_tag}`
   - Line 2: `   🏷️ {title}` (or `   🏷️ (no title set yet)` if untitled)
   - Line 3: `   > _{preview}_`
   - Blank line separator between entries.
3. **Cross-Platform Tagging**: When `--all` is supplied, tag the source on Line 1 (e.g. `[TG]`, `[WA]`). When single-platform, tag reflects current platform `[TG]`.
4. **Numeric Index Resolution**: `/resume <number>` resolves reliably against the exact numbered list rendered to the user.

## User Stories

1. As a mobile Telegram user, I want `/resume` to show my latest 10 titled sessions, so that I can easily switch to recent work without missing sessions.
2. As a mobile Telegram user, I want the session list formatted across 3 indented lines per session with a blank separator, so that each item is distinct and readable on small screens.
3. As a user, I want the active session to be clearly labeled `(active)` at the very top of the list, so that I know what conversation I am currently inside.
4. As a user, I want untitled sessions to clearly state `(no title set yet)`, so that I remember to run `/title` if the session matters.
5. As a user, I want cross-platform sessions to display `[TG]` or `[WA]` tags on Line 1, so that I immediately know which platform the session originated from.
6. As a user, I want typing `/resume 2` to resume the 2nd session listed in the output, so that numeric navigation is 100% consistent with display order.

## Implementation Decisions

- **Seam**: `_handle_resume_command` and `_list_titled_sessions` inside `gateway/slash_commands.py` (and relevant locale/formatter in `locales/en.yaml` and `hermes_cli/session_listing.py`).
- **Data Fetching**: Call `self._session_db.list_sessions_rich` with `order_by_last_active=True`, `limit=50`, and caller `session_key` (or `None` if `--all`).
- **Ordering & Assembly**:
  1. Inspect fetched sessions.
  2. If current session is present, prepend to list with `(active)` label.
  3. Append up to 10 past titled sessions (excluding current session).
  4. Total list size is 10 (or 11 if current session is present).
- **Line 1 Platform Tag**: Map source string to uppercase 2-letter tag (`telegram` -> `[TG]`, `whatsapp` -> `[WA]`, `discord` -> `[DC]`, `slack` -> `[SL]`).

## Testing Decisions

- Test with mock / real `SessionDB`:
  - 10+ titled sessions + untitled sessions. Assert exactly 10 past titled sessions are returned, sorted by `last_active DESC`.
  - Assert formatting matches: Line 1 (ID + tags), Line 2 (Title with emoji), Line 3 (Quote preview with indent).
  - Assert active session is at index 1 labeled `(active)` when inside a session.
  - Assert numeric resume (`/resume 2`) maps to `selected[1]["id"]`.

## Out of Scope

- Modifying SQL schema or SQLite migrations.
- Modifying `/sessions` command behavior (focused specifically on `/resume`).
- Automatic titling of untitled sessions.
