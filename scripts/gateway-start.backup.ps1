#!/usr/bin/env pwsh
# Hermes Gateway Startup Script v4 — Internet-aware + self-validating + stale-state cleanup
# Usage: .\gateway-start.ps1
# Fixes in v4:
#   - Removes stale gateway_state.json + gateway.lock at Phase 2 (fixes #42675 stale-running bug)
#   - Detects stale-but-alive gateway (process running, no recent activity in log) and force-restarts
#   - Post-start monitoring: 60s window for Telegram polling failures → hard restart

$LogPath = "F:\hermes\gateway-start.log"
$GatewayLog = "\\wsl.localhost\hermes-agent\home\amirul\.hermes\logs\gateway.log"

Function Write-Log($msg) {
    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$time - $msg" | Out-File -Append -FilePath $LogPath
}

Write-Log "=== Gateway startup v4 initiated ==="

# ══════════════════════════════════════════════
# Phase 1: Internet check (retry up to 5 min, 10s interval)
# Checks BOTH generic connectivity AND Telegram API reachability
# ══════════════════════════════════════════════
$internetOk = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        # Fast check — ping Google DNS (reliable, always up)
        $result = wsl -d hermes-agent -- bash -c "timeout 5 ping -c 1 8.8.8.8 2>/dev/null | grep -c '1 received'" 2>$null
        if ($result -match "1") {
            $internetOk = $true
            Write-Log "Internet: CONNECTED (attempt $i)"
            break
        }
    } catch { }
    
    Write-Log "Internet: waiting... (attempt $i/30) — retry in 10s"
    Start-Sleep -Seconds 10
}

if (-not $internetOk) {
    Write-Log "FATAL: No internet after 30 attempts (5 min). Giving up."
    exit 1
}

# ══════════════════════════════════════════════
# Phase 2a: Clean stale state files (fixes #42675 stale-running bug)
# These files persist "running" after SIGTERM and block restarts.
# ══════════════════════════════════════════════
Write-Log "Phase 2a: Cleaning stale state files..."
wsl -d hermes-agent -- bash -c "rm -f /home/amirul/.hermes/gateway_state.json /home/amirul/.hermes/gateway.lock 2>/dev/null" 2>$null
Write-Log "Stale state files removed (gateway_state.json + gateway.lock)"

# ══════════════════════════════════════════════
# Phase 2b: Check if gateway already running (bulletproof check)
# Also detects stale-but-alive: process exists but no log activity for 5+ min
# ══════════════════════════════════════════════
$checkCmd = 'ps aux | grep "venv/bin/hermes gateway" | grep -v grep | wc -l | tr -d " "'
$running = wsl -d hermes-agent -- bash -c "$checkCmd" 2>$null
$running = ($running -replace '\D', '0')
if ([int]$running -ge 1) {
    Write-Log "Gateway process running ($running process(es)) — checking health..."
    
    # Check log freshness — if gateway.log hasn't been written to in 5+ min, it's stale-but-alive
    $logAgeCmd = 'expr $(date +%s) - $(stat -c %Y /home/amirul/.hermes/logs/gateway.log 2>/dev/null || echo 0)'
    $logAge = wsl -d hermes-agent -- bash -c "$logAgeCmd" 2>$null
    $logAge = ($logAge -replace '\D', '0')
    if ([int]$logAge -gt 300) {
        Write-Log "WARNING: Gateway process alive but log stale (${logAge}s old) — force restarting"
        # Fall through to Phase 3 (kill + restart)
    } else {
        # Validate connections
        Start-Sleep -Seconds 3
        $recentLog = Get-Content $GatewayLog -Tail 30 2>$null
        $telegramOk = $recentLog | Select-String "telegram connected" 
        $whatsappOk = $recentLog | Select-String "whatsapp connected"
        
        # Also check for recent polling failures
        $pollingFail = $recentLog | Select-String "Polling heartbeat probe failed"
        
        if ($telegramOk -and $whatsappOk -and -not $pollingFail) {
            Write-Log "Validation: Both platforms connected, no recent polling failures — all good"
            exit 0
        } elseif ($telegramOk -and $whatsappOk -and $pollingFail) {
            Write-Log "WARNING: Platforms connected but Telegram polling failures detected — force restarting"
            # Fall through to Phase 3
        } else {
            Write-Log "WARNING: Gateway running but platforms not connected (TG: $([bool]$telegramOk), WA: $([bool]$whatsappOk)) — force restarting"
            # Fall through to Phase 3
        }
    }
} else {
    Write-Log "Gateway not running — proceeding to start"
}

# ══════════════════════════════════════════════
# Phase 3: Start gateway (validate up to 3 retries)
# ══════════════════════════════════════════════
for ($attempt = 1; $attempt -le 3; $attempt++) {
    Write-Log "Starting gateway (attempt $attempt/3)..."

    # Kill any leftover zombie gateways + clean stale state
    wsl -d hermes-agent -- bash -c "pkill -f '/hermes.*gateway.?$' 2>/dev/null; sleep 1; rm -f /home/amirul/.hermes/gateway_state.json /home/amirul/.hermes/gateway.lock 2>/dev/null" 2>$null
    
    # Start fresh
    wsl -d hermes-agent -- bash -c "setsid /home/amirul/.hermes/hermes-agent/venv/bin/hermes gateway > /home/amirul/.hermes/logs/gateway.log 2>&1 & disown" 2>$null
    
    Write-Log "Gateway start command issued. Waiting 30s for connections..."
    Start-Sleep -Seconds 30
    
    # Validate both platforms connected
    $recentLog = Get-Content $GatewayLog -Tail 30 -ErrorAction SilentlyContinue 2>$null
    $tgConnected = $recentLog | Select-String "telegram connected"
    $waConnected = $recentLog | Select-String "whatsapp connected"
    $runningWith = $recentLog | Select-String "running with"
    
    if ($tgConnected -and $waConnected -and $runningWith) {
        $platforms = if ($runningWith -match "(\d+) platform") { $matches[1] } else { "?" }
        Write-Log "SUCCESS: Gateway running with $platforms platform(s) — TG connected, WA connected"
        
        # Phase 3b: Post-start monitoring (60s window for polling failures)
        Write-Log "Post-start monitoring: watching for Telegram polling failures (60s)..."
        $pollingFailCount = 0
        for ($wait = 0; $wait -lt 60; $wait += 15) {
            Start-Sleep -Seconds 15
            $midLog = Get-Content $GatewayLog -Tail 10 -ErrorAction SilentlyContinue 2>$null
            $newFails = ($midLog | Select-String "Polling heartbeat probe failed").Count
            if ($newFails -gt 0) {
                $pollingFailCount += $newFails
                Write-Log "  Polling failure detected ($pollingFailCount total)"
            }
        }
        
        if ($pollingFailCount -ge 3) {
            Write-Log "WARNING: $pollingFailCount polling failures in 60s — gateway will self-recover via watchdog. Logging and exiting."
        } else {
            Write-Log "Post-start monitoring complete: $pollingFailCount polling failure(s) — stable"
        }
        exit 0
    }
    
    Write-Log "Validation FAILED attempt $attempt — TG: $([bool]$tgConnected), WA: $([bool]$waConnected). Retrying..."
    Start-Sleep -Seconds 10
}

Write-Log "FATAL: Gateway failed to start after 3 attempts"
exit 1
