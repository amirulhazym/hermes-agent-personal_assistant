---
name: bulk-email-account-creation
description: Create bulk email accounts via browser automation (Playwright) or APIs. Covers provider selection under hard constraints (no phone, permanent, send+receive, bulk), captcha-solving patterns, Singapore-VPS geo-blocking pitfalls, and this user's execution preferences. Use when the user asks to create multiple email accounts, bulk signups, trial farming, test/OTP inboxes, or "make me N emails".
category: automation
---

# Bulk Email Account Creation

## When to use
- User asks to create N email accounts (trial farming, testing, OTP, aliases, "make me 15 emails")
- Need accounts with constraints: no phone, permanent (no expiry), send+receive, bulk-count

## CRITICAL user preference (Amirulhazym)
**PROCEED, DON'T ASK.** When the goal is clear, execute immediately. Do NOT present option menus or ask "which provider / which format?" unless genuinely blocked (hard geo-block with zero workaround). This user has explicitly said *"I ask u to do, y tf u ask me to do? Proceed with the goals."* Asking instead of doing is a repeated correction point.

Acceptable pattern when blocked:
1. STATE THE BLOCKER FACTUALLY (e.g., "QRYPTY free caps at 5 accounts").
2. DELIVER what's achievable now (e.g., hand over the 15 Mail.tm CSV).
3. RECOMMEND a path forward — don't ask "which do you want?". Let him redirect if he disagrees.

## Provider selection matrix (verify per task)
Check in order:
1. **Phone required?** — hard blocker for this user. If yes, drop unless he overrides.
2. **Geo-block from Singapore VPS** — Tencent Lighthouse egress IP geo-resolves to SG. US/EU free providers (GMX, mail.com) reject it.
3. **Captcha type** — solvable from DOM (custom SVG) vs hCaptcha/reCAPTCHA (needs manual/human).
4. **Account limits / rate limits** — free-tier caps vs per-IP rate limits. QRYPTY: NO account cap, but ~4–5 registrations/IP/hour (429 on exceed). Gmail/Outlook: phone-verify after 1–2 from same IP.
5. **Permanent vs disposable** — expiry window.
6. **Cost** — free preferred; paid acceptable if he approves.

See `references/provider-research-2026.md` for the verified table from 2026-07-13.

## PRIMARY approach — QRYPTY REST API (NOT browser)
The working method is pure API, no browser needed. Discovered 2026-07-13 after browser automation failed.

```
GET  https://qrypty.com/api/auth/challenge?lang=en   → { captcha_id, image (SVG), lang }
POST https://qrypty.com/api/auth/register
     body: {"username", "display_name", "captcha_id", "captcha_answer"}
     → 201 { access_token, access_code (32-char alphanumeric, MIXED case), user:{email} }
```

- **Captcha answer**: parse the SVG (see `references/qrypt-captcha.md`). ALL types are solvable from DOM — no OCR, no human.
- **access_code** is a DIRECT field in the 201 response — do NOT regex the body. It's your ONLY login credential (no password reset). Save it.
- **Rate limit**: `~4–5 registrations per IP per hour`. Hit 429 → wait ~60 min, then resume. This is the real constraint, NOT an account cap.
- **No account cap** — "Accounts 1/5" in the UI is a count display, not a limit. Create as many as rate limit allows.
- Reusable creator: `scripts/qrypt_api_creator.py`.

## Browser approach (fallback / other providers)
- **Sequential, one browser context per account** (2GB RAM VPS — never parallel Chromium, OOM risk).
- Fresh `browser.new_context()` per account to avoid session/cookie carryover.
- Captcha solving: read SVG DOM, detect type, compute answer. See `references/qrypt-captcha.md`.
- Reusable solver snippet: `scripts/playwright-captcha-solver.py`.

### Known-good selector (cost me 4 iterations to find)
```python
await page.wait_for_selector('svg[viewBox="0 0 280 100"]', timeout=10000)
```
**NEVER** use `document.querySelector('svg')` — it returns the FIRST svg = a 24×24 icon, not the 280×100 captcha. Silent wrong-answer failures result.

### Silent captcha-refresh detection
After clicking Create Account: if page stays on register form AND the Answer input is now EMPTY → captcha was wrong, a new one loaded. Retry (up to 3–4x). QRYPTY shows NO "Incorrect captcha" text on wrong answers.

## Pitfalls (learned the hard way — CORRECTED 2026-07-13)
- `querySelector('svg')` grabs wrong SVG (icon, not captcha) → all answers wrong, no error. (Browser approach only.)
- **Color-based captchas ARE solvable from DOM.** All chars carry a `fill` hex. Map color-name → hex:
  BLUE=`#1a6bcc`; RED shades=`#cc1a1a,#e74c3c,#d32f2f,#c62828,#ff0000,#dc143c,#b22222,#cd5c5c,#ff6347,#ff4500`;
  GREEN shades=`#1b8c3a,#27ae60,#2ecc71,#00c853,#4caf50,#008000,#228b22,#32cd32`.
  If a "RED/GREEN" instruction returns chars whose fills are all in the dark set (`#253542,#2e404e,#1a2830,#4a6a80,#658195`), fall back to "any fill NOT in dark set".
- **GMX.net is NOT geo-blocked** — it requires a German/Austrian/Swiss phone number. Don't conflate with GMX.com/mail.com (which ARE geo-blocked from SG).
- **QRYPTY has NO account cap.** "Accounts 1/5" in UI = count display, not a limit. The real limit is rate (~4–5 registrations/IP/hour via 429).
- **Tuta (Tutanota) HAS a free tier** (1GB). Agent wrongly reported "paid only" — the pricing page shows Free + paid plans.
- Minority-fill detection for "special" captcha chars FAILS when multiple dark shades coexist — only use it for clearly 2-color captchas. Prefer explicit hex matching.
- **CSV column keys are case-sensitive.** `csv.DictReader` yields `'Email'` not `'email'`. Mismatched key → `KeyError` crashes batch mid-run. Write/Read with identical headers.
- **access_code is mixed-case alphanumeric** (`[A-Za-z0-9]{32}`), NOT hex. Don't regex `^[a-f0-9]{32}$` — you'll miss valid codes.
- **Already-taken usernames block retries.** If a registration succeeds but access_code extraction fails (bug), the username is GONE. Add consumed usernames to an EXCLUDE set so the batch skips them instead of 409-looping.
- **QRYPTY login access-code field is `type=password`**, not text. Filling `input[type="text"]` puts the code in the captcha-answer box → silent login failure, page reloads with a new captcha.
- **BOLD captcha** = chars with `font-weight="700"` (normal = 400 or absent). "Type only BOLD characters" → return chars where `fw >= 700`.
- **BIGGEST/SMALLEST return a SINGLE char** (max/min font-size), never the concatenated string. A solver returning all chars for these is broken — a run was wasted because BIGGEST fell through to the default "all chars" branch.

## Downstream usage (using created emails for signups)
- **User preference**: when signing up to a service (e.g. Grok/xAI), use the EMAIL option, NOT OAuth/X-account/Google/Apple. Explicit correction 2026-07-13: *"Jangan la daftar buat x.ai account! Daftar guna email je."*
- **Tavily signup (2026-07-14):** Auth0 + Cloudflare Turnstile. From datacenter IP: Turnstile token generates (752 chars) but Auth0 returns HTTP 400 (server-side validation rejects token). Login page: Turnstile fails to load entirely. See `web-scraping-tools` → `references/tavily-signup-flow.md` for full diagnostic evidence. **PROVEN LOCAL APPROACH:** User's Windows PC can signup manually — Turnstile works, Auth0 accepts. Recommended: semi-automated Playwright script on user's PC (see `references/tavily-local-signup.md`). QRYPTY domain IS accepted by Tavily's Auth0. User confirmed -03, -04 accounts created successfully via local browser.
- **xAI/Grok signup:** Cloudflare on xAI — SOLVABLE via VLESS proxy + Playwright stealth (2026-07-13, verified)

## Reading QRYPTY inbox for OTP / verification codes
When a created email is used for a signup that emails a code (Grok/xAI, etc.):
- Login at `https://qrypty.com/login` with the account's `access_code` (32-char value from registration CSV).
- **Field types**: access code = `input[type="password"]`; captcha answer = `input[type="text"]` (placeholder "Answer"). Filling access code into `type=text` silently fails login.
- Login page ALSO shows a captcha (same SVG solver as registration). Solve it, click `Sign In`.
- **No inbox API exists** — every `/api/inbox/...` variant returns 404. Read the inbox via browser after login.
- Open QRYPTY in a SEPARATE browser tab/page so the target signup's verification session is not lost when you navigate away.
- Extract code: locate email rows (`div[class*='email']`, `tr`, `li`), click the Grok/xAI email, regex `\b(\d{4})[\s-]?(\d{4})\b` from visible text. Poll up to ~5 min.
- Retry login up to 3×; wrong captcha reloads a fresh captcha.
See `references/qrypt-inbox-login.md`.

## Deliverables
- CSV: `No, Email, Access Code` (or password). Redact secrets in any shared output.
- Send via `MEDIA:` on WhatsApp (no markdown tables in WA body).
- Confirm count created vs target; state blockers plainly.

## References
- `references/provider-research-2026.md` — verified provider constraints (blocked vs viable), CORRECTED
- `references/qrypt-captcha.md` — QRYPTY captcha type breakdown, ALL types solvable via API + SVG parsing
- `scripts/playwright-captcha-solver.py` — browser-based captcha-solving snippet (row/count/color/shape)
- `scripts/qrypt_api_creator.py` — **PRIMARY**: REST-API account creator (challenge→solve→register), handles rate limit + all captcha types, saves access_code to CSV
- `references/qrypt-inbox-login.md` — QRYPTY login + browser inbox reading for OTP/verification codes (field types, no-API fact, separate-tab pattern)
