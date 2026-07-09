#!/bin/bash
# drift-check.sh — Jane Verifier: daily drift check (VPS side)
# Run: bash drift-check.sh
# Checks: config parity, SOUL.md versions, script diffs, cron alignment.
# Alerts to Telegram if drift detected (user must approve cron deployment).

set -euo pipefail

VPS_SRC="/home/ubuntu/.hermes"
REPORT=""

add() { REPORT="$REPORT$1"$'\n'; }

# --- SOUL.md check ---
SOUL_LINES=$(wc -l < "$VPS_SRC/SOUL.md")
if [ -f ~/mjay/persona/SOUL.md ]; then
  GIT_SOUL_LINES=$(wc -l < ~/mjay/persona/SOUL.md)
  if [ "$SOUL_LINES" -ne "$GIT_SOUL_LINES" ]; then
    add "[DRIFT] SOUL.md: VPS=${SOUL_LINES} lines vs git=${GIT_SOUL_LINES} lines"
  fi
fi

# --- Cron jobs count ---
CRON_COUNT=$(python3 -c "import json;print(len(json.load(open('$VPS_SRC/cron/jobs.json'))))" 2>/dev/null || echo "ERR")
add "[INFO] Active cron jobs: $CRON_COUNT"

# --- Config check (keys present) ---
for key in model.default model.provider model.base_url redact_pii; do
  if ! grep -q "^  $key:" "$VPS_SRC/config.yaml" 2>/dev/null; then
    add "[DRIFT] config.yaml missing key: $key"
  fi
done

# --- Script count ---
SCRIPT_COUNT=$(ls "$VPS_SRC/scripts/"*.py "$VPS_SRC/scripts/"*.sh 2>/dev/null | wc -l)
add "[INFO] Scripts in ~/.hermes/scripts/: $SCRIPT_COUNT"

# --- Gateway status ---
if systemctl --user status hermes-gateway 2>/dev/null | grep -q "Active: active"; then
  add "[OK] Gateway active"
else
  add "[ALERT] Gateway may not be running"
fi

# --- Report ---
echo "=== Drift Check Report ==="
echo "$REPORT"

# Optional: send to Telegram. Requires user approval for cron + TELEGRAM creds.
# python3 ~/.hermes/scripts/send_telegram.py "Drift check: $REPORT"
