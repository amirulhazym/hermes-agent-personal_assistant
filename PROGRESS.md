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

**Status**: IN PROGRESS

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
- TELEGRAM_ALLOWED_USERS=679729206 (user ID from @userinfobot)
- TELEGRAM_HOME_CHANNEL=679729206
- Verified: user sends "Hello", Hermes responds via DeepSeek (447 chars)
- Gateway logs confirm: "✓ telegram connected"

## Phase 5 — Connect WhatsApp

**Status**: COMPLETED (2026-06-24)

- WHATSAPP_ENABLED=true, WHATSAPP_MODE=bot
- WHATSAPP_ALLOWED_USERS=601166557800 (user's personal number)
- Bot number: Hotlink SIM (60175407200) - scanned QR via Linked Devices
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
  - G3: Admin/user split configured (`allow_admin_from` for user 679729206)
  - G4: Token usage verified via `hermes insights` (28,693 max session tokens)
  - G5: DeepSeek Pro escalation documented in DECISIONS.md
  - G6: WhatsApp session chmod 700 enforced
  - G7: Cold boot simulation passed (WSL2 terminate → restart → both platforms connected ~13s)

## Phase 7 — Persona, Memory, Same-Brain

**Status**: NOT STARTED

## Phase 8 — Proactive Cron Layer

**Status**: NOT STARTED

## Phase 9 — Capability Skills

**Status**: NOT STARTED

## Phase 10 — Hardening and Handover

**Status**: NOT STARTED
