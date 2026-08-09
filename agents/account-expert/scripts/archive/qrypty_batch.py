#!/usr/bin/env python3
"""
QRYPTY Mail batch account creator
Creates N permanent @qrypty.com accounts via Playwright
Saves CSV with email + access code
"""
import asyncio, csv, secrets, sys, os, json, re
from datetime import datetime

from playwright.async_api import async_playwright

# Known dark shades used for non-target characters in QRYPTY captcha
DARK_FILLS = {"#253542", "#2e404e", "#1a2830", "#4a6a80", "#658195"}

TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 30
DELAY_BETWEEN = 1  # seconds between accounts
OUTPUT = "/tmp/30_qrypty_accounts.csv"

async def solve_captcha(page):
    """Solve ANY QRYPTY captcha variant by reading SVG text elements.

    Handles:
    - 'How many GREEN characters?' → count chars with special color
    - 'Type only RED/BLUE/etc characters' → concatenate chars with that color
    - 'Type only TOP/BOTTOM row' → concatenate chars in that row
    - 'Type the DIFFERENT character' → find the unique char (color or value)
    """
    await page.wait_for_selector("svg text", timeout=10000)

    texts = await page.evaluate("""() => {
        const els = document.querySelectorAll('svg text');
        return Array.from(els).map(t => ({
            char: t.textContent.trim(),
            fill: t.getAttribute('fill') || t.style.fill || 'inherit',
            y: parseFloat(t.getAttribute('y') || t.style.y || 0)
        }));
    }""")

    if not texts or len(texts) < 2:
        return None

    instruction = texts[0]['char'].lower()
    chars = texts[1:]

    # Detect special color: chars whose fill is NOT a dark shade
    special_chars = [c for c in chars if c['fill'] not in DARK_FILLS]

    # Detect rows by y-coordinate with threshold-based clustering
    y_sorted = sorted(chars, key=lambda c: c['y'])
    rows = []
    current_row = []
    for c in y_sorted:
        if not current_row:
            current_row.append(c)
        elif abs(c['y'] - current_row[-1]['y']) < 20:
            current_row.append(c)
        else:
            rows.append(''.join(x['char'] for x in current_row))
            current_row = [c]
    if current_row:
        rows.append(''.join(x['char'] for x in current_row))

    # Determine action from instruction
    if 'top' in instruction and 'row' in instruction:
        return rows[0] if rows else ''

    elif 'bottom' in instruction and 'row' in instruction:
        return rows[-1] if rows else ''

    elif 'different' in instruction or 'unique' in instruction:
        # "Type the DIFFERENT character"
        # Strategy 1: Find chars with different fill/color
        if special_chars:
            return ''.join(c['char'] for c in special_chars)
        # Strategy 2: All same fill → find char whose VALUE differs from majority
        # Count frequency of each char value
        freq = {}
        for c in chars:
            freq[c['char']] = freq.get(c['char'], 0) + 1
        # Find minority value(s)
        min_freq = min(freq.values())
        answer = ''.join(ch for ch, cnt in freq.items() if cnt == min_freq)
        return answer

    elif 'how many' in instruction or 'count' in instruction:
        # Count characters of the special color
        if special_chars:
            return str(len(special_chars))
        # Fallback: count all chars
        return str(len(chars))

    elif 'type' in instruction:
        # Type only [COLOR] characters or type [something]
        if special_chars:
            return ''.join(c['char'] for c in special_chars)
        # Fallback: return all chars
        return ''.join(c['char'] for c in chars)

    else:
        # Fallback: concatenate all chars
        return ''.join(c['char'] for c in chars)


def user_name(n):
    """marryjane.ai-01, marryjane.ai-02, ... marryjane.ai-30"""
    return f"ai-marryjane-{n:02d}"


async def create_accounts():
    accounts = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled'
            ]
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            viewport={'width': 1280, 'height': 800},
            locale='en-US'
        )
        page = await context.new_page()

        for i in range(TARGET):
            username = user_name(i+1)
            nickname = f"User {secrets.choice(['A','B','C','D','E','F','G','H','J','K','M','N','P','R','T','X','Y'])}{secrets.randbelow(100):02d}"

            try:
                # Use fresh page for each account to avoid state issues
                if i > 0:
                    await page.close()
                    page = await context.new_page()

                await page.goto('https://qrypty.com/register', wait_until='networkidle', timeout=30000)
                await page.wait_for_timeout(2000)  # Let SPA render

                # Fill form
                username_input = page.locator('input[type="text"][placeholder="username"]')
                await username_input.fill(username)

                nickname_input = page.locator('input[type="text"][placeholder="Your name"]')
                await nickname_input.fill(nickname)

                # Solve captcha
                answer = await solve_captcha(page)
                if not answer:
                    print(f"  ❌ #{i+1}: Could not solve captcha")
                    continue

                # Type answer
                answer_input = page.locator('input[type="text"][placeholder="Answer"]')
                await answer_input.fill(answer)

                # Click Create Account
                create_btn = page.locator('button:has-text("Create Account")')
                await create_btn.click()

                # Extract access code — look for 32-char alphanumeric in paragraphs
                await page.wait_for_selector('text=YOUR ACCESS CODE', timeout=15000)
                await page.wait_for_timeout(1000)

                code = await page.evaluate("""() => {
                    const els = document.querySelectorAll('p');
                    for (const el of els) {
                        const t = el.textContent.trim();
                        if (t.length === 32 && /^[a-zA-Z0-9]+$/.test(t)) return t;
                    }
                    return '';
                }""")

                if code:
                    email = f"{username}@qrypty.com"
                    accounts.append({'email': email, 'access_code': code})
                    print(f"  ✅ #{i+1:2d} {email}  |  code: {code}")
                else:
                    print(f"  ⚠️ #{i+1}: Account created but couldn't extract code")
                    # Take screenshot for debugging
                    await page.screenshot(path=f"/tmp/qrypty_error_{i+1}.png")

            except Exception as e:
                print(f"  ❌ #{i+1}: {type(e).__name__}: {str(e)[:100]}")
                try:
                    await page.screenshot(path=f"/tmp/qrypty_error_{i+1}.png")
                except:
                    pass

            # Delay between accounts
            if i < TARGET - 1:
                delay = DELAY_BETWEEN + secrets.randbelow(3)
                print(f"     ...waiting {delay}s")
                await asyncio.sleep(delay)

        await browser.close()

    return accounts


async def main():
    print(f"=" * 55)
    print(f"  QRYPTY Mail Batch Creator — {TARGET} accounts")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"=" * 55)

    accounts = await create_accounts()

    # Save CSV
    with open(OUTPUT, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['No', 'Email', 'Access Code'])
        for idx, a in enumerate(accounts, 1):
            w.writerow([idx, a['email'], a['access_code']])

    print(f"\n{'=' * 55}")
    print(f"  RESULTS: {len(accounts)}/{TARGET} accounts created")
    print(f"  CSV: {OUTPUT}")
    print(f"{'=' * 55}")

    # Print summary
    for idx, a in enumerate(accounts, 1):
        print(f"  {idx:2d}. {a['email']:30s}  code: {a['access_code']}")

    return accounts


if __name__ == '__main__':
    asyncio.run(main())
