# Post-Restart Session Auto-Resume Path

## Verified From
`gateway/run.py:5007-5103` and `run.py:5660`

## How It Works

### During Shutdown (BEFORE drain)
```python
# Line 6396-6411 in _stop_impl()
# Mark all running sessions as resume_pending with reason "restart_timeout"
for _sk, _agent in list(self._running_agents.items()):
    self.session_store.mark_resume_pending(
        _sk, "restart_timeout"
    )
```

This writes a durable marker to SQLite (`~/.hermes/state.db` or `sessions/default.db`) that survives the gateway exit.

### During New Gateway Startup
```python
# Line 5660 in start()
self._schedule_resume_pending_sessions()
```

Called AFTER adapters connect but BEFORE startup restore completes. The function:

```python
# Line 5007-5103
def _schedule_resume_pending_sessions(self, platform=None) -> int:
    # 1. Query session_store for entries where:
    #    resume_pending=True
    #    AND NOT suspended
    #    AND resume_reason in _AUTO_RESUME_REASONS
    #       = {"restart_timeout", "shutdown_timeout", "restart_interrupted"}
    #    AND (platform is None OR origin.platform == platform)

    # 2. For each candidate:
    #    - Skip if freshness window expired (default: 3600s from last_resume_marked_at)
    #    - Skip if session_key already in _running_agents (already being resumed)
    #    - Skip if adapter not ready yet
    #    - Claim session slot (install _AGENT_PENDING_SENTINEL)
    #    - Create synthetic MessageEvent(text="", internal=True)
    #    - Dispatch to adapter via _run_startup_resume_event()

    # 3. On successful resume:
    #    The _is_resume_pending branch in _handle_message_with_agent
    #    injects a system note: "Previous session interrupted by gateway restart"
    #    Then runs the agent turn normally

    # 4. Auto-resume happens WITHOUT user message
```

### If Auto-Resume Fails
```python
# Line 5019 comment:
# "will auto-resume on the next real user message"
```

The session stays `resume_pending`. The `_is_resume_pending` branch in `_handle_message_with_agent` is triggered on ANY inbound message for that session_key, including the user's next message.

### Session Freshness Window
```python
_AUTO_RESUME_FRESHNESS_WINDOW = 3600  # seconds (configurable)
```
Sessions older than 3600 seconds since their last resume marker are skipped. The user's next message would trigger a fresh session.

### What the Resumed Session Sees
The synthetic event has `text=""` (empty). The `_is_resume_pending=True` flag causes the system to inject a preamble:
> "The previous session was interrupted by a gateway restart. Picking up where we left off."

This appears as a system note in the conversation. The agent then runs an automatic turn with the existing context.

### Transaction Finalization (Verification)
The resumed agent session is the one that runs verification:
1. New gateway starts → `_schedule_resume_pending_sessions()` → auto-resumes the interrupted session
2. The resumed session reads `restart-outcome.json` (written by kill script) and `restart-state.json`
3. Runs the 4-level verification checklist
4. Updates `restart-state.json` with final outcome + `verified_graceful`/`verified_forced`
5. Reports to user

### If User Never Messages Back
- `hello-world-watch` cron (no_agent, every 30s) independently sends Hello World proof to WhatsApp
- `chain_monitor.sh` cron continues ticking — confirms scheduler is alive
- Transaction record stays in active phase → treated as stale after 30s + systemctl verify → next restart clears it
