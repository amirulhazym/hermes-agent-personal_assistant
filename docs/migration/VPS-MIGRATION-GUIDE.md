# Hermes Agent — Tencent Cloud VPS Migration Guide

> **Purpose**: Move Hermes Agent from WSL2 (your PC) to Tencent Cloud VPS (always-on server)
> **Difficulty**: Intermediate
> **Time**: ~2-3 hours
> **Cost**: ~$10.08/year (Tencent Cloud轻量应用服务器 Singapore)
> **Last updated**: 30 June 2026

---

## Why Migrate to VPS?

| Factor | WSL2 (Current) | VPS (Target) |
|--------|----------------|--------------|
| Uptime | Only when PC is on | 24/7 always-on |
| Access | Only from home network | Accessible from anywhere |
| Reliability | Depends on PC stability | Independent server |
| Cost | Free (already owned) | $10.08/year |
| Latency | Zero (local) | ~50-100ms (Singapore) |
| Backup | Manual | Easier (snapshot) |

**Bottom line**: If you want Hermes always available (medication reminders, proactive messages), VPS is the way.

---

## Pre-Migration Checklist

Before you start, make sure you have:

- [ ] **Tencent Cloud account** — Register at https://cloud.tencent.com/
- [ ] **VPS purchased** — 轻量应用服务器, Singapore, Ubuntu 22.04/24.04, 2vCPU/2GB/40GB
- [ ] **SSH access** — Password or SSH key from Tencent Cloud console
- [ ] **Current WSL2 working** — We'll copy files from here

---

## Phase 1: Buy & Set Up Tencent Cloud VPS

### Step 1.1: Register & Login

1. Go to https://cloud.tencent.com/
2. Click "注册" (Register) or "登录" (Login)
3. Complete registration (need phone number + ID verification)
4. Go to控制台 (Console)

**Why**: You need an account to buy and manage VPS.

### Step 1.2: Buy 轻量应用服务器 (Lighthouse)

1. In Console, search for "轻量应用服务器" (Lighthouse)
2. Click "立即购买" (Buy Now)
3. Configure:
   - **Region**: Singapore (ap-singapore)
   - **Image**: Ubuntu 22.04 LTS or Ubuntu 24.04 LTS
   - **Spec**: 2vCPU / 2GB RAM / 40GB SSD (约$10.08/year)
   - **Billing**: 按量计费 (Pay-as-you-go) or 包年包月 (Monthly/Yearly)
4. Set root password (remember this!)
5. Complete payment

**Why**: This is your always-on server. Singapore region gives lowest latency to Malaysia.

### Step 1.3: Get SSH Access

1. In Lighthouse console, find your VPS
2. Note the **Public IP** (e.g., `123.234.456.789`)
3. Click "登录" (Login) → "密码登录" (Password Login)
4. Use:
   - Username: `root`
   - Password: (the one you set during purchase)

**Why**: SSH is how you'll remotely control the VPS from your PC.

### Step 1.4: Test SSH Connection

Open PowerShell on your PC and run:

```powershell
ssh root@YOUR_VPS_IP
```

Replace `YOUR_VPS_IP` with your actual IP.

Enter password when prompted. If you see `root@VM-xxxx:~#`, you're connected!

Type `exit` to disconnect.

**Why**: Verify SSH works before proceeding.

---

## Phase 2: Prepare VPS for Hermes

### Step 2.1: Update System

SSH into your VPS and run:

```bash
apt update && apt upgrade -y
```

**Why**: Always start with latest security patches.

### Step 2.2: Create Non-Root User

```bash
# Create user named 'amirul'
adduser amirul

# Add to sudo group
usermod -aG sudo amirul

# Allow password-less sudo (optional, convenient)
echo 'amirul ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/amirul
chmod 440 /etc/sudoers.d/amirul

# Switch to new user
su - amirul
```

**Why**: Running as root is dangerous. Use a regular user with sudo for safety.

### Step 2.3: Install Required Packages

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl build-essential
```

**Why**: Hermes needs Python 3.11+, Git, and build tools for compilation.

### Step 2.4: Install Node.js (for WhatsApp bridge)

```bash
# Install Node.js 22 LTS
curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
sudo apt install -y nodejs

# Verify
node --version  # Should show v22.x.x
npm --version   # Should show 10.x.x
```

**Why**: WhatsApp bridge (Baileys) requires Node.js.

---

## Phase 3: Install Hermes Agent on VPS

### Step 3.1: Install Hermes

```bash
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
```

This installs:
- Hermes CLI at `~/.hermes/`
- Python virtual environment
- All dependencies

**Why**: Official installation method ensures correct setup.

### Step 3.2: Verify Installation

```bash
hermes version
```

Should show: `Hermes Agent v0.17.0`

**Why**: Confirm installation succeeded before proceeding.

---

## Phase 4: Copy Files from WSL2 to VPS

This is the critical step — we'll copy your working config from WSL2 to VPS.

### Step 4.1: Create Backup Archive on WSL2

Open a **new PowerShell window** (keep VPS SSH open in another window):

```powershell
wsl -d hermes-rebuild-second -- bash -c "cd ~ && tar czf /tmp/hermes-backup.tar.gz .hermes/"
```

**Why**: Creates a compressed archive of all your Hermes files (config, persona, cron jobs, scripts, plugins).

### Step 4.2: Copy Archive to Your PC

```powershell
wsl -d hermes-rebuild-second -- bash -c "cp /tmp/hermes-backup.tar.gz <LOCAL_PATH>"
```

**Why**: Moves the archive to Windows filesystem so we can upload it to VPS.

### Step 3.3: Upload Archive to VPS

From PowerShell (not WSL2):

```powershell
scp <LOCAL_PATH>.tar.gz root@YOUR_VPS_IP:/tmp/
```

Enter password when prompted.

**Why**: SCP securely transfers files from your PC to VPS.

### Step 3.4: Extract Archive on VPS

Switch to your VPS SSH window (as user `amirul`):

```bash
# Move archive to home directory
sudo mv /tmp/hermes-backup.tar.gz /home/amirul/

# Extract
cd ~
tar xzf hermes-backup.tar.gz

# Verify
ls -la ~/.hermes/
```

You should see: `config.yaml`, `.env`, `SOUL.md`, `memories/`, `cron/`, `scripts/`, `plugins/`, etc.

**Why**: Restores all your Hermes configuration on the VPS.

### Step 3.5: Fix Permissions

```bash
chmod 600 ~/.hermes/.env
chmod 700 ~/.hermes/whatsapp/session/
```

**Why**: Security — prevent unauthorized access to secrets.

---

## Phase 5: Configure for VPS

### Step 5.1: Update Config for VPS

The config from WSL2 has some WSL2-specific settings. Update them:

```bash
nano ~/.hermes/config.yaml
```

Find and change:

```yaml
# Old (WSL2 specific)
terminal:
  backend: local

# New (VPS)
terminal:
  backend: local  # Keep as local, VPS is local to Hermes
```

Also update the MCP server path (if using cua-driver):

```yaml
# Old
mcp_servers:
  cua-driver:
    command: <LOCAL_PATH>.exe

# New (comment out or remove if not needed on VPS)
mcp_servers: {}
```

Save: Ctrl+O, Enter, Ctrl+X

**Why**: VPS doesn't have Windows paths or cua-driver.

### Step 5.2: Install Python Dependencies

```bash
cd ~/.hermes/hermes-agent
python3.11 -m venv venv
source venv/bin/activate
pip install -e .
pip install aiohttp trafilatura
```

**Why**: VPS needs the same Python packages as WSL2.

### Step 5.3: Apply Model Overrides

```bash
cd ~/.hermes/hermes-agent

# Apply the patch (if it applies cleanly)
git apply /tmp/2026-06-27_gemini-removal-model-overrides.patch

# If patch doesn't apply, run the fix script instead
bash ~/.hermes/scripts/fix-models.sh
```

**Why**: Ensures NVIDIA/OpenCode Zen curated model lists are applied.

### Step 5.4: Install WhatsApp Bridge Dependencies

```bash
cd ~/.hermes/hermes-agent/scripts/whatsapp-bridge
npm install
```

**Why**: WhatsApp bridge needs Node.js dependencies (Baileys, etc.).

---

## Phase 6: Set Up Gateway as Systemd Service

Systemd makes the gateway start automatically on boot and restart if it crashes.

### Step 6.1: Create Service File

```bash
sudo nano /etc/systemd/system/hermes-gateway.service
```

Paste this (replace `amirul` if your username is different):

```ini
[Unit]
Description=Hermes AI Gateway
After=network.target

[Service]
Type=simple
User=amirul
WorkingDirectory=/home/amirul/.hermes/hermes-agent
ExecStart=/home/amirul/.hermes/hermes-agent/venv/bin/hermes gateway
Restart=always
RestartSec=10
Environment=HOME=/home/amirul
Environment=PATH=/home/amirul/.hermes/hermes-agent/venv/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
```

Save: Ctrl+O, Enter, Ctrl+X

**Why**: Systemd manages the gateway process — auto-start on boot, auto-restart on crash.

### Step 6.2: Enable and Start Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable auto-start on boot
sudo systemctl enable hermes-gateway

# Start the service
sudo systemctl start hermes-gateway

# Check status
sudo systemctl status hermes-gateway
```

Should show: `Active: active (running)`

**Why**: Gateway now runs automatically and survives reboots.

### Step 6.3: Check Logs

```bash
# Recent logs
sudo journalctl -u hermes-gateway -n 50

# Or follow live
sudo journalctl -u hermes-gateway -f
```

Look for: `✓ telegram connected` and `✓ whatsapp connected`

**Why**: Verify both platforms connected successfully.

---

## Phase 7: Re-Pair WhatsApp on VPS

WhatsApp session from WSL2 won't work on VPS (different machine). You need to re-pair.

### Step 7.1: Start WhatsApp Pairing

```bash
hermes whatsapp
```

Choose **1** (Separate bot number).

QR code will appear in terminal.

### Step 7.2: Scan QR Code

On your **dedicated bot phone**:
1. Open WhatsApp
2. Settings → Linked Devices → Link a Device
3. Scan the QR code from the terminal

**Why**: WhatsApp links to the VPS as a new device.

### Step 7.3: Verify Connection

```bash
sudo journalctl -u hermes-gateway -f
```

Should see: `✓ whatsapp connected`

Press Ctrl+C to stop following logs.

**Why**: Confirm WhatsApp is connected.

---

## Phase 8: Verify Everything Works

### Step 8.1: Test Telegram

1. Open Telegram on your phone
2. Send a message to your bot
3. Wait for response

**Why**: Verify Telegram works on VPS.

### Step 8.2: Test WhatsApp

1. Open WhatsApp on your personal phone
2. Send a message to the bot number
3. Wait for response

**Why**: Verify WhatsApp works on VPS.

### Step 8.3: Check Cron Jobs

```bash
hermes cron list
```

Should show 28 active jobs.

**Why**: Verify scheduled tasks transferred correctly.

### Step 8.4: Check Service Status

```bash
sudo systemctl status hermes-gateway
```

Should show: `Active: active (running)`

**Why**: Confirm gateway is running as a service.

---

## Phase 9: Set Up Monitoring

### Step 9.1: Create Status Check Script

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
echo ""
echo "=== Disk Usage ==="
df -h / | tail -1
```

Save and make executable:

```bash
chmod +x ~/check-status.sh
```

**Why**: Quick way to check everything is healthy.

### Step 9.2: Run Status Check

```bash
~/check-status.sh
```

**Why**: Verify all components are working.

---

## Phase 10: Update Auto-Start (Optional)

If you want to keep the WSL2 version as a backup, update the Windows startup script to NOT auto-start the gateway (since it's now on VPS).

### Step 10.1: Disable WSL2 Auto-Start

```powershell
# Remove the startup shortcut
del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\Hermes Gateway.lnk"
```

**Why**: Avoids conflict — gateway now runs on VPS, not WSL2.

---

## Troubleshooting

### Gateway Won't Start

```bash
# Check logs for errors
sudo journalctl -u hermes-gateway -n 100

# Common fix: clear stale state
rm -f ~/.hermes/gateway_state.json
sudo systemctl restart hermes-gateway
```

### Telegram Not Connecting

```bash
# Check .env has correct token
grep TELEGRAM_BOT_TOKEN ~/.hermes/.env

# Restart gateway
sudo systemctl restart hermes-gateway
```

### WhatsApp Not Connecting

```bash
# Re-pair WhatsApp
hermes whatsapp
# Scan QR code again
```

### Cron Jobs Not Running

```bash
# Check cron scheduler
hermes cron list

# If empty, re-create jobs (see PROGRESS.md for full list)
```

### Can't SSH into VPS

1. Check IP address is correct
2. Check password is correct
3. In Tencent Cloud console, check "防火墙" (Firewall) allows port 22
4. Try restarting the VPS from console

---

## Final Checklist

After migration, verify:

- [ ] SSH into VPS works
- [ ] Gateway running (`systemctl status hermes-gateway`)
- [ ] Telegram connected
- [ ] WhatsApp connected
- [ ] 28 cron jobs active
- [ ] Medication reminders working
- [ ] Can chat from both platforms
- [ ] Gateway restarts after reboot (`sudo reboot` then check)

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

# File locations
~/.hermes/config.yaml     # Main config
~/.hermes/.env            # Secrets
~/.hermes/SOUL.md         # Persona
~/.hermes/logs/           # Logs
```

---

## What You've Achieved

After this migration:

1. **Always-on Hermes** — Works 24/7, even when PC is off
2. **Medication reminders** — Never miss a dose
3. **Proactive messages** — Morning briefings, evening check-ins
4. **Accessible from anywhere** — Not tied to home network
5. **Professional setup** — Proper server deployment

---

*Guide created by MiMo Code Agent for MJay project.*
*For questions, ask Hermes on Telegram.*
