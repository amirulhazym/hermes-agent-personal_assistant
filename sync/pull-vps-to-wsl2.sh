#!/bin/bash
# pull-vps-to-wsl2.sh — Pull live Hermes state from VPS to local WSL2 mirror
# Run: bash pull-vps-to-wsl2.sh
# Requires: SSH key ~/.ssh/id_ed25519 authorized on VPS.

set -euo pipefail

VPS_HOST="ubuntu@119.28.119.151"
VPS_HOME="/home/ubuntu/.hermes"
LOCAL_MIRROR="$HOME/.hermes-mirror"

SSH_KEY="$HOME/.ssh/id_ed25519"
if [ ! -f "$SSH_KEY" ]; then
  echo "ERROR: SSH key not found at $SSH_KEY"
  exit 1
fi

echo "=== Pulling Hermes state from VPS ==="
echo "Source: $VPS_HOST:$VPS_HOME/"
echo "Dest:   $LOCAL_MIRROR/"
echo ""

mkdir -p "$LOCAL_MIRROR"

rsync -avz --delete \
  -e "ssh -i $SSH_KEY -o ConnectTimeout=10" \
  --exclude='.env' \
  --exclude='.env.bak' \
  --exclude='.env.*' \
  --exclude='auth.json' \
  --exclude='platforms/*/session/' \
  --exclude='logs/' \
  --exclude='cache/' \
  --exclude='*.db' \
  --exclude='*.db-shm' \
  --exclude='*.db-wal' \
  --exclude='gateway_state.json' \
  --exclude='processes.json' \
  --exclude='channel_directory.json' \
  --exclude='provider_models_cache.json' \
  --exclude='models_dev_cache.json' \
  --exclude='__pycache__/' \
  --exclude='venv/' \
  --exclude='node_modules/' \
  --exclude='cron/output/' \
  --exclude='cron/.tick.lock' \
  --exclude='cron/ticker_heartbeat' \
  --exclude='cron/ticker_last_success' \
  --exclude='skills_prompt_snapshot.json' \
  "$VPS_HOST:$VPS_HOME/" \
  "$LOCAL_MIRROR/"

echo ""
echo "=== Pull complete ==="
echo "Mirror at: $LOCAL_MIRROR/"
ls "$LOCAL_MIRROR/"
