> **STATUS: SUPERSEDED** — historical plan from 2026-06-30. The VPS migration was completed and the live runtime now runs on Tencent Cloud Lighthouse. Do not execute; kept for historical reference only.
# VPS Migration Plan — Hermes Agent WSL2 → Tencent Cloud Lighthouse

> **Source**: WSL2 distro `hermes-rebuild-second` (working, tested)
> **Target**: Tencent Cloud Lighthouse VPS (Singapore, 2vCPU/2GB/40GB, Hermes Agent blueprint)
> **Date**: 30 June 2026
> **Estimated time**: 1-2 hours

---

## Key Discovery

Tencent Cloud Lighthouse has a **Hermes Agent blueprint** pre-installed. This means:
- Hermes v0.17.0 is already installed on the VPS
- User `<vps-user>` is pre-configured
- We only need to: copy config files, configure model, connect platforms

**Much simpler than fresh install.**

---

## VPS Specs (from user)

| Spec | Value |
|------|-------|
| Instance ID | lhins-xx |
| CPU | 2 Core |
| Memory | 2GB |
| System Disk | 40GB SSD |
| Traffic | 0.5TB/month |
| Region | Singapore |
| Blueprint | Hermes Agent v0.17.0 (v2026.6.19) |

---

## Migration Inventory

### Files to Copy (from WSL2 to VPS)

| # | File/Directory | Purpose | Size |
|---|---------------|---------|------|
| 1 | `~/.hermes/.env` | API keys + tokens (DEEPSEEK, TELEGRAM, WHATSAPP) | ~500B |
| 2 | `~/.hermes/config.yaml` | Full configuration (model, platforms, plugins, cron) | ~18KB |
| 3 | `~/.hermes/SOUL.md` | MJ persona definition | ~2.6KB |
| 4 | `~/.hermes/memories/MEMORY.md` | Durable agent memory | ~2.5KB |
| 5 | `~/.hermes/memories/USER.md` | User profile (Amirul) | ~1.3KB |
| 6 | `~/.hermes/cron/jobs.json` | All 28 scheduled jobs | ~30KB |
| 7 | `~/.hermes/scripts/` | 10 operational scripts | ~64KB |
| 8 | `~/.hermes/plugins/` | trafilatura + hybrid-web plugins | ~20KB |
| 9 | `~/.hermes/skills/` | 42 design skills | ~7MB |

### Files NOT to Copy (regenerated or Windows-only)

- `gateway_state.json` — ephemeral runtime state
- `state.db` + WAL — session database, rebuilt on first use
- `kanban.db` + WAL — task board, empty on fresh start
- `models_dev_cache.json` — fetched from API on startup
- `logs/` — fresh logs created at runtime
- `sessions/` — routing index rebuilt from gateway
- `hermes-agent/` — already installed via blueprint
- `node/` — WhatsApp bridge npm install handles this
- `bin/` — installed by hermes setup script
- `<LOCAL_PATH>*.ps1` — Windows scripts, not needed on VPS

### Additional: Obsidian Vault (Must Set Up on VPS)

| Item | Source | VPS Target |
|------|--------|------------|
| Obsidian vault structure | `<LOCAL_PATH>` (PARA: 0-inbox → 5-journal) | `~/obsidian-vault/` |
| Health.md | `2-areas/Personal/Health.md` | `~/obsidian-vault/2-areas/Personal/Health.md` |
| .env update | `OBSIDIAN_VAULT_PATH=<LOCAL_PATH>` | `OBSIDIAN_VAULT_PATH=/home/<vps-user>/obsidian-vault` |

**Why**: User requires Obsidian vault for full productivity. VPS gets its own local vault.

---

## User Decisions

| Decision | Choice |
|----------|--------|
| VPS user | `<vps-user>` (blueprint default, rename to `<owner>` later if desired) |
| Obsidian vault | **Mandatory** — set up on VPS at `~/obsidian-vault/` with full PARA structure |
| WhatsApp bot phone | Available now — re-pair during migration |

### Files Needing VPS-Specific Edits

| File | Change | Why |
|------|--------|-----|
| `config.yaml` | Remove `mcp_servers.cua-driver` section | cua-driver.exe is Windows-only |
| `.env` | Update/remove `OBSIDIAN_VAULT_PATH` | No <LOCAL_PATH> on VPS |
| `.env` | Remove `WHATSAPP_MODE` if present | Not needed on Linux |

### Post-Migration Actions

| Action | Why |
|--------|-----|
| Re-pair WhatsApp | Sessions are device-bound to machine |
| Re-apply model overrides | Fresh hermes install = upstream defaults |
| Verify Telegram works | Token should work as-is |
| Verify cron jobs | jobs.json transfers directly |
| Test both platforms | End-to-end verification |

---

## Step-by-Step Migration Plan

### Phase 1: Prepare VPS (via Tencent Cloud Console)

**Step 1.1**: Login to Tencent Cloud Console
- Go to https://console.tencentcloud.com/
- Find your Lighthouse instance

**Step 1.2**: Get SSH Access
- Click "Login" on your instance
- Select "Password Login"
- Username: `<vps-user>` (Hermes blueprint user)
- Password: (set during purchase)

**Step 1.3**: Test SSH from PowerShell
```powershell
ssh <vps-user>@YOUR_VPS_IP
```
- Verify you see `<vps-user>@VM-xxxx:~$`
- Type `exit` to disconnect

**Why**: Confirm SSH works before proceeding.

---

### Phase 2: Create Backup Archive on WSL2

**Step 2.1**: Create tar archive of Hermes config
```powershell
wsl -d hermes-rebuild-second -- bash -c "cd ~ && tar czf /tmp/hermes-config.tar.gz \
  .hermes/.env \
  .hermes/config.yaml \
  .hermes/SOUL.md \
  .hermes/memories/ \
  .hermes/cron/jobs.json \
  .hermes/scripts/ \
  .hermes/plugins/ \
  .hermes/skills/"
```

**Why**: Creates a compressed archive of only the files we need (excluding large runtime files).

**Step 2.2**: Copy archive to Windows filesystem
```powershell
wsl -d hermes-rebuild-second -- bash -c "cp /tmp/hermes-config.tar.gz <LOCAL_PATH>"
```

**Why**: Makes the archive accessible from Windows for SCP upload.

---

### Phase 3: Upload Archive to VPS

**Step 3.1**: Upload via SCP
```powershell
scp <LOCAL_PATH>.tar.gz <vps-user>@YOUR_VPS_IP:/tmp/
```

**Why**: Securely transfers the config archive to VPS.

**Step 3.2**: SSH into VPS and extract
```bash
ssh <vps-user>@YOUR_VPS_IP
cd ~
tar xzf /tmp/hermes-config.tar.gz
```

**Why**: Restores all config files on VPS.

**Step 3.3**: Verify files
```bash
ls -la ~/.hermes/.env ~/.hermes/config.yaml ~/.hermes/SOUL.md
ls ~/.hermes/cron/jobs.json
ls ~/.hermes/scripts/
ls ~/.hermes/plugins/
ls ~/.hermes/skills/ | wc -l
```

**Why**: Confirm all files transferred correctly.

---

### Phase 4: Configure VPS-Specific Settings

**Step 4.1**: Edit config.yaml — remove Windows-only MCP
```bash
nano ~/.hermes/config.yaml
```

Find and comment out or remove:
```yaml
mcp_servers:
  cua-driver:
    command: <LOCAL_PATH>.exe
    args:
      - mcp
```

Replace with:
```yaml
mcp_servers: {}
```

Save: Ctrl+O, Enter, Ctrl+X

**Why**: cua-driver.exe is a Windows binary, won't work on Linux VPS.

**Step 4.2**: Edit .env — update Obsidian path
```bash
nano ~/.hermes/.env
```

Find and update:
```bash
# Old (WSL2 path)
OBSIDIAN_VAULT_PATH=<LOCAL_PATH>

# New (VPS-local path)
OBSIDIAN_VAULT_PATH=/home/<vps-user>/obsidian-vault
```

**Why**: VPS doesn't have <LOCAL_PATH> drive. Vault will be local.

**Step 4.3**: Fix permissions
```bash
chmod 600 ~/.hermes/.env
chmod 700 ~/.hermes/whatsapp/session/ 2>/dev/null
```

**Why**: Security — prevent unauthorized access to secrets.

---

### Phase 4B: Set Up Obsidian Vault on VPS

**Step 4B.1**: Create vault directory structure
```bash
mkdir -p ~/obsidian-vault/{0-inbox,1-projects,2-areas,3-resources,4-archive,5-journal,templates}
mkdir -p ~/obsidian-vault/2-areas/Personal
```

**Why**: Recreates the PARA (Projects, Areas, Resources, Archive) structure on VPS.

**Step 4B.2**: Create Health.md
```bash
cat > ~/obsidian-vault/2-areas/Personal/Health.md << 'EOF'
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
- 06:00 slot: [to be filled after verification]
- 08:00 slot: [to be filled after verification]
- 12:00 slot: [to be filled after verification]
- 16:00 slot: [to be filled after verification]
- 20:00 slot: [to be filled after verification]
EOF
```

**Why**: Source of truth for medication schedule, referenced by cron jobs.

**Step 4B.3**: Verify vault accessible
```bash
ls -la ~/obsidian-vault/
```

Should show all 7 directories.

**Why**: Confirm vault structure is correct.

---

### Phase 5: Install Python Dependencies

**Step 5.1**: Activate venv and install extras
```bash
cd ~/.hermes/hermes-agent
source venv/bin/activate
pip install aiohttp trafilatura
```

**Why**: WhatsApp bridge needs aiohttp, web extraction needs trafilatura.

**Step 5.2**: Apply model overrides
```bash
cd ~/.hermes/hermes-agent
bash ~/.hermes/scripts/fix-models.sh
```

Or if that doesn't work:
```bash
python3 ~/.hermes/scripts/fix_models.py
```

**Why**: Ensures NVIDIA/OpenCode Zen curated model lists are applied.

---

### Phase 6: Configure DeepSeek Model

**Step 6.1**: Run setup wizard
```bash
hermes setup
```

Select "Quick setup — provider, model & messaging"

**Step 6.2**: Select DeepSeek provider
- Choose "DeepSeek" from the provider list
- Enter your DEEPSEEK_API_KEY (already in .env)

**Step 6.3**: Select model
- Choose "deepseek-v4-flash" as default

**Step 6.4**: Skip messaging setup
- Select "Skip — set up later with 'hermes setup gateway'"

**Why**: Configures the model provider. We'll connect platforms separately.

---

### Phase 7: Connect Telegram

**Step 7.1**: Verify Telegram token in .env
```bash
grep TELEGRAM_BOT_TOKEN ~/.hermes/.env
```

Should show your existing token (not the actual value, just confirmation it exists).

**Why**: Telegram token is transferable — same bot, same token works on VPS.

**Step 7.2**: Update Telegram allowlist
```bash
nano ~/.hermes/config.yaml
```

Find `platforms.telegram.extra.allow_from` and verify it contains your user ID `679729206`.

**Why**: Ensures only you can message the bot.

---

### Phase 8: Re-Pair WhatsApp

**Step 8.1**: Start WhatsApp pairing
```bash
hermes whatsapp
```

Choose **1** (Separate bot number).

QR code will appear.

**Step 8.2**: Scan QR code
On your **dedicated bot phone**:
1. Open WhatsApp
2. Settings → Linked Devices → Link a Device
3. Scan the QR code

**Why**: WhatsApp sessions are device-bound. Must re-pair on VPS.

---

### Phase 9: Set Up Systemd Service

**Step 9.1**: Create service file
```bash
sudo nano /etc/systemd/system/hermes-gateway.service
```

Paste:
```ini
[Unit]
Description=Hermes AI Gateway
After=network.target

[Service]
Type=simple
User=<vps-user>
WorkingDirectory=/home/<vps-user>/.hermes/hermes-agent
ExecStart=/home/<vps-user>/.hermes/hermes-agent/venv/bin/hermes gateway
Restart=always
RestartSec=10
Environment=HOME=/home/<vps-user>
Environment=PATH=/home/<vps-user>/.hermes/hermes-agent/venv/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
```

Save: Ctrl+O, Enter, Ctrl+X

**Why**: Systemd manages the gateway — auto-start on boot, auto-restart on crash.

**Step 9.2**: Enable and start service
```bash
sudo systemctl daemon-reload
sudo systemctl enable hermes-gateway
sudo systemctl start hermes-gateway
```

**Why**: Gateway now runs automatically and survives reboots.

**Step 9.3**: Check status
```bash
sudo systemctl status hermes-gateway
```

Should show: `Active: active (running)`

**Why**: Verify gateway started successfully.

---

### Phase 10: Verify Everything Works

**Step 10.1**: Check gateway logs
```bash
sudo journalctl -u hermes-gateway -n 30
```

Look for:
- `✓ telegram connected`
- `✓ whatsapp connected`
- `Gateway running with 2 platform(s)`

**Why**: Confirm both platforms connected.

**Step 10.2**: Test Telegram
- Send a message to your bot on Telegram
- Wait for response

**Why**: Verify Telegram works on VPS.

**Step 10.3**: Test WhatsApp
- Send a message to the bot number on WhatsApp
- Wait for response

**Why**: Verify WhatsApp works on VPS.

**Step 10.4**: Check cron jobs
```bash
hermes cron list
```

Should show 28 active jobs.

**Why**: Verify scheduled tasks transferred correctly.

**Step 10.5**: Create monitoring script
```bash
nano ~/check-status.sh
```

Paste:
```bash
#!/bin/bash
echo "=== Hermes Gateway Status ==="
sudo systemctl status hermes-gateway --no-pager | head -5
echo ""
echo "=== Platform Connections ==="
sudo journalctl -u hermes-gateway --since "5 minutes ago" | grep -E "connected|running"
echo ""
echo "=== Cron Jobs ==="
hermes cron list 2>/dev/null | grep -c "Name:" | xargs -I {} echo "Active jobs: {}"
```

Save and make executable:
```bash
chmod +x ~/check-status.sh
```

**Why**: Quick health check command.

---

## Final Checklist

After migration, verify:

- [ ] SSH into VPS works
- [ ] Gateway running (`systemctl status hermes-gateway`)
- [ ] Telegram connected and responding
- [ ] WhatsApp connected and responding
- [ ] 28 cron jobs active
- [ ] Medication reminders scheduled correctly
- [ ] Model overrides applied (DeepSeek V4 Flash)
- [ ] Plugins working (trafilatura, hybrid-web)
- [ ] Skills loaded (42 skills)
- [ ] Obsidian vault created at `~/obsidian-vault/` with PARA structure
- [ ] Health.md created with medication schedule
- [ ] OBSIDIAN_VAULT_PATH updated in .env
- [ ] Gateway survives reboot (`sudo reboot` then check)

---

## Commands Cheat Sheet

```bash
# Gateway management
sudo systemctl start hermes-gateway
sudo systemctl stop hermes-gateway
sudo systemctl restart hermes-gateway
sudo systemctl status hermes-gateway
sudo journalctl -u hermes-gateway -f

# Hermes commands
hermes cron list
hermes gateway status
hermes whatsapp
hermes version
hermes doctor

# Health check
~/check-status.sh
```

---

## What Changes After Migration

| Before (WSL2) | After (VPS) |
|---------------|-------------|
| Gateway starts on Windows login | Gateway starts on VPS boot (systemd) |
| Gateway stops when PC shuts down | Gateway runs 24/7 |
| Access only from home network | Accessible from anywhere |
| Status via PowerShell dashboard | Status via `systemctl` + journalctl |
| WhatsApp paired to WSL2 | WhatsApp paired to VPS (re-scan QR) |
| Obsidian vault on F: drive | Not available (or set up local vault) |
| cua-driver for screenshots | Not available (Windows binary) |

---

## Troubleshooting

### Gateway Won't Start
```bash
sudo journalctl -u hermes-gateway -n 50
rm -f ~/.hermes/gateway_state.json
sudo systemctl restart hermes-gateway
```

### Telegram Not Connecting
```bash
grep TELEGRAM_BOT_TOKEN ~/.hermes/.env
sudo systemctl restart hermes-gateway
```

### WhatsApp Not Connecting
```bash
hermes whatsapp
# Re-pair via QR scan
```

### Cron Jobs Not Running
```bash
hermes cron list
# If empty, check jobs.json was copied correctly
```

---

*Plan created by MiMo Code Agent for MJay VPS migration.*
