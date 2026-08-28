# QRYPTY Captcha Handling (CORRECTED 2026-07-13)

## API endpoints (PRIMARY method — no browser)
```
GET  https://qrypty.com/api/auth/challenge?lang=en
     → { captcha_id, image (SVG string), lang }
POST https://qrypty.com/api/auth/register
     headers: Content-Type: application/json
     body:    {"username", "display_name", "captcha_id", "captcha_answer"}
     → 201 { access_token, access_code (32-char [A-Za-z0-9], MIXED case), user:{email} }
```
- Rate limit: ~4–5/IP/hour. 429 → wait ~60 min.
- No account cap. "Accounts 1/5" in UI = counter, not limit.

## SVG structure
- Captcha SVG selector: `svg[viewBox="0 0 280 100"]`
- Instruction text = `<text x="140" y="15">...`
- Character glyphs = `<text ... font-size=".." fill="#..">X</text>` (monospace)
- Shapes = `<rect>` / `<circle>` (stroke-only, fill="none")
- Background = `<rect width="280" height="100" fill="#f0f4f7">` (EXCLUDE from shape counts)

## ALL TYPES SOLVABLE FROM DOM (no OCR, no human)
Parse chars with regex capturing x, y, font-size, font-weight, fill, char.
Sort by x. Then:

1. **TOP/BOTTOM row** — `y < 55` (TOP) or `y > 55` (BOTTOM). Threshold ~55px.
2. **BLUE** — chars where `fill == "#1a6bcc"`.
3. **RED** — chars where fill ∈ {`#cc1a1a,#e74c3c,#d32f2f,#c62828,#ff0000,#dc143c,#b22222,#cd5c5c,#ff6347,#ff4500`}.
   Fallback: any char whose fill is NOT in dark set {`#253542,#2e404e,#1a2830,#4a6a80,#658195,#1a6bcc`}.
4. **GREEN** — chars where fill ∈ {`#1b8c3a,#27ae60,#2ecc71,#00c853,#4caf50,#008000,#228b22,#32cd32`}.
5. **UNDERLINED / WITHOUT line** — find `<line stroke="#1a6bcc">` underlines; map each to nearest char above it (min x-distance); UNDERLINED = those chars, WITHOUT = the rest.
6. **BIGGEST / SMALLEST** — max/min by `(font_weight, font_size)`. BIGGEST prefers higher weight then larger size.
7. **CIRCLES** — count `<circle fill="none" stroke>` elements.
8. **SQUARES / RECTANGLES** — count `<rect>` where `abs(width-height) < 1` AND `width < 100` (excludes 280×100 background).
9. **SUM of digits** — sum of int(char) for digit chars.
10. **How many X? (generic)** — if chars exist and instruction says "how many", return `len(chars)`.

## Gotchas
- **access_code is mixed-case alphanumeric**, NOT hex. Don't regex `^[a-f0-9]{32}$`.
- **Already-taken usernames**: if a reg succeeds but you fail to save the code, that username is lost. Track consumed names in an EXCLUDE set.
- **Rate limit 429** counts even bad_captcha attempts sometimes — pace requests ~15–30s apart, retry bad_captcha with a FRESH challenge (re-GET /challenge), don't reuse the same captcha_id.

## Username format (user preference)
- NEVER "test" or bot-like. Use natural: `ai-marryjane-01`, `ai-marryjane-02`
- Dots stripped by QRYPTY (`marryjane.ai-01` → `marryjaneai-01`); hyphens/underscores preserved
- Collision fallback: `ai-marryjane-01-2`
