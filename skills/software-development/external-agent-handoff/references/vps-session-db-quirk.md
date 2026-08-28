# VPS Session DB Quirk — finding ALL sessions for a timeline

When building a full session timeline (e.g. for handoff docs), `session_search` tool is insufficient:

## Problem
- `session_search(query=...)` (FTS5 discover mode) misses sessions with empty titles or cron-generated sessions.
- `session_search(session_id=...)` fails when you pass the ID from a raw DB dump — the tool expects a different format (e.g. `20260708_040109_1391fedc` works, but the bare integer/UUID from DB does not).

## Working method (proven 2026-07-09)
1. Query the DB directly for ID + title + prefix:
```python
import sqlite3
db = sqlite3.connect('/home/ubuntu/.hermes/state.db')
c = db.cursor()
c.execute("SELECT id, title FROM sessions WHERE id LIKE '20260708%' OR id LIKE '20260709%' ORDER BY id")
for r in c.fetchall():
    print(r[0], '|', (r[1] or 'untitled')[:40])
```
2. The session ID prefix IS the date (`20260708_` = Aug 8). Use prefix filter — do NOT trust `started_at` column (it returns 1970 epoch — corrupted).
3. To read a session's content, pass the FULL id (with suffix) to `session_search(session_id=...)`. Large sessions return a saved file path — read with `read_file` offset/limit.

## Cron sessions
Cron jobs appear as sessions with IDs like `cron_06872bb284fa_20260708_131901`. They show in `session_search` browse but not always in keyword discover. Include them by listing all IDs with the date prefix.

## Messages table
For quick content scan without full session load:
```python
c.execute("SELECT id, role, content FROM messages WHERE session_id=? AND role='user' ORDER BY id", (sid,))
```
Truncate `content[:200]` to survey the conversation shape fast.
