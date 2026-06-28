# AUDIT.md — System Snapshot for Claude Audit

> Generated: 28 June 2026, 17:30 MYT (Updated after Resolution Plan execution)
> Purpose: Give Claude full context to deeply audit the Hermes Agent (MarryJane) project

---

## 1. System Overview

| Item | Value |
|---|---|
| Hermes Agent | v0.17.0 |
| Host OS | Windows 11 |
| WSL2 Distro | `hermes-agent` on F:\wsl\hermes-agent\ext4.vhdx (1.3 GB) |
| WSL Disk | 1007G total, 5G used (/), 951G available |
| F: Drive | 932G total, 691G used (75%), 241G available |
| Default Model | deepseek-v4-flash-free via OpenCode Zen |
| Vision Model | minimaxai/minimax-m3 via NVIDIA |
| Web Search | DDGS (free, unlimited) |
| Web Extract | trafilatura (custom plugin, free, no API key) |
| STT | faster-whisper (local, free) |
| Computer Use | cua-driver v0.6.8 (Windows binary at F:\hermes\cua-driver\) |
| Platforms | Telegram + WhatsApp (both connected) |
| Git Repo | amirulhazym/hermes-agent-personal_assistant (docs-only, SSH) |

---

## 2. Gateway Status

**Currently Running**: PID 2194 on WSL2, both platforms connected.

```
gateway_state: "running"
platforms:
  telegram: connected
  whatsapp: connected
active_agents: 0
```

**Known issues:**
1. `gateway_state.json` persists "running" after SIGTERM — blocks restart. Fix: `rm ~/.hermes/gateway_state.json`
2. Telegram polling conflict after restart — normal, old session expires in ~30s

---

## 3. Cron Jobs (Active)

### System Jobs (7)

| Name | Schedule | Last Run | Status |
|---|---|---|---|
| Daily Health | 09:00 daily | 28 Jun, 09:28 | OK |
| Morning Briefing | 07:00 daily | 28 Jun, 07:01 | OK |
| Evening Check-in | 21:00 daily | 28 Jun, 09:26 | OK¹ |
| Daily Usage Report | 08:00 daily | 28 Jun, 08:11 | OK² |
| Goal Check-in | 20:00 M/W/F | 27 Jun, 08:56 | OK |
| Weekly Review | 10:00 Sunday | 28 Jun, 10:00 | — |
| Log Rotate | 06:00 Sunday | 28 Jun, 06:07 | OK |
| DeepSeek Balance Check | 09:00 M/F | 26 Jun, 09:00 | OK |
| Daily API Billing Report | 09:00 daily | 28 Jun, 09:00 | OK |

¹ Old "No module named 'tools.send_message_tool'" error **resolved** after repo re-clone + gateway restart. Verified by manual trigger at 09:26.
² Old Telegram send error **resolved** after repo re-clone + gateway restart.

### Medication Reminders (20 jobs — generic names)

| Name | Schedule | Last Run | Status |
|---|---|---|---|
| Medication A + Supplement A | 06:00 daily | 28 Jun, 06:07 | OK |
| Medication B #1 + Medication C pagi | 08:00 daily | 28 Jun, 08:03 | OK¹ |
| Medication B #2 + Supplement B + Supplement C | 12:00 daily | 27 Jun, 12:07 | OK |
| Medication B #3 petang | 16:00 daily | 27 Jun, 20:56 | OK¹ |
| Medication C malam | 20:00 daily | 27 Jun, 20:56 | OK¹ |

Plus 15 follow-up timers (diligence checks). All delivered to `origin` platform.

¹ Old delivery errors resolved after repo re-clone + gateway restart.

**Medication cron note**: The cron system stores drug names internally (Akurit-4, Pyridoxine, Dexa, Letram, etc.) — these were sanitized in docs but still visible in `hermes cron list`. This is the actual medication schedule and is functional, not a docs issue.

---

## 4. Configuration Highlights

### Model Config
- Default: deepseek-v4-flash-free (OpenCode Zen)
- Vision: minimaxai/minimax-m3 (NVIDIA)
- All auxiliary tasks: DeepSeek V4 Flash
- Fallback: not configured
- Model overrides in `hermes_cli/models.py` and `agent/models_dev.py`

### Provider Setup
- **OpenCode Zen**: API key in .env, 6 free models curated, skip live fetch
- **NVIDIA**: API key in .env, 5 curated models, skip live fetch
- **Google Gemini**: Fully removed (5 code changes + plugin dir renamed to `_gemini/`)
- DeepSeek: Pending API key (currently routes through OpenCode Zen)

### Key Config Values
| Config | Value |
|---|---|
| max_turns | 60 |
| gateway_timeout | 1800s (30 min) |
| quiet_hours | 23:00–07:00 |
| max_daily_pings | 3 |
| max_weekly_checkins | 2 |
| timezone | Asia/Kuala_Lumpur |
| extract_backend | trafilatura |
| session_reset | idle 240 min + daily 04:00 |
| prompt_caching | cache_ttl: 5m |
| TTS | provider: edge (en-US-AriaNeural) |
| STT | provider: local (faster-whisper) |
| plugins enabled | web-trafilatura |
| mcp_servers | cua-driver |

### Config Version: `_config_version: 31` (migrated from v30 via `hermes doctor --fix`)

---

## 5. Filesystem Layout

### MJay Repo (docs & ops)
```
F:\AI Prep\OVIS\Hermes Agent\MJay\
├── PRD.md              — Product requirements
├── RUNBOOK.md          — Ops handover & recovery
├── DECISIONS.md        — All phase decisions
├── PROGRESS.md         — Phase tracking (0-14)
├── README.md           — Overview doc
├── AGENTS.md           — Safety rules for coding agents
├── AUDIT.md            — This file
├── patches/
│   └── 2026-06-27_gemini-removal-model-overrides.patch
```

### WSL2 (`~/.hermes/`)
```
~/.hermes/
├── hermes-agent/        — Cloned from NousResearch (re-cloned 27 Jun)
├── hermes-agent.bak/    — Backup of old corrupted clone
├── config.yaml          — Main config (v30)
├── .env                 — API keys
├── gateway_state.json   — PID 164, running
├── SOUL.md              — MJ persona definition
├── plugins/
│   ├── trafilatura/     — Custom web extract plugin
│   └── _gemini/         — Disabled Gemini plugin (renamed backup)
├── scripts/
│   ├── fix-models.sh    — Post-update model override recovery
│   ├── watchdog.sh      — v2 watchdog (CRLF fixed)
│   └── billing.py       — API billing script
├── memories/
│   └── MEMORY.md        — Durable memory
├── logs/
│   ├── gateway.log      — 3046 lines, 4.7 MB
│   ├── watchdog.log
│   └── agent.log
├── sessions/            — SessionDB (SQLite, ~49 MB)
├── state.db             — 49 MB + WAL/SHM
├── cron/                — Job definitions
├── cache/               — Model cache
├── platforms/
│   ├── telegram/
│   └── whatsapp/
├── node/                — Node.js for WhatsApp bridge
└── whatsapp/            — WhatsApp session
```

### Windows Drive (F:\)
```
F:\
├── hermes/
│   ├── gateway-start.ps1    — v4 startup script
│   ├── status.ps1           — Monitoring dashboard
│   └── cua-driver/
│       └── cua-driver.exe   — v0.6.8 (computer use)
├── obsidian-vault/          — PARA-structured vault
└── wsl/hermes-agent/        — WSL2 VHDX (1.3 GB)
```

---

## 6. Running Processes (WSL2)

```
PID 65   — WhatsApp bridge (node, bridge.js)
PID 2194 — Hermes Gateway (python3, hermes gateway)
PID 177  — cua-driver MCP subprocess
```

---

## 7. Security & Privacy

### Done
- ✅ All drug names → generics in docs (Akurit-4 → Medication A, etc.)
- ✅ All company names → generics in docs (Maistorage/Phison)
- ✅ PII sanitized across all tracked files
- ✅ Google Gemini fully removed
- ✅ API keys stored in .env only (not tracked)
- ✅ Git repo is docs-only (no source code, no keys)

### Needs Review
- ⚠️ `hermes cron list` still shows real drug names (internal cron system) — these are functional reminders, not docs
- ⚠️ API keys pasted in plaintext earlier in conversation — NVIDIA + OpenCode Zen keys should be regenerated
- ⚠️ gateway_state.json contains PID and platform status — low sensitivity but worth noting
- ⚠️ baileys WhatsApp library has 1 critical vulnerability with no upstream fix — monitor releases

### Resolved Since Initial Audit
- ✅ `hermes doctor` hang — was a PowerShell shell invocation issue, not a bug; works with `bash -l -c`
- ✅ Delivery failures (`tools.send_message_tool` missing) — caused by corrupted repo before Phase 14 re-clone; all deliveries verified working
- ✅ Telegram send error — resolved after repo re-clone; new gateway verified working
- ✅ Daily Health broken pipe — transient error on old gateway; verified working after restart
- ✅ Config v30→v31 migration — completed via `hermes doctor --fix`
- ✅ npm vulnerabilities — 4 of 5 fixed via `npm update`; 1 critical (baileys) has no fix upstream
- ✅ Skills Hub initialized — `hermes skills list` completed
- ✅ Model overrides restored — verified NVIDIA (5 curated), OpenCode Zen (6 free), Gemini removed

### Questions for Claude
1. Are there any remaining PII/exposure risks in the MJay repo or WSL2 configuration?
2. Is the `gateway_state.json` persistence bug architecture or misconfiguration?
3. Should medication names be aliased in the cron system itself (not just docs)?
4. Is the current backup/recovery strategy adequate?
5. Any security concerns with the current plugin setup (trafilatura user plugin)?
6. Should we add secrets rotation to the audit checklist?
7. Any concerns with the dual-platform setup (Telegram + WhatsApp) long-term?
8. What's the recommended approach for gateway remote restart from phone?
9. Is the baileys critical vulnerability (message spoofing) a practical risk for a personal assistant bot?
10. Should npm be added to PATH permanently for easier maintenance?
