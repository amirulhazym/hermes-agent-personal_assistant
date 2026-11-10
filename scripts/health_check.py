#!/usr/bin/env python3
"""Independent health monitor — runs via Linux system cron, not Hermes cron.

Silent when everything OK. Alerts on state change, escalation, or once every
6h while a problem persists. Recovery notice when the fault clears.

Memory tracking covers BOTH RAM availability and swap consumption, because a
host can sit at ~500MB free with swap 100% full and zero OOM headroom — the
old RAM-only check could not tell those states apart.

Uses WhatsApp bridge first; falls back to Telegram Bot API.
"""

import os
import json
import sys
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

    # If the job is outside its active execution window (e.g. night hours),
    # the last scheduled slot was hours ago. If the job already ran at or after
    # that previous slot (or ran during gateway catch-up), do not flag as missing.
    if last_run and last_run >= previous:
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


# Notification state: track failure fingerprint/severity, avoid spam
DEFAULT_STATE = {
    "consecutive_fails": 0,
    "last_notified_at": 0,
    "last_recovery_at": 0,
    "failed_components": [],
    "fingerprint": "",
    "max_severity": 0,
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

# Severity model: every check returns (severity, detail) where severity is
# None (healthy), "warning", or "critical".
SEV_RANK = {"warning": 1, "critical": 2}

# Memory thresholds. RAM threshold stays at the owner-approved 500MB floor;
# swap is tracked because a host can pass the RAM check with zero swap left.
RAM_WARN_MB = 500
RAM_CRIT_MB = 250
SWAP_WARN_PCT = 80
SWAP_CRIT_FREE_MB = 50
REMIND_SECONDS = 6 * 3600


def _meminfo():
    mem = {}
    with open("/proc/meminfo") as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2:
                mem[parts[0].rstrip(":")] = int(parts[1])
    return mem


def _top_consumers(n=3):
    """Aggregate RSS by process name; diagnostic hint, not a decision input."""
    seen = {}
    for status in Path("/proc").glob("[0-9]*/status"):
        try:
            name = rss = None
            for line in status.read_text(errors="ignore").splitlines():
                if line.startswith("Name:"):
                    name = line.split(":", 1)[1].strip()
                elif line.startswith("VmRSS:"):
                    rss = int(line.split()[1])
                    break
            if name and rss:
                seen[name] = seen.get(name, 0) + rss
        except (OSError, ValueError):
            continue
    return ", ".join(
        f"{name} {rss // 1024}MB"
        for name, rss in sorted(seen.items(), key=lambda kv: -kv[1])[:n]
    )


def _memory_summary():
    try:
        mem = _meminfo()
        avail_mb = mem.get("MemAvailable", 0) / 1024
        swap_total = mem.get("SwapTotal", 0) / 1024
        swap_free = mem.get("SwapFree", 0) / 1024
        return (
            f"RAM {avail_mb:.0f}MB avail; "
            f"swap {max(swap_total - swap_free, 0):.0f}/{swap_total:.0f}MB"
        )
    except Exception:
        return "Memory metrics unavailable"


def check_disk():
    stat = os.statvfs("/")
    total = stat.f_frsize * stat.f_blocks
    free = stat.f_frsize * stat.f_bavail
    used_pct = (1 - free / total) * 100
    if used_pct > 92:
        return "critical", f"Disk: {used_pct:.0f}% used"
    if used_pct > 85:
        return "warning", f"Disk: {used_pct:.0f}% used"
    return None, None


def check_memory():
    """RAM available AND swap pressure, with a top-consumer hint."""
    try:
        mem = _meminfo()
        avail_mb = mem.get("MemAvailable", 0) / 1024
        swap_total = mem.get("SwapTotal", 0) / 1024
        swap_free = mem.get("SwapFree", 0) / 1024
        swap_used = max(swap_total - swap_free, 0)
        swap_pct = (swap_used / swap_total * 100) if swap_total else 0.0

        detail = (
            f"RAM {avail_mb:.0f}MB avail; "
            f"swap {swap_used:.0f}/{swap_total:.0f}MB ({swap_pct:.0f}%)"
        )
        critical = avail_mb < RAM_CRIT_MB or (swap_total > 0 and swap_free < SWAP_CRIT_FREE_MB)
        warning = avail_mb < RAM_WARN_MB or swap_pct >= SWAP_WARN_PCT
        if not (critical or warning):
            return None, None
        return ("critical" if critical else "warning"), f"{detail} | top: {_top_consumers()}"
    except Exception as e:
        return "critical", f"Memory check error: {e}"

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

def _as_severity(result):
    """Adapt a legacy (ok, detail) check into the severity model."""
    ok, detail = result
    return (None, None) if ok else ("critical", detail)


def collect_checks():
    bridge = check_gateway()
    execution = check_cron_execution()
    delivery = check_cron_delivery(bridge[0], execution[0])
    return [
        ("Bridge transport", *_as_severity(bridge)),
        ("Cron execution", *_as_severity(execution)),
        ("Cron delivery", *_as_severity(delivery)),
        ("Disk space", *check_disk()),
        ("Memory", *check_memory()),
        ("Chain cooldown", *_as_severity(check_chain_cooldown())),
    ]


def decide(state, checks, now):
    """Decide whether to speak, and why.

    Policy (owner-approved):
      - notify immediately on a new fault;
      - notify immediately when the fault set or its severity changes;
      - otherwise repeat at most once every 6h while it persists;
      - notify once when everything returns to healthy.

    Returns (action, reason, new_state); action is none|alert|recovery.
    """
    active = [(n, s, d) for n, s, d in checks if s]
    fingerprint = "|".join(f"{n}:{s}" for n, s, _ in sorted(active))
    prev_fp = state.get("fingerprint") or ""
    prev_rank = int(state.get("max_severity") or 0)
    rank = max((SEV_RANK[s] for _, s, _ in active), default=0)
    last_notified = float(state.get("last_notified_at") or 0)

    new_state = dict(state)
    new_state["fingerprint"] = fingerprint
    new_state["max_severity"] = rank
    new_state["failed_components"] = [n for n, _, _ in active]

    if not active:
        new_state["consecutive_fails"] = 0
        if prev_fp or prev_rank:
            new_state["last_recovery_at"] = now
            return "recovery", sorted(state.get("failed_components") or []), new_state
        return "none", None, new_state

    new_state["consecutive_fails"] = min(int(state.get("consecutive_fails") or 0) + 1, 99)

    if not prev_fp:
        return "alert", "new fault", new_state
    if fingerprint != prev_fp:
        return "alert", "severity changed", new_state
    if rank > prev_rank:
        return "alert", "escalated", new_state
    if now - last_notified >= REMIND_SECONDS:
        return "alert", "6h reminder", new_state
    return "none", None, new_state


def format_alert(active, reason):
    worst = "critical" if any(s == "critical" for _, s, _ in active) else "warning"
    icon = "🔴" if worst == "critical" else "🟡"
    head = f"{icon} Health Monitor — {worst.upper()}"
    if reason == "6h reminder":
        head += " (still active, 6h update)"
    elif reason == "escalated":
        head += " (escalated)"
    lines = [head]
    for name, sev, detail in active:
        lines.append(f"• {name} [{sev}]: {detail}" if detail else f"• {name} [{sev}]")
    if any(n == "Memory" for n, _, _ in active):
        lines.append("Hint: ps -eo rss,args --sort=-rss | head -10")
    return "\n".join(lines)


def format_recovery(recovered):
    label = ", ".join(recovered) or "previous issue"
    return f"✅ Health Monitor — recovered: {label}\n{_memory_summary()}"


def run_self_test():
    """Exercise the notification policy without sending or touching state."""
    now = 1_700_000_000.0
    ok = (None, None)
    warn = ("warning", "RAM 480MB avail; swap 900/1987MB (45%)")
    crit = ("critical", "RAM 200MB avail; swap 1950/1987MB (98%)")
    cases = []

    def case(name, state, checks, expect_action, expect_reason=None):
        action, reason, _ = decide(state, checks, now)
        good = action == expect_action and (expect_reason is None or reason == expect_reason)
        cases.append((name, action, reason, good))

    base = dict(DEFAULT_STATE)
    case("healthy stays silent", base, [("Memory", *ok)], "none")
    case("new warning alerts at once", base, [("Memory", *warn)], "alert", "new fault")

    notified = dict(base, fingerprint="Memory:warning", max_severity=1,
                    failed_components=["Memory"], last_notified_at=now - 60)
    case("same warning within 6h is silent", notified, [("Memory", *warn)], "none")

    stale = dict(notified, last_notified_at=now - REMIND_SECONDS - 1)
    case("same warning after 6h reminds", stale, [("Memory", *warn)], "alert", "6h reminder")

    case("escalation to critical alerts", notified, [("Memory", *crit)], "alert", "severity changed")

    mixed = dict(base, fingerprint="Memory:warning", max_severity=1,
                 failed_components=["Memory"], last_notified_at=now - 60)
    case("new second component alerts",
         mixed, [("Memory", *warn), ("Disk space", "warning", "Disk: 88% used")],
         "alert", "severity changed")

    failed = dict(base, fingerprint="Memory:critical", max_severity=2,
                  failed_components=["Memory"], last_notified_at=now - 60)
    case("recovery fires once", failed, [("Memory", *ok)], "recovery")

    recovered = dict(base, fingerprint="", max_severity=0,
                     failed_components=[], last_recovery_at=now - 60)
    case("healthy after recovery stays silent", recovered, [("Memory", *ok)], "none")

    detail_change = dict(notified, fingerprint="Memory:warning")
    case("detail-only change does not spam", detail_change,
         [("Memory", "warning", "RAM 410MB avail; swap 950/1987MB (48%)")], "none")

    passed = sum(1 for *_, g in cases if g)
    for name, action, reason, good in cases:
        print(f"{'PASS' if good else 'FAIL'}  {name}: action={action} reason={reason}")
    print(f"{passed}/{len(cases)} passed")
    return 0 if passed == len(cases) else 1


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if "--self-test" in argv:
        return run_self_test()

    dry_run = "--dry-run" in argv
    state = load_state()
    now = time.time()
    checks = collect_checks()
    action, reason, new_state = decide(state, checks, now)
    active = [(n, s, d) for n, s, d in checks if s]

    message = None
    if action == "alert":
        message = format_alert(active, reason)
    elif action == "recovery":
        message = format_recovery(reason)

    if dry_run:
        print(f"action={action} reason={reason}")
        print(message or "(silent — no notification)")
        return 0

    if message and notify(message):
        new_state["last_notified_at"] = now
    save_state(new_state)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
