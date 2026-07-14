# RUNBOOK — Hermes Personal AI Agent

> Operational handover for the Hermes AI assistant running on **Tencent Cloud Lighthouse VPS (Singapore)**.
> Last updated: 2026-07-01 (post-VPS migration)

---

## 1. System Overview

Hermes is a personal AI assistant accessible via WhatsApp and Telegram, powered by **OpenCode (Zen + Go)** and **DeepSeek V4**.

### Architecture

```
Tencent Cloud Lighthouse VPS (Singapore)
  └── Ubuntu 24.04, user: ubuntu, IP: 119.28.119.151
        └── Hermes Agent v0.17.0 at ~/.hermes/   ← LIVE
              ├── config.yaml         (hardened: timezone KL, STT off, vision=opencode-zen/mimo)
              ├── .env                (API keys: DEEPSEEK, OPENCODE_ZEN, OPENCODE_GO, TELEGRAM)
              ├── SOUL.md             (persona - MarryJane / "Jane")
              ├── memories/           (MEMORY.md + USER.md - 7,526 bytes)
              ├── scripts/            (fix_models.py, watchdog.sh, restart-gateway.sh, etc.)
              ├── plugins/            (hybrid-web, web-trafilatura)
              ├── skills/             (42 skills including design skills)
              ├── platforms/whatsapp/ (paired session, creds.json)
              ├── cron/               (jobs.json, ticker files, .tick.lock)
              └── logs/               (gateway.log, watchdog.log, agent.log, errors.log)

Local Windows 11 PC (development only)
  └── F:\AI Prep\OVIS\Hermes Agent\MJay\    ← docs only (PRD, PROGRESS, DECISIONS, RUNBOOK, specs)
```

### SSH Access

```bash
ssh ubuntu@119.28.119.151
```

Key-based auth from Windows `~/.ssh/id_ed25519` configured. No password needed.

### Key Credentials (all on VPS, names only — values never logged)

| Secret | Location | Purpose |
|---|---|---|
| DeepSeek API key | `~/.hermes/.env` | LLM inference (default provider) |
| OpenCode Zen API key | `~/.hermes/.env` | Free-tier LLM + vision (`mimo-v2.5-free`) |
| OpenCode Go API key | `~/.hermes/.env` | Subscription LLM (newer models) |
| Telegram bot token | `~/.hermes/.env` | Telegram messaging |
| Telegram allowed users | `~/.hermes/.env` | Owner user ID |
| Telegram home channel | `~/.hermes/.env` | Owner's DM chat ID |
| WhatsApp session | `~/.hermes/platforms/whatsapp/session/` | WhatsApp credentials (creds.json + pre-keys) |

### Cron Jobs

| Name | Schedule | Delivery | Purpose |
|---|---|---|---|
| Morning Briefing | 07:00 daily | WhatsApp | Today's agenda |
| Evening Check-in | 21:00 daily | WhatsApp | End-of-day review |
| Daily Usage Report | 08:00 daily | Telegram | Token/cost monitoring |
| Goal Check-in | 20:00 Mon/Wed/Fri | WhatsApp | Habit tracking |
| Weekly Review | 10:00 Sunday | Telegram | Weekly summary |
| Daily Health | 09:00 daily | Telegram | Gateway uptime report |
| Log Rotate | 06:00 Sunday | Local (script) | Rotate log files |
| Gateway Watchdog | Every 5 min | Local (script) | Auto-restart if dead |
| Morning Medication #1 | 06:00 daily | WhatsApp | Medication reminder |
| ⏰ Follow-up #1 | 06:15 daily | WhatsApp | Follow-up if unconfirmed |
| ⏰ Follow-up #2 | 06:30 daily | WhatsApp | Follow-up if unconfirmed |
| ⏰ Follow-up #3 | 06:45 daily | WhatsApp | Last call follow-up |
| Morning Medication #2 | 08:00 daily | WhatsApp | Medication reminder |
| ⏰ Follow-up #1 | 08:15 daily | WhatsApp | Follow-up if unconfirmed |
| ⏰ Follow-up #2 | 08:30 daily | WhatsApp | Follow-up if unconfirmed |
| ⏰ Follow-up #3 | 08:45 daily | WhatsApp | Last call follow-up |
| Afternoon Medication | 12:00 daily | WhatsApp | Medication reminder |
| ⏰ Follow-up #1 | 12:15 daily | WhatsApp | Follow-up if unconfirmed |
| ⏰ Follow-up #2 | 12:30 daily | WhatsApp | Follow-up if unconfirmed |
| ⏰ Follow-up #3 | 12:45 daily | WhatsApp | Last call follow-up |
| Late Afternoon Medication | 16:00 daily | WhatsApp | Medication reminder |
| ⏰ Follow-up #1 | 16:15 daily | WhatsApp | Follow-up if unconfirmed |
| ⏰ Follow-up #2 | 16:30 daily | WhatsApp | Follow-up if unconfirmed |
| ⏰ Follow-up #3 | 16:45 daily | WhatsApp | Last call follow-up |
| Evening Medication | 20:00 daily | WhatsApp | Medication reminder |
| ⏰ Follow-up #1 | 20:15 daily | WhatsApp | Follow-up if unconfirmed |
| ⏰ Follow-up #2 | 20:30 daily | WhatsApp | Follow-up if unconfirmed |
| ⏰ Follow-up #3 | 20:45 daily | WhatsApp | Last call follow-up |

---

## 2. Startup / Shutdown

### Auto-Start (On Boot)

The gateway starts automatically at every Windows login via a Startup Folder shortcut:

```
shell:startup\Hermes Gateway.lnk
  → powershell.exe -NoProfile -ExecutionPolicy Bypass -File "F:\hermes\gateway-start.ps1"
```

This was set up by `F:\hermes\setup-auto-start.ps1` (run once). No admin rights needed.

What happens on boot/login:
1. You log into Windows
2. Startup folder scripts run (Hermes Gateway.lnk)
3. WSL2 is auto-started by the `wsl` command inside the script
4. `gateway-start.ps1` waits for internet (up to 5 min, 10s intervals)
5. Gateway starts with 3-attempt retry + platform validation
6. Telegram + WhatsApp connect

### Start Gateway (Manual)

```powershell
powershell -File "F:\hermes\gateway-start.ps1"
```

Check if started successfully:
```powershell
wsl -d hermes-agent -- bash -c "ps aux | grep 'venv/bin/hermes gateway' | grep -v grep"
```
Should show 2+ processes (Python gateway + Node.js WhatsApp bridge).

### Stop Gateway

```bash
# Inside WSL2
hermes gateway stop
```

### Graceful PC Shutdown

The gateway will be killed on shutdown. It auto-recovers via:
1. **Startup Folder shortcut** (runs on your next login)
2. **Watchdog cron** (every 5 min, restarts if gateway goes down while PC is on)

---

## 3. Backup

### What to Back Up

| Path | What it contains | Frequency |
|---|---|---|
| WSL2: `~/.hermes/` | All config, memory, skills, sessions, cron | Weekly |
| Windows: `F:\wsl\hermes-agent\ext4.vhdx` | WSL2 distro (optional, for full recovery) | Monthly |

### Backup Config + Memory

```powershell
# Windows PowerShell — backup entire Hermes home from WSL2
wsl -d hermes-agent -- bash -c "cd && tar czf /mnt/f/backups/hermes-backup-$(date +%Y%m%d).tar.gz .hermes/"
```

This creates `F:\backups\hermes-backup-20260625.tar.gz` containing everything.

### Backup WSL2 Distro (Full Recovery)

```powershell
wsl --export hermes-agent F:\wsl\backup\hermes-agent-full.tar
```

---

## 4. Restore

### Restore Config Only

```powershell
wsl -d hermes-agent -- bash -c "cd && tar xzf /mnt/f/backups/hermes-backup-20260625.tar.gz"
```

### Restore WSL2 Distro (After Reinstall)

```powershell
wsl --unregister hermes-agent
wsl --import hermes-agent F:\wsl\hermes-agent\ F:\wsl\backup\hermes-agent-full.tar
wsl -d hermes-agent
```

---

## 5. WhatsApp Re-Pairing

If WhatsApp disconnects (session expired, QR re-link needed):

```powershell
wsl -d hermes-agent -- bash -l -c "hermes whatsapp"
```

QR code will appear in terminal. On the **dedicated bot phone**:
1. Open WhatsApp
2. Settings → Linked Devices → Link a Device
3. Scan the QR code

The session is saved to `~/.hermes/whatsapp/session/` and persists across restarts.

---

## 6. Key Rotation

### Telegram Bot Token

1. Open Telegram → search @BotFather
2. Send `/mybots` → select your bot → API Token → Revoke
3. Send `/token` to get new token
4. Update `~/.hermes/.env`:

```bash
wsl -d hermes-agent -- bash -c "sed -i 's/TELEGRAM_BOT_TOKEN=.*/TELEGRAM_BOT_TOKEN=new_token_here/' ~/.hermes/.env"
```

5. Restart gateway

### DeepSeek API Key

1. Go to https://platform.deepseek.com/api_keys
2. Generate new key
3. Update `~/.hermes/.env`:

```bash
wsl -d hermes-agent -- bash -c "sed -i 's/DEEPSEEK_API_KEY=.*/DEEPSEEK_API_KEY=new_key_here/' ~/.hermes/.env"
```

4. Restart gateway

### WhatsApp Session (Full Reset)

Delete session and re-pair:

```bash
wsl -d hermes-agent -- bash -c "rm -rf ~/.hermes/whatsapp/session/"
```

Then run re-pairing steps from Section 5.

---

## 7. Model Switching

### Default: DeepSeek V4 Flash

```bash
# From Telegram/WhatsApp chat:
/model deepseek:deepseek-v4-flash
```

### Escalation: DeepSeek V4 Pro

```bash
# From Telegram/WhatsApp chat:
/model deepseek:deepseek-v4-pro
```

Use Pro for: hard reasoning, planning, debugging, large synthesis, high-stakes analysis.

### Permanent Config Change

```bash
wsl -d hermes-agent -- bash -c "sed -i 's/default: deepseek-v4-flash/default: deepseek-v4-pro/' ~/.hermes/config.yaml"
hermes gateway restart
```

---

## 8. Monitoring & Usage

### Quick Dashboard

```powershell
# One command to see everything
powershell -File "F:\hermes\status.ps1"

# Auto-refresh every 60 seconds
powershell -File "F:\hermes\status.ps1" -watch
```

The dashboard shows: gateway health, platform connections, cron jobs, watchdog status, disk space, recent logs, and quick action commands.

### Daily Usage

```bash
# Inside WSL2
hermes insights --days 1
```

Shows: token usage, cost estimates, session count, active days.

### Gateway Health

```bash
# Inside WSL2
hermes gateway status
```

Or check logs:
```bash
tail -20 ~/.hermes/logs/gateway.log
tail -20 ~/.hermes/logs/errors.log
```

### C Drive Space

```powershell
# Windows
Get-PSDrive C | Select-Object @{N='FreeGB';E={[math]::Round($_.Free/1GB,1)}}
```

If below 5 GB free, run Disk Cleanup or move files to F: drive.

---

## 9. Troubleshooting

### Gateway Not Responding on WhatsApp/Telegram

**Step 1**: Check if gateway is running
```powershell
wsl -d hermes-agent -- bash -c "ps aux | grep 'venv/bin/hermes gateway' | grep -v grep"
```

**Step 2**: If gateway not listed, restart manually:
```powershell
powershell -File "F:\hermes\gateway-start.ps1"
```

**Step 2b**: If gateway started but not responding, check with latest logs. The script auto-retries 3 times. For persistent failures, check Section 11 (Emergency Recovery).

**Step 3**: Check logs
```powershell
wsl -d hermes-agent -- bash -c "tail -20 ~/.hermes/logs/gateway.log"
```
Look for "whatsapp connected" and "telegram connected" messages.

### WSL2 Unresponsive

If `wsl -d hermes-agent -- bash -c "echo test"` hangs:
```powershell
wsl --terminate hermes-agent
wsl -d hermes-agent -- bash -c "setsid /home/amirul/.hermes/hermes-agent/venv/bin/hermes gateway &>/home/amirul/.hermes/logs/gateway.log &"
```

### WhatsApp Disconnected

Check logs for WhatsApp errors:
```bash
grep -i whatsapp ~/.hermes/logs/errors.log
```

If disconnected, re-pair using Section 5.

### DeepSeek API Errors

Check for payment/credit errors:
```bash
grep -i "402\|payment\|credit\|unhealthy" ~/.hermes/logs/gateway.log
```

If credits exhausted, top up at https://platform.deepseek.com/top-up

---

## 10. DeepSeek Budget Management

| Item | Detail |
|---|---|
| Daily cost estimate | ~$0.02-0.10 (Flash model) |
| Monthly soft cap | RM25 (~$5.30 USD) |
| Usage report | Daily at 08:00 to Telegram |
| Cron auto-pause | NOT automatic. To pause: `hermes cron pause <job-id>` |
| Re-enable | `hermes cron resume <job-id>` |

To check current spend:
```bash
# Inside WSL2
hermes insights --days 30
```

---

## 11. Emergency Gateway Recovery

### Gateway won't start — `gateway_state.json` stuck as "running"

If gateway exits unexpectedly (SIGTERM/timeout), it writes `gateway_state=running`. Subsequent starts see this and refuse to run.

**Fix:**
```bash
wsl -d hermes-agent -- rm -f ~/.hermes/gateway_state.json
```

Then start gateway via PowerShell (NOT inside WSL bash):
```powershell
Start-Process -WindowStyle Hidden -FilePath "wsl" -ArgumentList "-d", "hermes-agent", "--", "/home/amirul/.hermes/hermes-agent/venv/bin/hermes", "gateway"
```

**Why not `nohup`/`setsid`?** WSL kills background processes when the parent `wsl -- bash -c` exits, even with `nohup`. `Start-Process -WindowStyle Hidden` creates a standalone Windows process that survives.

---

## 12. File Locations on Disk

### VPS (LIVE production)
| Path | Purpose |
|---|---|
| `~/.hermes/` | Main Hermes directory (config, memories, skills, plugins, scripts) |
| `~/.hermes/.env` | All API keys (DEEPSEEK, OPENCODE_ZEN, OPENCODE_GO, TELEGRAM) |
| `~/.hermes/config.yaml` | Main config (timezone KL, STT off, vision, base_url) |
| `~/.hermes/platforms/whatsapp/session/` | WhatsApp paired session (creds.json + pre-keys) |
| `~/.hermes/memories/MEMORY.md` + `USER.md` | Persona memory (7,526 bytes) |
| `~/.hermes/cron/jobs.json` | Scheduled tasks |
| `~/.hermes/cron/ticker_heartbeat` + `ticker_last_success` | Scheduler liveness |
| `~/.hermes/logs/gateway.log` | Main gateway log |
| `~/.hermes/logs/watchdog.log` | Auto-restart events |
| `~/.hermes/logs/agent.log` + `errors.log` | Agent and error logs |
| `~/.config/systemd/user/hermes-gateway.service` | systemd user service unit |

### Local Windows (docs only, no agent runs here)
| Path | Purpose | Size |
|---|---|---|
| `F:\AI Prep\OVIS\Hermes Agent\MJay\` | Project repo (PRD, PROGRESS, DECISIONS, RUNBOOK, specs) | ~500 KB |
| `F:\obsidian-vault\` | Obsidian vault (PARA structure) | ~50 KB |
| `F:\Obsidian\` | Obsidian portable app | ~356 MB |
| `F:\wsl\hermes-rebuild-second\` | WSL2 distro (build source, no longer runs) | ~1.3 GB |
| `F:\wsl\hermes-agent\` | WSL2 distro (backup, never launched) | ~1.3 GB |

**Agent runs on VPS. Local WSL distros are kept as build sources. MJay repo is for docs only.**

---

## 13. Quick VPS Reference

```bash
# SSH into VPS
ssh ubuntu@119.28.119.151

# Gateway control
systemctl --user status hermes-gateway     # check status
systemctl --user restart hermes-gateway    # restart
systemctl --user stop hermes-gateway       # stop
journalctl --user -u hermes-gateway -n 50  # last 50 log lines

# Watch health
tail -f ~/.hermes/logs/gateway.log         # follow gateway log
cat ~/.hermes/gateway.pid                  # current PID
ls -la ~/.hermes/cron/ticker_heartbeat     # cron liveness

# Maintenance
free -h                                    # check RAM/swap
df -h                                      # check disk
ps aux | grep -i hermes                    # running processes
sudo swapon --show                         # swap status

# 24h stability check (auto-runs at 05:00 each day, can be triggered manually)
python3 ~/stability_check.py                # run now
cat ~/stability-report.txt                 # view last report

# Re-pair WhatsApp (if needed)
~/.hermes/hermes-agent/venv/bin/python -m hermes_cli.main whatsapp
```

---

## 14. Git Workflow (VPS → GitHub)

```bash
# VPS writes to hermes-live branch
cd ~/mjay
git add -A
git commit -m "hermes: <description>"
git push origin hermes-live

# User reviews PR on phone (GitHub mobile)
# Merges to main → triggers workflow
```

Branch strategy: `main` = human-only, `hermes-live` = agent-pushed working branch.
Full doc: `~/mjay/docs/git_workflow.md`

---

## 15. Known Issues (Non-blocking)

| Issue | Impact | Fix |
|-------|--------|-----|
| `cua-driver` MCP fails to init (Windows path) | None — falls back to default | Disable in `mcp_servers` config |
| `raft` CLI not in PATH | None — warning only | `curl -fsSL https://raft.build/install.sh \| bash` if needed |
| `cron/ticker_heartbeat` shows old timestamp | None — only updates on job fire | Wait for first job (07:00 next morning) |
| `hybrid-web` plugin (post-fix: fully working) | Was: warning. Now: extract works | ✅ FIXED 2026-07-01 04:45 AM |

---

---

## 16. PX-1 Research — Operational Reference

### Search Cascade (Tavily Multi-Key Pool)

| Item | Detail |
|------|--------|
| Plugin | `~/.hermes/plugins/search-cascade/` |
| Config | `web.search_backend: search-cascade`, `web.backend: tavily` |
| Env vars | `TAVILY_API_KEY` (primary, k0) + `TAVILY_API_KEYS` (11 comma-separated) |
| Rotation | Sticky-until-fail: reuse last successful key → next on error → DDGS fallback |
| Pool size | 11 keys (verify: `grep TAVILY_API_KEYS ~/.hermes/.env \| tr ',' '\n' \| wc -l`) |

### Usage Log

| File | Schema | Notes |
|------|--------|-------|
| `~/.hermes/logs/tavily_key_usage.jsonl` | `{ts, key_index, key_fingerprint, success, detail}` | Fingerprint = SHA256[:12], never logs key value |

### Extract (Hybrid-Web)

| Item | Detail |
|------|--------|
| Plugin | `~/.hermes/plugins/hybrid-web/` |
| Config | `web.extract_backend: hybrid-web` |
| Inherits | `WebSearchProvider` (ABC-compliant, proper extract() shape) |
| Chain | trafilatura (static) → crawl4ai (JS) → Playwright (fallback) |

### Research Expert Skill

| Item | Detail |
|------|--------|
| Path | `~/.hermes/skills/experts/research-expert/` |
| Artifacts | `~/.hermes/research/artifacts/YYYY-MM-DD-<slug>/` |
| Pipeline | plan → search → extract → verify → synthesize → artifact |
| Constraints | depth=1 / max=3, no med, labels VALIDATED/UNTESTED/REJECTED |

### Signup Pipeline (PC Only — NOT on VPS)

| Component | Location | Purpose |
|-----------|----------|---------|
| Batch script | `F:\HermesPrivate\turnstile-solver\batch_5.py` | CDP Chrome → Auth0 → QRYPTY → key extract |
| Chrome profile | `F:\HermesPrivate\tavily-chrome-profile\` | CDP `--remote-debugging-port=9222` |
| Key inventory | `F:\HermesPrivate\tavily-signup-windows\tavily_keys.json` | Local key store |
| QRYPTY accounts | `F:\Temp\opencode\tavily-signup-work\` | CSV + temp files |

**To add new keys:** run `batch_5.py` on Windows (Chrome CDP required), then re-merge to VPS `.env` and restart gateway.

### Quick Diagnostics

```bash
# VPS: verify key pool size
ssh ubuntu@119.28.119.151 'grep TAVILY_API_KEYS ~/.hermes/.env | tr "," "\n" | wc -l'

# VPS: verify gateway + plugins
ssh ubuntu@119.28.119.151 'systemctl --user is-active hermes-gateway'
ssh ubuntu@119.28.119.151 'ls ~/.hermes/plugins/{hybrid-web,search-cascade}'

# VPS: usage log tail
ssh ubuntu@119.28.119.151 'tail -3 ~/.hermes/logs/tavily_key_usage.jsonl'
```

---

*End of RUNBOOK. For issues not covered here, check Hermes docs at [hermes-agent.nousresearch.com/docs/](https://hermes-agent.nousresearch.com/docs/)*