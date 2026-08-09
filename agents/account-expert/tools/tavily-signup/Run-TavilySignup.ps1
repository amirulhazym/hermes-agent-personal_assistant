param(
  [ValidateSet('auto','chrome','msedge','brave','chromium')]
  [string]$Browser = 'auto',
  [string]$Email = '',
  [switch]$Status,
  [switch]$List,
  [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $Root
$env:PIP_CACHE_DIR = Join-Path $Root '.pip-cache'
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path $Root '.playwright-browsers'

if ($Root -match '^(?i)c:\\') {
  throw 'Do not run this package from C:. Move it to a private folder on F: first.'
}

if ($Root -match '(?i)(OneDrive|Dropbox|Google Drive|\\.git)') {
  throw 'Do not run this package inside synced folders or Git repos.'
}

$Python = Get-Command py -ErrorAction SilentlyContinue
if ($Python) {
  $PyExe = 'py'
  $PyBaseArgs = @('-3')
} else {
  $Python = Get-Command python -ErrorAction SilentlyContinue
  if (-not $Python) { throw 'Python 3 is required. Install Python, then re-run this script.' }
  $PyExe = 'python'
  $PyBaseArgs = @()
}

$Venv = Join-Path $Root '.venv'
if (-not (Test-Path -LiteralPath $Venv)) {
  & $PyExe @PyBaseArgs -m venv $Venv
}

$VenvPython = Join-Path $Venv 'Scripts\python.exe'
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -r (Join-Path $Root 'requirements.txt')

if ($Browser -eq 'chromium') {
  & (Join-Path $Venv 'Scripts\playwright.exe') install chromium
}

$ArgsList = @('tavily_signup.py', '--browser', $Browser)
if ($Email) { $ArgsList += @('--email', $Email) }
if ($Status) { $ArgsList += '--status' }
if ($List) { $ArgsList += '--list' }
if ($DryRun) { $ArgsList += '--dry-run' }

& $VenvPython @ArgsList
