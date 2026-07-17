#Requires -Version 7
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$cua = 'C:\Users\amiru\AppData\Local\Programs\Cua\cua-driver\bin\cua-driver.exe'
$out = [ordered]@{
  timestamp = (Get-Date).ToString('o')
  cua_driver_present = (Test-Path -LiteralPath $cua)
  cua_driver_version = $null
  cua_daemon = $null
  brave_running = [bool](Get-Process -Name brave -ErrorAction SilentlyContinue)
  inbound_listener = $false
}

if ($out.cua_driver_present) {
  try { $out.cua_driver_version = (& $cua --version 2>$null | Out-String).Trim() } catch { $out.cua_driver_version = 'error' }
  try { $out.cua_daemon = (& $cua status 2>$null | Out-String).Trim() } catch { $out.cua_daemon = 'error' }
}

$out | ConvertTo-Json -Depth 4
