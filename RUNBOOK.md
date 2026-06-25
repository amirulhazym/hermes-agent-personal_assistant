# RUNBOOK — Hermes Personal AI Agent

> Operational handover for the Hermes AI assistant running on WSL2 / Windows 11.
> Last updated: 2026-06-25

---

## 1. System Overview

Hermes is a personal AI assistant accessible via WhatsApp and Telegram, powered by DeepSeek V4 Flash.

### Architecture

```
Windows 11 PC
  └── WSL2 (hermes-agent distro) on F:\wsl\hermes-agent\
        └── Hermes Agent v0.17.0 at ~/.hermes/
              ├── config.yaml         (all settings)
              ├── .env                (secrets: API keys, tokens)
              ├── SOUL.md             (persona)
              ├── memories/USER.md    (user profile)
              ├── cron/jobs.json      (scheduled tasks)
              ├── whatsapp/session/   (WhatsApp credentials)
              └── logs/               (gateway.log, agent.log, errors.log)
```

### Key Credentials

| Secret | Location | Purpose |
|---|---|---|
| DeepSeek API key | `~/.hermes/.env` | LLM inference |
| Telegram bot token | `~/.hermes/.env` | Telegram messaging |
| WhatsApp session | `~/.hermes/whatsapp/session/` | WhatsApp messaging |

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

---

## 2. Startup / Shutdown

### Start Gateway

Windows login runs startup automatically via `shell:startup\hermes-gateway.bat`. To start manually:

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
1. Login startup script (when you log back in)
2. Watchdog cron (every 5 min, restarts if dead)

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

QR code will appear in terminal. On the **Hotlink phone** (60175407200):
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

**Step 2**: Run startup script (if gateway dead)
```powershell
powershell -File "F:\hermes\gateway-start.ps1"
```

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

## 11. File Locations on Disk

| Path | Drive | Purpose | Size |
|---|---|---|---|
| `F:\wsl\hermes-agent\` | F: | WSL2 distro (hermes VHDX) | ~1.3 GB |
| `F:\wsl\docker\` | F: | Docker Desktop data | ~280 MB |
| `F:\hermes\` | F: | PowerShell startup script + logs | ~10 KB |
| `F:\AI Prep\OVIS\Hermes Agent\MJay\` | F: | Project repo | ~500 KB |
| `C:\Users\amiru\AppData\Local\Docker\wsl\` | C: | Docker Desktop (moved to F:) | 0 |

**All WSL2 and Docker data is on F: drive. C: drive is only Windows system files.**

---

*End of RUNBOOK. For issues not covered here, check Hermes docs at [hermes-agent.nousresearch.com/docs/](https://hermes-agent.nousresearch.com/docs/)*
