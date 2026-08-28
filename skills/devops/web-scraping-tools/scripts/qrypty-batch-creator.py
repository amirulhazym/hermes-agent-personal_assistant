#!/usr/bin/env python3
"""
QRYPTY Mail batch account creator — v4
Creates N permanent @qrypty.com accounts via Playwright headless browser.
Handles ALL 5 captcha variants: row-typing, color-counting, color-typing,
different-character, and shape-counting.
Saves CSV with email + access code.

Usage: /usr/bin/python3.12 qrypty-batch-creator.py [count=30] [output=/tmp/qrypty_accounts.csv]

Key features:
- Correct SVG selector: svg[viewBox="0 0 280 100"] (NOT querySelector('svg'))
- Minority-fill detection for color captchas
- Row detection via 20px threshold clustering
- Wrong-captcha silent refresh detection (Answer field cleared)
- 3-attempt retry per account with captcha refresh
- Fallback usernames for collision handling
- Fresh browser context per account (avoids state pollution)
"""
import asyncio, csv, secrets, sys
from datetime import datetime
from playwright.async_api import async_playwright

TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 30
OUTPUT = sys.argv[2] if len(sys.argv) > 2 else "/tmp/qrypty_accounts.csv"


async def solve_captcha(page):
    """Solve QRYPTY captcha by reading SVG elements.

    Handles 5 variants:
    1. 'Type only TOP/BOTTOM row' — row via y-threshold
    2. 'How many GREEN/BLUE/RED characters?' — count minority-fill chars
    3. 'Type only BLUE/RED characters' — concatenate minority-fill chars
    4. 'Type the DIFFERENT character' — unique fill or char value
    5. 'How many SQUARES/CIRCLES?' — count SVG shapes
    """
    await page.wait_for_selector('svg[viewBox="0 0 280 100"]', timeout=10000)
    await asyncio.sleep(0.3)

    data = await page.evaluate("""() => {
        const svg = document.querySelector('svg[viewBox="0 0 280 100"]');
        if (!svg) return {instr: '', text_chars: [], shapes: []};
        const texts = svg.querySelectorAll('text');
        const instr = texts.length > 0 ? texts[0].textContent.trim() : '';
        const shapes = [];
        for (const el of svg.querySelectorAll('rect, circle, polygon, path')) {
            const w = parseFloat(el.getAttribute('width') || 0);
            const h = parseFloat(el.getAttribute('height') || 0);
            const r = parseFloat(el.getAttribute('r') || 0);
            const sw = parseFloat(el.getAttribute('stroke-width') || 0);
            const fill = el.getAttribute('fill') || '';
            if ((w > 7 || h > 7 || r >= 5) && sw >= 2 && fill !== '#f0f4f7' && w < 200)
                shapes.push({tag: el.tagName});
        }
        const text_chars = [];
        for (let i = 1; i < texts.length; i++) {
            const t = texts[i];
            text_chars.push({
                char: t.textContent.trim(),
                fill: t.getAttribute('fill') || '',
                y: parseFloat(t.getAttribute('y') || 0)
            });
        }
        return {instr, text_chars, shapes};
    }""")

    if not data or not data['instr']:
        return None

    instr = data['instr'].lower()

    # --- Shape-based: count shapes ---
    if len(data['text_chars']) < 2 and data['shapes']:
        s = data['shapes']
        rc = sum(1 for x in s if x['tag'] == 'rect')
        cc = sum(1 for x in s if x['tag'] == 'circle')
        if 'square' in instr: return str(rc)
        if 'circle' in instr: return str(cc)
        return str(len(s))

    # --- Text-based: detect minority fill as "special" ---
    chars = data['text_chars']
    if not chars: return None

    fill_counts = {}
    for c in chars:
        fill_counts[c['fill']] = fill_counts.get(c['fill'], 0) + 1

    most_common_fill = max(fill_counts, key=fill_counts.get) if fill_counts else ''
    special_fills = {f for f in fill_counts if f != most_common_fill}
    special_chars = [c for c in chars if c['fill'] in special_fills]

    # Row detection via 20px threshold clustering
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

    if 'top' in instr and 'row' in instr:
        return rows[0] if rows else ''
    if 'bottom' in instr and 'row' in instr:
        return rows[-1] if rows else ''
    if 'different' in instr or 'unique' in instr:
        if special_chars: return ''.join(c['char'] for c in special_chars)
        freq = {}
        for c in chars: freq[c['char']] = freq.get(c['char'], 0) + 1
        return min(freq, key=freq.get)
    if 'how many' in instr or 'count' in instr:
        if special_chars: return str(len(special_chars))
        return str(len(chars))
    if 'type' in instr:
        if special_chars: return ''.join(c['char'] for c in special_chars)
        return ''.join(c['char'] for c in chars)
    return ''.join(c['char'] for c in chars)


async def create_one(browser, username, nickname, max_attempts=4):
    """Try to create one account with retry. Returns (email, code) or None."""
    ctx = await browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        viewport={'width': 1280, 'height': 800}
    )
    page = await ctx.new_page()

    try:
        await page.goto('https://qrypty.com/register', wait_until='domcontentloaded', timeout=20000)
        await asyncio.sleep(2)

        await page.fill('input[placeholder="username"]', username, timeout=10000)
        await page.fill('input[placeholder="Your name"]', nickname, timeout=10000)

        for attempt in range(max_attempts):
            answer = await solve_captcha(page)
            if not answer:
                print(f"  ⚠️ {username}: Could not solve captcha #{attempt+1}")
                await page.click('button[aria-label="Refresh"]', timeout=5000)
                await asyncio.sleep(1.5)
                continue

            await page.fill('input[placeholder="Answer"]', answer, timeout=5000)
            await page.click('button:has-text("Create Account")')
            await asyncio.sleep(2)

            body = await page.text_content('body') or ''

            if 'YOUR ACCESS CODE' in body:
                code = await page.evaluate("""() => {
                    const w = document.createTreeWalker(document.body, 4, null, false);
                    while (w.nextNode()) {
                        const t = w.currentNode.textContent.trim();
                        if (t.length === 32 && /^[a-zA-Z0-9]+$/.test(t)) return t;
                    }
                    return '';
                }""")
                if code: return (f"{username}@qrypty.com", code)
                print(f"  ⚠️ {username}: No code found on success page")
                return None

            # Detect silent refresh: Answer field cleared = wrong captcha
            answer_val = await page.input_value('input[placeholder="Answer"]', timeout=3000)
            if not answer_val:
                print(f"  ⚠️ {username}: Captcha wrong [{answer}], retry {attempt+1}/{max_attempts}")
                continue

            # Still on register with answer still filled — maybe taken/validation error
            print(f"  ⚠️ {username}: Submitted but answer still present (taken?), attempt {attempt+1}")
            await page.click('button[aria-label="Refresh"]', timeout=5000)
            await asyncio.sleep(1.5)

        return None

    except Exception as e:
        print(f"  ⚠️ {username}: Error - {str(e)[:60]}")
        return None
    finally:
        await page.close()
        await ctx.close()


async def main():
    print(f"{'=' * 55}")
    print(f"  QRYPTY Batch Creator v4 — {TARGET} accounts")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'=' * 55}")

    accounts = []
    p = await async_playwright().start()
    b = await p.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
    )

    for i in range(TARGET):
        base = i + 1
        nick = f"U{secrets.choice('ABCDEFGHJKMNPRTXY')}{secrets.randbelow(100):02d}"

        user = f"ai-marryjane-{base:02d}"
        result = await create_one(b, user, nick)

        if not result:
            user = f"ai-marryjane-{base:02d}-2"
            print(f"  🔄 #{i+1:2d} Trying: {user}")
            result = await create_one(b, user, nick)

        if result:
            accounts.append({'email': result[0], 'access_code': result[1]})
            print(f"  ✅ #{i+1:2d} {result[0]:35s}  {result[1]}")
        else:
            print(f"  ❌ #{i+1:2d}: Failed")

        if i < TARGET - 1:
            await asyncio.sleep(2)

    await b.close()
    await p.stop()

    with open(OUTPUT, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['No', 'Email', 'Access Code'])
        for idx, a in enumerate(accounts, 1):
            w.writerow([idx, a['email'], a['access_code']])

    print(f"\n{'=' * 55}")
    print(f"  RESULTS: {len(accounts)}/{TARGET}")
    print(f"  CSV: {OUTPUT}")
    print(f"{'=' * 55}")
    for a in accounts:
        print(f"  {a['email']:35s}  {a['access_code']}")


if __name__ == '__main__':
    asyncio.run(main())
