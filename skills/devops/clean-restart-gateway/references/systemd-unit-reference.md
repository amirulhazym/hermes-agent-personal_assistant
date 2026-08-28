# Systemd Unit Configuration

## Verification Source
`systemctl --user cat hermes-gateway.service` and `systemctl --user show hermes-gateway.service`

## Unit File
```
[Unit]
Description=Hermes Agent Gateway - Messaging Platform Integration
After=network-online.target
Wants=network-online.target
StartLimitIntervalSec=0                # No rate limiting interval

[Service]
Type=simple
ExecStart=python -m hermes_cli.main gateway run
WorkingDirectory=/home/ubuntu/.hermes
Environment=HERMES_HOME=/home/ubuntu/.hermes
Restart=always                          # Always restart on exit
RestartSec=5                            # 5 second delay between restarts
RestartForceExitStatus=75               # Exit code 75 triggers restart
KillMode=mixed                          # SIGTERM to main PID, others survive until TimeoutStopSec
KillSignal=SIGTERM
ExecReload=/bin/kill -USR1 $MAINPID
TimeoutStopSec=210                      # Wait 210s before SIGKILL escalation
SendSIGKILL=yes                         # Send SIGKILL after timeout
FinalKillSignal=SIGKILL                 # Signal 9 for final kill
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=default.target
```

## Key Values Reference

| Setting | Value | Effect |
|---------|-------|--------|
| `Type` | `simple` | systemd considers service started when `ExecStart` forks |
| `Restart` | `always` | Restarts regardless of exit code (0, 1, or signal) |
| `RestartSec` | 5 | Delay before restart attempt |
| `RestartForceExitStatus` | 75 | Exit code 75 forces restart even with `Restart=on-failure` |
| `KillMode` | `mixed` | SIGTERM to main PID only; rest of cgroup survives until `TimeoutStopSec` |
| `KillSignal` | `SIGTERM` | Signal sent on stop/restart |
| `TimeoutStopSec` | 210 | Max wait before SIGKILL escalation (30s headroom above 180s drain) |
| `SendSIGKILL` | yes | Escalate to SIGKILL after TimeoutStopSec |
| `FinalKillSignal` | `SIGKILL` (9) | Final force-kill signal |
| `ExecStop` | (not set) | Not needed for Type=simple |
| `StartLimitIntervalSec` | 0 | **No rate-limiting interval** — burst never enforced |
| `StartLimitBurst` | 5 | Burst limit cap (inert when IntervalSec=0) |
| `StartLimitAction` | none | Even if hit, just warn |
| `MainPID` | (auto) | Always identifies gateway python process |
| `GuessMainPID` | yes | Auto-detect main PID |
| `NRestarts` | (counter) | Increments on each restart (cosmetic only) |

## Cgroup Hierarchy
Both gateway and bridge live in the same cgroup:
```
/user.slice/user-1000.slice/<PRIVATE_RUNTIME_IDENTIFIER>/app.slice/hermes-gateway.service
├─ python gateway (MainPID)
├─ node bridge.js (child)
└─ agent subprocesses (bash, etc.)
```

## Start-Limit Behavior (Critical)
- `StartLimitIntervalSec=0` means **no start-limit protection is active**
- The `NRestarts` counter keeps incrementing but never blocks restarts
- Two deliberate restarts will NOT trigger `start-limit-hit`
- The counter resets when the service enters a non-restarting state for longer than the interval (but interval=0 means it never resets AND never blocks)

## Shutdown Timeline
| Duration | Phase | Escalation |
|----------|-------|------------|
| 0-5s | Graceful shutdown (drain=0) | Systemd waits |
| 5-180s | Drain timeout (drain=180) | Systemd waits — **deprecated, use drain=0** |
| 180-210s | Post-drain cleanup | Systemd still waits |
| 210s | TimeoutStopSec reached | **SIGKILL to cgroup** |

After SIGKILL at 210s:
- systemd sends SIGKILL (FinalKillSignal) to the entire cgroup
- Bridge and any remaining subprocesses are also killed
- Service transitions to `failed` state (signal-killed)
- `Restart=always` triggers restart regardless

## Verification Commands (Not Blocked by Guard)
```bash
systemctl --user status hermes-gateway.service      # Current state
systemctl --user show hermes-gateway.service          # All properties
systemctl --user cat hermes-gateway.service           # Unit file
systemctl --user is-active hermes-gateway.service     # active/inactive
systemctl --user is-failed hermes-gateway.service     # failed/active
```
