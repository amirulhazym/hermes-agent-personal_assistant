#!/usr/bin/env python3
"""
Create a new QRYPTY email account for Grok signup.
Flow: GET challenge → parse SVG captcha → POST register → verify login → handoff
"""
import json
import random
import re
import string
import urllib.request
import urllib.error
import ssl
import sys
import time
from datetime import datetime, timezone

API_BASE = "https://qrypty.com"

# SSL context
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36',
    'Accept': 'application/json',
}


def api_get_challenge():
    req = urllib.request.Request(f"{API_BASE}/api/auth/challenge", method='GET', headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=15, context=CTX)
    return json.loads(resp.read().decode())


def solve_captcha(data):
    """Parse the SVG captcha and return the solution string."""
    svg = data['image']
    cid = data['captcha_id']

    # Extract instruction
    instr_match = re.search(r'<text[^>]*>([^<]+)</text>', svg)
    if not instr_match:
        return cid, None
    instruction = instr_match.group(1).strip()
    print(f"  Instr: '{instruction}'", end='')

    # Collect all single-character text elements (skip instruction at y<25)
    chars = []
    for m in re.finditer(r'<text\s+([^>]*)>([A-Za-z0-9])</text>', svg):
        attrs = m.group(1)
        char = m.group(2)
        y = float(re.search(r'y="([^"]+)"', attrs).group(1))
        if y < 25:
            continue
        x = float(re.search(r'x="([^"]+)"', attrs).group(1))
        fs = float(re.search(r'font-size="([^"]+)"', attrs).group(1))
        fw_match = re.search(r'font-weight="([^"]+)"', attrs)
        fw = fw_match.group(1) if fw_match else None
        has_rotate = 'rotate' in attrs
        chars.append({'x': x, 'y': y, 'fs': fs, 'fw': fw, 'char': char, 'rotated': has_rotate})

    # Collect colored lines
    underline_lines = []  # blue stroke
    strikethrough_lines = []  # red stroke
    dividing_line_y = None

    for m in re.finditer(r'<line\s+([^>]*?)/?>', svg):
        attrs = m.group(1)
        try:
            x1 = float(re.search(r'x1="([^"]+)"', attrs).group(1))
            y1 = float(re.search(r'y1="([^"]+)"', attrs).group(1))
            x2 = float(re.search(r'x2="([^"]+)"', attrs).group(1))
            y2 = float(re.search(r'y2="([^"]+)"', attrs).group(1))
        except (AttributeError, ValueError):
            continue

        if '1a6bcc' in attrs:
            underline_lines.append((x1, y1, x2, y2))
        elif 'cc2e2e' in attrs:
            strikethrough_lines.append((x1, y1, x2, y2))
        elif 'stroke-dasharray' in attrs:
            dividing_line_y = (y1 + y2) / 2

    # Helper: check if char is underlined
    def has_underline(c):
        for x1, y1, x2, y2 in underline_lines:
            if (min(x1, x2) - 15) <= c['x'] <= (max(x1, x2) + 15) and (c['y'] + 2) <= min(y1, y2) <= (c['y'] + 20):
                return True
        return False

    def has_strikethrough(c):
        for x1, y1, x2, y2 in strikethrough_lines:
            mid_y = (y1 + y2) / 2
            if (min(x1, x2) - 15) <= c['x'] <= (max(x1, x2) + 15) and abs(c['y'] - mid_y) < 12:
                return True
        return False

    il = instruction.lower()

    # --- Handle "How many CIRCLES?" ---
    if 'circle' in il and 'how many' in il:
        # Count large circles (fill="none", r >= 10)
        big_circles = 0
        for m in re.finditer(r'<circle\s+([^>]*?)/?>', svg):
            attrs = m.group(1)
            if 'fill="none"' in attrs or "fill='none'" in attrs:
                r_match = re.search(r'r="([^"]+)"', attrs)
                if r_match and float(r_match.group(1)) >= 10:
                    big_circles += 1
        solution = str(big_circles)
        print(f" -> {solution}")
        return cid, solution

    # If no character elements found, return None
    if not chars:
        print(" -> (no chars)")
        return cid, None

    # --- Handle the rest ---
    if 'biggest' in il:
        max_c = max(chars, key=lambda c: c['fs'])
        solution = max_c['char']
    elif 'smallest' in il or 'small' in il:
        min_fs = min(c['fs'] for c in chars)
        smallest = sorted([c for c in chars if c['fs'] == min_fs], key=lambda c: c['x'])
        solution = ''.join(c['char'] for c in smallest)
    elif 'top' in il:
        threshold = dividing_line_y if dividing_line_y else 55
        top_chars = sorted([c for c in chars if c['y'] < threshold], key=lambda c: c['x'])
        solution = ''.join(c['char'] for c in top_chars)
    elif 'bottom' in il:
        threshold = dividing_line_y if dividing_line_y else 55
        bot_chars = sorted([c for c in chars if c['y'] >= threshold], key=lambda c: c['x'])
        solution = ''.join(c['char'] for c in bot_chars)
    elif 'underlin' in il or 'with line' in il:
        lined = sorted([c for c in chars if has_underline(c) or has_strikethrough(c)], key=lambda c: c['x'])
        solution = ''.join(c['char'] for c in lined)
    elif 'without line' in il or 'no line' in il:
        no_line = sorted([c for c in chars if not has_underline(c) and not has_strikethrough(c)], key=lambda c: c['x'])
        solution = ''.join(c['char'] for c in no_line)
    elif 'upright' in il:
        upright = sorted([c for c in chars if not c['rotated']], key=lambda c: c['x'])
        solution = ''.join(c['char'] for c in upright)
    elif 'bold' in il:
        # Bold = font-weight="700"
        bold = sorted([c for c in chars if c['fw'] == '700'], key=lambda c: c['x'])
        if not bold:
            # All chars are bold if none have different weight
            bold = sorted(chars, key=lambda c: c['x'])
        solution = ''.join(c['char'] for c in bold)
    else:
        # Fallback: all chars
        allc = sorted(chars, key=lambda c: c['x'])
        solution = ''.join(c['char'] for c in allc)

    print(f" -> '{solution}'")
    return cid, solution


def api_register(username, password, access_code, captcha_id, captcha_solution, display_name=None):
    payload = {
        "username": username,
        "password": password,
        "access_code": access_code,
        "captcha_id": captcha_id,
        "captcha_solution": captcha_solution,
        "display_name": display_name or username,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{API_BASE}/api/auth/register", data=data, method='POST',
        headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json', 'Accept': 'application/json'}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15, context=CTX)
        return {'success': True, 'data': json.loads(resp.read().decode())}
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        detail = ""
        try:
            detail = json.loads(body).get("detail", body)
        except:
            detail = body
        return {'success': False, 'code': e.code, 'detail': detail, 'body': body}


def api_login(username, password):
    payload = {"username": username, "password": password}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{API_BASE}/api/auth/login", data=data, method='POST',
        headers={'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json', 'Accept': 'application/json'}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15, context=CTX)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        return {"error": f"HTTP {e.code}", "detail": body}


def test_grok_access():
    results = {}
    for url, label in [
        ("https://accounts.x.ai", "accounts.x.ai"),
        ("https://grok.com", "grok.com"),
        ("https://x.ai", "x.ai"),
    ]:
        try:
            req = urllib.request.Request(url, method='GET', headers=HEADERS)
            resp = urllib.request.urlopen(req, timeout=10, context=CTX)
            results[label] = {"reachable": True, "status": resp.getcode()}
        except urllib.error.HTTPError as e:
            results[label] = {"reachable": True, "status": e.code}
        except urllib.error.URLError as e:
            results[label] = {"reachable": False, "error": str(e.reason)}
        except Exception as e:
            results[label] = {"reachable": False, "error": str(e)}
    return results


def main():
    print("=" * 60)
    print("QRYPTY Account Creation for Grok Signup")
    print("=" * 60)

    # Step 0: Test xAI/Grok access
    print("\n[0] Testing xAI/Grok access...")
    access_results = test_grok_access()
    for label, result in access_results.items():
        if result.get("reachable"):
            print(f"  {'✅' if result['status'] < 400 else '⚠️'} {label}: HTTP {result['status']}")
        else:
            print(f"  ❌ {label}: {result.get('error', 'unknown')}")

    accounts_xai_ok = access_results.get("accounts.x.ai", {}).get("reachable", False) \
                       and access_results.get("accounts.x.ai", {}).get("status", 0) < 400

    # Account details
    BASE_USER = "boss-amirul-01"
    GROK_PASSWORD = "SuperGrok_2026!"

    # Try to create account
    user = BASE_USER
    display = "Boss Amirul AI"
    # QRYPTY password (random, strong) - different from Grok password
    qrypty_pw = ''.join(random.choices(string.ascii_letters + string.digits, k=16)) + "!2026"
    ac = ''.join(random.choices(string.ascii_letters + string.digits, k=32))

    print(f"\nTarget account: {user}")
    print(f"Grok password: {GROK_PASSWORD}")
    print()

    # Wait a moment before starting
    time.sleep(5)

    # Main registration loop
    MAX_ATTEMPTS = 8
    success = False

    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"--- Attempt {attempt}/{MAX_ATTEMPTS} ---")

        try:
            challenge = api_get_challenge()
        except Exception as e:
            print(f"  Error getting challenge: {e}")
            time.sleep(3)
            continue

        cid, solution = solve_captcha(challenge)
        if not solution:
            print("  Could not solve captcha, retrying...")
            time.sleep(1)
            continue

        result = api_register(user, qrypty_pw, ac, cid, solution, display)

        if result['success']:
            print(f"  ✅ SUCCESS!")
            success = True
            break
        elif 'already exists' in str(result.get('detail', '')).lower():
            print(f"  ⚠️ '{user}' taken, checking alternatives...")
            found_alt = False
            for suffix in ['02', '03', '04', '05', '06', '07', '08', '09', '10']:
                alt_user = f"boss-amirul-{suffix}"
                alt_display = f"Boss Amirul {suffix}"
                alt_ac = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
                time.sleep(2)
                try:
                    chal2 = api_get_challenge()
                    cid2, sol2 = solve_captcha(chal2)
                    if not sol2:
                        continue
                    res2 = api_register(alt_user, qrypty_pw, alt_ac, cid2, sol2, alt_display)
                    if res2['success']:
                        user, display, ac = alt_user, alt_display, alt_ac
                        print(f"  ✅ SUCCESS with '{alt_user}'")
                        success = True
                        found_alt = True
                        break
                    elif 'rate_limit' in str(res2.get('detail', '')).lower():
                        print(f"  Rate limited on alt, waiting...")
                        time.sleep(30)
                    else:
                        print(f"  '{alt_user}': {res2.get('detail', 'failed')[:80]}")
                except Exception as e:
                    print(f"  Error on alt: {e}")
                    time.sleep(3)

            if not found_alt:
                print("  ❌ All alternatives exhausted")
                sys.exit(1)
            break
        elif 'rate_limit' in str(result.get('detail', '')).lower():
            wait = min(5 * attempt, 45)
            print(f"  Rate limited. Waiting {wait}s...")
            time.sleep(wait)
        elif 'captcha' in str(result.get('detail', '')).lower():
            print("  Captcha rejected. Retrying...")
            time.sleep(2)
        else:
            print(f"  Failed: {result.get('detail', str(result))[:100]}")
            time.sleep(3)

    if not success:
        print("  ❌ Failed after max attempts")
        sys.exit(1)

    email = f"{user}@qrypty.com"
    print(f"\n✅ Account: {email}")
    print(f"   QRYPTY Password: {qrypty_pw}")
    print(f"   Access Code: {ac}")

    # Verify login
    print("\n--- Verifying login ---")
    lg = api_login(user, qrypty_pw)
    login_ok = lg.get("success") or lg.get("token") or lg.get("message") == "Login successful"
    if login_ok:
        print("  ✅ Login OK")
    else:
        print(f"  ⚠️ Login issue: {str(lg)[:100]}")
        # Try access code as password
        lg2 = api_login(user, ac)
        if lg2.get("success") or lg2.get("token"):
            print("  ✅ Login with access code works!")

    # Append to CSV
    print("\n--- Updating CSV ---")
    csv_path = "/tmp/qrypty_accounts.csv"
    try:
        with open(csv_path, 'r') as f:
            lines = f.readlines()
        last_idx = 0
        for line in lines:
            for part in line.strip().split('|'):
                if part.strip().isdigit() and int(part.strip()) > last_idx:
                    last_idx = int(part.strip())
        new_idx = last_idx + 1
        new_line = f"{len(lines)}|{new_idx},{email},{pw},{ac},{display}\n"
        with open(csv_path, 'a') as f:
            f.write(new_line)
        print(f"  ✅ CSV line {new_idx} added")
    except Exception as e:
        print(f"  CSV error: {e}")

    # Write handoff JSON
    print("\n--- Writing /tmp/option_a_ready.json ---")

    instructions = (
        "=== Grok/xAI Signup Handoff Instructions ===\n\n"
        f"1. QRYPTY EMAIL ACCESS:\n"
        f"   - Open https://qrypty.com in your phone browser\n"
        f"   - Click 'Login'\n"
        f"   - Username: {user}\n"
        f"   - Password (use either):\n"
        f"     a) '{ac}' (access code - recommended)\n"
        f"     b) '{pw}'\n"
        f"   - Navigate to Inbox to see received emails\n\n"
        f"2. GROK/XAI SIGNUP:\n"
        f"   - Open https://accounts.x.ai/signup in your phone browser\n"
        f"   - Enter email: {email}\n"
        f"   - Enter password: {GROK_PASSWORD}\n"
        f"   - Cloudflare Turnstile often auto-resolves on mobile or doesn't appear\n"
        f"   - Submit the registration form\n"
        f"   - Switch to QRYPTY inbox to find the verification email\n"
        f"   - Click the verification link (opens in browser)\n"
        f"   - Complete any profile setup\n\n"
        f"3. AFTER CREATION:\n"
        f"   - Log in at https://grok.com with {email} / {GROK_PASSWORD}\n"
        f"   - For SuperGrok: add payment method in Account Settings\n"
        f"   - You can also use the official Grok mobile app\n\n"
        f"4. TROUBLESHOOTING:\n"
        f"   - If QRYPTY login fails, try the other password option\n"
        f"   - If verification email doesn't appear within 5 min, check spam folder\n"
        f"   - If signup page doesn't load, try a different mobile browser (Chrome/Safari)\n"
        f"   - Turnstile on phone usually passes automatically\n"
    )

    output = {
        "email": email,
        "qrypty_username": user,
        "qrypty_password": pw,
        "qrypty_access_code": ac,
        "grok_password": GROK_PASSWORD,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "xai_access_reachable_here": accounts_xai_ok,
        "access_results": {k: {"reachable": v.get("reachable"), "status": v.get("status")}
                          for k, v in access_results.items()},
        "instructions": instructions.strip()
    }

    with open("/tmp/option_a_ready.json", "w") as f:
        json.dump(output, f, indent=2)
    print("  ✅ Written!")

    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"  QRYPTY Email:         {email}")
    print(f"  QRYPTY Username:      {user}")
    print(f"  QRYPTY Password:      {pw}")
    print(f"  QRYPTY Access Code:   {ac}")
    print(f"  Grok Password:        {GROK_PASSWORD}")
    print(f"  accounts.x.ai reachable from VPS: {'YES' if accounts_xai_ok else 'NO'}")
    print(f"  Handoff file:         /tmp/option_a_ready.json")


if __name__ == "__main__":
    main()
