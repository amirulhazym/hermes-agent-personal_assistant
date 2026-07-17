#Requires -Version 7
param(
  [ValidateSet('Install', 'Uninstall', 'Run')]
  [string]$Action = 'Install',
  [string]$TaskName = 'Hermes Web Operator PC Worker',
  [int]$RestartDelaySeconds = 5
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$WorkerScript = Join-Path $PSScriptRoot 'web-operator-worker.ps1'
$LauncherScript = $PSCommandPath
$PowerShellExe = Join-Path $PSHOME 'pwsh.exe'

if (-not (Test-Path -LiteralPath $WorkerScript)) {
  throw "Worker script missing at $WorkerScript"
}
if (-not (Test-Path -LiteralPath $PowerShellExe)) {
  throw "PowerShell executable missing at $PowerShellExe"
}

function Quote-Argument([string]$Value) {
  return '"' + $Value.Replace('"', '\"') + '"'
}

function New-WorkerAction {
  $arguments = '-NoProfile -ExecutionPolicy Bypass -File ' + (Quote-Argument $LauncherScript) +
    ' -Action Run'
  return New-ScheduledTaskAction -Execute $PowerShellExe -Argument $arguments
}

function Install-WorkerTask {
  $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited
  $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
  $trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
  Register-ScheduledTask -TaskName $TaskName -Action (New-WorkerAction) -Trigger $trigger `
    -Principal $principal -Settings $settings -Description 'Outbound-only Hermes PX-1b Windows mailbox worker.' `
    -Force | Out-Null
  Write-Output "registered task=$TaskName"
}

function Uninstall-WorkerTask {
  Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
  Write-Output "unregistered task=$TaskName"
}

if ($Action -eq 'Install') {
  Install-WorkerTask
  exit 0
}

if ($Action -eq 'Uninstall') {
  Uninstall-WorkerTask
  exit 0
}

while ($true) {
  try {
    & $WorkerScript -Action Run -Seconds 0
    if ($LASTEXITCODE -ne 0) {
      Write-Warning "worker exited with code $LASTEXITCODE"
    }
  } catch {
    Write-Warning ("worker failed: " + $_.Exception.Message)
  }
  Start-Sleep -Seconds $RestartDelaySeconds
}
