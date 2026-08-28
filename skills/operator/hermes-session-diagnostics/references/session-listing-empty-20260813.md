# Empty `/sessions` + `/resume` — Telegram DM case (2026-08-13)

## Symptom
User ran `/sessions` in Telegram DM → "No sessions found. Use /title My Session to name this chat, or /sessions full to include unnamed sessions."
Same DM via `/resume` could not bind prior sessions.

## Environment
- Hermes VPS, `~/.hermes/state.db` = 1.84 GB, 1,139 session rows, 95,489 messages.
- Target chat session_key: `agent:main:telegram:dm:679729206` (user 679729206, display_name amirulhazym).

## Investigation (read-only first)
1. `sessions.json` (legacy mirror) showed the live session with correct session_key — not the cause.
2. `SELECT session_key, COUNT(*) FROM sessions GROUP BY session_key` → 10 distinct keys; the Telegram DM had 37 rows but **0 listable**.
3. Walked parent chain from current session `20260813_043109_7d6ea4d4` up to root `20260808_040236_9eee6992`: **217 chained rows**, all `source='telegram'`, display_name/user_id/chat_id = NULL on 180 of them (only the last ~37, created Aug 12 21:xx+, carry routing columns).
4. Ran the ACTUAL code path on a copy:
   ```python
   from hermes_state import SessionDB
   from hermes_cli.session_listing import query_session_listing
   # query_session_listing(source='telegram', session_key=KEY, current_session_id=CUR, include_unnamed=False, exclude_sources=['tool'], limit=10)
   ```
   → **RETURNED 0 rows** on the real DB. Confirmed listing is scoped by `session_key` and orphans drop out.
5. Contrast: WhatsApp DM `agent:main:whatsapp:dm:601166557800` has **root rows with session_key populated** → 2 listable rows. That is why one chat worked and the other did not.

## Root cause
The Telegram DM's chain root (and 180 ancestors) predate `session_key`/`user_id`/`chat_id` population, so they are `NULL`. `/sessions` filters on `session_key`; `/resume`'s `_resume_target_allowed` fails closed on NULL ownership. Both silently exclude the orphaned history → empty list. **Code is correct; data is orphaned.**

## Fix (proven on copy, NOT applied to prod)
Backfill on the 180 NULL ancestors:
```sql
UPDATE sessions SET session_key='agent:main:telegram:dm:679729206', user_id='679729206', chat_id='679729206', display_name='amirulhazym'
WHERE id IN (<180 ancestor ids>);
```
Re-running `query_session_listing` on the copy then returned the named row `Hermes Integration Reconciliation Review #108`.

## Status at session end
- Diagnosis: PROVEN (live code path, copy).
- Prod write: **NOT applied** — user had not approved the `state.db` modification. Mark any future "sessions fixed" claim PARTIAL/UNVERIFIED until the live backfill is run (with backup).

## Code pointers
- `gateway/slash_commands.py:4665` `_handle_sessions_command`
- `hermes_cli/session_listing.py:45` `query_session_listing` (visbility cut = `include_unnamed` + current-session skip)
- `hermes_state.py:7104` `list_sessions_rich` (the `session_key = ?` WHERE clause + `_LISTABLE_CHILD_SQL`)
- `hermes_state_common.py:103` `_LISTABLE_CHILD_SQL` (root + branch children only)
- `gateway/slash_commands.py:1030` `_resume_target_allowed` (fail-closed ownership)
