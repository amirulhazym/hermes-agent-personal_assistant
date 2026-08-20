#!/usr/bin/env bash
# Safe-only post-midnight diagnostics. Uses Python sqlite3; no sqlite3 CLI dependency.
set -uo pipefail
LOG=/home/ubuntu/.hermes/logs/auto-after-midnight.log
PROPOSALS=/home/ubuntu/.hermes/logs/proposals
LOCK=/home/ubuntu/.hermes/logs/auto-after-midnight.lock
mkdir -p "$PROPOSALS"
exec 9>"$LOCK"
if ! flock -n 9; then
  printf '%s LOCKED\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$LOG"
  exit 0
fi
START=$(date -u +%Y-%m-%dT%H:%M:%SZ)
{
  echo "===== auto-after-midnight $START ====="
} >> "$LOG"

python3 - "$LOG" "$PROPOSALS" <<'PY'
import json, sqlite3, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path
log = Path(sys.argv[1]); proposals = Path(sys.argv[2])
db = 'file:/home/ubuntu/.hermes/state.db?mode=ro'
try:
    con = sqlite3.connect(db, uri=True)
    cur = con.cursor()
    tables = {r[0] for r in cur.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    # Schema-backed activity check: messages.timestamp is numeric epoch in this DB.
    cols = [r[1] for r in cur.execute('PRAGMA table_info(messages)')]
    if 'timestamp' not in cols or 'role' not in cols:
        raise RuntimeError(f'unsupported messages schema: {cols}')
    now = int(datetime.now(timezone.utc).timestamp())
    inbound = cur.execute("SELECT COUNT(*) FROM messages WHERE role='user' AND timestamp >= ?", (now - 3600,)).fetchone()[0]
    fts = cur.execute('SELECT COUNT(*) FROM messages_fts').fetchone()[0] if 'messages_fts' in tables else None
    con.close()
    disk = subprocess.check_output(['df', '-P', '/'], text=True).splitlines()[-1].split()[3]
    tmp_proc = subprocess.run(['du', '-B1', '-s', '/tmp'], capture_output=True, text=True)
    tmp = tmp_proc.stdout.split()[0] if tmp_proc.stdout.split() else '0'
    tmp_du_rc = tmp_proc.returncode
    log.write_text(log.read_text() + f'user_inbound_last_hour={inbound}\nfts5_messages_count={fts}\ndisk_free_kb={disk} tmp_used_bytes={tmp} tmp_du_rc={tmp_du_rc}\n')
    p = proposals / (datetime.now().strftime('%Y%m%d') + '-proposals.md')
    p.write_text('# Safe diagnostics\n\n- Schema-backed activity query completed.\n- user_inbound_last_hour: ' + str(inbound) + '\n- FTS5 rows: ' + str(fts) + '\n- No code/config/deploy action executed.\n')
    log.write_text(log.read_text() + f'proposal_written={p}\nstatus=PASS\n')
except Exception as exc:
    log.write_text(log.read_text() + f'status=FAIL error={exc!r}\n')
    raise
PY
END=$(date -u +%Y-%m-%dT%H:%M:%SZ)
printf '%s end=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$END" >> "$LOG"