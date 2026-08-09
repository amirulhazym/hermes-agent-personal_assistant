# Token Exchange Failure Patterns

## Pattern 1: PKCE + Confidential Client Conflict (FIXED 2026-07-15)

**Error:** `(invalid_grant) code_verifier or verifier is not needed`

**Root cause:** `google_auth_oauthlib`'s `Flow.from_client_secrets_file()` with `autogenerate_code_verifier=True` creates a PKCE challenge in the auth URL. Desktop app OAuth clients that have a `client_secret` are confidential clients — Google's token endpoint rejects PKCE when client_secret-based auth is already available.

**Symptom chain:**
1. `--auth-url` generates URL with `code_challenge=S256...` parameter
2. User authorizes, gets valid code
3. `--auth-code` exchange fails with "code_verifier or verifier is not needed"

**Permanent fix (applied 2026-07-15 to this VPS's setup.py):**
Edit `setup.py` to:
- Remove `autogenerate_code_verifier=True` from the `Flow.from_client_secrets_file()` call in `get_auth_url()`
- Remove `code_verifier=pending_auth["code_verifier"]` from the `Flow.from_client_secrets_file()` call in `exchange_auth_code()`
- Relax the `_load_pending_auth()` check to not require `code_verifier` field

After patching: generate fresh URL → user authorizes → exchange succeeds on first try.

**IMPORTANT:** The `google-workspace` bundled skill's SKILL.md still references "PKCE exchange" in Step 4 — that's outdated for Desktop app clients. The bundled skill is protected (Nous Research), so the agent must patch its own `setup.py` copy directly.

## Pattern 2: Expired Auth Code

**Error:** `(invalid_grant) Token has expired` or generic invalid_grant

**Cause:** Google OAuth codes expire in ~5 minutes. If user is slow to paste the code back, it becomes invalid.

**Fix:** Generate fresh URL, user re-authorizes immediately. No need to delete pending state (it reuses the stored state/redirect_uri).

## Pattern 3: State Mismatch

**Error:** `ERROR: OAuth state mismatch`

**Cause:** Multiple auth URLs generated for the same OAuth client in different browser tabs. Each `--auth-url` generates a unique state, but only the last one is saved to `google_oauth_pending.json`.

**Fix:** Always use the LATEST generated URL. If multiple were generated, clear state and do one clean cycle.

## Pattern 4: Scope Mismatch

**Warning:** `Token missing some Google Workspace scopes`

**Cause:** User deselected some scopes during consent screen. Works fine but certain API calls will fail.

**Fix:** Re-run full OAuth cycle, ensure all desired scopes are checked during consent.

## Safe Reset Sequence

Complete clean-slate reauth (no PKCE, Desktop app client_secret auth):

```bash
rm -f ~/.hermes/google_oauth_pending.json ~/.hermes/google_token.json
python3 $HOME/.hermes/skills/productivity/google-workspace/scripts/setup.py --auth-url
```

If exchange still fails after re-auth, verify setup.py has `autogenerate_code_verifier` removed (patched 2026-07-15 for this VPS).
