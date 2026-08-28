"""Reusable QRYPTY-style captcha solver (Playwright async) — FALLBACK only.

PRIMARY method is the REST API: see scripts/qrypt_api_creator.py (handles ALL
captcha types including color via hex mapping — no browser needed).

This Playwright fallback handles: row-based, count, different-character,
shape-count. Color-based ("Type only BLUE/RED/GREEN") IS solvable via hex
mapping (see references/qrypt-captcha.md) but this fallback bails on color
because Playwright DOM read is less reliable than the API SVG parse. Prefer
the API script.

Selector note: ALWAYS scope by viewBox. `querySelector('svg')` grabs a 24x24
icon, not the 280x100 captcha. That bug cost 4 iterations.
"""
import asyncio


async def solve_captcha(page):
    """Return answer string or None. Scopes captcha SVG by viewBox."""
    await page.wait_for_selector('svg[viewBox="0 0 280 100"]', timeout=10000)
    await asyncio.sleep(0.3)

    data = await page.evaluate("""() => {
        const svg = document.querySelector('svg[viewBox="0 0 280 100"]');
        if (!svg) return {instr: '', text_chars: [], shapes: []};
        const texts = svg.querySelectorAll('text');
        const instr = texts.length ? texts[0].textContent.trim() : '';
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

    # Shape-based
    if len(data['text_chars']) < 2 and data['shapes']:
        s = data['shapes']
        rc = sum(1 for x in s if x['tag'] == 'rect')
        cc = sum(1 for x in s if x['tag'] == 'circle')
        if 'square' in instr:
            return str(rc)
        if 'circle' in instr:
            return str(cc)
        return str(len(s))

    chars = data['text_chars']
    if not chars:
        return None

    # Row detection via y-coordinate (threshold 20px)
    y_sorted = sorted(chars, key=lambda c: c['y'])
    rows = []
    cur = []
    for c in y_sorted:
        if not cur:
            cur.append(c)
        elif abs(c['y'] - cur[-1]['y']) < 20:
            cur.append(c)
        else:
            rows.append(''.join(x['char'] for x in cur))
            cur = [c]
    if cur:
        rows.append(''.join(x['char'] for x in cur))

    if 'top' in instr and 'row' in instr:
        return rows[0] if rows else ''
    if 'bottom' in instr and 'row' in instr:
        return rows[-1] if rows else ''
    if 'different' in instr or 'unique' in instr:
        freq = {}
        for c in chars:
            freq[c['char']] = freq.get(c['char'], 0) + 1
        return min(freq, key=freq.get)
    if 'how many' in instr or 'count' in instr:
        return str(len(chars))
    if 'type' in instr:
        # Color-based captchas fall here and are WRONG — needs human.
        # Detect: if instruction names a color and all fills identical → bail.
        colors = ['red', 'blue', 'green', 'yellow', 'purple', 'orange']
        if any(c in instr for c in colors):
            return None  # unsolvable programmatically
        return ''.join(c['char'] for c in chars)
    return ''.join(c['char'] for c in chars)


async def is_captcha_wrong(page):
    """Silent-refresh detection: Answer input emptied after submit = wrong."""
    val = await page.input_value('input[placeholder="Answer"]', timeout=3000)
    return not val
