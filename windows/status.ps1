#!/usr/bin/env pwsh
# Hermes Monitoring Dashboard
# Usage: .\status.ps1          — one-shot status
#        .\status.ps1 -watch   — auto-refresh every 60s
# Last updated: 2026-06-25

param([switch]$watch)

function Get-HermesStatus {
    Clear-Host
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

    Write-Host "╔════════════════════════════════════════════════╗" -ForegroundColor Cyan
    Write-Host "║        HERMES AGENT — STATUS DASHBOARD         ║" -ForegroundColor Cyan
    Write-Host "╠════════════════════════════════════════════════╣" -ForegroundColor Cyan
    Write-Host "║  Updated: $timestamp              ║" -ForegroundColor DarkGray
    Write-Host "╚════════════════════════════════════════════════╝" -ForegroundColor Cyan
    Write-Host ""

    # 1. Gateway Health
    Write-Host "═══ GATEWAY ═══" -ForegroundColor Yellow
    $gwRunning = wsl -d hermes-agent -- bash -c "pgrep -f 'venv/bin/hermes gateway' 2>/dev/null | wc -l" 2>$null
    $gwRunning = ($gwRunning -replace '\D', '0')
    if ([int]$gwRunning -ge 2) {
        Write-Host "  Status:    RUNNING ($gwRunning processes)" -ForegroundColor Green
    } elseif ([int]$gwRunning -eq 1) {
        Write-Host "  Status:    DEGRADED ($gwRunning process — WhatsApp bridge missing?)" -ForegroundColor Yellow
    } else {
        Write-Host "  Status:    DEAD" -ForegroundColor Red
    }

    # Platform connections (from gateway log)
    $lastTelegram = Select-String -Path "\\wsl.localhost\hermes-agent\home\amirul\.hermes\logs\gateway.log" -Pattern "telegram connected" 2>$null | Select-Object -Last 1
    $lastWhatsApp = Select-String -Path "\\wsl.localhost\hermes-agent\home\amirul\.hermes\logs\gateway.log" -Pattern "whatsapp connected" 2>$null | Select-Object -Last 1
    $lastRunning = Select-String -Path "\\wsl.localhost\hermes-agent\home\amirul\.hermes\logs\gateway.log" -Pattern "running with" 2>$null | Select-Object -Last 1

    if ($lastTelegram) { Write-Host "  Telegram:  CONNECTED — $($lastTelegram.Line.Substring(0,19))" -ForegroundColor Green }
    else { Write-Host "  Telegram:  NO RECENT CONNECTION" -ForegroundColor Red }
    if ($lastWhatsApp) { Write-Host "  WhatsApp:  CONNECTED — $($lastWhatsApp.Line.Substring(0,19))" -ForegroundColor Green }
    else { Write-Host "  WhatsApp:  NO RECENT CONNECTION" -ForegroundColor Red }
    Write-Host ""

    # 2. Cron Jobs
    Write-Host "═══ CRON ═══" -ForegroundColor Yellow
    $cronOutput = wsl -d hermes-agent -- bash -c "/home/amirul/.hermes/hermes-agent/venv/bin/hermes cron list 2>/dev/null" 2>$null
    if ($cronOutput) {
        $activeCount = ([regex]::Matches($cronOutput, "\[active\]")).Count
        Write-Host "  Active:    $activeCount jobs" -ForegroundColor $(if($activeCount -eq 7){'Green'}else{'Yellow'})
        $cronNames = [regex]::Matches($cronOutput, "Name:\s+(.+)") | ForEach-Object { $_.Groups[1].Value.Trim() }
        foreach ($name in $cronNames) {
            Write-Host "    └ $name" -ForegroundColor DarkGray
        }
    } else {
        Write-Host "  Cron data unavailable" -ForegroundColor Red
    }
    Write-Host ""

    # 3. Watchdog
    Write-Host "═══ WATCHDOG ═══" -ForegroundColor Yellow
    $wdLog = Get-Content "\\wsl.localhost\hermes-agent\home\amirul\.hermes\logs\watchdog.log" -Tail 3 2>$null
    if ($wdLog) {
        $lastRestart = $wdLog | Select-String "Restart" | Select-Object -Last 1
        if ($lastRestart) {
            Write-Host "  Last restart: $($lastRestart.Line)" -ForegroundColor Yellow
        } else {
            Write-Host "  Status:    Healthy (no recent restarts)" -ForegroundColor Green
        }
    } else {
        Write-Host "  Status:    No watchdog activity yet" -ForegroundColor DarkGray
    }
    Write-Host ""

    # 4. C Drive Space
    Write-Host "═══ DISK ═══" -ForegroundColor Yellow
    $c = Get-PSDrive C -ErrorAction SilentlyContinue
    if ($c) {
        $freeGB = [math]::Round($c.Free / 1GB, 1)
        $color = if ($freeGB -lt 3) { 'Red' } elseif ($freeGB -lt 5) { 'Yellow' } else { 'Green' }
        Write-Host "  C: drive:  $freeGB GB free" -ForegroundColor $color
    }
    $f = Get-PSDrive F -ErrorAction SilentlyContinue
    if ($f) {
        Write-Host "  F: drive:  $([math]::Round($f.Free/1GB,1)) GB free" -ForegroundColor DarkGray
    }
    Write-Host ""

    # 5. Recent Gateway Log
    Write-Host "═══ RECENT LOGS ═══" -ForegroundColor Yellow
    $lastLines = Get-Content "\\wsl.localhost\hermes-agent\home\amirul\.hermes\logs\gateway.log" -Tail 5 -ErrorAction SilentlyContinue
    if ($lastLines) {
        foreach ($line in $lastLines) {
            $short = $line.Substring(0, [Math]::Min(90, $line.Length))
            if ($line -match "error|fail|down|dead") {
                Write-Host "  $short" -ForegroundColor Red
            } elseif ($line -match "connected|running|ok") {
                Write-Host "  $short" -ForegroundColor Green
            } else {
                Write-Host "  $short" -ForegroundColor DarkGray
            }
        }
    }
    Write-Host ""

    # 6. Quick Actions
    Write-Host "═══ ACTIONS ═══" -ForegroundColor Yellow
    Write-Host "  Start gateway:  powershell -File F:\hermes\gateway-start.ps1" -ForegroundColor DarkGray
    Write-Host "  Tail logs:      wsl -d hermes-agent -- tail -f ~/.hermes/logs/gateway.log" -ForegroundColor DarkGray
    Write-Host "  Insights:       wsl -d hermes-agent -- bash -l -c 'hermes insights --days 7'" -ForegroundColor DarkGray
    Write-Host "  RUNBOOK:        F:\AI Prep\OVIS\Hermes Agent\MJay\RUNBOOK.md" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "Press Ctrl+C to exit (watch mode)" -ForegroundColor DarkGray
}

do {
    Get-HermesStatus
    if ($watch) {
        Start-Sleep -Seconds 60
    }
} while ($watch)
