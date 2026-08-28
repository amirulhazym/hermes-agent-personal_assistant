#!/usr/bin/env python3
"""
hello_watch.py — no_agent cron script for Hello World delivery.

Checks if hello-world-pending.txt exists (written by hello-world hook on
gateway:startup). If found and >10 seconds old (gateway fully up), outputs
a "Hello World" message which the cron system delivers to the user.

This script runs with no_agent=true, so its stdout IS the delivered message.
Empty stdout = silent = nothing sent.
"""
import os
import sys
import time
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
PENDING = HERMES_HOME / "hello-world-pending.txt"
SENT_MARKER = HERMES_HOME / "hello-world-sent.txt"

if not PENDING.exists():
    # Nothing pending — silent exit
    sys.exit(0)

# Check if we already sent for THIS restart instance (avoid double-send)
pending_ts = PENDING.read_text(encoding="utf-8").strip()
if SENT_MARKER.exists():
    sent_ts = SENT_MARKER.read_text(encoding="utf-8").strip()
    if sent_ts == pending_ts:
        # Already sent for this restart — clean up and silent
        PENDING.unlink(missing_ok=True)
        SENT_MARKER.unlink(missing_ok=True)
        sys.exit(0)

# Wait a minimum of 10 seconds after restart to ensure gateway is fully up
if time.time() - PENDING.stat().st_mtime < 10:
    sys.exit(0)

# Deliver Hello World
print("🌏 Hello World! Gateway restarted successfully ✅")
sys.stdout.flush()

# Record delivery to prevent repeats
SENT_MARKER.write_text(pending_ts, encoding="utf-8")
PENDING.unlink(missing_ok=True)
