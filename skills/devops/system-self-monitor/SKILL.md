---
name: system-self-monitor
description: "Set up independent system monitoring using Linux system cron (not Hermes cron) with dual notification channels — primary (WhatsApp bridge) + backup (Telegram Bot API). Silent on success, alerts on failure with rate-limiting."
version: 1.2.0
author: Jane
created: 2026-07-04
---

# System Self-Monitor

## When to use

- User asks for "MJ monitor dari belakang" — independent monitoring that works even when Hermes gateway is down
- User asks for health checks on Hermes VPS (gateway, cron, disk, memory)
- User wants alerting that doesn't depend on being in a conversation
- Setting up cron-independent watchdog for any long-running system

## Architecture

```
Linux system cron (crontab -e)
  └─ Python script (every N min)
       ├─ Checks: process liveness, disk, memory, heartbeats
       ├─ Silent if all OK
       └─ If problem → notify via:
            ├─ Primary: WhatsApp bridge (port 3000 — works while gateway is up)
            └─ Backup: Telegram Bot API (works unconditionally — independent of gateway)
```

## Key principles

1. **Independence** — MUST work without Hermes gateway. Only use tools that survive gateway restarts (system cron, Telegram Bot API, file system).
2. **Silence is success** — normal operation = zero noise. Only messages when something breaks.
3. **Rate-limited alerts** — first failure notifies immediately. Re-notifies only every 3rd consecutive fail or after 30 min. Prevents spam.
4. **Recovery notification** — when degraded state returns to healthy, send one "✅ All clear" message.

## Implementation steps

### Step 1: Write the health check script

Script should:

1. **Define constants** — chat IDs, bridge URL, Telegram token, file paths
2. **Read Telegram token from `.env` file** — not from environment (system cron doesn't source Hermes .env)
3. **State management** — JSON file tracking `consecutive_fails`, `last_notified_at`, `last_recovery_at`, and `failed_components` (component names, not only one aggregate failure counter)
4. **Check functions** — each returns (ok: bool, detail: str|None); keep bridge transport, cron execution, and cron delivery as separate checks
5. **Rate-limiting logic** — notify on first fail, re-notify every 3rd consecutive fail or after 30 min silence
6. **Recovery logic** — if previous state had failures and now OK, identify the recovered component(s); never emit a generic “all systems recovered” message when only one boundary recovered
7. **Schedule-aware checks with boundary grace** — Checks that wrap a cron-scheduled process (hourly, daily, or windowed) must account for both the active window and the boundary around the expected run. A check before the next scheduled occurrence, or immediately after it while the job is still writing output, is not evidence of a missed run. Use `croniter` plus an explicit post-run grace period; test exact boundary times, not only obvious off-hours.
8. **Silent on success** — exit 0, no stdout

**Boundary contract:** An output file and `last_run_at` prove scheduler/script execution; they do not prove channel delivery. Hermes cron metadata `last_delivery_error` is the delivery-side evidence available to the independent monitor. A bridge `/health` response proves transport state only, not destination-side receipt.

### Step 2: Register in system cron

```bash
(crontab -l 2>/dev/null; echo "*/15 * * * * /usr/bin/python3 /path/to/script.py") | crontab -
```

### Step 3: Test end-to-end

```
1. Run script with healthy system → verify silent exit
2. Simulate a failure → verify notification arrives on both channels
3. Restore health → verify recovery notification
4. Manually run twice in quick succession → verify rate-limiting works (no double notification)
```

## Notification channels

### Primary: WhatsApp bridge

```python
WHATSAPP_BRIDGE = "http://127.0.0.1:3000"
WHATSAPP_CHAT_ID = "user_chat_id@lid"  # Obtain from gateway logs or config

def send_whatsapp(message):
    payload = json.dumps({"chatId": WHATSAPP_CHAT_ID, "message": message})
    req = urllib.request.Request(
        f"{WHATSAPP_BRIDGE}/send",
        data=payload.encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False
```

### Backup: Telegram Bot API

```python
def _read_telegram_token(env_path):
    for line in Path(env_path).read_text().splitlines():
        line = line.strip()
        if line.startswith("TELEGRAM_BOT_TOKEN="):
            return line.split("=", 1)[1].strip("\"' ")

def send_telegram(message, token, chat_id):
    payload = json.dumps({"chat_id": chat_id, "text": message})
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload.encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read()).get("ok", False)
    except Exception:
        return False
```

## State JSON format

```json
{
  "consecutive_fails": 0,
  "last_notified_at": 0,
  "last_recovery_at": 0,
  "failed_components": []
}
```

## Rate-limiting logic

```python
# Notify on first failure
if prev_fails == 0:
    should_notify = True
# Re-notify every 3 consecutive fails (silence in between)
elif state["consecutive_fails"] % 3 == 0:
    should_notify = True
# Or if >30 min since last notification
elif now - last_notified > 1800:
    should_notify = True
```

## Common checks to implement

| Check | Method | Threshold | Schedule-aware? |
|-------|--------|-----------|----------------|
| Bridge transport | `GET /health` on bridge port | Returns `{"status": "connected"}` | N/A (always on; transport only, not receipt) |
| Cron execution | Compare expected occurrence with job `last_run_at`, `last_status`, `last_error`, and matching output-file timestamp | Expected occurrence + bounded grace | **YES** |
| Cron delivery | Inspect Hermes job `last_delivery_error` and bridge state | Any current delivery error → alert | **YES** |
| Disk space | `os.statvfs("/")` | >85% used → alert | N/A (always on) |
| Memory | Read `/proc/meminfo` | <500MB available → alert | N/A (always on) |
| Chain cooldown anomaly | Read chain-state.json | D count >5 → flag | N/A (always on) |

## Pitfalls

| Pitfall | Fix |
|---------|-----|
| Assuming Hermes cron is reliable | Use Linux system cron (`crontab -e`) — independent of Hermes gateway |
| Relying solely on WhatsApp notification | WhatsApp bridge dies when gateway dies. Always have Telegram backup |
| Using env vars in cron script | System cron spawns a minimal env. Read secrets from `.env` file directly |
| Sending alerts every tick | Rate-limit: first fail → notify. Then only every 3rd consecutive fail or 30 min |
| Not sending recovery | After failures, a silent recovery means user never knows it's fixed. Send one "✅ All clear" |
| Capping `consecutive_fails` without bound | Cap at 99 to prevent overflow but still allow rate-limiting to work |
| Conflating execution with delivery | Separate `last_run_at`/output/status from `last_delivery_error`/bridge state; report the failing boundary explicitly |
| Treating bridge `connected` as user receipt | Connected means transport is available, not destination-side receipt; retain message ID and user reply where available |
| Reloading Hermes gateway after every monitor edit | This monitor runs under independent Linux cron; edit/test the script directly and do not restart the gateway unless the gateway itself changed |
| Generic recovery text | Persist `failed_components` and name only the recovered component(s) |
| False alarms from off-hours cron checks | Make the check schedule-aware: use `croniter` to parse the monitored job's expression and skip the check when the next run is >30 min away (job is in its off-window). See `references/health-monitor-setup-2026-07-04.md` for a worked example. |

## Implementation detail: schedule-aware cron execution and delivery separation

When monitoring a cron job with a limited operating window (e.g. `*/15 5-22 * * *`), do not use only “next run is within 30 minutes” as the active test. That logic falsely alerts immediately before the first run of the day and can race the scheduler at the exact minute.

Required algorithm:

1. Load the monitored job's cron expression and metadata from `~/.hermes/cron/jobs.json`.
2. Normalize all comparisons to the configured business timezone (for this installation: `Asia/Kuala_Lumpur`), rather than relying on the host timezone label.
3. Use `croniter` to compute the previous and next scheduled occurrences.
4. At the exact scheduled minute, treat that occurrence as the current expected occurrence; `croniter.get_prev()` may otherwise return the prior occurrence.
5. Before the first expected run, do not classify the previous day's output as stale. After an occurrence, allow a bounded post-run grace period (normally 2–5 minutes).
6. After grace, require both scheduler/job evidence (`last_run_at`, successful status, no execution error) and output-file evidence corresponding to the expected occurrence. A latest-file age check alone is insufficient.
7. Check delivery separately using `last_delivery_error` and bridge transport state. If execution is current but delivery has an error, report **cron execution healthy / cron delivery degraded**.
8. Track failed component names in state and identify those names in recovery alerts.
9. A direct edit to an independent Linux-cron monitor does not require a Hermes gateway/bridge reload; verify the monitor process directly, then observe a scheduled invocation when practical.
10. Test boundary cases explicitly: just before first run, exact scheduled minute, shortly after it, missed run after grace, normal between-run time, off-hours, execution failure, delivery failure, and bridge disconnection.

For every scheduled pipeline, report execution and delivery separately: an output file proves script execution, not WhatsApp/Telegram receipt. Preserve the exact output timestamp, exit/status, transport response, destination/chat ID, message ID where available, and destination-side evidence where available.

### Incident interpretation rule

A stale-output alert is not proof that the scheduler stopped, and a successful output file is not proof that delivery worked. During an incident, collect both evidence streams:

- **Execution:** output file timestamp, `cron.scheduler` entry, exit/status, and expected schedule occurrence.
- **Delivery:** adapter attempt, HTTP/bridge response, destination/chat ID, message ID where available, and destination-side reply/receipt.

If execution continues while transport fails, report **cron healthy / delivery degraded**, not “cron stopped.” If transport later returns `connected`, classify it as **recovered but not yet stable** until repeated probes plus a real delivery and (where possible) a user-side receipt succeed. Do not let a recovery notification collapse these states into “all systems recovered.”

**Reference:** See `references/health-monitor-setup-2026-07-04.md` for the original schedule-aware pattern and `references/cron-boundary-and-transport-separation-2026-07-29.md` for the boundary false-positive and execution-versus-delivery case study.

**Fallback principle:** If croniter is unavailable, the job isn't found, or the schedule is not parseable, fall back conservatively and label the result as lower-confidence; do not silently present a pre-run stale check as a missed execution.

## Related Hermes cron documentation

The `hermes cron` system uses a scheduler INSIDE the gateway process. Its `ticker_heartbeat` file is not reliable for checking liveness — the scheduler thread may be running but the file writer could be broken. Always check `gateway.log` / `agent.log` for `cron.scheduler` entries to confirm cron is actually ticking.
