# Browser Custom Captcha Solving via JS DOM Inspection

## Technique: Solve Custom Visual Captchas Programmatically

Verified working against **QRYPTY Mail** registration (2026-07-13).
Five captcha variants encountered across multiple sessions — see variants below.

## The Problem

Some sites use custom visual captchas (not reCAPTCHA/hCaptcha) that ask you to
count characters of a specific color, type characters from a specific row, or
identify the "different" character. A screenshot (browser_vision) CAN solve this
but costs a vision LLM call per captcha and is slower. A better approach: read
the fill colors and positions directly from the DOM via JS evaluation.

## Critical: Correct SVG Selector

QRYPTY's registration page has **6 SVG elements**. The captcha is at index 3,
identifiable by `viewBox="0 0 280 100"`:

```javascript
// WRONG — matches first SVG (small 24x24 icon, not captcha)
document.querySelector('svg')

// CORRECT — matches captcha SVG specifically
document.querySelector('svg[viewBox="0 0 280 100"]')
```

Using `querySelector('svg')` silently fails because it reads a tiny refresh icon
SVG (no text, no shapes) instead of the captcha. Always use the viewBox selector.

## Captcha Variants (all 5 observed)

### Variant 1: Row-Typing ("Type only TOP row" / "Type only BOTTOM row")

| Detail | Value |
|--------|-------|
| Instruction | "Type only TOP row" or "Type only BOTTOM row" |
| Answer | Concatenation of row characters in display order |
| Row detection | Y-coordinate threshold clustering (20px gap between rows) |

**Row detection algorithm** — use threshold-based clustering, NOT rounding:

```python
y_sorted = sorted(chars, key=lambda c: c['y'])
rows = []
cur = []
for c in y_sorted:
    if not cur: cur.append(c)
    elif abs(c['y'] - cur[-1]['y']) < 20: cur.append(c)
    else:
        rows.append(''.join(x['char'] for x in cur))
        cur = [c]
if cur: rows.append(''.join(x['char'] for x in cur))
```

**Pitfall with rounding approach:** `round(y/5)*5` splits rows when y values
like 35 and 39 within the same row round to different bins (35→35, 39→40).
Round-to-5 fails when row span > 4px. Always use threshold clustering.

### Variant 2: Color-Counting ("How many GREEN characters?")

| Detail | Value |
|--------|-------|
| Instruction | "How many GREEN characters?" (or RED, BLUE, etc.) |
| Answer | Count of chars with the special (minority) fill color |

**Detection:** Use **minority-fill** approach, NOT hardcoded hex values.

```python
fill_counts = {}
for c in chars:
    fill_counts[c['fill']] = fill_counts.get(c['fill'], 0) + 1

most_common_fill = max(fill_counts, key=fill_counts.get) if fill_counts else ''
special_fills = {f for f in fill_counts if f != most_common_fill}
special_chars = [c for c in chars if c['fill'] in special_fills]
```

**Why not hardcoded hex?** The "special" color varies between captchas and the
same hex value (#4a6a80, #658195) might be the "blue" in one captcha but the
"normal" in another. Detection by minority frequency is more reliable than
matching specific color names to hex values.

### Variant 3: Color-Typing ("Type only BLUE characters")

| Detail | Value |
|--------|-------|
| Instruction | "Type only BLUE/RED characters" |
| Answer | Concatenation of chars with the special (minority) fill |
| Pitfall | Color-specific detection may fail if fill values aren't distinct in DOM |

**Limitation (2026-07-13):** When ALL characters report identical fill values
(dark shades like #253542, #2e404e, #1a2830), the "special" color is NOT
detectable from the DOM. The color difference appears to be rendered via a
mechanism invisible to `getAttribute('fill')` and `computedStyle.fill`.

**Fallback when minority-fill is empty:** Return ALL characters (usually wrong
but the only option without vision analysis). The captcha silently refreshes
on wrong answer without showing "Incorrect captcha" text.

### Variant 4: Different Character ("Type the DIFFERENT character")

| Detail | Value |
|--------|-------|
| Instruction | "Type the DIFFERENT character" or "Type the UNIQUE character" |
| Detection | Strategy 1: special color chars (different fill). Strategy 2: char value appearing least frequently |

```python
if special_chars:
    return ''.join(c['char'] for c in special_chars)
# All same fill → find char whose VALUE differs from majority
freq = {}
for c in chars: freq[c['char']] = freq.get(c['char'], 0) + 1
return min(freq, key=freq.get)  # char appearing fewest times
```

### Variant 5: Shape-Counting ("How many SQUARES?")

| Detail | Value |
|--------|-------|
| Instruction | "How many SQUARES?" or "How many CIRCLES?" |
| Answer | Count of SVG elements matching the requested shape type |
| Detection | Count `<rect>` for squares, `<circle>` for circles, filter out decorative elements |

**Heuristic for filtering:** Include shapes with `stroke-width >= 2` and
size > 7px or radius >= 5. Exclude tiny decorative dots (r < 5, opacity < 1)
and the background fill rect (fill='#f0f4f7' or w > 200).

## Detecting Wrong Captcha (Silent Refresh)

QRYPTY does NOT show "Incorrect captcha" text when the captcha answer is wrong.
Instead, it silently refreshes the captcha while keeping the form filled.

**Detection method:** After clicking submit, check if the Answer input field
is empty. If empty → captcha was wrong, click Refresh button and retry:

```python
answer_val = await page.input_value('input[placeholder="Answer"]', timeout=3000)
if not answer_val:
    # Wrong captcha — page silently refreshed
    await page.click('button[aria-label="Refresh"]')
    continue
```

## Access Code Extraction

The 32-character access code is NOT inside a `<p>` tag. It appears as a direct
text node. Extract via TreeWalker:

```python
code = await page.evaluate("""() => {
    const w = document.createTreeWalker(document.body, 4, null, false);
    while (w.nextNode()) {
        const t = w.currentNode.textContent.trim();
        if (t.length === 32 && /^[a-zA-Z0-9]+$/.test(t)) return t;
    }
    return '';
}""")
```

**Pitfall:** `document.querySelectorAll('p')` and regex on `.innerHTML` may
accidentally match font-hash strings from CSS (also 32-char alphanumeric).
TreeWalker with length check is more reliable, but still trust the access code
page context (check for "YOUR ACCESS CODE" text first).

## QRYPTY Registration Form Fields

| Field | Selector | Notes |
|-------|----------|-------|
| Username | `input[placeholder="username"]` | `@qrypty.com` auto-appended |
| Nickname | `input[placeholder="Your name"]` | Display name |
| Captcha | SVG `viewBox="0 0 280 100"` | 5 variant types |
| Answer | `input[placeholder="Answer"]` | Captcha answer input |
| Create button | `button:has-text("Create Account")` | Form submit |
| Refresh | `button[aria-label="Refresh"]` | New captcha on error |

## Retry Strategy

```python
for attempt in range(3):
    answer = solve_captcha(page)
    if not answer:
        refresh captcha, continue

    fill answer → click submit → wait 2s

    if 'YOUR ACCESS CODE' in body: SUCCESS
    if answer field is empty: WRONG → refresh, continue
    otherwise: UNKNOWN → refresh, continue
```

## Limitations

- Only works for **custom** captchas where answer is in styled DOM elements.
  Does NOT work for reCAPTCHA, hCaptcha, Cloudflare Turnstile, or image CAPTCHAs.
- Color-typing variants may fail when all chars report identical DOM fills
  (the color difference is invisible to `getAttribute('fill')`).
- QRYPTY rotates captcha types aggressively. New types may emerge that aren't
  covered by this reference — check DOM structure and update this reference.

## When to Use This

- A registration form has a custom visual captcha with embedded answer in SVG
- You need to automate account creation on a JS-rendered site with custom challenge
- In a **plan → confirm → execute** flow where user approved automated creation
