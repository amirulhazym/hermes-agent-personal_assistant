#!/bin/bash
# Hermes Gateway Watchdog v3
# Checks if gateway is running AND healthy, restarts if dead or stale.
# Improvements over v2:
#   - Cleans stale gateway_state.json before restart (fixes #42675)
#   - Detects stale-but-alive: process exists but log not written for 10+ min
#   - Force-restarts stale gateways instead of silently ignoring them

LOG="/home/amirul/.hermes/logs/watchdog.log"
GATEWAY="/home/amirul/.hermes/hermes-agent/venv/bin/hermes"
GW_LOG="/home/amirul/.hermes/logs/gateway.log"
STATE_FILE="/home/amirul/.hermes/gateway_state.json"
LOCK_FILE="/home/amirul/.hermes/gateway.lock"
STALE_LOG_SECS=600  # 10 minutes — if gateway.log not written in this time, force restart

count=$(ps aux 2>/dev/null | grep "venv/bin/hermes gateway" | grep -v grep | wc -l | tr -d '[:space:]')

# Function: clean stale state and restart
restart_gateway() {
    local reason="$1"
    echo "$(date "+%Y-%m-%d %H:%M:%S +08"): $reason. Cleaning state + restarting..." >> "$LOG"
    rm -f "$STATE_FILE" "$LOCK_FILE" 2>/dev/null
    pkill -f '/hermes.*gateway.?$' 2>/dev/null
    sleep 2
    setsid "$GATEWAY" gateway >> "$GW_LOG" 2>&1 &
    disown
    sleep 5
    new_count=$(ps aux 2>/dev/null | grep "venv/bin/hermes gateway" | grep -v grep | wc -l | tr -d '[:space:]')
    echo "$(date "+%Y-%m-%d %H:%M:%S +08"): Restart issued. New count: $new_count" >> "$LOG"
}

if [ "$count" -lt 1 ]; then
    # Gateway process not running
    restart_gateway "Gateway down (count=$count)"
    exit 0
fi

# Gateway process exists — check if it's stale (log not written recently)
if [ -f "$GW_LOG" ]; then
    log_mtime=$(stat -c %Y "$GW_LOG" 2>/dev/null || echo 0)
    now=$(date +%s)
    log_age=$((now - log_mtime))
    if [ "$log_age" -gt "$STALE_LOG_SECS" ]; then
        restart_gateway "Gateway stale-but-alive (log ${log_age}s old, threshold ${STALE_LOG_SECS}s)"
        exit 0
    fi
fi

# Gateway is alive and log is fresh — all good, no action needed
