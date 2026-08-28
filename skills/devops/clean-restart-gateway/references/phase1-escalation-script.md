# Phase 1 — Escalation Kill Script (bridge-first + SIGKILL)

## When to Use
**Phase 1 only.** The running gateway has `drain_timeout=180` (read at startup before config change). SIGTERM alone blocks 180s. This script kills the bridge first, then SIGKILLs the gateway. Proven working (July 17 incident).

## Prerequisites
- `config.yaml` already updated: `agent.restart_drain_timeout: 0` (takes effect on next gateway)
- restart-state.json written with `status: requested, method: phase1-escalation`

## Script
Write to `/tmp/gw_refresh.sh`:
```bash
#!/bin/bash
set -e
HERMES_HOME="$HOME/.hermes"
PID_FILE="$HERMES_HOME/gateway.pid"
OUTCOME_FILE="$HERMES_HOME/logs/restart-outcome.json"

# 1. Read gateway PID
PID=$(python3 -c "import json;print(json.load(open('$PID_FILE'))['pid'])")

# 2. Write planned-stop marker (for clean gateway_state tracking)
python3 -c "
import json
from datetime import datetime, timezone
open('$HERMES_HOME/.gateway-planned-stop.json', 'w').write(json.dumps({
    'target_pid': $PID,
    'written_at': datetime.now(timezone.utc).isoformat(),
}))
"

# 3. Kill bridge child first (avoids orphan on SIGKILL)
BRIDGE_PID=$(ps -eo pid,ppid,cmd | grep bridge.js | grep -v grep | awk '{print $1}')
if [ -n "$BRIDGE_PID" ]; then
  kill "$BRIDGE_PID"
  echo "SIGTERM sent to bridge PID $BRIDGE_PID"
  for i in 1 2 3 4 5; do
    kill -0 "$BRIDGE_PID" 2>/dev/null || { echo "Bridge exited after ${i}s"; break; }
    sleep 1
  done
  kill -0 "$BRIDGE_PID" 2>/dev/null && kill -9 "$BRIDGE_PID" && echo "Bridge force-killed"
fi

# 4. SIGKILL gateway (safe now — bridge already dead)
kill -9 "$PID"
echo "SIGKILL sent to gateway PID $PID"

# 5. Write outcome (read by new session)
python3 -c "
import json
from datetime import datetime, timezone
outcome = {
    'ts': datetime.now(timezone.utc).isoformat(),
    'old_pid': $PID,
    'method': 'bridge-first-sigkill',
    'outcome': 'killed_forced',
    'note': 'Phase 1 escalation — bridge killed first, then SIGKILL gateway. New gateway picks up drain_timeout=0.',
}
with open('$OUTCOME_FILE', 'w') as f:
    json.dump(outcome, f)
"
```

## Launch
```bash
terminal(background=true): bash /tmp/gw_refresh.sh
```

## Expected Timeline
| Time | Event |
|------|-------|
| T+0s | Script starts |
| T+0.1s | Bridge receives SIGTERM |
| T+0.1-5s | Bridge dies, port 3000 freed |
| T+5s | SIGKILL to gateway → immediate death |
| T+5s | systemd detects process killed |
| T+5s | Restart counter incremented |
| T+10s | systemd RestartSec=5 → new gateway starts |
| T+10-15s | New gateway boots with drain_timeout=0 |
| Total | **~10-15s** |

## Safety
✅ Bridge killed first — no orphan process
✅ Planned-stop marker written — gateway_state "stopped" persists correctly
✅ New gateway reads `drain_timeout: 0` — all future restarts use Phase 2
✅ systemd Restart=always — auto-respawns
✅ New gateway's `_kill_stale_bridge_by_pidfile()` cleans any remaining bridge

## Do NOT
- **Skip bridge kill before SIGKILL** — orphaning bridge holds port 3000 → respawn conflict
- **Use this for Phase 2** — once drain_timeout=0, just use SIGTERM (Phase 2 script)
