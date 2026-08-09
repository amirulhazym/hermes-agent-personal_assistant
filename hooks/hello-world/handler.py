"""
hello-world hook — fires on gateway:startup and writes a pending marker
so the hello_watch cron script picks it up and sends "Hello World" to
whichever channel is configured for the cron job's delivery.

Design: minimal, fail-open, no imports beyond stdlib.
"""
import os
import sys
import time
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
PENDING_FILE = HERMES_HOME / "hello-world-pending.txt"

_RESTART_TS = str(int(time.time()))


def handle(event_type: str, context: dict) -> None:
    """Write a pending marker on every gateway restart."""
    if event_type != "gateway:startup":
        return
    try:
        PENDING_FILE.parent.mkdir(parents=True, exist_ok=True)
        PENDING_FILE.write_text(_RESTART_TS, encoding="utf-8")
        print(f"[hooks:hello-world] Gateway restarted — wrote {PENDING_FILE}", flush=True)
    except Exception as e:
        print(f"[hooks:hello-world] Error writing pending file: {e}", file=sys.stderr, flush=True)
