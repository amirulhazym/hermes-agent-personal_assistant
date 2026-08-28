# Session Store Schema & Listing Logic (hermes-agent source citations)

All citations are from `~/.hermes/hermes-agent/` as of the 2026-08-13 debug session.
Paths relative to that root.

## Table: `sessions` (in `~/.hermes/state.db`)
Relevant columns:
- `id` TEXT — session id, format `YYYYMMDD_HHMMSS_hex`.
- `source` TEXT — `telegram`, `whatsapp`, `cli`, `cron`, `subagent`, `unknown`, `tool`.
- `session_key` TEXT — gateway scope key, e.g. `agent:main:telegram:dm:679729206`. NULL on legacy/orphaned rows.
- `user_id`, `chat_id`, `thread_id`, `display_name` TEXT — ownership/identity columns. Originally only `source`+`user_id` were stored; `chat_id`/`thread_id`/`display_name`/full `session_key` capture came later. Rows created before that have NULLs.
- `parent_session_id` TEXT — forms compression/reset chains. NULL on true roots.
- `model_config` TEXT (JSON) — may hold `_branched_from` (branch marker) and `_delegate_from` (subagent marker).
- `archived` INT (0/1).
- `title` TEXT, `message_count` INT, `end_reason` TEXT (`compression`, `session_reset`, `idle`, `cron_complete`, `agent_close`, `orphaned_compression`, NULL...).

## Listing filter chain (the scope that hides orphaned rows)
`gateway/slash_commands.py::_handle_sessions_command` (line ~4665):
- Calls `query_session_listing(...)` from `hermes_cli/session_listing.py`.
- Passes `session_key` (caller's scope) and `exclude_sources=['tool']`.

`hermes_cli/session_listing.py::query_session_listing` (line 45):
- Calls `session_db.list_sessions_rich(source=..., session_key=session_key, exclude_sources=..., limit=...)`, then drops:
  - the current session id,
  - untitled rows unless `include_unnamed`.

`hermes_state.py::list_sessions_rich` (line 7104) — the WHERE that matters:
- `_LISTABLE_CHILD_SQL` (from `hermes_state_common.py` line 103):
  `(s.parent_session_id IS NULL OR <_BRANCH_CHILD_SQL>)`
  where `_BRANCH_CHILD_SQL` (line 85) checks `_branched_from` marker OR legacy `end_reason='branched'` parent heuristic.
- `session_key = ?` scope (line 7205-7207) — **this is the filter that excludes NULL-key ancestors**.
- `exclude_sources` → `s.source NOT IN (...)`.
- `archived = 0` (unless include_archived).

So a row is listable for a chat only if:
1. it is a root OR a branch child, AND
2. its `session_key` == caller's key, AND
3. not source `tool`, AND
4. not archived.

Orphaned historical rows fail (2) because `session_key IS NULL`.

## /resume fail-closed ownership (shares the cause)
`gateway/slash_commands.py::_handle_resume_command` → `_resume_target_allowed` (line 1030):
- For an inactive/persisted row, falls back to DB row `source`+`user_id`+`chat_id`+`thread_id` match against the caller.
- Any row with NULL `user_id`/`chat_id` (or mismatching `source`) → **fails closed** (returns False). So the same orphaned rows are not resumable either.
- Design note (lines 1065-1071): legacy NULL-owner rows are intentionally NOT resumable via this path; you must backfill ownership or use admin `--all`.

## Copy-first reproduction recipe (verified 2026-08-13)
```python
import shutil, pathlib, sys
sys.path.insert(0, '/home/ubuntu/.hermes/hermes-agent')
from hermes_state import SessionDB
from hermes_cli.session_listing import query_session_listing
shutil.copy('/home/ubuntu/.hermes/state.db', '/tmp/state_test.db')
db = SessionDB(db_path=pathlib.Path('/tmp/state_test.db'))
rows = query_session_listing(db, source='telegram',
    session_key='agent:main:telegram:dm:679729206',
    current_session_id='<current session id>',
    include_unnamed=False, exclude_sources=['tool'], limit=10)
print(len(rows))   # 0 before backfill on the broken chat
```

Observed (real VPS, 2026-08-13): Telegram DM `679729206` chain = 217 rows; 37 with `session_key`, 180 NULL → `/sessions` returns 0. WhatsApp DM `601166557800` root had `session_key` populated → 2 listable. Backfilling `session_key`+`user_id`+`chat_id`+`display_name` on the 180 NULL ancestors → `/sessions` returned the expected named row.
