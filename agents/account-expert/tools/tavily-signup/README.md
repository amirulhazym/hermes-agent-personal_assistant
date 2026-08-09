# Tavily Signup Package (Windows Local)

Semi-automates the remaining seven Tavily signups. You still complete the real Turnstile and email verification manually.

## Important Security Rules

- Do **not** put this folder in OneDrive, Dropbox, Google Drive, Git, or any shared/synced directory.
- Recommended location: a private folder on `F:` such as `F:\HermesPrivate\tavily-signup`.
- Never paste API keys, QRYPTY access codes, or passwords into chat.
- `tavily_keys.json` contains raw API keys. Keep it local and private.
- This package does not upload keys to Hermes/VPS. Import keys later with a separate approved step.

## Accounts Covered

Only these seven pending accounts are included by default:

- owner@example.invalid
- owner@example.invalid
- owner@example.invalid
- owner@example.invalid
- owner@example.invalid
- owner@example.invalid
- owner@example.invalid

Already completed manually: current account, `owner@example.invalid`, `owner@example.invalid`. Their keys are not imported to the VPS by this package.

## Quick Start

Open PowerShell in this folder on Windows:

```powershell
.\Run-TavilySignup.ps1 -Browser chrome -Email owner@example.invalid
```

Pilot first with `owner@example.invalid`. After it stores a valid key locally, continue:

```powershell
.\Run-TavilySignup.ps1 -Browser chrome
```

Browser choices:

- `chrome` (recommended if installed)
- `msedge`
- `brave`
- `chromium` (requires Playwright Chromium fallback)
- omit `-Browser` to auto-pick Chrome, Edge, Brave, then Chromium

## What You Do Manually

For each signup:

1. Complete the Turnstile challenge in the headed browser.
2. Open QRYPTY mailbox at `https://qrypty.com`.
3. Use the **32-character Access Code** from the protected account CSV/package.
4. Click the Tavily verification link.
5. If auto key extraction fails, paste the Tavily API key into the hidden prompt.

The CSV `Password` field is for the Tavily account flow only unless independently confirmed otherwise. QRYPTY mailbox login uses the Access Code.

## Useful Commands

```powershell
# No signup; list account status only
.\.venv\Scripts\python.exe .\tavily_signup.py --list

# Counts only: total/completed/pending/failed
.\.venv\Scripts\python.exe .\tavily_signup.py --status

# Dry run one account
.\.venv\Scripts\python.exe .\tavily_signup.py --dry-run --email owner@example.invalid

# Retry one account
.\Run-TavilySignup.ps1 -Browser chrome -Email owner@example.invalid
```

## Output

`tavily_keys.json` is written atomically and contains:

- account email
- raw API key
- API-key fingerprint
- completion timestamp
- validation status

Raw keys are intentionally stored only in this local protected output file.

## Limitations

- No CAPTCHA bypass. You must solve Turnstile yourself.
- No VPS signup execution.
- Browser UI can change; if extraction fails, use hidden manual paste.
- Do not send `tavily_keys.json` to chat, Git, or the VPS until a separate import step is approved.
