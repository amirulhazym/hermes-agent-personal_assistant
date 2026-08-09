#!/bin/bash
# Hermes Gateway Watchdog
# Checks if the systemd --user gateway service is healthy; restarts if stale.
#
# Fixes 2026-07-11 (F-03):
#   - Was hardcoded /home/amirul (wrong user) -> now /home/ubuntu.
#   - Used a manual `setsid` launch that fought the real systemd --user
#     supervisor -> now delegates restarts to `systemctl --user`.

export XDG_RUNTIME_DIR="/run/user/$(id -u)"
export DBUS_SESSION_BUS_ADDRESS="unix:path=/run/user/$(id -u)/bus"

HERMES_HOME="/home/ubuntu/.hermes"
LOG="$HERMES_HOME/logs/watchdog.log"
STATE_FILE="$HERMES_HOME/gateway_state.json"
LOCK_FILE="$HERMES_HOME/gateway.lock"
STALE_LOG_SECS=600

SERVICE="hermes-gateway"

is_active() {
    systemctl --user is-active --quiet "$SERVICE" 2>/dev/null
}

restart_gateway() {
    local reason="$1"
    echo "$(date "+%Y-%m-%d %H:%M:%S +08"): $reason. Restarting $SERVICE..." >> "$LOG"
    # Clear possibly-stale gateway state before restart (original watchdog intent)
    rm -f "$STATE_FILE" "$LOCK_FILE" 2>/dev/null
    systemctl --user restart "$SERVICE" 2>>"$LOG"
    sleep 5
    if is_active; then
        echo "$(date "+%Y-%m-%d %H:%M:%S +08"): Restart OK" >> "$LOG"
    else
        echo "$(date "+%Y-%m-%d %H:%M:%S +08"): Restart FAILED" >> "$LOG"
    fi
}

if ! is_active; then
    restart_gateway "Gateway service not active"
    exit 0
fi

# Gateway active — check for stale logs (optional staleness signal)
GW_LOG="$HERMES_HOME/logs/gateway.log"
if [ -f "$GW_LOG" ]; then
    log_mtime=$(stat -c %Y "$GW_LOG" 2>/dev/null || echo 0)
    now=$(date +%s)
    log_age=$((now - log_mtime))
    if [ "$log_age" -gt "$STALE_LOG_SECS" ]; then
        restart_gateway "Gateway stale-but-alive (log ${log_age}s old, threshold ${STALE_LOG_SECS}s)"
        exit 0
    fi
fi

echo "$(date "+%Y-%m-%d %H:%M:%S +08"): Gateway healthy" >> "$LOG"
