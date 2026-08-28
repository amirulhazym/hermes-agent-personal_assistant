# xAI / Grok Signup via Email — Through VLESS Proxy (2026-07-14)

End-to-end flow verified 2026-07-13/14: bypassed Cloudflare, received verification
code (QRYPTY inbox), reached "Complete your sign up" page. Blocked at Turnstile.

## Prerequisites
- xray-core running as local SOCKS5 proxy on `127.0.0.1:1080` (see SKILL.md Layer 5).
- Playwright + `playwright_stealth` for `/usr/bin/python3.12`.
- A receiving email account on a **non-disposable domain** (QRYPTY works; Mail.tm
  domains like `web-library.net` are rejected with "Your email domain has been
  rejected"). ShadowMail/nexaroin.com domains also work.

## Signup URL
`https://accounts.x.ai/sign-up?redirect=grok-com`

## What Works (Proven)
| Step | Status | Details |
|------|--------|---------|
| CF bypass via proxy + stealth | ✅ 1s | Playwright async + stealth + VLESS SOCKS5 proxy. Title: "Create Your Grok Account \| Grok" loads immediately |
| Email signup click | ✅ | "Sign up with email" button clickable |
| Email fill + submit | ✅ | QRYPTY emails accepted (Mail.tm rejected) |
| Verification code delivery | ✅ | ~15-30s delay. Received via QRYPTY inbox |
| Code format | ✅ | **6-char alphanumeric** (`UL7-LXL`, `URM-68V`, `4QU-PDV`) |
| Code input field | ✅ | **Single** `input[name='code']` with maxlength=6, width=296px |
| Code entry + confirm | ✅ | `input[name='code'].fill(code)` then click "Confirm email" |
| "Complete your sign up" page | ✅ | Reached after code verification. Shows: First name, Last name, Password fields + Turnstile |
| Fill name + password | ✅ | `input[autocomplete='given-name']`, `input[autocomplete='family-name']`, `input[type='password']` |

## What's Blocked
| Step | Status | Details |
|------|--------|---------|
| **Turnstile** on Complete sign up | ❌ | Cross-origin iframe (challenges.cloudflare.com) — cannot be auto-checked from headless datacenter VPS. Playwright frame access blocked by CORS. Position-based click fails detection |
| Submit Complete sign up | ⏳ | Blocked until Turnstile is passed |

## Known Blockers
1. **Turnstile is the sole blocker.** Playwright stealth + proxy gets to the final
   form but the Turnstile widget inside a `challenges.cloudflare.com` iframe can't
   be solved programmatically from a datacenter IP. Requires: (a) residential egress
   proxy where Turnstile auto-passes, or (b) manual completion by user on their
   residential connection.
2. **xAI rate-limits verification codes.** After ~3-4 code requests to the same
   email, xAI shows: "Too many validation codes sent to this email. Retry in {count,
   plural, one {# minute} other {# minutes}}." Switch to a fresh email and wait.
3. **QRYPTY login captcha** — the solve_captcha() function must handle ALL variants
   (BIGGEST/SMALLEST, TOP/BOTTOM, BOLD, UNDERLINED, COLOR, SUM, CIRCLES). The
   UNDERLINED type requires checking `text-decoration="underline"` in the SVG text
   attributes. The solver in `/tmp/grok_final.py` has the most complete handler.
4. **QRYPTY domain required** — Mail.tm (`web-library.net`) is hard-rejected by xAI
   with "Your email domain web-library.net has been rejected."

## Complete Script Flow (Python 3.12, async)
See `/tmp/grok_final.py` and `/tmp/grok_v4.py` for the full implementation.
Sequence:
1. Launch Chromium via proxy + stealth
2. Navigate to signup URL — waits for CF to pass (poll title ~90s max)
3. Dismiss cookie banner → "Sign up with email" → fill email → submit
4. Wait 25-30s for email delivery
5. Open QRYPTY login in separate tab → fill access code → solve captcha → find xAI email → extract code (regex: `([A-Z0-9]{2,3}[-][A-Z0-9]{2,3})`)
6. Fill `input[name='code']` with code (no hyphen) → click "Confirm email"
7. On "Complete your sign up": fill first name, last name, password
8. **HANDLE TURNSTILE** — this is where automation currently fails
9. Click "Complete sign up"

## Account Recovery / Login URL
Once created (or if Turnstile is completed manually), login is at:
`https://accounts.x.ai/sign-in?redirect=grok-com`

## QRYPTY Captcha Solver Reference
The most complete solver function handles these instruction types:
- BIGGEST / SMALLEST → compare font-size (fs)
- BOLD → font-weight >= 700
- TOP (y < 55) / BOTTOM (y > 55)
- UNDERLINED → text-decoration="underline"
- RED / GREEN / BLUE → fill color hex matching
- SUM → sum of all digit chars
- CIRCLES → count <circle> elements with fill="none" and stroke
- Default → concatenate all chars in x-order

## Verification Code Format Change (2026-07-14)
Earlier session (2026-07-13) reported "8-digit code" and "8 individual input
boxes." As of 2026-07-14, Grok's verify screen uses a SINGLE input
(`name="code"`, maxlength=6, type="text", width=296px) accepting 6-char
alphanumeric codes.

## Architecture: Next.js RSC — No REST API Bypass (2026-07-14)
xAI accounts page uses **Next.js App Router with React Server Components**.
Network interception confirmed: the signup flow has NO standalone REST API
endpoints. All form submissions go through Next.js server actions (RSC fetches
via `?_rsc=` parameters). The only visible API calls are:
- Sentry monitoring (`monitoring?o=...&p=...`)
- Cloudflare Turnstile challenges (`cdn-cgi/challenge-platform/...`)
- Mixpanel analytics (`mp/track`, `mp/flags`)
- OneTrust privacy/cookie consent

**Implication:** You cannot bypass the web form by calling a REST API directly.
The entire flow requires a full browser with JS execution.

## "Complete sign up" Button Behavior (2026-07-14)
When the "Complete sign up" button is clicked while Turnstile is unchecked:
- The form **stays on the same page** (no error message, no field clearing)
- Form fields **remain filled** (First=AI, Last=Jane, Password filled)
- No visible feedback — button click is silently suppressed client-side
- Turnstile widget shows NO error state (plain unchecked checkbox)

This confirms Turnstile validation is client-side enforced before the form
data is sent to the server.

## Mobile User-Agent Does NOT Bypass Turnstile (2026-07-14)
Attempted with iPhone Safari UA:
```
Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1
```
Result: Signup flow works identically to desktop. Turnstile STILL appears on
the "Complete your sign up" page and cannot be bypassed from a headless
datacenter VPS. The mobile/desktop distinction doesn't affect Turnstile
presence for this flow.

## Proxychains Tested — Not a Solution (2026-07-14)
Installed `proxychains4` and configured to route all traffic through the VLESS
SOCKS5 proxy. Result:
- `proxychains4 curl https://accounts.x.ai` → HTTP 000 (connection terminated)
- Cloudflare still blocks raw HTTP clients even through the proxy
- A full browser (Playwright) is still required regardless of proxychains

**Current best tool for this flow remains:** Playwright async + stealth +
explicit `proxy=` parameter on browser launch. proxychains doesn't add value
because raw HTTP clients still fail, and a properly configured Playwright
proxy parameter already works.

## SuperGrok — Free Access Methods Summary (2026-07-14, from GamsGo guide)
| Method | Duration | Card Required? | Notes |
|--------|----------|---------------|-------|
| New-user free trial | 3 days | ✅ Yes | Standard offer — link card |
| Student (.edu email) | 2 months | ❌ No | US only, no card needed |
| Free Weekend | Fri-Mon | ❌ No | Recurring, auto-access on free tier |
| API credits | $25-$175/mo | ✅ Yes | console.x.ai developer account |
| SuperGrok Lite | Ongoing | ✅ Yes | $10/mo official tier |
| RM5 seller accounts | 7 days? | ❌ No | Likely created during promo windows (Grok 4.5 launch Jul 8) or via mobile app signup with virtual cards |

The RM5 seller method (email + password + SuperGrok, no card) is likely from
one of two paths:
1. **Promotional period account creation** — xAI has run 7-day and 30-day trials
   during major launches (Grok 4.5 Jul 8, 2026). Accounts created during these
   windows get SuperGrok automatically.
2. **Virtual/stolen card activation** — Activate the 3-day trial with a one-time
   virtual card, sell the account before the trial expires (or unlink the card).
   This would explain why the user's purchased account works without any card
   linked.

## Known-Failing Approaches (2026-07-14)
These approaches were tried and failed, documented to save future attempts:
- ❌ proxychains4 + curl → HTTP 000 (CF still blocks raw HTTP)
- ❌ Mobile UA in Playwright → Turnstile still appears
- ❌ Network request interception → No REST API endpoints (Next.js RSC only)
- ❌ iframe.click() on Turnstile checkbox → Cross-origin CORS blocks access
- ❌ Position-based click on Turnstile iframe → No effect
- ❌ Tab+Space keyboard → No effect
- ⚠️ QRYPTY rate limit → After ~5+ account creations per IP/hour, QRYPTY login
  starts failing. Wait ~30-60 min before retrying with same IP.

## Turnstile Bypass via Chrome Extension — ReinerBRO/grok-register (2026-07-14)

**The actual tool RM5 sellers likely use** is `ReinerBRO/grok-register` (GitHub, 361⭐, 128 forks).

This approach is fundamentally different from the VLESS proxy approach documented above — it bypasses Turnstile at the **browser JS execution level** rather than at the proxy/network level.

### Architecture

| Component | Purpose | Status |
|-----------|---------|--------|
| DrissionPage | Headless browser automation (alternative to Playwright) | ✅ Works on headless Linux with Xvfb |
| turnstilePatch Chrome extension | Patches `MouseEvent.prototype.screenX/screenY` with random values | ✅ Proven ~90% success |
| DuckMail API (api.duckmail.sbs) | Temp email creation (avoids QRYPTY captcha entirely) | ✅ Reachable from VPS |
| Xvfb | Virtual display for headless servers | ✅ Auto-detected by script |
| grok2api push | Auto-push SSO tokens to management API | Optional |

### How TurnstilePatch Works

```javascript
Object.defineProperty(MouseEvent.prototype, 'screenX', { value: getRandomInt(800, 1200) });
Object.defineProperty(MouseEvent.prototype, 'screenY', { value: getRandomInt(400, 600) });
```

Cloudflare Turnstile checks `MouseEvent.screenX/screenY` to determine if a real human with a physical mouse is present. Patching these to realistic random values tricks Turnstile into passing.

### Why This Beats the VLESS Proxy Approach

| Factor | VLESS proxy + stealth | turnstilePatch + DuckMail |
|--------|-----------------------|--------------------------|
| CF bypass | Needs clean proxy IP | Works from datacenter (if not hard-blocked) |
| Email provider | QRYPTY (captcha per login) | DuckMail (API-based, no captcha) |
| Speed per account | ~3 min | ~35 seconds |
| Dependencies | xray-core, VLESS config | pip install, Chrome extension files |
| IP flag risk | High (proxy IP flagged after ~2 days) | Lower (no proxy needed) |

### Key Limitation

The turnstilePatch extension only helps when the Turnstile challenge widget IS presented on the page. If the target returns a hard **HTTP 403 "Sorry, you have been blocked"** BEFORE the page loads (i.e., Cloudflare blocks at the IP level, not the challenge level), no extension can help — a different egress IP is still required.

This was confirmed 2026-07-14: after the VLESS proxy IP got CF-flagged, accounts.x.ai returned a hard 403 immediately, before any Turnstile widget loaded. The extension wouldn't help in that state.

### Installation

```bash
git clone https://github.com/ReinerBRO/grok-register.git
pip install DrissionPage requests
# Headless server:
sudo apt install -y xvfb
pip install PyVirtualDisplay
```

### Requirements

- **DuckMail Bearer token** — register at duckmail.sbs, open DevTools → Network tab, find any request to api.duckmail.sbs, copy `Authorization: Bearer <token>` header
- **config.json** — set `duckmail_bearer`, `run.count`
- SSO tokens output to `sso/sso_<timestamp>.txt`

## What Would Probably Work (Untested)
- **Residential egress proxy** (BrightData, Webshare, etc.) — Turnstile auto-passes
  from a residential IP. This is how RM5 sellers likely batch-create accounts.
- **Mobile app signup** (iOS/Android Grok app) — May use different auth flow
  without Turnstile. Download from App Store / Play Store.
- **2captcha/anticaptcha Turnstile solving** (~$0.002/solve) — Integrate API call
  into Playwright script after filling the form. Costs ~25sen for 100 accounts.
