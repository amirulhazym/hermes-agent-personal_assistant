# Self-restart → auto-resume loop (2026-07-29 incident)

## Failure chain

A restart script was launched from the active Hermes gateway agent and targeted the gateway's own PID:

```text
agent tool starts self-termination script
→ gateway receives SIGTERM
→ active tool turn is interrupted
→ systemd starts a new gateway
→ Hermes schedules the interrupted session for auto-resume
→ resumed agent sees the unfinished terminal call
→ same self-termination command is replayed
```

This is not an ordinary model iteration loop. It is a process-restart/auto-resume feedback loop.

## Evidence pattern

Capture all of these before claiming recovery:

- repeated `SIGTERM` / shutdown-context entries;
- repeated tool errors containing the same restart request ID;
- repeated `Scheduled auto-resume for ... restart-interrupted session(s)`;
- systemd `NRestarts` increasing;
- restart-state stuck at `requested` with no `new_pid`, `completed_at`, or outcome;
- current service/bridge status after the loop has stopped.

## Safe response

1. Stop executing the restart command and remove only the temporary trigger after confirming it is not running.
2. Do not issue another restart from the active gateway session.
3. Verify service PID, systemd state, bridge `/health`, queue length, credentials existence, and restart-state read-only.
4. If the bridge is connected, perform live inbound/outbound delivery verification instead of reloading.
5. Any future restart must be launched by an external supervisor/operator and must be single-shot/idempotent.

## Status boundary

A running gateway and connected bridge prove current availability only. They do not prove that the interrupted restart transaction completed cleanly, that no message was lost during restart windows, or that destination-side receipt was observed. Keep those claims separate.
