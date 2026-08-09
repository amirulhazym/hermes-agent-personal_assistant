#!/usr/bin/env python3
"""
QRYPTY Mail batch account creator — v2
Handles ALL captcha types: text (color/row/different) and SHAPES (squares/circles etc.)
"""
import asyncio, csv, secrets, sys, re
from datetime import datetime
from playwright.async_api import async_playwright

DARK_FILLS = {"#253542", "#2e404e", "#1a2830", "#4a6a80", "#658195"}
TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 30
DELAY_BETWEEN = 2
OUTPUT = "/tmp/30_qrypty_accounts.csv"

async def solve_captcha(page):
    """Solve ANY QRYPTY captcha by reading SVG elements."""
    await page.wait_for_selector('svg[viewBox="0 0 280 100"]', timeout=10000)
    await asyncio.sleep(0.5)

    # Get the instruction text and ALL SVG child elements
    data = await page.evaluate("""() => {
        const svg = document.querySelector('svg[viewBox="0 0 280 100"]');
        if (!svg) return {instr: '', text_chars: [], shapes: []};

        const texts = svg.querySelectorAll('text');
        const instr = texts.length > 0 ? texts[0].textContent.trim() : '';

        // Get shapes (rect, circle, polygon) with significant size
        const shapes = [];
        const all = svg.querySelectorAll('rect, circle, polygon, path');
        for (const el of all) {
            const rect = el.getBoundingClientRect();
            // Only count visible, non-decorative shapes
            const w = parseFloat(el.getAttribute('width') || rect.width || 0);
            const h = parseFloat(el.getAttribute('height') || rect.height || 0);
            const r = parseFloat(el.getAttribute('r') || (rect.width / 2) || 0);
            const fill = el.getAttribute('fill') || '';
            const stroke = el.getAttribute('stroke') || '';
            const sw = parseFloat(el.getAttribute('stroke-width') || 0);

            // Skip decorative elements (tiny dots, filled background rects)
            const isTiny = (w > 0 && w < 8) || (h > 0 && h < 8) || (r > 0 && r < 5);
            const isBackground = fill === '#f0f4f7' || (w > 200 && h > 50);

            if (!isTiny && !isBackground && sw >= 2) {
                shapes.push({
                    tag: el.tagName,
                    w: Math.round(w), h: Math.round(h), r: Math.round(r),
                    stroke: stroke
                });
            }
        }

        // Get text characters from SVG
        const text_chars = [];
        for (let i = 1; i < texts.length; i++) {
            text_chars.push({
                char: texts[i].textContent.trim(),
                fill: texts[i].getAttribute('fill') || texts[i].style.fill || 'inherit',
                y: parseFloat(texts[i].getAttribute('y') || texts[i].style.y || 0)
            });
        }

        return {instr, text_chars, shapes};
    }""")

    if not data or not data['instr']:
        return None

    instr = data['instr'].lower()

    # --- SHAPE-BASED CAPTCHA (no text chars, just shapes) ---
    if len(data['text_chars']) < 2 and len(data['shapes']) > 0:
        shapes = data['shapes']
        r_count = len([s for s in shapes if s['tag'] == 'rect'])
        c_count = len([s for s in shapes if s['tag'] == 'circle'])
        total_shapes = len(shapes)

        if 'square' in instr:
            return str(r_count)
        elif 'circle' in instr or 'round' in instr or 'oval' in instr:
            return str(c_count)
        elif 'triangle' in instr:
            tri = len([s for s in shapes if s['tag'] == 'polygon' or s['tag'] == 'path'])
            return str(tri) if tri > 0 else str(total_shapes)
        elif 'shape' in instr or 'many' in instr:
            return str(total_shapes)
        else:
            return str(total_shapes)

    # --- TEXT-BASED CAPTCHA ---
    chars = data['text_chars']
    if len(chars) < 1:
        return None

    special_chars = [c for c in chars if c['fill'] not in DARK_FILLS]

    # Row detection
    y_sorted = sorted(chars, key=lambda c: c['y'])
    rows = []
    current = []
    for c in y_sorted:
        if not current:
            current.append(c)
        elif abs(c['y'] - current[-1]['y']) < 20:
            current.append(c)
        else:
            rows.append(''.join(x['char'] for x in current))
            current = [c]
    if current:
        rows.append(''.join(x['char'] for x in current))

    if 'top' in instr and 'row' in instr:
        return rows[0] if rows else ''
    elif 'bottom' in instr and 'row' in instr:
        return rows[-1] if rows else ''
    elif 'different' in instr or 'unique' in instr:
        if special_chars:
            return ''.join(c['char'] for c in special_chars)
        freq = {}
        for c in chars:
            freq[c['char']] = freq.get(c['char'], 0) + 1
        min_freq = min(freq.values())
        return ''.join(ch for ch, cnt in freq.items() if cnt == min_freq)
    elif 'how many' in instr or 'count' in instr:
        if special_chars:
            return str(len(special_chars))
        return str(len(chars))
    elif 'type' in instr:
        if special_chars:
            return ''.join(c['char'] for c in special_chars)
        return ''.join(c['char'] for c in chars)
    else:
        return ''.join(c['char'] for c in chars)


def user_name(n):
    return f"ai-marryjane-{n:02d}"


async def create_accounts():
    accounts = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            viewport={'width': 1280, 'height': 800}
        )
        page = await context.new_page()

        for i in range(TARGET):
            username = user_name(i+1)
            nickname = f"User {secrets.choice('ABCDEFGHJKMNPRTXY')}{secrets.randbelow(100):02d}"

            # Fresh page per account to avoid state issues
            if i > 0:
                try:
                    await page.close()
                except:
                    pass
                page = await context.new_page()

            try:
                await page.goto('https://qrypty.com/register', wait_until='domcontentloaded', timeout=20000)
                await asyncio.sleep(2.5)

                # Fill form
                await page.fill('input[placeholder="username"]', username, timeout=10000)
                await page.fill('input[placeholder="Your name"]', nickname, timeout=10000)

                # Solve captcha with up to 3 retries
                answer = None
                for attempt in range(3):
                    answer = await solve_captcha(page)
                    if answer:
                        await page.fill('input[placeholder="Answer"]', answer, timeout=5000)
                        await page.click('button:has-text("Create Account")')
                        await asyncio.sleep(2.5)

                        body = await page.text_content('body') or ''

                        if 'Incorrect captcha' in body:
                            print(f"  ⚠️ #{i+1:2d} {username}: Wrong captcha (answer [{answer}]), retry {attempt+1}/3")
                            # Click refresh button to get new captcha
                            await page.click('button[aria-label="Refresh"]', timeout=5000)
                            await asyncio.sleep(1.5)
                            continue

                        if 'YOUR ACCESS CODE' in body:
                            break  # Success!

                        # Still on register page - may be another issue
                        if attempt < 2:
                            await page.click('button[aria-label="Refresh"]', timeout=5000)
                            await asyncio.sleep(1.5)
                    else:
                        print(f"  ⚠️ #{i+1:2d} {username}: Could not solve captcha, retry {attempt+1}/3")
                        await page.click('button[aria-label="Refresh"]', timeout=5000)
                        await asyncio.sleep(1.5)

                if not answer:
                    print(f"  ❌ #{i+1:2d} {username}: All captcha attempts failed")
                    continue

                body = await page.text_content('body') or ''

                if 'Incorrect captcha' in body:
                    print(f"  ❌ #{i+1:2d} {username}: Wrong captcha (answer was [{answer}])")
                    continue

                if 'YOUR ACCESS CODE' in body:
                    # Extract code
                    code = await page.evaluate("""() => {
                        const walker = document.createTreeWalker(document.body, 4, null, false);
                        while (walker.nextNode()) {
                            const t = walker.currentNode.textContent.trim();
                            if (t.length === 32 && /^[a-zA-Z0-9]+$/.test(t)) return t;
                        }
                        return '';
                    }""")

                    if code:
                        email = f"{username}@qrypty.com"
                        accounts.append({'email': email, 'access_code': code})
                        print(f"  ✅ #{i+1:2d} {email}  |  code: {code}")
                        continue

                # Check if we're on the regular page (failure)
                if 'Create Account' in body or 'create' in body.lower():
                    print(f"  ❌ #{i+1:2d} {username}: Still on register page (creation failed)")
                    continue

                print(f"  ⚠️ #{i+1:2d} {username}: Unknown state")

            except Exception as e:
                err = str(e)[:80]
                print(f"  ❌ #{i+1:2d} {username}: {err}")

            if i < TARGET - 1:
                delay = DELAY_BETWEEN + secrets.randbelow(2)
                await asyncio.sleep(delay)

        await browser.close()

    return accounts


async def main():
    print(f"{'='*55}")
    print(f"  QRYPTY Mail Batch v2 — {TARGET} accounts")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}")

    accounts = await create_accounts()

    # Save CSV
    with open(OUTPUT, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['No', 'Email', 'Access Code'])
        for idx, a in enumerate(accounts, 1):
            w.writerow([idx, a['email'], a['access_code']])

    print(f"\n{'='*55}")
    print(f"  RESULTS: {len(accounts)}/{TARGET} accounts created")
    print(f"  CSV: {OUTPUT}")
    print(f"{'='*55}")

    for idx, a in enumerate(accounts, 1):
        print(f"  {idx:2d}. {a['email']:30s}  code: {a['access_code']}")


if __name__ == '__main__':
    asyncio.run(main())
