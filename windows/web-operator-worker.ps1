#Requires -Version 7
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('Enroll', 'Run', 'Stop', 'Once')]
  [string]$Action,

  [string]$VpsHost = 'ubuntu@119.28.119.151',
  [string]$RemoteHermes = '/home/ubuntu/.hermes',
  [string]$LocalRoot = '',
  [string]$PythonExe = 'python',
  [double]$Seconds = 90,
  [double]$Poll = 1.0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$cua = 'C:\Users\amiru\AppData\Local\Programs\Cua\cua-driver\bin\cua-driver.exe'
if (-not $LocalRoot) {
  $LocalRoot = Join-Path $env:USERPROFILE '.hermes\web-operator'
}
$LocalBridge = Join-Path $LocalRoot 'bridge'
$SyncScript = Join-Path $PSScriptRoot 'web-operator-bridge-sync.ps1'
$RepoScripts = Join-Path (Split-Path $PSScriptRoot -Parent) 'scripts'

function Write-Status([string]$Message) {
  Write-Output ("[web-operator-worker] " + $Message)
}

function Ensure-Cua {
  if (-not (Test-Path -LiteralPath $cua)) { throw "cua-driver missing at $cua" }
  $st = (& $cua status 2>&1 | Out-String)
  if ($st -match 'not running') {
    Start-Process -FilePath $cua -ArgumentList @('serve') -WindowStyle Hidden | Out-Null
    Start-Sleep -Seconds 2
  }
  try { & $cua autostart enable 2>&1 | Out-Null } catch { }
}

if ($Action -eq 'Stop') {
  Write-Status 'Stopping local cua-driver serve'
  if (Test-Path -LiteralPath $cua) { & $cua stop 2>&1 | Out-String | Write-Output }
  exit 0
}

Ensure-Cua
& $cua status 2>&1 | Out-String | Write-Output

# Ensure local package import path
$env:PYTHONPATH = if ($env:PYTHONPATH) { "$RepoScripts\..;$env:PYTHONPATH" } else { "$RepoScripts\.." }
# Prefer repo root that contains scripts/web_operator
$RepoRoot = Split-Path $PSScriptRoot -Parent
$env:PYTHONPATH = "$RepoRoot;$env:PYTHONPATH"

if ($Action -eq 'Enroll' -or $Action -eq 'Run' -or $Action -eq 'Once') {
  New-Item -ItemType Directory -Path $LocalBridge -Force | Out-Null
  # Generate enrollment + one heartbeat via worker-loop for 3s
  & $PythonExe -m scripts.web_operator worker-loop --bridge-root $LocalBridge --seconds 2 --poll 0.5 --cua-exe $cua
  # Sync up enrollment request + status
  & $SyncScript -Action SyncOnce -VpsHost $VpsHost -LocalBridge $LocalBridge -RemoteBridge "$RemoteHermes/web-operator/bridge"

  # Enroll on VPS using request file
  $req = Get-ChildItem -LiteralPath (Join-Path $LocalBridge 'devices') -Filter '*.request.json' | Select-Object -First 1
  if ($req) {
    $payload = Get-Content -LiteralPath $req.FullName -Raw | ConvertFrom-Json
    $deviceId = $payload.device_id
    $pub = $payload.public_key_b64
    $enrollCmd = "export PYTHONPATH=$RemoteHermes; /home/ubuntu/.hermes/hermes-agent/venv/bin/python -m scripts.web_operator bridge-enroll --config $RemoteHermes/web-operator/config.yaml --device-id $deviceId --public-key-b64 $pub --label windows-pc"
    & ssh -o BatchMode=yes -o ConnectTimeout=20 $VpsHost $enrollCmd
    Write-Status "enrolled device_id=$deviceId"
  }
}

if ($Action -eq 'Enroll') {
  Write-Status 'Enroll complete (outbound mailbox + VPS device record)'
  exit 0
}

if ($Action -eq 'Once' -or $Action -eq 'Run') {
  $deadline = [datetime]::UtcNow.AddSeconds($Seconds)
  while ([datetime]::UtcNow -lt $deadline) {
    & $SyncScript -Action SyncOnce -VpsHost $VpsHost -LocalBridge $LocalBridge -RemoteBridge "$RemoteHermes/web-operator/bridge"
    & $PythonExe -m scripts.web_operator worker-loop --bridge-root $LocalBridge --seconds 2 --poll 0.5 --cua-exe $cua
    & $SyncScript -Action SyncOnce -VpsHost $VpsHost -LocalBridge $LocalBridge -RemoteBridge "$RemoteHermes/web-operator/bridge"
    if ($Action -eq 'Once') { break }
    Start-Sleep -Seconds $Poll
  }
  Write-Status 'worker cycle done'
  exit 0
}
