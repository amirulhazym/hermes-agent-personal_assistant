# Provider Research — Bulk Email (2026-07-13, CORRECTED)
Environment: Singapore VPS (Tencent Lighthouse), SG egress IP.
Goal: 30 permanent accounts, NO phone, send+receive, bulk-capable.

## BLOCKED / UNUSABLE from SG IP
| Provider | Status | Reason |
|----------|--------|--------|
| GMX.com | BLOCKED | Geo: "country where GMX registration is no longer possible" |
| mail.com | BLOCKED | Same 1&1 IONOS company, identical geo-block |
| Zoho Mail | Phone req | Forces +65 phone number |
| Cock.li | Down | HTTP 404 (site unreachable) |
| Posteo | Blocked | HTTP 403 from SG IP |
| IONOS | Wrong path | HTTP 404 (wrong URL; paid anyway) |

## NEEDS FOREIGN PHONE (not geo-blocked)
| Provider | Phone | Note |
|----------|-------|------|
| GMX.net | German/AT/CH mobile | Reaches form fine; needs DE/AT/CH number. NOT geo-blocked. |

## VIABLE
| Provider | Phone | Cost | Captcha | Limit | Domain |
|----------|-------|------|---------|-------|--------|
| QRYPTY | None | Free | rotating SVG (ALL solvable via API) | **NO cap** (~4–5/IP/hr rate limit) | @qrypty.com |
| Runbox | OPTIONAL | 30-day trial → €19.50/yr (~RM90) | hCaptcha (manual) | none hard | @runbox.com / @runbox.no |
| ProtonMail | Maybe | Free (SGD 0) | none visible | 1 addr/acct | @proton.me |
| Tuta | None | **Free tier (1GB) + paid** | none visible | free limits | @tutamail.com / @tuta.io |
| Mail.tm | None | Free (disposable ~7d) | none | API instant | web-library.net etc |

## Notes
- **QRYPTY is the best path**: no phone, permanent, send/receive, ALL captcha types solvable via REST API (see qrypt-captcha.md). Real constraint = rate limit (~4–5/IP/hr), NOT account count. Use staggered batch (~3/hr) to avoid 429.
- Runbox: phone "Optional" — recovery email required (use Mail.tm). hCaptcha = manual solve only.
- ProtonMail free: may demand phone/email verification per account; 1GB, 1 address. Use Mail.tm as verification inbox.
- **Tuta HAS free tier** (1GB) — agent wrongly said "paid only". Signup: tuta.com → Free plan → username+password, skip phone.
- Mail.tm: API-based, no captcha, instant. Good for OTP/trial but NOT permanent (~7d expiry).

## GitHub bulk-account tools
No working generic email creator exists. Search returned only:
- ChatGPT / Pinterest / Instagram account creators (irrelevant)
- `hamnfiji-i/Email-account-creator` = README + Telegram spam link, NO code

## Conclusion
"30 permanent + no phone + free" IS achievable via QRYPTY (no cap, just rate-limited). Realistic paths:
- **QRYPTY ×N** (free, permanent, API captcha solver) — best, just pace for rate limit
- Runbox trials (no phone, paid after 30d) — alt if QRYPTY rate limit unacceptable
- ProtonMail free ×N (if verification bypassable via Mail.tm recovery)
- Mail.tm disposable ×N (fast, for OTP/trials, not permanent)
