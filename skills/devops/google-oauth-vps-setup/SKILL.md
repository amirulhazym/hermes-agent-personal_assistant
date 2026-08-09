---
name: google-oauth-vps-setup
description: "End-to-end Google Cloud OAuth setup on a headless VPS: GCP project security (no billing), API enablement, OAuth consent screen, Desktop app client, token exchange via setup.py, and gws CLI install. Covers common failure modes (PKCE mismatches, expired codes) and billing safety."
version: 1.0.0
platforms: [linux, macos]
tags: [gcp, google-cloud, oauth, google-workspace, gws, billing-safety]
---

# Google OAuth VPS Setup

Setting up Google Workspace APIs (Gmail, Drive, Sheets, Docs) on a headless Hermes VPS.

## 1. Billing Safety (CRITICAL — do not skip)

User has trauma from unexpected Gemini API billing (self-reported). This MUST be treated seriously.

**Rules:**
- New GCP projects default to **no billing account** — keep it that way
- WITHOUT a linked billing account, Google CANNOT charge for API usage
- Workspace APIs (Gmail/Drive/Sheets/Docs) are free, no billing model
- Exceed quota without billing → get `429 Too Many Requests` error, NOT a bill
- NEVER enable billing on the project
- Verify: https://console.cloud.google.com/billing/projects → confirm column shows "Billing is disabled"

**If user has past billing trauma:**
1. Acknowledge it directly — don't dismiss
2. Show explicit evidence from official docs
3. Walk them through the billing projects page to verify

## 2. Create GCP Project & Enable APIs

Direct links for mobile (user's preferred mode):

| API | Link |
|-----|------|
| Gmail | `https://console.cloud.google.com/apis/library/gmail.googleapis.com` |
| Drive | `https://console.cloud.google.com/apis/library/drive.googleapis.com` |
| Sheets | `https://console.cloud.google.com/apis/library/sheets.googleapis.com` |
| Docs | `https://console.cloud.google.com/apis/library/docs.googleapis.com` |

## 3. OAuth Consent Screen

https://console.cloud.google.com/apis/credentials/consent

- App name: e.g. "Hermes Agent"
- User type: **External**
- User support email: user's Google email
- Developer contact: user's Google email
- Test users: add the Google account(s) that will authenticate
- Scopes page: skip (handled during auth URL generation by setup.py)

## 4. Create OAuth Client

https://console.cloud.google.com/apis/credentials

- Type: **Desktop app** (the correct type for Hermes/gws CLI)
- Download JSON → save to `~/.hermes/google_client_secret.json`
- Set file permissions: `chmod 600 ~/.hermes/google_client_secret.json`

## 5. Install gws CLI (optional)

```bash
npm install -g @googleworkspace/cli --prefix ~/.local
# Package is @googleworkspace/cli, NOT @google/gws
# Add ~/.local/bin to PATH
```

Verify: `gws --version`

## 6. Token Exchange via setup.py

```bash
GSETUP="python3 $HOME/.hermes/skills/productivity/google-workspace/scripts/setup.py"

# Step A: Load client secret
$GSETUP --client-secret ~/.hermes/google_client_secret.json

# Step B: Generate auth URL (saves OAuth state to google_oauth_pending.json)
$GSETUP --auth-url
# → Send URL to user. User opens in browser, authorizes, gets redirected to
#   http://localhost:1/?code=4/... (page fails to load — expected)
# → User copies full redirect URL and shares the code

# Step C: Exchange code for token
$GSETUP --auth-code "4/0AXEQxIB..."
# → Token saved to ~/.hermes/google_token.json

# Step D: Verify
$GSETUP --check
```

**Important:** The `setup.py` script does NOT support `--services` flag despite what the google-workspace SKILL.md says. Scopes are hardcoded in the script (gmail read/send/modify, calendar, drive, contacts, spreadsheets, documents). To use a subset, the user must manually deselect scopes during consent screen.

## 7. Token Exchange Troubleshooting

### "code_verifier or verifier is not needed" (FIXED 2026-07-15)

**Root cause:** Desktop app OAuth clients with client_secret should NOT use PKCE. The setup.py script had `autogenerate_code_verifier=True` which conflicts with client_secret-based auth.

**Permanent fix (applied 2026-07-15 to this VPS):**
Patched `setup.py` to remove `autogenerate_code_verifier=True` and the `code_verifier` exchange parameter. No more PKCE — client_secret handles auth.

**If re-patching is needed:** Load `google-oauth-vps-setup` skill and read `references/token-exchange-patterns.md` for exact changes.

### "The code may have expired"

Auth codes expire in ~5 minutes. Regenerate URL and have user re-authorize immediately.

### "Token exchange failed" with invalid_grant

Could mean:
1. Code expired → regenerate URL
2. PKCE state corrupted → delete `google_oauth_pending.json`, retry
3. OAuth client misconfigured → verify Desktop app type in GCP Console

## 8. User Preferences (captured from this user)

- **DO NOT** re-suggest options after user says "proceed" — execute
- **DO NOT** offer alternatives once user decided. User finds it frustrating ("shibau")
- When unsure, check official docs — "jangan palatao" (don't bluff)
- Acknowledge billing trauma seriously, with evidence
- User works mobile (Android) for GCP admin — use direct links, not CLI
- User has /personality caveman set — keep responses terse
- User communicates in Manglish — mirror the mix

## 9. References

See `references/token-exchange-patterns.md` for common failure patterns.
