# Session Routing Repair — copy-paste SQL & commands (verified 2026-08-13)

All python via `venv/bin/python` from `/home/ubuntu/.hermes/hermes-agent`.
state.db is WAL — concurrent writes with the gateway running are safe; only the
in-memory routing map goes stale until restart.

## 0. Diagnose
```python
import sqlite3
c=sqlite3.connect('/home/ubuntu/.hermes/state.db'); cur=c.cursor()
cur.execute("SELECT COALESCE(source,'NULL'), COUNT(*) FROM sessions WHERE session_key IS NULL GROUP BY 1")
for r in cur.fetchall(): print(r)
cur.execute("SELECT DISTINCT session_key FROM sessions WHERE source='whatsapp' AND session_key IS NOT NULL")
print('keyed whatsapp:', [r[0] for r in cur.fetchall()])
cur.execute("SELECT DISTINCT session_key FROM sessions WHERE source='telegram' AND session_key IS NOT NULL")
print('keyed telegram:', [r[0] for r in cur.fetchall()])
```

## 1. Backup + official repair
```bash
cd /home/ubuntu/.hermes
TS=$(date +%Y%m%d_%H%M%S)
cp -p state.db "state.db.bak-approaches-${TS}"
sha256sum state.db "state.db.bak-approaches-${TS}"
cd /home/ubuntu/.hermes/hermes-agent
venv/bin/python -m hermes_cli.main sessions repair-routing          # dry-run
echo "y" | timeout 120 venv/bin/python -m hermes_cli.main sessions repair-routing --apply
venv/bin/python -m hermes_cli.main sessions repair-routing          # re-report
```

## 2. Telegram bulk backfill (SAFE only if exactly ONE keyed telegram key exists)
```python
import sqlite3
c=sqlite3.connect('/home/ubuntu/.hermes/state.db'); cur=c.cursor()
key='agent:main:telegram:dm:679729206'
cur.execute("UPDATE sessions SET session_key=?, user_id='679729206', chat_id='679729206', display_name='amirulhazym' WHERE source='telegram' AND session_key IS NULL", (key,))
c.commit()
cur.execute("SELECT COUNT(*) FROM sessions WHERE source='telegram' AND session_key IS NULL")
print('remaining NULL:', cur.fetchone()[0])
```

## 3. WhatsApp per-chain recover (down-chain BFS, then DM default)
```python
import sqlite3
from collections import defaultdict
c=sqlite3.connect('/home/ubuntu/.hermes/state.db'); cur=c.cursor()
children=defaultdict(list)
cur.execute("SELECT id, parent_session_id, session_key FROM sessions WHERE source='whatsapp'")
for rid,par,k in cur.fetchall():
    if par: children[par].append(rid)
def find_keyed_down(start):
    seen=set(); stack=list(children.get(start,[])); keys=set()
    while stack:
        nid=stack.pop()
        if nid in seen: continue
        seen.add(nid)
        cur.execute('SELECT session_key FROM sessions WHERE id=?',(nid,))
        k=cur.fetchone()[0]
        if k: keys.add(k)
        stack.extend(children.get(nid,[]))
    return keys
DM='agent:main:whatsapp:dm:601166557800'
updates=[]
cur.execute("SELECT id FROM sessions WHERE source='whatsapp' AND session_key IS NULL")
for nid in [r[0] for r in cur.fetchall()]:
    keys=find_keyed_down(nid)
    tgt=list(keys)[0] if len(keys)==1 else DM
    updates.append((tgt, nid))
cur.executemany("UPDATE sessions SET session_key=?, user_id=?, chat_id=?, display_name='amirulhazym' WHERE id=? AND session_key IS NULL",
                [(t, t.split(':')[-1], t.split(':')[-1], n) for t,n in updates])
c.commit()
```
NOTE: per-chain recovery is IMPERFECT for WhatsApp — it only recovers groups
with a keyed descendant. On this system 431/436 went DM-default; only ~5-9 had
chain evidence. For a solo user this is acceptable; do NOT present it as
accurate group attribution.

## 4. CRITICAL: fix WhatsApp identity to LID (not phone)
Session_key keeps the phone suffix, but `user_id`/`chat_id` MUST be the LID
(`13186321408227@lid`) for DM, and JID for groups — else the `/sessions`
ownership filter (`_resume_target_allowed`, slash_commands.py ~1131) silently
drops every tagged row.
```python
import sqlite3
c=sqlite3.connect('/home/ubuntu/.hermes/state.db'); cur=c.cursor()
LID='13186321408227@lid'
cur.execute("UPDATE sessions SET user_id=?, chat_id=? WHERE session_key='agent:main:whatsapp:dm:601166557800' AND (user_id IS NOT ? OR chat_id IS NOT ?)", (LID, LID, LID, LID))
cur.execute("UPDATE sessions SET user_id=?, chat_id=replace(substr(session_key, length('agent:main:whatsapp:group:')+1), ':601166557800', '') WHERE session_key LIKE 'agent:main:whatsapp:group:%' AND (user_id IS NOT ? OR chat_id IS NOT ?)", (LID, LID, LID))
c.commit()
```
Get the authoritative LID from `~/.hermes/sessions/sessions.json` origin blocks
or any naturally-keyed row — never from the session_key.

## 5. Verify the REAL path (with ownership filter)
```python
from pathlib import Path
from hermes_cli.session_listing import query_session_listing
from hermes_state import SessionDB
db = SessionDB(Path('/home/ubuntu/.hermes/state.db'))
rows = query_session_listing(db, session_key='agent:main:whatsapp:dm:601166557800',
                             source='whatsapp', include_unnamed=False, limit=50)
# replicate the DM ownership rule:
#   row_uid == CALLER_UID and row_chat == CALLER_CHAT  (CALLER = LID)
```
`/sessions` page limit is 10 (`rows[:10]`, slash_commands.py:4725); the active
session is excluded from listing by design.

## 6. Verify gateway restart actually happened
```bash
ps -eo pid,ppid,etimes,cmd | grep "hermes_cli.main gateway run" | grep -v grep
journalctl --user -u hermes-gateway --since "today" --no-pager | grep -iE "status=75|Stopping gateway for restart|Started hermes-gateway"
```
PID change + journal `status=75` = restart proven. Never trust user report alone
(`/clean-restart-gateway` is a SKILL, not a restart command — it does not reboot
the gateway).
