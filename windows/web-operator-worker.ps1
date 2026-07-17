#Requires -Version 7
param(
  [Parameter(Mandatory = $true)]
  [ValidateSet('Enroll', 'Run', 'Stop')]
  [string]$Action,

  [string]$ConfigPath = '',
  [string]$PythonExe = 'python',
  [string]$PackagePath = ''
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Write-Status([string]$Message) {
  Write-Output ("[web-operator-worker] " + $Message)
}

if ($Action -eq 'Enroll') {
  Write-Status 'Enroll creates local device identity only. No inbound ports.'
  Write-Status 'Run Python grant enrollment after package deploy (explicit approval required).'
  exit 0
}

if ($Action -eq 'Stop') {
  Write-Status 'Stop is advisory in this scaffold; production stop uses signed revoke/stop messages.'
  exit 0
}

if ($Action -eq 'Run') {
  if (-not $PackagePath) {
    throw 'PackagePath required for Run'
  }
  Write-Status 'Outbound-only worker run scaffold. Connects to VPS control plane when configured.'
  Write-Status 'Does not open public listeners. Does not accept arbitrary shell from VPS.'
  & $PythonExe -c "print('web-operator worker scaffold ready')"
  exit $LASTEXITCODE
}
