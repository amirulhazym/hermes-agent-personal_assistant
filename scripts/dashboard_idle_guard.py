#!/usr/bin/env python3
"""Stop the Hermes dashboard after it has been idle for N hours.

Owner policy (2026-11-10): the dashboard is "on" only while someone is using
it. RDC/desktop-commander is explicitly out of scope — never touched here.

Idle = no ESTABLISHED TCP connection to the dashboard port for `--idle-hours`.
A connection that stays open (browser tab left open) counts as activity, which
is the intended meaning of "in use".

Runs from a systemd timer as root; state is a single epoch file so restarts of
the guard do not lose the idle clock.

Usage:
    dashboard_idle_guard.py --dry-run
    dashboard_idle_guard.py --idle-hours 4
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from typing import Optional, Tuple

SERVICE = "hermes-dashboard.service"
PORT = 9119
STATE_FILE = "/var/lib/hermes-dashboard-idle/last_activity"
IDLE_HOURS = 4.0


def _run(cmd: list) -> Tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        return p.returncode, (p.stdout + p.stderr).strip()
    except (OSError, subprocess.SubprocessError) as exc:
        return 127, str(exc)


def service_active(service: str = SERVICE) -> bool:
    rc, out = _run(["systemctl", "is-active", service])
    return rc == 0 and out == "active"


def count_active_connections(port: int = PORT) -> int:
    """ESTABLISHED connections to the dashboard port."""
    rc, out = _run(["ss", "-Htn", "state", "established", f"sport = :{port}"])
    if rc != 0:
        return 0
    return len([line for line in out.splitlines() if line.strip()])


def read_last_activity(path: str = STATE_FILE) -> Optional[float]:
    try:
        with open(path, "r") as fh:
            return float(fh.read().strip())
    except (OSError, ValueError):
        return None


def write_last_activity(now: float, path: str = STATE_FILE) -> None:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as fh:
            fh.write(str(int(now)))
    except OSError as exc:
        print(f"warn: cannot write state {path}: {exc}")


def decide(
    now: float,
    last_activity: float,
    idle_seconds: float,
    active_connections: int,
) -> str:
    """Return one of: 'active', 'idle-keep', 'idle-stop'."""
    if active_connections > 0:
        return "active"
    if now - last_activity >= idle_seconds:
        return "idle-stop"
    return "idle-keep"


def main(argv: Optional[list] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--idle-hours", type=float, default=IDLE_HOURS)
    ap.add_argument("--state-file", default=STATE_FILE)
    ap.add_argument("--service", default=SERVICE)
    ap.add_argument("--port", type=int, default=PORT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    now = time.time()

    if not service_active(args.service):
        # Keep the clock fresh while it is down so a manual start always gets
        # the full idle window instead of being reaped on the next tick.
        write_last_activity(now, args.state_file)
        print(json.dumps({"action": "noop", "reason": "service-inactive"}))
        return 0

    last = read_last_activity(args.state_file)
    if last is None:
        write_last_activity(now, args.state_file)
        print(json.dumps({"action": "init", "reason": "no-state", "idle_hours": args.idle_hours}))
        return 0

    conns = count_active_connections(args.port)
    verdict = decide(now, last, args.idle_hours * 3600, conns)

    payload = {
        "action": "keep" if verdict != "idle-stop" else "stop",
        "reason": verdict,
        "idle_hours": args.idle_hours,
        "idle_for_hours": round((now - last) / 3600, 2),
        "established": conns,
        "dry_run": args.dry_run,
    }

    if verdict == "idle-stop" and not args.dry_run:
        rc, out = _run(["systemctl", "stop", args.service])
        payload["stop_rc"] = rc
        if rc != 0:
            payload["stop_error"] = out[:200]
        else:
            write_last_activity(now, args.state_file)
    elif verdict == "active":
        write_last_activity(now, args.state_file)

    print(json.dumps(payload))
    return 0 if payload.get("stop_rc", 0) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
