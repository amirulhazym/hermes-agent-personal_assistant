# Session DB Recovery — Recovering "What Did We Say On Date X"

**Why this exists:** On 2026-07-09 the agent fabricated "CC = C+D" from memory, then had to recover what the user actually meant by grepping Hermes' session DB. The recovery took ~30s and would have prevented a full rage-loop if done BEFORE answering. This file is the reusable technique.

## Where conversation history lives

Hermes stores all chat history in a SQLite DB, NOT just in gateway.log.

- **DB path:** `/home/ubuntu/.hermes/state.db`
- **Tables:**
  - `sessions` — one row per session. Columns: `id`, `source`, `user_id`, `title`, `started_at` (epoch float), `message_count`, ...
  - `messages` — one row per message. Columns: `id`, `session_id`, `role` (user/assistant/tool), `content`, `tool_name`, `timestamp` (epoch float), ...
  - FTS5 virtual tables (`messages_fts*`) exist but plain `LIKE` on `content` is simpler and reliable.

## What gateway.log / agent.log do NOT give you

`~/.hermes/logs/gateway.log` stores inbound message text + response **char count only**, not response text. Example:
```
2026-07-03 14:15:46 INFO gateway.run: inbound message: ... msg='Dah makan both CCC now.'
2026-07-03 14:15:46 INFO ... response ready: ... response=167 chars
```
You cannot read what the agent *answered* from logs. For full Q&A context you MUST query `state.db`.

## Recovery recipe (copy-paste, verified 2026-07-09)

```python
import sqlite3, datetime
con = sqlite3.connect('/home/ubuntu/.hermes/state.db')
con.row_factory = sqlite3.Row
cur = con.cursor()

# 1. Find any message containing a shorthand/phrase
needle = '%CCC%'   # or '%CC%', '%both%', '%med_confirm%', etc.
cur.execute(
    "SELECT session_id, role, content, timestamp FROM messages "
    "WHERE content LIKE ? ORDER BY id", (needle,))
for r in cur.fetchall():
    d = dict(r)
    print(d['session_id'], '|', d['role'], '|', repr(d['content'])[:300])

# 2. Read the full conversation in the session you found
sid = '<session_id from step 1>'
cur.execute("SELECT role, content, timestamp FROM messages WHERE session_id=? ORDER BY id", (sid,))
for r in cur.fetchall():
    d = dict(r)
    c = d['content']
    if d['role'] == 'tool' and len(c) > 200:
        c = c[:200] + '...[tool truncated]'
    ts = datetime.datetime.fromtimestamp(
        d['timestamp'], tz=datetime.timezone(datetime.timedelta(hours=8))
    ).strftime('%Y-%m-%d %H:%M')
    print(f'[{ts}][{d["role"]}]', c[:600]); print('---')
```

## Known quirks

- **Timestamps are epoch floats in MYT (+08).** Convert with `datetime.timezone(timedelta(hours=8))`.
- **Multi-session splits:** Long sessions get auto-compressed/split (gateway.log shows `Session split detected: X → Y`). The `messages` table still holds all of them keyed by `session_id` — query by the ID you found, not by a guessed one.
- **FTS5 `session_search` tool may return 0 results** for date-scoped queries even when rows exist in `state.db`. If `session_search(query=...)` returns empty, fall back to the raw SQL above.
- **Tool messages are noisy.** Filter `role != 'tool'` or truncate tool output (as in recipe) or you'll drown in JSON blobs.
- **WhatsApp vs Telegram:** `source` column distinguishes them; the chat_id in logs (e.g. `13186321408227@lid`) maps to a `user_id` in `sessions`.

## When to use this (not just meds)

Any time the user says "semalam kau faham", "recall what we decided", "kau pernah cakap", or references a shorthand/code you don't have evidence for — query state.db BEFORE answering. Memory recall is NOT evidence.
