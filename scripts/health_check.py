#!/usr/bin/env python3
"""Independent health monitor — runs via Linux system cron, not Hermes cron.

Silent when everything OK. Sends alert when something breaks.
Uses WhatsApp bridge first; falls back to Telegram Bot API.
"""

import os
import json
import time
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

# ── Cron schedule detection (croniter from Hermes venv) ──────────────────────
_CRONITER_AVAILABLE = False
_croniter = None
try:
    VENV_SITE = Path.home() / ".hermes/hermes-agent/venv/lib/python3.11/site-packages"
    if VENV_SITE.exists():
        import sys as _sys
        _sys.path.insert(0, str(VENV_SITE))
    from croniter import croniter as _croniter
    _CRONITER_AVAILABLE = True
except ImportError:
    pass

HOME = Path.home()
HERMES_HOME = HOME / ".hermes"

WHATSAPP_CHAT_ID = "13186321408227@lid"
WHATSAPP_BRIDGE = "http://127.0.0.1:3000"
TELEGRAM_CHAT_ID = "679729206"

# Read .env for Telegram token — independent of env vars
ENV_FILE = HERMES_HOME / ".env"
_TELEGRAM_TOKEN = None
if ENV_FILE.exists():
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            _TELEGRAM_TOKEN = line.split("=", 1)[1].strip("\"'")
            break

STATE_FILE = HERMES_HOME / "scripts/health_state.json"
LAST_CRON_OUTPUT_DIR = HERMES_HOME / "cron/output/c97c00f2fb46"
JOBS_FILE = HERMES_HOME / "cron/jobs.json"
MONITORED_JOB_ID = "c97c00f2fb46"
MONITOR_TIMEZONE = ZoneInfo("Asia/Kuala_Lumpur")
POST_RUN_GRACE_SECONDS = 5 * 60
OCCURRENCE_TOLERANCE_SECONDS = 2 * 60


# ── Cron schedule helpers ─────────────────────────────────────────────────────

def _load_jobs():
    """Load Hermes cron jobs from jobs.json."""
    try:
        with open(JOBS_FILE) as f:
            data = json.load(f)
        return data.get("jobs", [])
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _get_job(job_id, jobs):
    """Find a cron job by ID."""
    for job in jobs:
        if job.get("id") == job_id:
            return job
    return None


def _parse_myt(value):
    """Parse a Hermes timestamp and normalize it to Malaysia time."""
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=MONITOR_TIMEZONE)
        return parsed.astimezone(MONITOR_TIMEZONE)
    except (TypeError, ValueError):
        return None


def _cron_bounds(cron_expr, now):
    """Return the previous and next scheduled occurrences around ``now``."""
    if not _CRONITER_AVAILABLE or not cron_expr or _croniter is None:
        return None, None
    try:
        base = _parse_myt(now)
        if base is None:
            return None, None
        if _croniter.match(cron_expr, base):
            previous = base.replace(second=0, microsecond=0)
        else:
            previous = _croniter(cron_expr, base).get_prev(datetime)
        following = _croniter(cron_expr, base).get_next(datetime)
        return _parse_myt(previous), _parse_myt(following)
    except (TypeError, ValueError, KeyError):
        return None, None


def _matches_occurrence(value, expected):
    if value is None or expected is None:
        return False
    delta = (value - expected).total_seconds()
    return -OCCURRENCE_TOLERANCE_SECONDS <= delta <= POST_RUN_GRACE_SECONDS


def _assess_cron_execution(job, latest_output_at, now=None):
    """Assess scheduler/script execution independently of message delivery."""
    if not job:
        return False, f"Job {MONITORED_JOB_ID} not found"
    if not job.get("enabled", True):
        return True, None

    schedule = job.get("schedule", {})
    cron_expr = schedule.get("expr") if schedule.get("kind") == "cron" else None
    if not cron_expr:
        return False, "Monitored job has no parseable cron schedule"

    if job.get("last_status") not in (None, "ok"):
        return False, f"Script status: {job.get('last_status')}: {job.get('last_error') or 'unknown error'}"

    current = _parse_myt(now or datetime.now(MONITOR_TIMEZONE))
    if current is None:
        return False, "Unable to determine monitor time"
    previous, _following = _cron_bounds(cron_expr, current)
    if previous is None:
        return False, "Unable to calculate expected cron occurrence"

    last_run = _parse_myt(job.get("last_run_at"))
    latest_output = (
        datetime.fromtimestamp(latest_output_at, MONITOR_TIMEZONE)
        if latest_output_at is not None else None
    )
    created_at = _parse_myt(job.get("created_at"))

    # Before a job's first expected occurrence, silence is correct.
    if created_at and previous < created_at and last_run is None:
        return True, None

    # The scheduled occurrence is still inside the post-run grace window.
    if (current - previous).total_seconds() < POST_RUN_GRACE_SECONDS:
        return True, None

    run_matches = _matches_occurrence(last_run, previous)
    output_matches = _matches_occurrence(latest_output, previous)
    if run_matches and output_matches:
        return True, None

    expected = previous.strftime("%Y-%m-%d %H:%M %Z")
    evidence = []
    if not run_matches:
        evidence.append(f"last_run_at={job.get('last_run_at') or 'missing'}")
    if not output_matches:
        evidence.append("matching output file missing")
    return False, f"Expected execution at {expected}; " + "; ".join(evidence)


def _assess_cron_delivery(job, bridge_connected, execution_ok=True):
    """Assess delivery separately from scheduler/script execution."""
    if not job:
        return False, f"Job {MONITORED_JOB_ID} not found; delivery unknown"
    if not execution_ok:
        return False, "Delivery unknown because the expected cron execution is not current"
    if job.get("last_delivery_error"):
        return False, f"Execution recorded, but delivery failed: {job['last_delivery_error']}"
    if not bridge_connected:
        return False, "Bridge transport is disconnected; delivery cannot be confirmed"
    return True, None


# Notification state: track how many consecutive failures, avoid spam
DEFAULT_STATE = {
    "consecutive_fails": 0,
    "last_notified_at": 0,
    "last_recovery_at": 0,
    "failed_components": [],
}

def load_state():
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return dict(DEFAULT_STATE)

def save_state(state):
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def send_whatsapp(message):
    payload = json.dumps({"chatId": WHATSAPP_CHAT_ID, "message": message}).encode()
    req = urllib.request.Request(
        f"{WHATSAPP_BRIDGE}/send",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False

def send_telegram(message):
    token = _TELEGRAM_TOKEN
    if not token:
        return False
    payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}).encode()
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get("ok", False)
    except Exception:
        return False

def notify(message):
    whatsapp_ok = send_whatsapp(message)
    telegram_ok = send_telegram(f"🛡️ Health Monitor\n<pre>{message}</pre>")
    return whatsapp_ok or telegram_ok

def check_gateway():
    try:
        req = urllib.request.Request(f"{WHATSAPP_BRIDGE}/health", method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            if data.get("status") == "connected":
                return True, None
            return False, f"Bridge status: {data.get('status')}"
    except Exception as e:
        return False, f"Bridge unreachable: {e}"

def _latest_cron_output_at():
    """Return the mtime of the newest output file, or None if absent."""
    files = list(LAST_CRON_OUTPUT_DIR.glob("*.md"))
    if not files:
        return None
    try:
        return max(path.stat().st_mtime for path in files)
    except OSError:
        return None


def check_cron_execution():
    """Check scheduler invocation, script status, and output-file evidence."""
    try:
        job = _get_job(MONITORED_JOB_ID, _load_jobs())
        return _assess_cron_execution(job, _latest_cron_output_at())
    except Exception as e:
        return False, f"Cron execution check error: {e}"


def check_cron_delivery(bridge_connected, execution_ok):
    """Check the delivery boundary without treating it as cron execution."""
    try:
        job = _get_job(MONITORED_JOB_ID, _load_jobs())
        return _assess_cron_delivery(job, bridge_connected, execution_ok)
    except Exception as e:
        return False, f"Cron delivery check error: {e}"

def check_disk():
    stat = os.statvfs("/")
    total = stat.f_frsize * stat.f_blocks
    free = stat.f_frsize * stat.f_bavail
    used_pct = (1 - free / total) * 100
    if used_pct > 85:
        return False, f"Disk: {used_pct:.0f}% used"
    return True, None

def check_memory():
    try:
        with open("/proc/meminfo") as f:
            mem = {}
            for line in f:
                parts = line.split()
                mem[parts[0].rstrip(":")] = int(parts[1])
        avail_mb = mem.get("MemAvailable", 0) / 1024
        if avail_mb < 500:
            return False, f"Memory: {avail_mb:.0f}MB available"
        return True, None
    except Exception as e:
        return False, f"Memory check error: {e}"

def check_chain_cooldown():
    """Flag if D reminder count > 5 (spam anomaly)."""
    state_file = HERMES_HOME / "chain-state.json"
    try:
        with open(state_file) as f:
            data = json.load(f)
        d_count = data.get("reminder_counts", {}).get("D", 0)
        if d_count > 5:
            return False, f"D reminder count: {d_count} (possible spam)"
        return True, None
    except Exception:
        return True, None  # No state yet = fine

def main():
    state = load_state()
    now = time.time()

    bridge_check = check_gateway()
    execution_check = check_cron_execution()
    delivery_check = check_cron_delivery(bridge_check[0], execution_check[0])
    checks = [
        ("Bridge transport", bridge_check),
        ("Cron execution", execution_check),
        ("Cron delivery", delivery_check),
        ("Disk space", check_disk()),
        ("Memory", check_memory()),
        ("Chain cooldown", check_chain_cooldown()),
    ]

    failures = [(name, detail) for name, (ok, detail) in checks if not ok]
    failed_components = [name for name, _detail in failures]
    all_ok = len(failures) == 0

    prev_fails = state.get("consecutive_fails", 0)
    previous_components = set(state.get("failed_components", []))
    last_notified = state.get("last_notified_at", 0)

    if all_ok:
        state["consecutive_fails"] = 0
        state["failed_components"] = []
        # Recovery message identifies the component(s) that actually recovered.
        if prev_fails > 0 or previous_components:
            recovered = ", ".join(sorted(previous_components)) or "previous issue"
            if notify(f"✅ Health Monitor — recovered: {recovered}"):
                state["last_notified_at"] = now
            state["last_recovery_at"] = now
        save_state(state)
        return  # Silent exit — everything fine

    # We have failures
    state["consecutive_fails"] = min(prev_fails + 1, 99)
    state["failed_components"] = failed_components

    should_notify = False

    # Notify on first failure
    if prev_fails == 0:
        should_notify = True
    # Re-notify every 3 consecutive fails (suppress spam)
    elif state["consecutive_fails"] % 3 == 0:
        should_notify = True
    # Also re-notify if >30 min since last notification
    elif now - last_notified > 1800:
        should_notify = True

    if should_notify:
        lines = ["⚠️ Health Monitor — Issues detected:"]
        for name, detail in failures:
            lines.append(f"  • {name}: {detail}")
        message = "\n".join(lines)
        sent = notify(message)
        if sent:
            state["last_notified_at"] = now

    save_state(state)


if __name__ == "__main__":
    main()
