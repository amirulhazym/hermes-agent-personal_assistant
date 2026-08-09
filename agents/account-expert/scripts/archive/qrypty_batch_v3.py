#!/usr/bin/env python3
"""
QRYPTY Mail batch account creator — v3
Handles ALL captcha types with retry logic and collision avoidance.
"""
import asyncio, csv, secrets, sys
from datetime import datetime
from playwright.async_api import async_playwright

DARK_FILLS = {"#253542", "#2e404e", "#1a2830", "#4a6a80", "#658195"}
TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 30
OUTPUT = "/tmp/30_qrypty_accounts.csv"

async def solve_captcha(page):
    """Solve ANY QRYPTY captcha by reading SVG elements."""
    await page.wait_for_selector('svg[viewBox="0 0 280 100"]', timeout=10000)
    await asyncio.sleep(0.3)

    data = await page.evaluate("""() => {
        const svg = document.querySelector('svg[viewBox="0 0 280 100"]');
        if (!svg) return {instr: '', text_chars: [], shapes: []};
        const texts = svg.querySelectorAll('text');
        const instr = texts.length > 0 ? texts[0].textContent.trim() : '';
        const shapes = [];
        const all = svg.querySelectorAll('rect, circle, polygon, path');
        for (const el of all) {
            const w = parseFloat(el.getAttribute('width') || 0);
            const h = parseFloat(el.getAttribute('height') || 0);
            const r = parseFloat(el.getAttribute('r') || 0);
            const sw = parseFloat(el.getAttribute('stroke-width') || 0);
            const fill = el.getAttribute('fill') || '';
            if ((w > 7 || h > 7 || r >= 5) && sw >= 2 && fill !== '#f0f4f7' && w < 200) {
                shapes.push({
                    tag: el.tagName,
                    w: Math.round(w), h: Math.round(h), r: Math.round(r)
                });
            }
        }
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

    # Shape-based: count shapes
    if len(data['text_chars']) < 2 and data['shapes']:
        shapes = data['shapes']
        r_count = len([s for s in shapes if s['tag'] == 'rect'])
        c_count = len([s for s in shapes if s['tag'] == 'circle'])
        if 'square' in instr: return str(r_count)
        elif 'circle' in instr: return str(c_count)
        else: return str(len(shapes))

    # Text-based: characters
    chars = data['text_chars']
    if not chars:
        return None

    special_chars = [c for c in chars if c['fill'] not in DARK_FILLS]

    # Row detection via y threshold
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
        return min(freq, key=freq.get)  # char appearing least
    if 'how many' in instr or 'count' in instr:
        if special_chars: return str(len(special_chars))
        return str(len(chars))
    if 'type' in instr:
        if special_chars: return ''.join(c['char'] for c in special_chars)
        return ''.join(c['char'] for c in chars)
    return ''.join(c['char'] for c in chars)


async def create_account_page(browser, username, nickname):
    """Try to create one account. Returns (email, access_code) or None."""
    context = await browser.new_context(
        user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        viewport={'width': 1280, 'height': 800}
    )
    page = await context.new_page()

    try:
        await page.goto('https://qrypty.com/register', wait_until='domcontentloaded', timeout=20000)
        await asyncio.sleep(2)

        await page.fill('input[placeholder="username"]', username, timeout=10000)
        await page.fill('input[placeholder="Your name"]', nickname, timeout=10000)

        for attempt in range(3):
            answer = await solve_captcha(page)
            if not answer:
                print(f"  ⚠️ {username}: No solve for captcha, refresh {attempt+1}/3")
                await page.click('button[aria-label="Refresh"]', timeout=5000)
                await asyncio.sleep(1.5)
                continue

            await page.fill('input[placeholder="Answer"]', answer, timeout=5000)
            await page.click('button:has-text("Create Account")')
            await asyncio.sleep(2)

            body = await page.text_content('body') or ''

            if 'YOUR ACCESS CODE' in body:
                # Extract the 32-char code
                code = await page.evaluate("""() => {
                    const walker = document.createTreeWalker(document.body, 4, null, false);
                    while (walker.nextNode()) {
                        const t = walker.currentNode.textContent.trim();
                        if (t.length === 32 && /^[a-zA-Z0-9]+$/.test(t)) return t;
                    }
                    return '';
                }""")
                if code:
                    return (f"{username}@qrypty.com", code)
                print(f"  ⚠️ {username}: Access code page but no code found")
                return None

            if 'Incorrect captcha' in body:
                print(f"  ⚠️ {username}: Wrong captcha [{answer}], refresh {attempt+1}/3")
                await page.click('button[aria-label="Refresh"]', timeout=5000)
                await asyncio.sleep(1.5)
                continue

            # Still on register page — might be username taken or other error
            print(f"  ⚠️ {username}: Submitted but stayed on register (attempt {attempt+1}/3)")
            if attempt < 2:
                await page.click('button[aria-label="Refresh"]', timeout=5000)
                await asyncio.sleep(1.5)

        return None  # All attempts failed

    except Exception as e:
        print(f"  ⚠️ {username}: Error - {str(e)[:60]}")
        return None
    finally:
        await page.close()
        await context.close()


async def main():
    print(f"{'='*55}")
    print(f"  QRYPTY Mail Batch v3 — {TARGET} accounts")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}")

    accounts = []
    browser = await async_playwright().start()
    b = await browser.chromium.launch(
        headless=True,
        args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
    )

    for i in range(TARGET):
        # Try username, then suffix if taken
        base_num = i + 1
        username = f"ai-marryjane-{base_num:02d}"
        nickname = f"User {secrets.choice('ABCDEFGHJKMNPRTXY')}{secrets.randbelow(100):02d}"

        result = await create_account_page(b, username, nickname)

        if result:
            email, code = result
            accounts.append({'email': email, 'access_code': code})
            print(f"  ✅ #{i+1:2d} {email}  |  code: {code}")
        else:
            # Try with alternate suffix
            alt_user = f"ai-marryjane-{base_num:02d}-2"
            print(f"  🔄 #{i+1:2d} Trying alternate: {alt_user}")
            result = await create_account_page(b, alt_user, nickname)
            if result:
                email, code = result
                accounts.append({'email': email, 'access_code': code})
                print(f"  ✅ #{i+1:2d} {email}  |  code: {code}")
            else:
                print(f"  ❌ #{i+1:2d}: Both usernames failed")

        if i < TARGET - 1:
            await asyncio.sleep(1 + secrets.randbelow(2))

    await b.close()
    await browser.stop()

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
        print(f"  {idx:2d}. {a['email']:35s}  {a['access_code']}")


if __name__ == '__main__':
    asyncio.run(main())
