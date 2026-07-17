#Requires -Version 7
param(
  [ValidateSet('PushStatus', 'PullInbox', 'PushOutbox', 'SyncOnce', 'Loop')]
  [string]$Action = 'SyncOnce',
  [string]$VpsHost = 'ubuntu@119.28.119.151',
  [string]$RemoteBridge = '/home/ubuntu/.hermes/web-operator/bridge',
  [string]$LocalBridge = '',
  [int]$Seconds = 0,
  [double]$Poll = 1.0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if (-not $LocalBridge) {
  $LocalBridge = Join-Path $env:USERPROFILE '.hermes\web-operator\bridge'
}

foreach ($name in @('devices', 'inbox', 'outbox', 'status', 'keys', 'consumed')) {
  $p = Join-Path $LocalBridge $name
  if (-not (Test-Path -LiteralPath $p)) {
    New-Item -ItemType Directory -Path $p -Force | Out-Null
  }
}

function Invoke-ScpDown([string]$Remote, [string]$Local) {
  & scp -o BatchMode=yes -o ConnectTimeout=20 "$VpsHost`:$Remote" $Local 2>$null
}
function Invoke-ScpUp([string]$Local, [string]$Remote) {
  & scp -o BatchMode=yes -o ConnectTimeout=20 $Local "$VpsHost`:$Remote" 2>$null
}
function Invoke-Ssh([string]$Cmd) {
  & ssh -o BatchMode=yes -o ConnectTimeout=20 $VpsHost $Cmd
}

function Sync-Once {
  # Ensure remote dirs
  Invoke-Ssh "mkdir -p $RemoteBridge/{devices,inbox,outbox,status,keys,consumed}"

  # Push local enrollment requests + status + outbox results (outbound from PC)
  Get-ChildItem -LiteralPath (Join-Path $LocalBridge 'devices') -Filter '*.request.json' -ErrorAction SilentlyContinue | ForEach-Object {
    Invoke-ScpUp $_.FullName "$RemoteBridge/devices/$($_.Name)"
  }
  Get-ChildItem -LiteralPath (Join-Path $LocalBridge 'status') -Filter '*.json' -ErrorAction SilentlyContinue | ForEach-Object {
    Invoke-ScpUp $_.FullName "$RemoteBridge/status/$($_.Name)"
  }
  Get-ChildItem -LiteralPath (Join-Path $LocalBridge 'outbox') -Filter '*.json' -ErrorAction SilentlyContinue | ForEach-Object {
    Invoke-ScpUp $_.FullName "$RemoteBridge/outbox/$($_.Name)"
  }

  # Pull inbox grants + VPS public key
  $tmp = Join-Path $env:TEMP ("wo-inbox-" + [guid]::NewGuid().ToString())
  New-Item -ItemType Directory -Path $tmp -Force | Out-Null
  try {
    & scp -o BatchMode=yes -o ConnectTimeout=20 "$VpsHost`:$RemoteBridge/inbox/*.json" "$tmp/" 2>$null
    Get-ChildItem -LiteralPath $tmp -Filter '*.json' -ErrorAction SilentlyContinue | ForEach-Object {
      if ($_.Name -notlike '*.done') {
        Copy-Item -LiteralPath $_.FullName -Destination (Join-Path $LocalBridge "inbox\$($_.Name)") -Force
      }
    }
    Invoke-ScpDown "$RemoteBridge/keys/vps_public.json" (Join-Path $LocalBridge 'keys\vps_public.json')
  } finally {
    Remove-Item -LiteralPath $tmp -Recurse -Force -ErrorAction SilentlyContinue
  }
}

if ($Action -eq 'SyncOnce' -or $Action -eq 'PushStatus' -or $Action -eq 'PullInbox' -or $Action -eq 'PushOutbox') {
  Sync-Once
  Write-Output "sync-ok local=$LocalBridge"
  exit 0
}

if ($Action -eq 'Loop') {
  $end = if ($Seconds -gt 0) { [datetime]::UtcNow.AddSeconds($Seconds) } else { [datetime]::MaxValue }
  while ([datetime]::UtcNow -lt $end) {
    Sync-Once
    Start-Sleep -Seconds $Poll
  }
  exit 0
}
