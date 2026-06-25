# PROGRESS.md — Hermes Personal AI Agent

> What was done, commands run, blockers, test results. Maintained per PRD §0.

## Phase 0 — Pre-flight Verification

**Status**: COMPLETED (2026-06-24)

- Read PRD.md fully
- Read mimo-review.md and deepseek-review.md
- Verified all links in PRD §6 against live docs
- Confirmed Hermes Agent v0.17.0 (v2026.6.19)
- Confirmed DeepSeek V4 models and pricing
- Confirmed Baileys actively maintained (v7.0.0-rc13)
- Confirmed Oracle Always Free limits
- Confirmed OpenCode config schema valid
- Identified 5 deviations from PRD
- Applied 8 PRD amendments (A1-A8)
- Created risk register consolidation
- Go/No-Go: CONDITIONAL GO → APPROVED

## Phase 1 — Project Guardrails

**Status**: COMPLETED (2026-06-24)

### Completed
- [x] Initialize git repository
- [x] Create `.gitignore`
- [x] Create `AGENTS.md`
- [x] Create `opencode.json`
- [x] Create `DECISIONS.md`
- [x] Amend `PRD.md` (A1-A8)
- [x] Verify no secrets tracked
- [x] All guardrail files in place

### Verified
- No `.env`, `*.key`, `*.pem`, `auth.json` in working tree
- No `session/`, `platforms/`, `.hermes/` directories tracked

## Phase 2 — Install Hermes Agent

**Status**: COMPLETED (2026-06-24)

- Installed WSL2 distro named `hermes-agent` on F:\wsl\hermes-agent\ (1.32 GB VHDX)
- Ubuntu 24.04.4 LTS, user: amirul
- Hermes Agent v0.17.0 (2026.6.19) installed via official installer
- Python 3.11.15, Node.js v22.23.1
- All 95 Python dependencies installed, 72 skills synced
- Missing: ripgrep (grep fallback), ffmpeg (TTS limited)

## Phase 3 — Configure DeepSeek V4

**Status**: COMPLETED (2026-06-24)

- Provider: deepseek
- Default model: deepseek-v4-flash
- Base URL: https://api.deepseek.com
- Auxiliary tasks (compression/approval/extraction) routed to main provider
- Verified: `hermes chat -q "..."` returns correct response
- DEEPSEEK_API_KEY configured in .env

## Phase 4 — Connect Telegram

**Status**: COMPLETED (2026-06-24)

- Bot created via @BotFather on user's main Telegram account
- TELEGRAM_BOT_TOKEN configured in .env
- TELEGRAM_ALLOWED_USERS= (owner's user ID from @userinfobot)
- TELEGRAM_HOME_CHANNEL= (owner's DM chat ID)
- Verified: user sends "Hello", Hermes responds via DeepSeek (447 chars)
- Gateway logs confirm: "✓ telegram connected"

## Phase 5 — Connect WhatsApp

**Status**: COMPLETED (2026-06-24)

- WHATSAPP_ENABLED=true, WHATSAPP_MODE=bot
- WHATSAPP_ALLOWED_USERS= (owner's personal number)
- Bot number: Dedicated SIM - scanned QR via Linked Devices
- Session saved at ~/.hermes/whatsapp/session/ (creds.json + pre-keys)
- Verified: user sends message from personal phone, Hermes responds
- Gateway logs confirm: "✓ whatsapp connected"

## Phase 6 — Always-on Gateway

**Status**: COMPLETED (2026-06-25)

- Installed user systemd service: `hermes-gateway.service`
- Enabled lingering with `loginctl enable-linger` (survives logout)
- Enabled systemd in WSL2 via `/etc/wsl.conf` (`[boot] systemd=true`)
- Service commands: `hermes gateway stop/start/status`
- Created Windows Startup script at `shell:startup\hermes-gateway.bat`
- Auto-starts on Windows login via systemd + startup script (two layers)
- Crash recovery tested: stop → start → both platforms reconnect in ~12s
- Daily health cron created: "Daily Health" at 09:00 to Telegram (ad5a112aaf25)
- **Log rotation**: logrotate configured (weekly, 4 weeks, 50 MB threshold, compressed). Weekly no-agent cron (22daea844dba).
- Logs at `~/.hermes/logs/`: agent.log, gateway.log, errors.log
- Verified: `Gateway running with 2 platform(s)`, both platforms live
- **Phase 0-6 audit**: All gaps closed (2026-06-25)
  - G1: Non-allowlisted Telegram user denied (config confirmed, default behavior)
  - G2: Non-allowlisted WhatsApp sender denied (config confirmed, default behavior)
  - G3: Admin/user split configured (`allow_admin_from` for owner user)
  - G4: Token usage verified via `hermes insights` (28,693 max session tokens)
  - G5: DeepSeek Pro escalation documented in DECISIONS.md
  - G6: WhatsApp session chmod 700 enforced
  - G7: Cold boot simulation passed (WSL2 terminate → restart → both platforms connected ~13s)

## Phase 7 — Persona, Memory, Same-Brain

**Status**: COMPLETED (2026-06-25)

### Completed
- [x] `SOUL.md` written (2616 bytes) — persona, same-brain rules, memory policy, behavior rules, session_search instruction
- [x] `USER.md` written (937 chars) — Amirul's profile
- [x] Memory config verified (`memory_enabled=true`, `write_approval=false`, limits 2200/1375)
- [x] Idle timeout reduced: 24h → 4h for faster cross-platform memory sync
- [x] Cross-platform session_search instruction added to SOUL.md
- [x] Gateway restarted with new persona
- [x] Same-brain test passed: taught "fav color: black" on Telegram → recalled on WhatsApp
- [x] Verify unrelated live threads stay separate (separate session keys per platform)

## Phase 8 — Proactive Cron Layer

**Status**: COMPLETED (2026-06-25)

### Completed
- [x] Timezone: Asia/Kuala_Lumpur (UTC+8)
- [x] Morning Briefing (84f1c76a) — 07:00 daily, WhatsApp
- [x] Evening Check-in (fdb1a6c5) — 21:00 daily, WhatsApp (next: TODAY)
- [x] Goal Check-in (ff0c952e) — Mon/Wed/Fri 20:00, WhatsApp
- [x] Weekly Review (be706510) — Sunday 10:00, Telegram
- [x] Daily Usage Report (dab454f9) — 08:00 daily, Telegram
- [x] Daily Health Report — already exists from Phase 6 (ad5a112a, 09:00, Telegram)
- [x] Log Rotate — already exists from Phase 6 (22daea84, Sunday 06:00, local)
- [x] Proactive controls: quiet hours 23:00-07:00, max 3 pings/day, max 2 check-ins/week
- [x] All schedules verified outside quiet hours
- [x] Cron test triggered: Daily Usage Report manually queued for delivery test

## Phase 9 — Capability Skills

**Status**: COMPLETED (2026-06-25)

### Completed
- [x] Web search: default toolsets include web_search + web_extract (best-effort, free)
- [x] Voice transcription: STT enabled via faster-whisper (local, free, base model)
- [x] Telegram topics: `/topic` command available for multi-session workspaces
- [x] DND mode: "dnd"/"jangan kacau" to pause all proactive messages, "back" to resume
- [x] All platform toolsets confirmed: hermes-telegram, hermes-whatsapp (web, terminal, file, vision, tts, browser, skills, todo, cronjob)

### Verified Capabilities (from previous phases)
- [x] Cross-platform chat via WhatsApp and Telegram (Phase 4-5)
- [x] Durable memory shared across platforms (Phase 7)
- [x] DeepSeek Flash default (Phase 3)
- [x] Owner-controlled Pro escalation (Phase 3/7)
- [x] Proactive cron messages (Phase 8)
- [x] Reminder/task capture (memory system, Phase 7)
- [x] Habit/goal tracking (memory + cron, Phase 7-8)
- [x] Draft-and-confirm pattern (SOUL.md, Phase 7)
- [x] Runtime approval flow (built-in Hermes)
- [x] Gateway health and usage reports (Phase 6/8)
- [x] Web search via DuckDuckGo (DDGS, Phase 9) — verified working on both platforms
- [x] Voice transcription via faster-whisper (STT, Phase 9) — available, free, local

### Not implemented (per PRD constraints)
- ffmpeg (outgoing TTS voice) — requires `sudo apt install ffmpeg` (blocked by opencode.json). Install manually later.
- Paid Tool Gateway services — intentionally avoided per PRD §4.2

## Phase 10 — Hardening and Handover

**Status**: IN PROGRESS

### Section A — Security Audit (PASSED)
- [x] A1: Allowlists verified (Telegram and WhatsApp: owner only, no wildcard)
- [x] A2: Admin commands configured (admin split with allow_admin_from)
- [x] A3: .gitignore reviewed (covers all patterns, no secrets leaked)
- [x] A4: Secret permissions checked (.env: 600, config.yaml: 600, session: 700)
- [x] A5: Logs checked for leaks (none found)

### Section B — Budget & Cron (PASSED)
- [x] B1: All 8 cron schedules verified outside quiet hours (23:00-07:00)
- [x] B2: RM25 soft cap documented, daily usage report monitors spend

### Section C — RUNBOOK.md (DONE)
- [x] C1: System Overview
- [x] C2: Startup/Shutdown procedures
- [x] C3-C4: Backup and Restore
- [x] C5: WhatsApp Re-pairing
- [x] C6: Key Rotation (Telegram, DeepSeek, WhatsApp)
- [x] C7: Model Switching (Flash/Pro)
- [x] C8: Monitoring & Usage
- [x] C9: Troubleshooting guide
- [x] C10: Budget management
- [x] C11: File locations on disk

### Section D — Final Test Plan
- [x] D1: Model test PASSED (user verified `/model deepseek:deepseek-v4-pro` works)
- [x] D2: Memory test PASSED (cross-platform teach/recall verified)
- [x] D3: Web search test PASSED (DDGS search works on both platforms)
- [ ] D4: Cron test — auto at 21:00 tonight (Evening Check-in)
- [ ] D5: Access test — skipped (config verified, non-allowlisted deny = default)

### Deliverables
- [x] RUNBOOK.md — operational documentation (11 sections)
- [x] ADVANCED-IDEAS.md — 10 advanced Hermes use cases
- [x] F:\hermes\status.ps1 — monitoring dashboard (gateway, cron, watchdog, disk, logs)
- [x] Watchdog script — fixed output redirect to gateway.log
- [x] README.md — comprehensive project README (7 sections, combined beginner/technical/narrative)
