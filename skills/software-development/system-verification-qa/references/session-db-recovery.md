# Session DB Recovery — when session_search misses sessions

## Problem (observed 2026-07-09)

`session_search` (discover mode) missed 20+ sessions from 8/7 because they had:
- Empty titles (`title = null`)
- Were cron jobs (`source = 'cron'`)
- The full-text index didn't cover them well

Worse: `session_search(session_id='20260708_040109_1391')` **fails** with "session_id not found" because the DB stores IDs with a suffix the search tool doesn't expect (e.g. `20260708_040109_1391fedc`, not `20260708_040109_1391`).

## Fix: query state.db directly via sqlite3

```python
import sqlite3, datetime

db = sqlite3.connect('/home/ubuntu/.hermes/state.db')
c = db.cursor()

# List ALL recent sessions with exact IDs + titles + timestamps
c.execute("""
    SELECT id, title, started_at, source
    FROM sessions
    WHERE started_at >= 1751913600000  -- optional: filter by epoch ms
    ORDER BY started_at DESC
""")
for row in c.fetchall():
    sa = row[2]
    dt = datetime.datetime.fromtimestamp(sa/1000)
    ds = dt.strftime('%Y-%m-%d %H:%M')
    print(ds, '|', row[3][:10], '|', row[0], '|', (row[1] or '')[:55])
```

## Key columns in `sessions` table

| Column | Type | Notes |
|--------|------|-------|
| `id` | text | Full ID WITH suffix (e.g. `20260708_040109_1391fedc`) |
| `title` | text | Often NULL for cron/background sessions |
| `started_at` | int | **Epoch milliseconds** (not seconds!) — divide by 1000 |
| `source` | text | `whatsapp`, `telegram`, `cron`, `cli` |
| `ended_at` | int | Epoch ms; NULL if still active |
| `message_count` | int | Total messages in session |

## Getting messages from a specific session

```python
c.execute("SELECT role, content FROM messages WHERE session_id=? ORDER BY id", (full_id,))
for m in c.fetchall():
    if m[0] == 'user' and m[1]:
        print(m[1][:300])  # truncate long content
```

## Gotcha: column names

The `sessions` table does NOT have `created_at` or `session_id` columns. Use `started_at` and `id` respectively.

## When to use this

- User asks "what did we do on date X?" and session_search returns nothing
- You need the exact session ID to pass to `session_search(session_id=...)` for full context
- Reconstructing a timeline across multiple days (audit/sync work)
- Verifying whether a claimed change actually happened in a session

## Pitfall: don't trust session_search's "no results"

Empty discover-mode results often mean the index missed them, NOT that no sessions exist. Always cross-check with the sqlite3 query above before concluding "8/7 was empty."
