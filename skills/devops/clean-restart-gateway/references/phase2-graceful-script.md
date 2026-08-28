# Phase 2 — Graceful Kill Script (planned-stop + SIGTERM, drain=0)

## When to Use
**Phase 2 only.** The running gateway has `drain_timeout: 0` in config.yaml (set during Phase 0, loaded at startup after Phase 1 restart). SIGTERM alone triggers clean exit in ~5s without any force kill needed.

## Prerequisites
- `config.yaml` has `agent.restart_drain_timeout: 0` ✅
- restart-state.json written with `status: requested, method: phase2-graceful`

## Trigger Sequence
1. Kill script writes planned-stop marker with correct `target_start_time`
2. Planned-stop watcher thread consumes marker (~1ms) → initiates shutdown
3. SIGTERM arrives ~93ms later → redundant (shutdown already started by watcher)
4. `_drain_active_agents(0)` returns immediately (0.00s drain)
5. Adapters disconnect (~3s), bridge stops (~2s), gateway exits (~5s total)
6. systemd RestartSec=5 → new gateway at ~10s

Both the watcher and SIGTERM converge at `runner.stop()` — idempotent.

## Kill Script

Write to `/tmp/gw_refresh.sh`:

```bash
#!/bin/bash
# Phase 2: graceful restart — planned-stop marker + SIGTERM
set -e
HERMES_HOME="$HOME/.hermes"
PID_FILE="$HERMES_HOME/gateway.pid"
OUTCOME_FILE="$HERMES_HOME/logs/restart-outcome.json"

PID=$(python3 -c "import json;print(json.load(open('$PID_FILE'))['pid'])")

# Read start_time using robust parser matching gateway's _get_process_start_time
# Gateway: int(open(f'/proc/{pid}/stat').read().split()[21])
# After stripping PID + (comm): start_time at tail.split()[19]
START_TIME=$(python3 -c "
raw = open(f'/proc/$PID/stat').read()
full = raw.split()
close = raw.rindex(') ')
tail = raw[close+2:].split()
consumer = int(full[21])
producer = int(tail[19])
assert consumer == producer
print(consumer)
")

# Write planned-stop marker with verified matching start_time
python3 -c "
import json, os
from datetime import datetime, timezone
record = {
    'target_pid': $PID,
    'target_start_time': $START_TIME,
    'stopper_pid': os.getpid(),
    'written_at': datetime.now(timezone.utc).isoformat(),
}
with open('$HERMES_HOME/.gateway-planned-stop.json', 'w') as f:
    json.dump(record, f)
    f.flush()
    os.fsync(f.fileno())
"

# SIGTERM — watcher thread consumes marker first, initiates shutdown
kill "$PID"
echo "SIGTERM sent to PID $PID"

# Write outcome record
python3 -c "
import json
from datetime import datetime, timezone
outcome = {
    'ts': datetime.now(timezone.utc).isoformat(),
    'old_pid': $PID,
    'method': 'planned-stop-sigterm',
    'outcome': 'killed_graceful',
    'note': 'Phase 2 graceful restart — watcher consumed marker, drain=0.',
}
with open('$OUTCOME_FILE', 'w') as f:
    json.dump(outcome, f)
"
```

## Launch
```bash
terminal(background=true): bash /tmp/gw_refresh.sh
```

## Verification (in new session after restart)
1. Confirm marker was consumed: `~/.hermes/.gateway-planned-stop.json` does NOT exist
2. Confirm log: `"Received UNKNOWN as a planned gateway stop"` (watcher path) OR `"Received SIGTERM — initiating shutdown"` (redundant signal path)
3. Run 4-level verification checklist from SKILL.md
4. Update restart-state.json with outcome
5. Confirm hello-world proof
