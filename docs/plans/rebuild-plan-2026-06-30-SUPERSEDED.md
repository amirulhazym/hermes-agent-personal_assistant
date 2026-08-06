> **STATUS: SUPERSEDED** — historical plan from 2026-06-30. The VPS migration was completed and the live runtime now runs on Tencent Cloud Lighthouse. Do not execute; kept for historical reference only.
# Rebuild Plan — Hermes Agent (MJay) — ISOLATED ENVIRONMENT

> **Context**: Distro was wiped by `wsl --unregister`. Hermes v0.17.0 freshly reinstalled on WSL2. All config lost. Current MJay repo and WSL2 distro are AUDITED and MUST NOT be touched.
> **Date**: 2026-06-30
> **Strategy**: Create entirely new environment — new project folder + new WSL2 distro. Copy what we need from originals.

---

## CRITICAL CONSTRAINT

**DO NOT modify anything in:**
- `<LOCAL_PATH>` (audited repo)
- Existing WSL2 distro `hermes-agent`

**CREATE new:**
- `<LOCAL_PATH>` — new project directory (copy of repo)
- New WSL2 distro `hermes-rebuild` — fresh install, all config goes here

---

## Phase 0 — Create Isolated Environment

**Goal**: Duplicate repo to new location, create new WSL2 distro.

### Step 0.1: Create new project directory
```powershell
# In PowerShell (Windows)
mkdir <LOCAL_PATH>
```

### Step 0.2: Copy repo files (read-only from MJay)
```powershell
# Copy entire MJay repo to new location (preserve structure)
xcopy "<LOCAL_PATH>*" "<LOCAL_PATH>" /E /I /H /Y
```

### Step 0.3: Create new WSL2 distro
```powershell
# Import Ubuntu as new distro (separate from hermes-agent)
wsl --import hermes-rebuild <LOCAL_PATH>:\wsl\backup\hermes-agent-full.tar

# Set default user to amirul
ubuntu2404.exe config --default-user amirul
```

### Step 0.4: Verify isolation
```powershell
# Confirm both distros exist independently
wsl --list --verbose
# Should show: hermes-agent (original) + hermes-rebuild (new)
```

**Checkpoint**: New directory `<LOCAL_PATH>` exists, new distro `hermes-rebuild` created.

---

## Phase A — Base Setup (provision.sh)

**Goal**: Restore directory structure, scripts, config template, persona files, trafilatura plugin, watchdog crontab.

### Step A.1: Open new WSL2 distro
```powershell
wsl -d hermes-rebuild
```

### Step A.2: Navigate to new repo
```bash
cd <LOCAL_PATH>
```

### Step A.3: Run provisioning
```bash
bash provision.sh
```

### Step A.4: Verify output
- "PROVISIONING COMPLETE" message
- All directories exist under `~/.hermes/`
- Scripts installed to `~/.hermes/scripts/`
- Config template copied to `~/.hermes/config.yaml`
- Persona files (SOUL.md, USER.md, MEMORY.md) in place
- Trafilatura plugin installed

**Checkpoint**: `~/.hermes/` fully populated from provision.sh.

---

## Phase B — Environment Variables (.env)

**Goal**: Create `~/.hermes/.env` with all required API keys and tokens.

### Step B.1: Open .env for editing
```bash
nano ~/.hermes/.env
```

### Step B.2: Add the following (guide user to fill in their own values)
```bash
# DeepSeek API (required — only paid component)
DEEPSEEK_API_KEY=sk-your-deepseek-key-here

# OpenCode Zen (free tier — vision model)
OPENCODE_ZEN_API_KEY=your-opencode-zen-key-here

# OpenCode Go (optional — model listing)
OPENCODE_GO_API_KEY=your-opencode-go-key-here

# Telegram
TELEGRAM_BOT_TOKEN=your-telegram-bot-token-here
TELEGRAM_ALLOWED_USERS=your-telegram-user-id
TELEGRAM_HOME_CHANNEL=your-telegram-chat-id

# WhatsApp
WHATSAPP_ENABLED=true
WHATSAPP_ALLOWED_USERS=your-phone-number

# Obsidian
OBSIDIAN_VAULT_PATH=<LOCAL_PATH>
```

### Step B.3: Save and exit
- Ctrl+O, Enter, Ctrl+X

### Step B.4: Lock permissions
```bash
chmod 600 ~/.hermes/.env
```

**Checkpoint**: `.env` exists with correct permissions (600), all required keys present.

**NEVER paste secrets in chat — edit directly in WSL2 using nano.**

---

## Phase C — Config.yaml Customization

**Goal**: Edit `~/.hermes/config.yaml` with platform-specific settings.

### Step C.1: Open config
```bash
nano ~/.hermes/config.yaml
```

### Step C.2: Key changes needed
- `model.default`: `deepseek-v4-flash` (or `deepseek-v4-flash-free` via OpenCode Zen)
- `model.provider`: `deepseek` (or `opencode` for free tier)
- `toolsets`: Add `hermes-telegram` and `hermes-whatsapp`
- Platform configs: Telegram and WhatsApp sections
- `reasoning_effort`: `xhigh`
- `timezone`: `Asia/Kuala_Lumpur`
- `quiet_hours`: `23:00-07:00`
- `extract_backend`: `trafilatura`
- `plugins.enabled`: Add `web-trafilatura`

### Step C.3: Save and exit

**Checkpoint**: Config valid, gateway can parse it.

---

## Phase C2 — Apply Model Overrides (from patch file)

**Goal**: Apply Gemini removal + NVIDIA/OpenCode Zen curated model lists from `patches/2026-06-27_gemini-removal-model-overrides.patch`.

### Why this matters
The patch file contains critical customizations:
1. **Gemini removal** — removes unused Google provider (5 files changed)
2. **NVIDIA models** — curated 5-model list (skip live API fetch)
3. **OpenCode Zen models** — 6 free models only (no billing needed)
4. **Hardcoded model lists** — prevents `hermes update` from overwriting customizations

### Step C2.1: Navigate to hermes-agent source
```bash
cd ~/.hermes/hermes-agent
```

### Step C2.2: Apply the patch
```bash
# Copy patch from Windows repo
cp <LOCAL_PATH>.patch /tmp/

# Apply patch
git apply /tmp/2026-06-27_gemini-removal-model-overrides.patch
```

### Step C2.3: Verify changes
```bash
# Check Gemini removed
grep -r "gemini" hermes_cli/auth.py hermes_cli/models.py agent/models_dev.py
# Should show only comments: "# Gemini removed — not using (MJ override 2026-06-27)"

# Check NVIDIA models curated
grep -A 10 '"nvidia"' hermes_cli/models.py
# Should show: minimax-m3, kimi-k2.6, deepseek-v4-flash, deepseek-v4-pro, glm-5.1

# Check OpenCode Zen free models
grep -A 10 '"opencode-zen"' hermes_cli/models.py
# Should show: deepseek-v4-flash-free, minimax-m3-free, mimo-v2.5-free, etc.
```

### Step C2.4: Reinstall with overrides
```bash
cd ~/.hermes/hermes-agent
pip install -e .
```

### Step C2.5: Disable Gemini plugin
```bash
# Rename to prevent auto-extend from resurrecting Gemini
mv ~/.hermes/hermes-agent/plugins/model-providers/gemini \
   ~/.hermes/hermes-agent/plugins/model-providers/_gemini
```

**Checkpoint**: Patch applied, Gemini removed, curated model lists in place, reinstall successful.

---

## Phase D — WhatsApp Pairing

**Goal**: Re-link WhatsApp via QR code.

### Step D.1: In WSL2 (hermes-rebuild)
```bash
hermes whatsapp
```

### Step D.2: QR code appears in terminal

### Step D.3: On dedicated bot phone
- WhatsApp → Settings → Linked Devices → Link a Device
- Scan QR code

### Step D.4: Session saved
- `~/.hermes/whatsapp/session/creds.json` exists

**Checkpoint**: WhatsApp session established.

---

## Phase E — Gateway Start & Verify

**Goal**: Start gateway, verify both platforms connected.

### Step E.1: Open PowerShell (as Administrator)

### Step E.2: Start gateway
```powershell
Start-Process -WindowStyle Hidden -FilePath "wsl" -ArgumentList "-d", "hermes-rebuild", "--", "/home/amirul/.hermes/hermes-agent/venv/bin/hermes", "gateway"
```

### Step E.3: Wait for startup (1-2 minutes)

### Step E.4: Check logs
```powershell
wsl -d hermes-rebuild -- bash -c "tail -20 ~/.hermes/logs/gateway.log"
```

### Step E.5: Look for
- "✓ telegram connected"
- "✓ whatsapp connected"

**Checkpoint**: Gateway running (PID visible), both platforms connected.

---

## Phase F — Cron Jobs

**Goal**: Restore all 27 cron jobs (7 system + 20 medication reminders).

### Step F.1: Check existing crons
```bash
hermes cron list
```

### Step F.2: Add system crons
- Morning Briefing (07:00 daily, WhatsApp)
- Evening Check-in (21:00 daily, WhatsApp)
- Daily Usage Report (08:00 daily, Telegram)
- Goal Check-in (20:00 Mon/Wed/Fri, WhatsApp)
- Weekly Review (10:00 Sunday, Telegram)
- Daily Health (09:00 daily, Telegram)
- Log Rotate (06:00 Sunday, local)

### Step F.3: Add medication reminder crons
- 5 medication slots (06:00, 08:00, 12:00, 16:00, 20:00)
- Each slot: main reminder + 3 follow-ups (+15, +30, +45 min)
- Total: 5 × 4 = 20 medication jobs

### Step F.4: Add DeepSeek Balance Check
- Mon/Fri at 09:00, Telegram

### Step F.5: Verify
```bash
hermes cron list
# Should show 27+ active jobs
```

**Checkpoint**: All 27 cron jobs active and scheduled correctly.

---

## Phase G — Obsidian Vault

**Goal**: Restore PARA structure and health tracking notes.

### Step G.1: Check if vault exists
```bash
ls <LOCAL_PATH>
```

### Step G.2: Create PARA structure (if not exists)
```bash
mkdir -p <LOCAL_PATH>{0-inbox,1-projects,2-areas,3-resources,4-archive,5-journal,templates}
```

### Step G.3: Create Health.md
```bash
cat > <LOCAL_PATH>.md << 'EOF'
# Health Tracking

## Medication Schedule

| Time | Medication | Notes |
|------|------------|-------|
| 06:00 | Medication A + Supplement A | With food |
| 08:00 | Medication B #1 + Medication C | Empty stomach |
| 12:00 | Medication B #2 + Supplement B + Supplement C | With food |
| 16:00 | Medication B #3 | Afternoon |
| 20:00 | Medication C | Evening |

## Cron Job IDs
- 06:00 slot: [to be filled after cron creation]
- 08:00 slot: [to be filled after cron creation]
- 12:00 slot: [to be filled after cron creation]
- 16:00 slot: [to be filled after cron creation]
- 20:00 slot: [to be filled after cron creation]
EOF
```

### Step G.4: Verify Hermes can access vault
```bash
hermes "read <LOCAL_PATH>.md"
```

**Checkpoint**: Vault structure exists, Health.md created, Hermes can access vault.

---

## Phase H — Windows Scripts

**Goal**: Restore auto-start and monitoring dashboard.

### Step H.1: Verify scripts exist
```powershell
dir <LOCAL_PATH>
# Should show: gateway-start.ps1, status.ps1
```

### Step H.2: Create <LOCAL_PATH>
```powershell
mkdir <LOCAL_PATH>
```

### Step H.3: Copy scripts
```powershell
Copy-Item "<LOCAL_PATH>.ps1" "<LOCAL_PATH>" -Force
Copy-Item "<LOCAL_PATH>.ps1" "<LOCAL_PATH>" -Force
```

### Step H.4: Update gateway-start.ps1 for new distro
- Change `hermes-agent` → `hermes-rebuild` in the script
- Or create a new script pointing to hermes-rebuild

### Step H.5: Set up auto-start shortcut
```powershell
# Create shortcut in shell:startup
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\Hermes Gateway.lnk")
$Shortcut.TargetPath = "powershell.exe"
$Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"<LOCAL_PATH>.ps1`""
$Shortcut.Save()
```

**Checkpoint**: Scripts in place, auto-start configured for hermes-rebuild.

---

## Phase I — Plugins & Skills

**Goal**: Restore trafilatura plugin and design skills.

### Step I.1: Verify trafilatura plugin
```bash
ls ~/.hermes/plugins/trafilatura/
# Should show: __init__.py, plugin.yaml, provider.py
```

### Step I.2: Install design skills
```bash
# Copy skills from repo
cp -r <LOCAL_PATH>* ~/.hermes/skills/
```

### Step I.3: Install hybrid-web plugin
```bash
# Copy hybrid-web plugin
mkdir -p ~/.hermes/plugins/hybrid-web
cp <LOCAL_PATH>* ~/.hermes/plugins/hybrid-web/
# Note: hybrid-web may need separate setup — check docs
```

### Step I.4: Verify skills
```bash
hermes skills list
# Should show 29+ skills
```

**Checkpoint**: All plugins and skills installed.

---

## Phase J — Hardening & Verification

**Goal**: Security audit, final verification, RUNBOOK check.

### Step J.1: Security checks
```bash
# Check .env permissions
ls -la ~/.hermes/.env
# Should show: -rw------- (600)

# Check WhatsApp session permissions
ls -la ~/.hermes/whatsapp/session/
# Should show: drwx------ (700)

# Check for secrets in logs
grep -r "sk-" ~/.hermes/logs/
# Should return nothing
```

### Step J.2: Test platforms
- Send message from Telegram → verify response
- Send message from WhatsApp → verify response

### Step J.3: Test cron jobs
```bash
# Manually trigger one job
hermes cron trigger <job-id>
# Verify delivery
```

### Step J.4: Run monitoring dashboard
```powershell
powershell -File "<LOCAL_PATH>.ps1"
# Should show all green
```

**Checkpoint**: All systems operational, security verified.

---

## Decision Point: WSL2 vs Tencent Cloud VPS

After rebuild is complete on WSL2, evaluate migration to Tencent Cloud VPS:
- **Pros**: Always-on (no PC dependency), static IP, better uptime
- **Cons**: Additional cost ($10.08/year), network latency, WhatsApp session management
- **Decision**: User decides after WSL2 rebuild is stable

---

## Summary

| Phase | Description | Est. Time |
|-------|-------------|-----------|
| 0 | Create isolated environment | 10 min |
| A | Base setup (provision.sh) | 5 min |
| B | Environment variables | 10 min |
| C | Config.yaml | 15 min |
| C2 | Apply model overrides (patch) | 10 min |
| D | WhatsApp pairing | 5 min |
| E | Gateway start & verify | 5 min |
| F | Cron jobs | 20 min |
| G | Obsidian vault | 10 min |
| H | Windows scripts | 5 min |
| I | Plugins & skills | 15 min |
| J | Hardening & verification | 15 min |
| **Total** | | **~115 min** |

---

## Isolation Verification Checklist

Before proceeding, verify:
- [ ] `<LOCAL_PATH>` — UNTOUCHED
- [ ] WSL2 distro `hermes-agent` — UNTOUCHED
- [ ] New directory `<LOCAL_PATH>` — CREATED
- [ ] New WSL2 distro `hermes-rebuild` — CREATED
- [ ] All work happens in new environment only
