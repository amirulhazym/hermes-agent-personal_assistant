# Grok/xAI — Strategy & Research

## Status (July 14, 2026)
- 7-day free trial exists on grok.com/plans but **requires credit/debit card**
- Grok 4.5 launch promotion (Jul 8) no-card window has closed
- Purchased RM5 accounts (e.g. owner@example.invalid) still work until their trial expires

## Known Access Methods

| Method | Card? | Cost | Notes |
|--------|-------|------|-------|
| 3-day SuperGrok trial | ✅ Card needed | $0 | Cancel immediately, still get 3 days |
| 7-day SuperGrok trial | ✅ Card needed | $0 | grok.com/plans — current offer |
| Outlook email trick | ✅ Still needs card | $0 | Reddit: outlook.com email triggers trial option |
| Student .edu | ❌ No card | 2 months free | .edu email required |
| GamsGo shared | ❌ No card | ~$3.99/mo | Legitimate shared account service |
| API credits | ❌ No card | $25 free | console.x.ai — instant credits |
| RM5 reseller | ❌ No card | RM5 | Works until trial expires if created during promo |
| Free Weekend | ❌ No card | Free | Fri-Mon UTC, temporary Grok 4 access |

## Tools Available
- **ReinerBRO/grok-register** (`tools/grok-register/`) — Batch account creation via DuckMail + turnstilePatch
- **QRYPTY batch** (`scripts/qrypty_vfinal.py`) — Bulk email creation
- **VLESS proxy** — Bypasses geo-restrictions for automation

## Grok Account Inventory (QRYPTY)
- 30 accounts at `accounts/qrypty_30_accounts.csv`
- Domains: `@qrypty.com` (~30-day persistence without login)
- **Used:** ai-marryjane-03 (user tested — free tier), ai-marryjane-05, ai-marryjane-10 (script tests)
- **Fresh:** ai-marryjane-04, 11–15, 17–36, 42

## To Proceed With Automation
1. User registers at duckmail.sbs → provides Bearer token
2. Create `tools/grok-register/config.json` with token
3. Install deps: DrissionPage, curl_cffi, Xvfb, playwright chromium
4. Run batch: `python DrissionPage_example.py --count 10`
5. Test resulting accounts for SuperGrok status
