# QRYPTY Inbox Login & OTP Reading

How to read a verification/OTP code from a QRYPTY mailbox after creating the account.
Needed when a created email is used for a signup that emails a code (Grok/xAI, etc.).

## Login flow
- URL: `https://qrypty.com/login`
- **Access code field = `input[type="password"]`** (the 32-char `access_code` from the registration CSV).
- **Captcha answer field = `input[type="text"]`** (placeholder "Answer").
- Login page shows the SAME SVG captcha as registration. Solve it with the same solver
  (BIGGEST/SMALLEST/BOLD/GREEN/BLUE/TOP/BOTTOM/SUM/CIRCLES — see `qrypt-captcha.md`).
- Click `Sign In` (exact text). On success the inbox view loads (URL contains `inbox`
  or an "Inbox" element appears). Wrong captcha → page reloads with a fresh captcha.

## CRITICAL field-type pitfall
Filling `input[type="text"]` with the access code puts it in the CAPTCHA-ANSWER box.
Login silently fails, page reloads with a new captcha, and you loop. Always target
`input[type="password"]` for the access code.

## No inbox API — use the browser
Every `/api/inbox/...` variant (tested: `/api/inbox/{user}`, `/api/inbox?username=`,
`/api/messages/{user}`, `/api/mailbox/{user}`, `/api/email/{user}/inbox`, `/api/user/{user}/messages`)
returns **404**. There is no programmatic inbox endpoint. Read it via the browser after login.

## Separate-tab pattern (preserves signup session)
When reading the code mid-signup, open QRYPTY in a NEW `context.new_page()` (or new tab),
NOT by navigating the signup page away. Navigating the signup page to `/login` destroys the
verification session state (the 8-box code entry resets).

```python
def get_code(browser, context):
    page = context.new_page()
    Stealth().apply_stealth_sync(page)
    for attempt in range(3):
        page.goto("https://qrypty.com/login", wait_until="domcontentloaded", timeout=30000)
        time.sleep(4)
        if "inbox" in page.url or page.locator("text=Inbox").count() > 0:
            break
        page.fill('input[type="password"]', ACCESS_CODE)
        time.sleep(1)
        svg = page.inner_html('svg[viewBox="0 0 280 100"]')
        page.fill('input[type="text"]', solve_captcha(svg))
        time.sleep(1)
        page.get_by_text("Sign In", exact=True).first.click()
        time.sleep(5)
        if "inbox" in page.url or page.locator("text=Inbox").count() > 0:
            break
    for email in page.locator("div[class*='email'], div[class*='message'], tr, li, .mail-item").all():
        try:
            text = email.inner_text()
            if "grok" in text.lower() or "xai" in text.lower() or "verif" in text.lower():
                email.click(); time.sleep(3)
                visible = page.inner_text("body")
                m = re.search(r'\b(\d{4})[\s-]?(\d{4})\b', visible)
                return m.group(1) + m.group(2) if m else None
        except: continue
    page.close()
    return None
```

## Code extraction
- xAI/Grok sends an 8-digit code (e.g. `48456360`). Regex: `\b(\d{4})[\s-]?(\d{4})\b`.
- Arrives within ~1 min. Poll the inbox up to ~5 min (re-login each poll if session expires).
- The email subject looks like `WRU-XXXX xAI confirmation code`.

## BOLD captcha detail (login + registration)
`font-weight="700"` = bold; `400` or absent = normal. "Type only BOLD characters" →
return chars where `fw >= 700`. Discovered because the solver initially missed BOLD and
the login captcha failed.
