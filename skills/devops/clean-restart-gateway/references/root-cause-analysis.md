# Clean Restart Gateway — Root Cause Analysis

## The Problem
The July 17 clean-restart-gateway run took ~3 minutes with 4 ad-hoc scripts, troubleshooting loop, and eventual SIGKILL. The original skill claimed "takeover marker bypasses drain" — this was wrong.

## Verified Facts (Live VPS Evidence)

### Signal Timeline (from `journalctl --user -u hermes-gateway`)
```
07:12:49  SIGTERM #1 acknowledged → drain starts (180s timeout)
07:12:49  "Shutdown context: signal=SIGTERM under_systemd=yes parent_pid=1115"
07:14:28  SIGTERM #2 (from gw_sigint.sh or retry)
07:15:04  Bridge exited with code -15 (SIGTERM) — from gw_controlled_stop.sh
07:15:05  SIGTERM #3
07:15:42  systemd: "code=killed, status=9/KILL" ← SIGKILL from gw_force_kill.sh
07:15:47  systemd: "Scheduled restart job, restart counter is at 5"
07:15:47  "Started hermes-gateway.service" (fresh PID 1623393)
```

### What Killed the Gateway
- Not SIGTERM (drain was running)
- Not bridge death (that helped but didn't unblock the drain)
- **SIGKILL** from `gw_force_kill.sh` at 07:15:42

### What the Takeover Marker Actually Does
From `gateway/run.py:17270-17363` — verified live:

```python
def shutdown_signal_handler(received_signal=None):
    # 1. Check takeover marker
    planned_takeover = consume_takeover_marker_for_self()  # bool

    # 2. Check planned-stop marker (if not takeover)
    planned_stop = consume_planned_stop_marker_for_self()

    # 3. ALL THREE paths converge at:
    asyncio.create_task(runner.stop())  # <--- line 17363, ALWAYS called
```

The takeover marker does NOT change the shutdown path. It only:
- Changes the log message ("planned takeover" vs "initiating shutdown")
- Prevents `_signal_initiated_shutdown = True`, which controls `gateway_state` persistence

But `runner.stop()` → `_drain_active_agents(180)` runs in ALL cases.

### The Real Fix
In `gateway/run.py:4344`:
```python
async def _drain_active_agents(self, timeout: float):
    if not self._running_agents:
        return snapshot, False  # No agents → no drain
    if timeout <= 0:
        return snapshot, True   # timeout=0 → return immediately
    # ... otherwise wait up to timeout seconds
```

Setting `config.yaml: agent.restart_drain_timeout: 0` makes the drain return immediately. Gateway exits cleanly in ~5s.

### The Catch-22
The agent running the restart IS an active session counted in `self._running_agents`. The drain waits for ALL agents to finish. So the agent waits 180s for itself to finish. After 180s timeout, agents are force-interrupted, THEN tool subprocesses are killed, adapters disconnect, and gateway exits.

## Why the V2 Skill Was Wrong
The v2 skill claimed the takeover marker "calls sys.exit(0) immediately — bypassing the 180s drain loop." This statement appears:
- In the SKILL.md KEY FACT section
- In references/takeover-kill-script.md
- In the WHY GATEWAY SHUTDOWN section

All of these are incorrect. The handler does NOT call sys.exit(0) for a takeover marker. It calls `runner.stop()` like every other path.

## Proper Methodology (Two-Phase)

### Phase 1 — One-Time Config Change + Escalation Restart
1. Set `config.yaml: agent.restart_drain_timeout: 0`
2. Kill bridge first (SIGTERM, wait up to 5s, force-kill if needed)
3. SIGKILL gateway (safe — bridge already dead)
4. New gateway starts with `drain_timeout=0`

### Phase 2 — All Future Restarts (Graceful)
1. Write planned-stop marker
2. SIGTERM → `_drain_active_agents(0)` → returns immediately
3. Adapters disconnect cleanly (~3s)
4. Bridge stops (~2s)
5. Gateway exits with code 0
6. systemd RestartSec=5 → new gateway at ~8-10s

## Source Files Verified
| File | Key Finding |
|------|-------------|
| `config.yaml` (line 21) | `restart_drain_timeout: 180` |
| `gateway/run.py:17270-17363` | Signal handler — ALL paths call `runner.stop()` |
| `gateway/run.py:4325-4353` | `_drain_active_agents` — returns immediately when timeout ≤ 0 |
| `gateway/status.py` | `write_takeover_marker()` — field 22 of `/proc/PID/stat` |
| `systemctl --user cat hermes-gateway.service` | `Restart=always`, `RestartSec=5`, `KillMode=mixed`, `TimeoutStopSec=210` |
| `/tmp/gw_*.sh` (4 files) | Evidence of troubleshooting loop |

## Credits
- Root cause document authored by user (amirulhazym) — 95% correct analysis
- Live verification + correction of takeover marker claim by MJ Hermes Agent (2026-07-17)
