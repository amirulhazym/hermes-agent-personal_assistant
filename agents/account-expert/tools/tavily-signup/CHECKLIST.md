# Tavily Signup Checklist (No Secrets)

Use this as an operational checklist only. Do **not** write passwords, access codes, or API keys here.

## Pilot

Process first:

- `owner@example.invalid`

Command:

```powershell
.\Run-TavilySignup.ps1 -Browser chrome -Email owner@example.invalid
```

## Per Account Steps

1. Browser opens Tavily home/signup.
2. Confirm the account email shown by the script.
3. Complete Turnstile manually.
4. If Tavily asks for email verification:
   - Open `https://qrypty.com`.
   - Use the account's **32-character Access Code** from the protected CSV/package.
   - Do **not** use chat for access codes.
   - Click the matching Tavily verification link for the same account.
5. Return to PowerShell and press ENTER when prompted.
6. If key extraction fails, paste the Tavily key into the hidden prompt.
7. Confirm status with:

```powershell
.\.venv\Scripts\python.exe .\tavily_signup.py --status
```

## Remaining Seven Accounts

| # | Email | Status |
|---|-------|--------|
| 05 | owner@example.invalid | Pending |
| 10 | owner@example.invalid | Pending |
| 11 | owner@example.invalid | Pending |
| 12 | owner@example.invalid | Pending |
| 13 | owner@example.invalid | Pending |
| 14 | owner@example.invalid | Pending |
| 15 | owner@example.invalid | Pending |

## Notes

- The CSV Password field is not the QRYPTY mailbox credential unless independently confirmed.
- QRYPTY mailbox login uses the 32-character Access Code.
- Do not paste API keys into this checklist.
- Do not send keys to MJ, GPT, chat, Git, or VPS during signup.
