#!/bin/bash
# provision.sh — Rebuild the Hermes Agent (MJay) from repo backup
# Run this from a fresh WSL2 Ubuntu 24.04 install.
#
# Usage:
#   1. Clone the MJay repo: git clone <repo-url> ~/MJay && cd ~/MJay
#   2. Run: bash provision.sh
#   3. Edit ~/.hermes/config.yaml (set your Telegram user ID, choose model)
#   4. Create ~/.hermes/.env with your API keys (see template below)
#   5. Open PowerShell and run: powershell -File F:\hermes\gateway-start.ps1
#
# This script is IDEMPOTENT — safe to run multiple times.
# It will not overwrite existing config or .env files.

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

HERMES_HOME="$HOME/.hermes"
REPO_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "============================================"
echo "  Hermes Agent (MJay) — Provisioning Script"
echo "============================================"
echo ""

# ── 0. Pre-flight checks ──
if [ ! -f "$REPO_DIR/config/config.yaml.template" ]; then
    error "config/config.yaml.template not found. Run from the MJay repo root."
    exit 1
fi
info "Repo root: $REPO_DIR"

# ── 1. Install Hermes Agent ──
if command -v hermes &>/dev/null; then
    info "Hermes CLI found: $(hermes version 2>/dev/null || echo 'version check skipped')"
else
    info "Installing Hermes Agent v0.17.0..."
    curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash
fi

# Ensure hermes home exists
mkdir -p "$HERMES_HOME"/{scripts,memories,plugins/trafilatura,logs,cron,platforms,sessions,cache}

# ── 2. Persona files ──
for f in SOUL.md USER.md MEMORY.md; do
    src="$REPO_DIR/persona/$f"
    dst="$HERMES_HOME/memories/$f"
    if [ "$f" = "SOUL.md" ]; then
        dst="$HERMES_HOME/SOUL.md"
    fi
    if [ -f "$src" ]; then
        if [ -f "$dst" ]; then
            info "persona/$f already exists — skipping"
        else
            cp "$src" "$dst"
            info "persona/$f → $dst"
        fi
    fi
done

# ── 3. Scripts ──
info "Installing scripts..."
cp -n "$REPO_DIR/scripts/"*.py "$HERMES_HOME/scripts/" 2>/dev/null || true
cp -n "$REPO_DIR/scripts/"*.sh "$HERMES_HOME/scripts/" 2>/dev/null || true
chmod +x "$HERMES_HOME/scripts/"*.sh "$HERMES_HOME/scripts/"*.py 2>/dev/null || true
info "Scripts installed to $HERMES_HOME/scripts/"

# ── 4. Config template ──
if [ -f "$HERMES_HOME/config.yaml" ]; then
    info "config.yaml already exists — leaving untouched"
else
    cp "$REPO_DIR/config/config.yaml.template" "$HERMES_HOME/config.yaml"
    info "config.yaml template copied — EDIT IT before starting gateway"
fi

# ── 5. Trafilatura plugin ──
for f in plugin.yaml __init__.py provider.py; do
    src="$REPO_DIR/plugins/trafilatura/$f"
    dst="$HERMES_HOME/plugins/trafilatura/$f"
    if [ -f "$src" ]; then
        if [ -f "$dst" ]; then
            info "plugins/trafilatura/$f already exists — skipping"
        else
            cp "$src" "$dst"
            info "plugins/trafilatura/$f installed"
        fi
    fi
done

# ── 6. Windows scripts (copy to F:\hermes\) ──
if [ -d "/mnt/f/hermes" ]; then
    info "Copying Windows scripts to F:\\hermes\\..."
    cp "$REPO_DIR/windows/gateway-start.ps1" "/mnt/f/hermes/" 2>/dev/null || true
    cp "$REPO_DIR/windows/status.ps1" "/mnt/f/hermes/" 2>/dev/null || true
    info "Windows scripts copied"
else
    warn "F:\\hermes\\ not found — skipping Windows script copy"
    warn "  Create the directory on Windows then re-run provision.sh"
fi

# ── 7. Apply model overrides ──
if [ -f "$HERMES_HOME/scripts/fix_models.py" ]; then
    info "Applying model overrides (fix_models.py)..."
    python3 "$HERMES_HOME/scripts/fix_models.py" --verify 2>&1 || {
        warn "Some overrides not applied — running fix_models.py..."
        python3 "$HERMES_HOME/scripts/fix_models.py"
    }
fi

# ── 8. Crontab (watchdog) ──
if ! crontab -l 2>/dev/null | grep -q "watchdog.sh"; then
    info "Adding watchdog crontab (every 5 min)..."
    (crontab -l 2>/dev/null; echo "*/5 * * * * $HERMES_HOME/scripts/watchdog.sh") | crontab -
else
    info "Watchdog crontab already set"
fi

# ── Complete ──
echo ""
echo "============================================"
echo "  PROVISIONING COMPLETE"
echo "============================================"
echo ""
echo "NEXT STEPS (manual):"
echo ""
echo "  1. Edit config:  $HERMES_HOME/config.yaml"
echo "     → Replace <YOUR_TELEGRAM_USER_ID> with your actual Telegram user ID"
echo "     → Choose your default model (model.default + model.provider)"
echo ""
echo "  2. Create .env:   $HERMES_HOME/.env"
echo "     Required env vars:"
echo "       DEEPSEEK_API_KEY=sk-..."
echo "       OPENCODE_ZEN_API_KEY=..."
echo "       OPENCODE_GO_API_KEY=..."
echo "       TELEGRAM_BOT_TOKEN=..."
echo "       WHATSAPP_ENABLED=true"
echo "       WHATSAPP_ALLOWED_USERS=<your_phone_number>"
echo "       OBSIDIAN_VAULT_PATH=/mnt/f/obsidian-vault"
echo ""
echo "     Safety: chmod 600 $HERMES_HOME/.env"
echo ""
echo "  3. WhatsApp pair: hermes whatsapp"
echo "     → Scan QR code via phone WhatsApp → Linked Devices"
echo ""
echo "  4. Start gateway (PowerShell, as Administrator):"
echo "     powershell -File F:\\hermes\\gateway-start.ps1"
echo ""
echo "  5. Verify:"
echo "     → Check Telegram for /billing /status /model"
echo "     → Check WhatsApp for message response"
echo "     → Run: wsl -d hermes-agent -- bash -lc 'hermes cron list'"
echo ""
echo "============================================"
echo ""
info "Provisioning done. Review the NEXT STEPS above."
