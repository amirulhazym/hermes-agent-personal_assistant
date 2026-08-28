# ChatGPT Plus via Hermes `openai-codex`

Session-derived reference: 2026-07-28. This is a provider-integration pattern, not a claim that any particular model slug is permanently available.

## Scope

Use this for a ChatGPT Plus/Pro subscription used by Hermes **without an OpenAI API key**. The correct Hermes provider is the built-in `openai-codex` OAuth provider. Do not model this as a third-party custom provider.

## Authentication flow

1. Run the built-in Hermes login flow, normally:

   ```bash
   hermes auth add openai-codex
   ```

2. The implementation requests a device code from:

   ```text
   POST https://auth.openai.com/api/accounts/deviceauth/usercode
   JSON: {"client_id": <Hermes Codex OAuth client id>}
   ```

3. Show the user the returned `user_code` and direct them to:

   ```text
   https://auth.openai.com/codex/device
   ```

4. If ChatGPT shows an error saying device code authorization must be enabled, the user must enable **device code authorization for Codex** in ChatGPT Security Settings, then request a fresh code. Do not reuse the old code.

5. Poll the device token endpoint with the returned `device_auth_id` and `user_code`:

   ```text
   POST https://auth.openai.com/api/accounts/deviceauth/token
   JSON: {"device_auth_id": <id>, "user_code": <code>}
   ```

   Treat HTTP 403/404 as pending during the documented polling window; do not treat those responses as credential failure immediately.

6. Exchange the returned `authorization_code` and `code_verifier` at:

   ```text
   POST https://auth.openai.com/oauth/token
   grant_type=authorization_code
   code=<authorization_code>
   redirect_uri=https://auth.openai.com/deviceauth/callback
   client_id=<Hermes Codex OAuth client id>
   code_verifier=<code_verifier>
   ```

7. Save the resulting OAuth credentials through Hermes auth persistence. Never print access or refresh tokens in the report.

## Account prerequisite

The device-code page may require the account-level ChatGPT Security setting before it accepts the code. The browser login page can otherwise show a phone-number step followed by an error. This is an account setting issue, not proof that the OAuth endpoint or Hermes provider is broken.

## Provider/config distinction

`openai-codex` is built in:

- It belongs in `model.provider`, not necessarily under `providers:`.
- Its built-in overlay uses the Codex transport and the backend URL `https://chatgpt.com/backend-api/codex`.
- It does **not** require the custom-provider plugin + `providers:` dual registration used by FTF/A6API-style endpoints.
- A stale `model.base_url` from another provider can conflict with runtime resolution; clear it or set it to the provider's intended base URL before restarting the gateway.

Expected config shape:

```yaml
model:
  provider: openai-codex
  default: <model returned by live catalog>
  base_url: ""
```

## Token-conservative verification matrix

Run the cheapest checks in this order:

1. **Auth state:** `hermes auth list` shows an `openai-codex` OAuth credential.
2. **Live model catalog:** perform the provider's model metadata GET. This uses no generation tokens. Do not assume a remembered/static model list is current.
3. **One minimal inference per required model:** ask each model to return a one-word response. Record the raw response and session ID.
4. **Picker/resolver check without inference:** call the same Python model-switch/discovery functions used by `/model`; verify provider slug, model IDs, API mode, and base URL.
5. **Gateway restart only after config changes:** restart once, then verify the new PID, service state, bridge/readiness, and loaded config.
6. **User-visible Telegram/WhatsApp `/model` test:** distinguish backend picker generation from actual message delivery/rendering. Do not claim the latter unless it was observed.

Avoid multi-turn, tool-calling, verbose, and stress tests unless the user explicitly approves them; subscription limits make those unnecessary during initial setup.

## Live catalog and `/model` evidence boundary

Hermes's Codex model discovery should use the authenticated live endpoint when a runtime OAuth token is available, then fall back to local/config/static sources only when live discovery fails. A model appearing in a static list is not proof that the account can use it.

The gateway `/model` implementation has two paths:

- interactive platforms call `list_picker_providers(...)` and then `adapter.send_model_picker(...)`;
- text fallback calls `list_authenticated_providers(...)` and formats provider/model lines.

For a strong non-token-consuming check, execute both discovery functions and inspect the `openai-codex` row. Then separately label actual Telegram/WhatsApp receipt as user-visible evidence still pending if no message was sent.

## Usage and quota checks

For the user's operational checks after setup, separate three scopes:

1. **Selected provider/model:** `/status` in the gateway or `hermes status --all` on the VPS. `OpenAI API: ✗` is expected when using Plus OAuth; `OpenAI Codex: ✓ logged in` is the relevant auth signal.
2. **Current session + server-side subscription limits:** `/usage`. The handler reports Hermes session token counters and also fetches the authenticated Codex account usage snapshot. For the built-in backend, the account usage route resolves to `/wham/usage`. This is a metadata GET and consumes no generation tokens.
3. **Historical Hermes activity:** `/insights 1` or `hermes insights --days 1 --source telegram`. This is local session-DB analytics, not a direct ChatGPT Plus quota meter. It reports recorded model/session/token/tool activity.

Treat these as separate evidence domains. The provider may return only a primary usage window (displayed as `Session`) and omit a secondary/weekly window; report that omission as a data gap rather than inferring a weekly percentage. Never convert Hermes-local token totals into Plus quota/credits without a provider-documented mapping. If `hermes insights` exceeds a short shell timeout on a populated database, retry with a longer timeout before treating it as unavailable.

## Reporting rules

Report these separately:

- **Inference proven:** raw response + session ID for each model.
- **Catalog proven:** direct live metadata response and exact model IDs.
- **Resolver proven:** `/model` backend returns the provider row and selection resolver accepts each model.
- **Gateway proven:** post-restart PID/service/bridge/readiness evidence.
- **UI receipt:** only proven after a real `/model` message is observed.

Do not say “all models work” based only on catalog visibility. Do not say “Telegram `/model` works” based only on Python picker output.

## Session-specific evidence

The 2026-07-28 test used three minimal `reply OK` calls:

- `gpt-5.6-luna` → `OK`, session `20260728_204922_c5de01`
- `gpt-5.6-terra` → `OK`, session `20260728_205819_371a20`
- `gpt-5.6-sol` → `OK`, session `20260728_205821_c217a5`

The live catalog returned six IDs at that time: `gpt-5.6-sol`, `gpt-5.6-terra`, `gpt-5.6-luna`, `gpt-5.5`, `gpt-5.4`, and `gpt-5.4-mini`. Treat these as historical evidence for that account/time, not a permanent catalog guarantee.

## Replacing a dead entry: add-before-remove + timeout reality (verified 2026-08-25)

When a user reports "one of my Codex accounts no longer works, can you re-auth with the working one?", the safe replacement sequence is:

1. **Inventory the pool first, never assume which entry is dead.**
   ```python
   import json
   pool = json.load(open("/home/ubuntu/.hermes/auth.json"))["credential_pool"]
   for e in pool.get("openai-codex", []):
       print(e.get("id"), e.get("label"),
             "auth=", e.get("auth_type"),
             "src=", e.get("source"),
             "token_len=", len(e.get("access_token","")))
   ```
   Pool entries are dicts with fields `id`, `label`, `auth_type`, `source`, `access_token`, and optionally `last_error_reset_at` / `expires_at`. The `label` is the only human-meaningful identifier. The `id` is a short hash; do not match on it across sessions.

2. **Add the new account first, prune later.** The credential pool rotates automatically when one entry fails (401/402/429/usage-limit). Adding a healthy entry alongside the suspect one is safe — the gateway tries the higher-priority entry first and rotates to the new one on failure. **Removing a suspected-dead entry before a working replacement is verified is a one-way door**: if the guess was wrong, the user has zero Codex access until re-auth completes.

3. **Use a non-default label** with `hermes auth add openai-codex --label <name>`. Follow the existing pattern (the built-in defaults are `account2`, `device_code`); use `account3`, `account4`, ... or a descriptive tag like `work-shared` if multiple people share the same Hermes install.

4. **Device-code timeout is the silent failure mode (live-failed 2026-08-25).** The CLI prints `https://auth.openai.com/codex/device` + a code (e.g. `B76A-C0886`), then polls the token endpoint in a foreground loop. The user must complete the browser-side approval before the device code expires — OpenAI's window is roughly 5–15 minutes, and the abort presents as `httpx.ReadTimeout` from `_codex_device_code_login` in `hermes_cli/auth.py:8202`, called from `auth_commands.py:311`. **Critical pitfall: the process exits with code 0 even on timeout, with a stack trace appended to stdout/stderr.** The pool is unchanged on a timeout — there is no partial write. Re-run the command for a fresh code; never try to reuse an expired one.

5. **Run the add in the background, not the foreground.** Default `terminal()` foreground will hit its 60s/180s timeout while polling — the auth flow is designed to wait for the user, not to fail fast. Use:
   ```python
   terminal(
       command="hermes auth add openai-codex --label account3 --no-browser",
       background=True,
       notify_on_complete=True,
   )
   ```
   `--no-browser` keeps the auto-launch out of the way; the headless pattern is the safe default. Read the URL + code from the first `process(action="poll")` preview. Relay both to the user immediately and tell them to approve in the same turn — every minute between code-issue and approve shrinks the available window.

6. **Verify before claiming success. Exit code 0 is not enough.** Run the same `auth.json` inventory snippet from step 1 and report the measured count:
   - Before: 2 entries (e.g. `account2`, `device_code`)
   - After a successful add: 3 entries, new label present
   - After a timeout: still 2 entries, **even though the CLI printed exit 0**
   A failed flow leaves zero footprint in `auth.json`; that is the authoritative proof.

7. **Removing a confirmed-dead entry** (only after step 6 + the new account is verified):
   ```bash
   hermes auth remove openai-codex --label <dead-label>
   ```
   The remove command keys by `id`, `label`, or `index`; prefer `--label` for readability. Re-run the inventory snippet to confirm the count dropped.

## Hand-off: "teach me hands-on" pattern (verified 2026-08-25)

When the user transitions mid-session from "do it for me" to "teach me hands-on so I can do it myself" (phrasing observed: *"macam mana aku nak work on it dari first step sampai model call test?"*), the working delivery shape is:

- **Cheat-sheet file via `MEDIA:`** — short, location-anchored: real file paths, real line numbers in `~/.hermes/config.yaml` (e.g. `providers:` at line 15, `model_aliases:` at line 837), exact command shape. This is the artifact the user re-opens in their terminal.
- **Lab manual as a Google Doc** — same content, restructured for a fresh session to execute from: verdict-first sections, tables for every measured number, troubleshooting table at the end. Use the `/gdocs` pipeline (`md2ops.py` → `format_doc_v2.py` → `verify_doc.py`); verify must report PASS before delivery.
- **Glossary gap to address explicitly**: "where each piece lives" — the user consistently wants to know *where to look*, not just *what to run*. A 5–7 row "file path → purpose" table in both the cheat sheet and the doc addresses this without prose. They re-use this when the next provider appears.
- **C1 false-positive pitfall in `/gdocs`**: structural section dividers (`## 4. Step 0-2` immediately followed by `### Step 0`) trigger C1 ("heading has no content") in `verify_doc.py`. Fix: insert a one-sentence intro paragraph between the structural heading and its first sub-heading. Re-render (the renderer clears the body first, so re-runs repair instead of duplicating).

Do not try to do everything in chat — the user wants a take-away artefact they can follow without the agent present. Sending `MEDIA:` and the doc URL together is the right close.
