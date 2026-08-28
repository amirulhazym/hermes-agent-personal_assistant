#!/usr/bin/env python3
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

DB = Path('/home/ubuntu/.hermes/state.db')
LOG_DIR = Path('/home/ubuntu/.hermes/logs')
OUT = LOG_DIR / 'cron-health.last.json'

def cron_entries():
    out = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
    return [line for line in out.stdout.splitlines() if line.strip() and not line.lstrip().startswith('#')]

def db_probe():
    con = sqlite3.connect(f'file:{DB}?mode=ro', uri=True)
    cur = con.cursor()
    tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    messages = cur.execute('SELECT COUNT(*) FROM messages').fetchone()[0] if 'messages' in tables else None
    fts = cur.execute('SELECT COUNT(*) FROM messages_fts').fetchone()[0] if 'messages_fts' in tables else None
    con.close()
    return {'tables_present': sorted(tables), 'messages_count': messages, 'messages_fts_count': fts}

try:
    data = {
        'status': 'PASS',
        'timestamp_utc': datetime.now(timezone.utc).isoformat(),
        'cron_entry_count': len(cron_entries()),
        'cron_entries': cron_entries(),
        'db': db_probe(),
    }
except Exception as exc:
    data = {'status': 'FAIL', 'timestamp_utc': datetime.now(timezone.utc).isoformat(), 'error': repr(exc)}
OUT.write_text(json.dumps(data, indent=2) + '\n')
print(json.dumps(data, indent=2))
sys.exit(0 if data['status'] == 'PASS' else 1)