# ⚕ Hermes — Personal AI Agent

[![Version](https://img.shields.io/badge/hermes-v0.17.0-blue)](https://github.com/NousResearch/hermes-agent)
[![Model](https://img.shields.io/badge/DeepSeek-V4%20Flash%20%2F%20Pro-blueviolet)](https://api-docs.deepseek.com)
[![Platforms](https://img.shields.io/badge/WhatsApp%20%2B%20Telegram-brightgreen)]()
[![Status](https://img.shields.io/badge/phase-11%2F11%20complete-success)]()

**One brain, many faces.** A personal AI assistant that lives across WhatsApp and Telegram — same memory, same persona, same skills. Powered by DeepSeek V4. Operational since June 2026.

```
                         USER
                          │
           ┌──────────────┴──────────────┐
           ▼                             ▼
      WhatsApp                        Telegram
    (daily chat)                    (admin/control)
           │                             │
           └──────────────┬──────────────┘
                          ▼
               Hermes Gateway (WSL2)
                          │
                ┌─────────┴─────────┐
                ▼                   ▼
          Durable Memory     DeepSeek V4
         (cross-platform)   Flash / Pro
```

### ⚡ What Hermes Can Do

| 💬 Chat | 🔍 Search | 🧠 Memory | 📓 Knowledge Base | ⏰ Proactive | 🔄 Switch |
|---|---|---|---|---|---|
| Natural conversation in Malay/English/rojak across both platforms | DDGS (DuckDuckGo) web search from any chat | Remembers facts, preferences, deadlines across platforms | Obsidian vault with PARA structure — Hermes reads, searches, creates notes | 27 scheduled jobs: briefings, check-ins, usage reports, **medication reminders** | `/model` to switch between DeepSeek Flash and Pro instant |

---

## 🚀 Getting Started

### 📋 What You Need

| Item | Purpose |
|---|---|
| DeepSeek API key | LLM inference (the only paid component — ~$0.02-0.10/day) |
| WhatsApp phone number | Bot number (dedicated SIM recommended) |
| Telegram account | BotFather access to create the bot |
| Windows 11 PC | Or any always-on Linux host (see VPS migration below) |

### 📁 Where Everything Lives

```
F:\
├── wsl\hermes-agent\          ← WSL2 distro (VHDX, 1.3 GB)
│   └── home\amirul\.hermes\
│       ├── config.yaml         ← All settings (model, cron, tools, memory)
│       ├── .env                ← API keys, tokens (chmod 600)
│       ├── SOUL.md             ← Persona and behavior rules
│       ├── memories\           ← USER.md + MEMORY.md (shared across platforms)
│       ├── cron\\               ← 27+ scheduled jobs (incl. 20 med reminders)
│       ├── whatsapp\session\   ← WhatsApp credentials (chmod 700)
│       └── logs\               ← gateway.log, agent.log, errors.log, watchdog.log
├── obsidian-vault\             ← Knowledge base (PARA structure, plain .md)
├── Obsidian\                   ← Obsidian 1.12.7 portable app
├── hermes\                     ← Startup scripts + status dashboard
│   ├── gateway-start.ps1       ← 3-layer auto-start entry point
│   └── status.ps1              ← One-command monitoring dashboard
└── AI Prep\OVIS\Hermes Agent\MJay\  ← This repo (all docs + config)
```

### 💬 How to Chat with Hermes

| Platform | How | Example |
|---|---|---|
| **Telegram** | DM your bot | `Hello` → Hermes responds |
| **WhatsApp** | Message bot's Hotlink number | `Pagi boss` → Hermes responds |

### ⌨️ Quick Commands (from chat)

| Command | What it does |
|---|---|
| `/model deepseek:deepseek-v4-pro` | Switch to Pro for hard tasks |
| `/model deepseek:deepseek-v4-flash` | Switch back to Flash |
| `/usage` | Show session token usage |
| `/new` | Fresh session (loads updated memory) |
| `/background <task>` | Run long research in background |
| `/cron add "every 2h" "remind me..."` | Create scheduled task |
| `/topic` | Enable multi-session DM mode |
| `/approve` / `/deny` | Approve/deny pending dangerous actions |
| `/skills` | List all available skills |
| `Search latest news about X` | Web search via DDGS |

---

## 🏗️ Architecture

### 🖥️ System Diagram

```
User message (WhatsApp/Telegram)
    │
    ▼
Gateway process (single long-running daemon)
    ├── Platform adapters (Telegram API + WhatsApp Baileys bridge)
    ├── Session store (SQLite, FTS5 indexed)
    ├── Cron scheduler (60s tick, file-locked)
    └── Housekeeping (circuit breakers, health checks)
    │
    ▼
Agent Core
    ├── SOUL.md → system prompt
    ├── USER.md + MEMORY.md → durable context
    ├── Skills system → procedural memory
    └── Tool policy → approval gates, blocklist
    │
    ▼
DeepSeek API (https://api.deepseek.com)
    ├── Default: deepseek-v4-flash ($0.0028/M cache-hit)
    └── Escalation: deepseek-v4-pro ($0.003625/M cache-hit)
```

### 📊 Technology Stack

| Component | Technology | Purpose |
|---|---|---|
| Agent framework | Hermes Agent v0.17.0 (Nous Research, MIT) | Core agent with memory, skills, cron, multi-platform |
| LLM | DeepSeek V4 Flash/Pro | Primary inference model |
| Host | WSL2 on Windows 11 + Ubuntu 24.04 LTS | Runtime environment (all data on F: drive) |
| WhatsApp bridge | Baileys v7 (WhiskeySockets) | Unofficial WhatsApp Web protocol client |
| Telegram | python-telegram-bot via official Bot API | Official Telegram integration |
| Web search | DDGS v9.14 (DuckDuckGo) | Free unlimited search backend |
| Memory | MEMORY.md + USER.md + FTS5 SQLite | Cross-platform durable + session search |
| Voice transcription | faster-whisper (base model, local, free) | Speech-to-text for voice notes |
| Knowledge base | Obsidian 1.12.7 portable (F:) + vault (F:) | Second brain with PARA structure, accessible to both Hermes and user |
| Cron | Hermes built-in + Linux crontab | 27+ scheduled jobs + watchdog (incl. 20 med reminders) |
| Monitoring | status.ps1 (PowerShell) + logs + Telegram alerts | Gateway health, disk space, cron status |
| Source control | Git + GitHub (private repo) | All config, docs, decisions tracked |

### 🔄 Data Flow

1. **User sends message** on WhatsApp or Telegram → platform adapter receives it
2. **Session store** loads conversation context (SQLite FTS5) + **durable memory** (MEMORY.md/USER.md) injected into system prompt
3. **Agent processes** with tool access (web search, memory, cron, terminal)
4. **DeepSeek API** generates response (Flash default, Pro on escalation)
5. **Response delivered** back to same platform, session updated

### 🔒 Security Model (7 Layers)

| Layer | Mechanism | Status |
|---|---|---|
| 1 — User authorization | Platform allowlists (specific IDs only) | ✅ Active |
| 2 — Admin/user split | `allow_admin_from` gates dangerous commands | ✅ Configured |
| 3 — Dangerous command approval | Pattern-based approval prompts | ✅ Active |
| 4 — Secret protection | `.env` chmod 600, session chmod 700, auto-redaction in logs | ✅ Verified |
| 5 — SSRF protection | RFC 1918/loopback/link-local blocked by default | ✅ Active |
| 6 — Context injection scanning | `.env` and prompt injection patterns blocked | ✅ Active |
| 7 — Git safety | `.gitignore` covers all secret paths, commits verified clean | ✅ Verified |

### 🚨 Gateway Resilience (3-Layer Auto-Start)

```
PC power on / Windows login
    │
    ▼
Layer 1: Startup Folder → gateway-start.ps1
    │ (checks WSL2, starts gateway if dead, logs to F:\hermes\gateway-start.log)
    │
Layer 2: Linux crontab → every 5 min
    │ (pgrep check → setsid restart if < 2 processes → logs to watchdog.log + gateway.log)
    │
Layer 3: Daily Health Report → Telegram 09:00
    │ (Hermes checks gateway health, reports platform status, usage)
    │
    ▼
Gateway always recovered within 5 minutes of any failure
```

### 🧠 Same-Brain Memory Architecture

```
WhatsApp session (chat: 13186...@lid)
    │                               │
    ├─ Session transcript (FTS5 SQLite, platform-isolated)
    │                               │
    └─ Durable memory ──────┬──────┘
                            │
                    MEMORY.md + USER.md
                   (2,200 + 1,375 chars)
                 Shared across ALL platforms
                            │
                    ┌───────┴───────┐
                    │               │
            Telegram session    CLI session
          (chat: 679729206)   (any terminal)
```

**How it works:**
- Durable memory (MEMORY.md + USER.md) is **injected into every session's system prompt at start**
- Changes written to disk immediately, visible on **next session reset** (idle 4h or daily 4 AM)
- `session_search` tool finds past conversations from ALL platforms via FTS5 SQLite
- Architecture matches PRD design exactly — confirmed working in cross-platform tests

### 📅 Cron Orchestration

#### System Jobs (7)

| Job | Schedule | To | Purpose |
|---|---|---|---|
| Morning Briefing | 07:00 daily | WhatsApp | Today's commitments + habit nudge |
| Daily Usage Report | 08:00 daily | Telegram | Token usage + cost estimate (RM) |
| Daily Health Report | 09:00 daily | Telegram | Gateway health + platform status |
| Goal Check-in | 20:00 Mon/Wed/Fri | WhatsApp | Habit tracking encouragement |
| Evening Check-in | 21:00 daily | WhatsApp | EOD review + carry-forward |
| Weekly Review | 10:00 Sunday | Telegram | Open loops + weekly priorities |
| Log Rotate | 06:00 Sunday | Local | Logrotate (no-agent, $0 cost) |

#### Medication Reminder System (20 jobs)

| Time | Initial Reminder | +15 min | +30 min | +45 min |
|------|:----------------:|:-------:|:-------:|:-------:|
| **06:00** | Akurit-4 + Pyridoxine | ⏰ | ⏰ | ⏰ |
| **08:00** | Dexamethasone #1 + Letram | ⏰ | ⏰ | ⏰ |
| **12:00** | Dexamethasone #2 + Vit D + Ca | ⏰ | ⏰ | ⏰ |
| **16:00** | Dexamethasone #3 (last dose) | ⏰ | ⏰ | ⏰ |
| **20:00** | Letram (evening) | ⏰ | ⏰ | ⏰ |

Each slot: initial reminder + 3 follow-ups every 15 min until confirmed. Single separate messages, never bundled.

**Controls:**
- Quiet hours: 23:00–07:00 MYT (no proactive messages)
- Daily cap: max 3 non-urgent pings
- Stop/later/snooze via "dnd" / "jangan kacau"
- No cron fires during quiet hours

---

## 📖 The Build Journey

### 🎯 Why I Built This

I wanted a personal AI assistant that **lives where I already communicate** — WhatsApp for daily chat, Telegram for admin/review work. Not another app. Not a web dashboard. Something that feels human, remembers me, and proactively helps. Built on the open-source Nous Research Hermes Agent framework, powered by DeepSeek (the only paid component at ~RM2-3/month).

The project connects to my work interest in the **MaiStorage/Phison ecosystem** (enterprise storage, on-premise AI, edge AI infrastructure). Building Hermes was partly about learning how AI agents work end-to-end — from LLM inference to persistent memory to cross-platform messaging to self-healing infrastructure.

### 📈 Phase Timeline (June 2026)

| Phase | What | Key Moment |
|---|---|---|
| **0** — Pre-flight | Verified all docs, DeepSeek pricing, Baileys maintenance | Confirmed everything before touching code |
| **1** — Guardrails | AGENTS.md, opencode.json, .gitignore, git init | Build-time safety first |
| **2** — Install | Hermes v0.17.0 on WSL2, pinned version | Moved WSL2 distro to F: drive to save SSD space |
| **3** — DeepSeek | Configured Flash default, Pro escalation, auxiliary routing | Verified with test query |
| **4** — Telegram | BotFather setup, allowlist admin config | First cross-platform message received |
| **5** — WhatsApp | Baileys QR pairing, dedicated Hotlink SIM | Two platforms, one brain confirmed |
| **6** — Gateway | Systemd attempt → Linux crontab, startup scripts, daily health cron | **Systemd disabled** (WSL2 bug), replaced with reliable crontab watchdog |
| **7** — Persona | SOUL.md (rojak persona), USER.md profile, memory policy | **Same-brain test passed**: taught on WhatsApp, recalled on Telegram |
| **8** — Cron | 7 proactive jobs, quiet hours, caps, scheduling | First evening check-in fired at 21:00 |
| **9** — Web | DDGS (DuckDuckGo) free search, voice transcription | Web search limited by API keys, DDGS resolved it |
| **10** — Harden | Security audit, RUNBOOK.md, monitoring dashboard, VPS migration guide | 5/5 security items passed; no secrets in logs |
| **11** — Obsidian + Health | Knowledge base vault (PARA), portable app, medication reminder system (20 cron jobs) | Zero C: drive — vault + app on F:. 20 medication reminders with 15-min escalation. |

### 🎓 Key Decisions & Lessons Learned

**1. Oracle Cloud vs WSL2 on Owned Hardware**
Oracle Always Free ARM (2 OCPU, 12 GB RAM) was the original target. But Oracle requires a credit card for identity verification — my debit cards were rejected. Moved to WSL2 on my Windows 11 PC. Bonus: zero cloud billing anxiety, zero reclamation risk, and the architecture is identical to a future Linux VPS.

**2. Systemd Hell in WSL2**
Enabling `systemd=true` in `/etc/wsl.conf` was a mistake. It caused WSL2 to hang, killed background processes, and made `setsid`/`nohup` unreliable. **The fix**: disabled systemd, reverted to WSL2's default init process. Gateway now starts reliably via `setsid`. Lesson: WSL2 + systemd is not production-ready.

**3. DDGS vs Brave vs SerpAPI — Why Free Won**
Hermes supports Exa, Firecrawl, Tavily, and other paid web search backends. For a personal assistant, free wins. DDGS (DuckDuckGo Python package) provides unlimited searches with no API key. It's search-only (no URL extraction), but that's fine for 98% of use cases. Brave free tier (2,000/month) was the backup.

**4. Docker Desktop Moved to F: Drive**
Docker Desktop stores WSL2 distros on C: drive by default — consuming precious SSD space. Exported both `docker-desktop` and `docker-desktop-data` to F: drive, freed **4.8 GB** on C:. All WSL2, Docker, and project data now lives on F: exclusively.

**5. Cross-Platform Memory Is Harder Than It Looks**
Hermes uses a "frozen snapshot" pattern — memory loads at session start, not mid-session. Teaching a fact on WhatsApp won't appear on Telegram until the Telegram session resets (idle timeout or `/new`). **Solution**: reduced idle timeout from 24h to 4h, added `session_search` instruction in SOUL.md. Trade-off accepted.

**6. Obsidian — Second Brain for Under RM0, Now With Health Tracking**
Added a plain-file knowledge base accessible to both Hermes and the user. No subscriptions, no cloud, no lock-in. Hermes reads, searches, creates notes directly in the vault via the Obsidian skill. Portable app on F: drive, zero C: impact. PARA structure keeps things organised from day one. The entire setup took under 30 minutes — vault, app, skill, and first notes all live. **Expanded to include medication tracking**: 20 daily reminder cron jobs with 15-min escalation, Health.md as source of truth for medication schedule, verified online before committing.

---

## ☁️ VPS / Cloud Migration

### ⏰ When to Migrate

- You need **24/7 uptime** beyond your PC's availability
- Your home internet is unreliable (mobile hotspot)
- You want external access without keeping your PC on

### 📦 Prerequisites

| Item | Recommendation | Cost |
|---|---|---|
| VPS | Hetzner CX22 (2 vCPU, 4 GB RAM) or Oracle ARM | ~€4/month or free |
| OS | Ubuntu 24.04 LTS | Free |
| Domain | Optional — for Telegram webhook mode | ~$10/year |
| Node.js | v22 LTS (for WhatsApp bridge) | Free |

### 📋 Migration Steps

**Step 1 — Backup everything**
```bash
# Inside WSL2
tar czf /mnt/f/backups/hermes-full-$(date +%Y%m%d).tar.gz ~/.hermes/
```

**Step 2 — Copy to VPS**
```bash
scp /mnt/f/backups/hermes-full-*.tar.gz user@vps-ip:~/
```

**Step 3 — Set up VPS**
```bash
ssh user@vps-ip
sudo apt update && sudo apt upgrade -y
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
tar xzf hermes-full-*.tar.gz -C ~/
```

**Step 4 — Re-pair WhatsApp**
WhatsApp session is tied to your previous IP. Scan QR on the VPS:
```bash
hermes whatsapp
```
Scan from Hotlink phone. Session saved on VPS for subsequent restarts.

**Step 5 — Telegram — just works**
Telegram Bot API is IP-agnostic. No re-pairing needed. The same token works from the VPS.

**Step 6 — Install gateway as a proper systemd service**
(This is where VPS is **better** than WSL2 — systemd just works.)

```bash
hermes gateway install
sudo loginctl enable-linger $USER
systemctl --user enable hermes-gateway
systemctl --user start hermes-gateway
```

**Differences from WSL2:**

| Feature | WSL2 (current) | VPS |
|---|---|---|
| Gateway auto-start | Startup folder + crontab watchdog | Native systemd `Restart=always` |
| WhatsApp QR | Scan from Windows terminal | Scan from SSH terminal (or use `screen`) |
| C: drive limitation | N/A (F: drive used) | N/A |
| Internet | Mobile hotspot (intermittent) | Always on |
| Monitoring | `status.ps1` | `hermes gateway status` + systemd journal |

---

## 🛠️ Operations & Monitoring

### 📊 One-Command Dashboard

```powershell
powershell -File "F:\hermes\status.ps1"

# Auto-refresh every 60 seconds
powershell -File "F:\hermes\status.ps1" -watch
```

Shows: gateway health, platform connections, cron jobs, watchdog status, disk space, recent logs, quick action commands.

### 🔧 Common Maintenance

| Task | Command |
|---|---|
| Check gateway status | `wsl -d hermes-agent -- ps aux \| grep hermes` |
| Restart gateway | `powershell -File "F:\hermes\gateway-start.ps1"` |
| View live logs | `wsl -d hermes-agent -- tail -f ~/.hermes/logs/gateway.log` |
| Usage insights | `wsl -d hermes-agent -- bash -l -c "hermes insights --days 7"` |
| Cron list | `wsl -d hermes-agent -- bash -l -c "hermes cron list"` |
| WhatsApp re-pair | `wsl -d hermes-agent -- bash -l -c "hermes whatsapp"` |
| Backup config | `wsl -d hermes-agent -- tar czf /mnt/f/backups/hermes-$(date +%Y%m%d).tar.gz ~/.hermes/` |
| C: drive check | PowerShell: `Get-PSDrive C \| Select Free` |

### 📚 Documentation Index

| Document | What It Contains |
|---|---|
| [`PRD.md`](PRD.md) | Product requirements, architecture, implementation plan, risk register |
| [`DECISIONS.md`](DECISIONS.md) | All decisions across phases, verified facts, deviations, open questions |
| [`PROGRESS.md`](PROGRESS.md) | Phase-by-phase progress tracking, what was done, commands run, blockers |
| [`RUNBOOK.md`](RUNBOOK.md) | Operational handover — startup, backup, restore, troubleshooting, key rotation |
| [`ADVANCED-IDEAS.md`](ADVANCED-IDEAS.md) | 10 advanced Hermes use cases (self-improvement, chained cron, voice chains) |
| [`AGENTS.md`](AGENTS.md) | Safety rules for coding agents working on this project |

---

## 📋 Quick Reference

### 📞 Platform Config

| Platform | Purpose |
|---|---|
| WhatsApp | Daily chat via dedicated bot number |
| Telegram | Admin surface via BotFather-created bot |

### 💰 Model Pricing (DeepSeek, per 1M tokens)

| Model | Cache Hit | Cache Miss | Output |
|---|---|---|---|
| Flash | $0.0028 | $0.14 | $0.28 |
| Pro | $0.003625 | $0.435 | $0.87 |

### ⏰ Cron Jobs Summary

| Time | Platform | What |
|---|---|---|
| 06:00-06:45 | WhatsApp | Medication: Akurit-4 + Pyridoxine (4 jobs) |
| 07:00 | WhatsApp | Morning briefing |
| 08:00-08:45 | WhatsApp | Medication: Dexa #1 + Letram (4 jobs) |
| 08:00 | Telegram | Usage report |
| 09:00 | Telegram | Health report |
| 12:00-12:45 | WhatsApp | Medication: Dexa #2 + Vit D + Ca (4 jobs) |
| 16:00-16:45 | WhatsApp | Medication: Dexa #3 (4 jobs) |
| 20:00 (M/W/F) | WhatsApp | Goal check-in |
| 20:00-20:45 | WhatsApp | Medication: Letram malam (4 jobs) |
| 21:00 | WhatsApp | Evening check-in |
| Sun 06:00 | Local | Log rotate |
| Sun 10:00 | Telegram | Weekly review |

**Total: 27 active cron jobs** (7 system + 20 medication reminders)

---

*Powered by DeepSeek V4 · GitHub · Private repo · Last updated June 27, 2026*
