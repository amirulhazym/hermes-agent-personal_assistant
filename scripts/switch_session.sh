#!/bin/bash
# switch_session.sh — Stop gateway, modify files, start gateway
# Runs via systemd-run timer, NOT as child of gateway process

sleep 3

# Stop gateway first (no more _save() overwrites)
systemctl --user stop hermes-gateway

# Modify sessions.json
python3 -c "
import json
with open('/home/ubuntu/.hermes/sessions/sessions.json') as f:
    d = json.load(f)
for k in d:
    if 'whatsapp:dm' in k and '601166557800' in k:
        d[k]['session_id'] = '20260727_180853_f758b16a'
        print(f'Updated: {k} -> 20260727_180853_f758b16a')
with open('/home/ubuntu/.hermes/sessions/sessions.json', 'w') as f:
    json.dump(d, f, indent=2)
"

# Modify state.db
python3 -c "
import sqlite3, time
db = sqlite3.connect('/home/ubuntu/.hermes/state.db')
db.execute('UPDATE sessions SET ended_at=?, end_reason=? WHERE id=? AND ended_at IS NULL',
    (time.time(), 'session_switch', '20260728_084152_61cef7b6'))
db.execute('UPDATE sessions SET ended_at=NULL, end_reason=NULL WHERE id=?',
    ('20260727_180853_f758b16a',))
db.commit()
db.close()
print('State.db updated')
"

# Start gateway
systemctl --user start hermes-gateway

echo 'Done. Gateway restarted with caveman session.'
