# Health Monitor Implementation (2026-07-04)

## Environment

- **Server**: Tencent Lighthouse VPS (Singapore), Ubuntu
- **User**: ubuntu
- **Hermes home**: `/home/ubuntu/.hermes`
- **Python**: `/usr/bin/python3` (system Python)

## Script location

`/home/ubuntu/.hermes/scripts/health_check.py`

## Cron entry

```
*/15 * * * * /usr/bin/python3 /home/ubuntu/.hermes/scripts/health_check.py
```

## State file

`/home/ubuntu/.hermes/scripts/health_state.json`

## Channels

| Channel | Target | Method |
|---------|--------|--------|
| WhatsApp | 13186321408227@lid | `POST /send` on localhost:3000 |
| Telegram | chat_id=679729206, bot=MJ_aiassistantbot | `api.telegram.org/bot<TOKEN>/sendMessage` |

## Chat ID discovery

- **WhatsApp**: Extract `WHATSAPP_HOME_CHANNEL` from `.env` (shows `@lid` format)
- **Telegram**: From gateway logs / earlier bot interaction (chat_id=679729206)
- Verify both with actual send test before deploying

## Telegram token discovery

Read `TELEGRAM_BOT_TOKEN` from `~/.hermes/.env`. The script reads it directly from file (not env var) because system cron doesn't source `.env`.

## Verification checklist

- [x] Silent when healthy (no stdout, exit 0)
- [x] Alert on failure (WhatsApp + Telegram)
- [x] Recovery notification when problem resolves
- [x] Rate-limiting: 1st fail → notify, every 3rd consecutive → re-notify, >30 min → re-notify
- [x] System cron registered and running

## Fix: Schedule-aware cron checking (2026-07-05)

**Problem:** Health monitor was falsely flagging "cron not ticking" for the Domino Chain Medication Monitor (job_id `c97c00f2fb46`) during its off-hours (22:00-05:00). The cron schedule `*/15 5-22 * * *` means it only runs from 5am to 10pm, but the health check checked for fresh output 24/7.

**Fix:** Added `_cron_is_active_now()` function that uses `croniter` (from Hermes agent venv) to check whether the monitored cron job's next run is within a 30-minute window from the current time. If the next run is >30 min away (off-hours), the cron check is skipped and returns healthy instead of triggering a false alarm.

**Files changed:** `~/.hermes/scripts/health_check.py`
- Added `_CRONITER_AVAILABLE` import hack (loads croniter from Hermes venv)
- Added `_load_jobs()` — reads `~/.hermes/cron/jobs.json`
- Added `_get_job_cron_expr(job_id, jobs)` — extracts cron expression by job ID
- Added `_cron_is_active_now(cron_expr, window_min=30)` — uses croniter to check if next run is within window
- Modified `check_cron_ticking()` — calls `_cron_is_active_now()` before checking file ages

**Fallback:** If `croniter` is unavailable, or the job is not found in jobs.json, or the schedule kind isn't `cron`, the function returns `True` (check as usual — old behavior) to avoid silently missing real failures.
