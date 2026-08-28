# Gateway Startup Hooks for Monitoring

## The Hello World Pattern

Use `gateway:startup` hooks to confirm a successful restart and detect
unexpected reboots (OOM kills, bot crashes, silent restarts).

## Mechanism

```python
# ~/.hermes/hooks/hello-world/handler.py
import os, sys, time
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))

def handle(event_type: str, context: dict) -> None:
    if event_type != "gateway:startup":
        return
    (HERMES_HOME / "hello-world-pending.txt").write_text(str(int(time.time())))
    print("[hooks:hello-world] Wrote pending marker", flush=True)
```

The cron job watches for the pending file:
```python
# ~/.hermes/scripts/hello_watch.py — no_agent=true
PENDING = Path.home() / ".hermes" / "hello-world-pending.txt"
SENT_MARKER = Path.home() / ".hermes" / "hello-world-sent.txt"

if PENDING.exists() and (time.time() - PENDING.stat().st_mtime) > 10:
    print("Test message delivered!")
    SENT_MARKER.write_text(PENDING.read_text())
    PENDING.unlink()
else:
    sys.exit(0)  # silent
```

## Hook Configuration

```yaml
# ~/.hermes/hooks/hello-world/HOOK.yaml
name: hello-world
events:
  - gateway:startup
```

Cron job:
```
name: hello-world-watch
schedule: every 1 minute
script: hello_watch.py
no_agent: true
deliver: whatsapp:CHAT_ID  # or 'origin' for auto-detect
```

## Design Rules

1. **Always use a 10-second delay** — the hook fires during gateway init,
   before the cron scheduler fully starts. The delay ensures the cron system
   is ready to receive and deliver.
2. **Sent marker prevents double-send** — if the gateway restarts twice in
   quick succession (systemd restart loop), the same restart instance isn't
   announced twice.
3. **Fails open** — if the hook errors, the cron script silently exits.
   No message is sent, but no error is raised.
4. **PENDING + SENT_MARKER in .hermes/** — avoids permission issues and
   keeps monitoring artifacts co-located with gateway state.

## Extending

Same mechanism works for:
- Daily health checks (cron every 5 min, sends heartbeat on absence)
- Uptime monitoring (compare restart timestamps)
- Bot self-recovery alerts (detect 3+ restarts in 10 min = problem)
