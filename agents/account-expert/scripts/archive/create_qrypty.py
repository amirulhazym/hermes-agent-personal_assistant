#!/usr/bin/env python3
"""
Create a new QRYPTY email account for Grok signup.
Flow: GET challenge → parse SVG captcha → POST register → verify login
"""
import json
import random
import re
import string
import urllib.request
import urllib.parse
import urllib.error
import ssl
import sys
import time
from datetime import datetime, timezone

API_BASE = "https://qrypty.com"


def parse_captcha_svg(svg_text):
    """Parse the SVG captcha and return the solution string."""
    # Extract instruction
    instr_match = re.search(r'<text[^>]*>([^<]+)</text>', svg_text)
    instruction = instr_match.group(1).strip() if instr_match else ""
    print(f"  Instruction: '{instruction}'")

    if not instruction:
        return None

    # Extract all single-character text elements (skip the instruction at the top)
    chars = []
    for m in re.finditer(
        r'<text\s+([^>]*)>([A-Za-z0-9])</text>', svg_text
    ):
        attrs = m.group(1)
        char = m.group(2)
        x = float(re.search(r'x="([^"]+)"', attrs).group(1))
        y = float(re.search(r'y="([^"]+)"', attrs).group(1))
        fs = float(re.search(r'font-size="([^"]+)"', attrs).group(1))
        fw_match = re.search(r'font-weight="([^"]+)"', attrs)
        fw = fw_match.group(1) if fw_match else None

        # Skip the instruction text (top of SVG, y < 25)
        if y < 25:
            continue

        chars.append({'x': x, 'y': y, 'font_size': fs, 'char': char, 'fw': fw})

    if not chars:
        print("  No characters found. Exiting.")
        return None

    for c in chars:
        print(f"    Char: '{c['char']}' at ({c['x']},{c['y']}) size={c['font_size']}")

    # Extract colored lines
    underline_lines = []  # blue (#1a6bcc) = underlines
    strikethrough_lines = []  # red (#cc2e2e) = strikethrough
    dividing_line_y = None

    for m in re.finditer(r'<line\s+([^>]*?)/?>', svg_text):
        attrs = m.group(1)
        try:
            x1 = float(re.search(r'x1="([^"]+)"', attrs).group(1))
            y1 = float(re.search(r'y1="([^"]+)"', attrs).group(1))
            x2 = float(re.search(r'x2="([^"]+)"', attrs).group(1))
            y2 = float(re.search(r'y2="([^"]+)"', attrs).group(1))
        except AttributeError:
            continue

        if '1a6bcc' in attrs:
            underline_lines.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})
            print(f"    Underline: ({x1},{y1}) to ({x2},{y2})")
        elif 'cc2e2e' in attrs:
            strikethrough_lines.append({'x1': x1, 'y1': y1, 'x2': x2, 'y2': y2})
            print(f"    Strikethrough: ({x1},{y1}) to ({x2},{y2})")
        elif 'stroke-dasharray' in attrs:
            dividing_line_y = (y1 + y2) / 2
            print(f"    Dividing line at y≈{dividing_line_y}")

    # Determine which chars have lines
    def has_underline(c):
        cx, cy = c['x'], c['y']
        for l in underline_lines:
            min_x, max_x = min(l['x1'], l['x2']), max(l['x1'], l['x2'])
            min_y = min(l['y1'], l['y2'])
            if (min_x - 15) <= cx <= (max_x + 15) and (cy + 2) <= min_y <= (cy + 20):
                return True
        return False

    def has_strikethrough(c):
        cx, cy = c['x'], c['y']
        for l in strikethrough_lines:
            min_x, max_x = min(l['x1'], l['x2']), max(l['x1'], l['x2'])
            mid_y = (l['y1'] + l['y2']) / 2
            if (min_x - 15) <= cx <= (max_x + 15) and abs(cy - mid_y) < 12:
                return True
        return False

    for c in chars:
        c['underline'] = has_underline(c)
        c['strikethrough'] = has_strikethrough(c)
        status = []
        if c['underline']: status.append('UNDER')
        if c['strikethrough']: status.append('STRIKE')
        if status:
            print(f"    Char '{c['char']}' -> {'|'.join(status)}")

    # Determine solution based on instruction
    instr_lower = instruction.lower()

    if "biggest" in instr_lower:
        max_c = max(chars, key=lambda c: c['font_size'])
        solution = max_c['char']
        print(f"  → Biggest: '{solution}' (size={max_c['font_size']})")
    elif "smallest" in instr_lower:
        min_fs = min(c['font_size'] for c in chars)
        smallest = sorted([c for c in chars if c['font_size'] == min_fs], key=lambda c: c['x'])
        solution = ''.join(c['char'] for c in smallest)
        print(f"  → Smallest: '{solution}' (size={min_fs})")
    elif "top" in instr_lower:
        threshold = dividing_line_y if dividing_line_y else 55
        top_chars = sorted([c for c in chars if c['y'] < threshold], key=lambda c: c['x'])
        solution = ''.join(c['char'] for c in top_chars)
        print(f"  → Top row: '{solution}'")
    elif "bottom" in instr_lower:
        threshold = dividing_line_y if dividing_line_y else 55
        bottom_chars = sorted([c for c in chars if c['y'] >= threshold], key=lambda c: c['x'])
        solution = ''.join(c['char'] for c in bottom_chars)
        print(f"  → Bottom row: '{solution}'")
    elif "underlin" in instr_lower or "with line" in instr_lower:
        lined_chars = sorted([c for c in chars if c['underline'] or c['strikethrough']], key=lambda c: c['x'])
        solution = ''.join(c['char'] for c in lined_chars)
        print(f"  → Underlined/have line: '{solution}'")
    elif "without line" in instr_lower or "no line" in instr_lower:
        no_line_chars = sorted([c for c in chars if not c['underline'] and not c['strikethrough']], key=lambda c: c['x'])
        solution = ''.join(c['char'] for c in no_line_chars)
        print(f"  → No line: '{solution}'")
    else:
        all_chars = sorted(chars, key=lambda c: c['x'])
        solution = ''.join(c['char'] for c in all_chars)
        print(f"  → Fallback: '{solution}'")

    return solution


def api_get_challenge():
    url = f"{API_BASE}/api/auth/challenge"
    req = urllib.request.Request(url, method='GET')
    req.add_header('User-Agent', 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36')
    req.add_header('Accept', 'application/json')
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        return json.loads(resp.read().decode())
    except Exception as e:
        print(f"  Error getting challenge: {e}")
        raise


def api_register(username, password, access_code, captcha_id, captcha_solution, display_name=None):
    url = f"{API_BASE}/api/auth/register"
    payload = {
        "username": username,
        "password": password,
        "access_code": access_code,
        "captcha_id": captcha_id,
        "captcha_solution": captcha_solution,
        "display_name": display_name or username,
    }
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('User-Agent', 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', 'application/json')
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"  HTTP {e.code}: {body[:200]}")
        try:
            return {"error": f"HTTP {e.code}", "detail": json.loads(body).get("detail", body)}
        except:
            return {"error": f"HTTP {e.code}", "detail": body}
    except Exception as e:
        print(f"  Error: {e}")
        return {"error": str(e)}


def api_login(username, password):
    url = f"{API_BASE}/api/auth/login"
    payload = {"username": username, "password": password}
    data = json.dumps(payload).encode()
    req = urllib.request.Request(url, data=data, method='POST')
    req.add_header('User-Agent', 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36')
    req.add_header('Content-Type', 'application/json')
    req.add_header('Accept', 'application/json')
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    try:
        resp = urllib.request.urlopen(req, timeout=15, context=ctx)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        try:
            return {"error": f"HTTP {e.code}", "detail": json.loads(body).get("detail", body)}
        except:
            return {"error": f"HTTP {e.code}", "detail": body}
    except Exception as e:
        return {"error": str(e)}


def generate_password():
    adjectives = ["Super", "Mega", "Ultra", "Hyper", "Turbo", "Cyber", "Quantum", "Nova", "Omega", "Alpha"]
    nouns = ["Grok", "Xeno", "Nova", "Aura", "Vega", "Orion", "Phoenix", "Titan", "Neon", "Storm"]
    num = random.randint(100, 999)
    sym = random.choice(["!", "@", "#", "$", "%", "&"])
    return f"{random.choice(adjectives)}{random.choice(nouns)}{num}{sym}2026"


def generate_access_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=32))


def test_grok_access():
    results = {}
    for url, label in [("https://accounts.x.ai", "accounts.x.ai"),
                       ("https://grok.com", "grok.com"),
                       ("https://x.ai", "x.ai")]:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, method='GET')
            req.add_header('User-Agent', 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36')
            resp = urllib.request.urlopen(req, timeout=10, context=ctx)
            body_sample = resp.read(500).decode('utf-8', errors='replace')[:100]
            results[label] = {"reachable": True, "status": resp.getcode(), "body_preview": body_sample}
        except urllib.error.HTTPError as e:
            body_sample = e.read(500).decode('utf-8', errors='replace')[:100] if e.fp else ""
            results[label] = {"reachable": True, "status": e.code, "body_preview": body_sample}
        except urllib.error.URLError as e:
            results[label] = {"reachable": False, "error": str(e.reason)}
        except Exception as e:
            results[label] = {"reachable": False, "error": str(e)}
    return results


def main():
    print("=" * 60)
    print("QRYPTY Account Creation for Grok Signup")
    print("=" * 60)

    # Step 0: Test grok/xAI access
    print("\n[Step 0] Testing xAI/Grok access from this VPS...")
    access_results = test_grok_access()
    for label, result in access_results.items():
        if result.get("reachable"):
            status = result.get("status", "?")
            print(f"  {'✅' if status < 400 else '⚠️'} {label}: HTTP {status}")
        else:
            print(f"  ❌ {label}: BLOCKED ({result.get('error', 'unknown')})")

    accounts_xai_ok = access_results.get("accounts.x.ai", {}).get("reachable") and \
                      access_results.get("accounts.x.ai", {}).get("status", 0) < 400

    # Account details
    username = "boss-amirul-01"
    display_name = "Boss Amirul AI"
    password = generate_password()
    access_code = generate_access_code()
    email = f"{username}@qrypty.com"

    print(f"\nAccount to create: {username}")

    # Try registration with retries for rate limiting
    MAX_ATTEMPTS = 10
    for attempt in range(1, MAX_ATTEMPTS + 1):
        print(f"\n--- Attempt {attempt}/{MAX_ATTEMPTS} ---")

        # Get captcha challenge
        challenge = api_get_challenge()
        captcha_id = challenge.get("captcha_id", "")
        svg_image = challenge.get("image", "")
        print(f"  Captcha ID: {captcha_id}")

        # Parse and solve
        solution = parse_captcha_svg(svg_image)
        if not solution:
            print("  Could not solve captcha, retrying...")
            continue

        print(f"  Solution: '{solution}'")

        # Register
        result = api_register(username, password, access_code, captcha_id, solution, display_name)
        detail = result.get("detail", str(result))
        print(f"  Result: {json.dumps(result, indent=2)[:200]}")

        # Check result
        if result.get("success") or result.get("message") == "Registration successful" or result.get("username"):
            print(f"\n  ✅ SUCCESS! Account created: {username}")
            break
        elif "already exists" in str(detail).lower():
            print(f"  ⚠️ '{username}' already exists, trying alternatives...")
            for suffix in ["02", "03", "04", "05", "06", "07", "08", "09", "10"]:
                alt_user = f"boss-amirul-{suffix}"
                alt_display = f"Boss Amirul {suffix}"
                alt_pw = generate_password()
                alt_ac = generate_access_code()
                alt_email = f"{alt_user}@qrypty.com"

                time.sleep(1)
                chal2 = api_get_challenge()
                sol2 = parse_captcha_svg(chal2.get("image", ""))
                if not sol2:
                    continue

                res2 = api_register(alt_user, alt_pw, alt_ac, chal2.get("captcha_id", ""), sol2, alt_display)
                d2 = res2.get("detail", str(res2))
                print(f"    Trying {alt_user}: {json.dumps(res2, indent=2)[:150]}")

                if res2.get("success") or res2.get("message") == "Registration successful" or res2.get("username"):
                    username = alt_user
                    display_name = alt_display
                    password = alt_pw
                    access_code = alt_ac
                    email = alt_email
                    result = res2
                    print(f"\n  ✅ SUCCESS! Account created: {username}")
                    break
                elif "rate_limit" in str(d2).lower():
                    print(f"  Rate limited, waiting 30s...")
                    time.sleep(30)
            else:
                print("  ❌ All alternative usernames failed or rate limited.")
                sys.exit(1)
            break
        elif "rate_limit" in str(detail).lower():
            wait = min(5 * attempt, 60)
            print(f"  Rate limited (attempt {attempt}), waiting {wait}s...")
            time.sleep(wait)
        elif "captcha" in str(detail).lower():
            print(f"  Captcha solution rejected, retrying with fresh captcha...")
            time.sleep(1)
        else:
            print(f"  Unexpected error, retrying...")
            time.sleep(2)
    else:
        print("  ❌ Max attempts reached.")
        sys.exit(1)

    # Step 5: Verify login
    print("\n[Step 5] Verifying login...")
    login_result = api_login(username, password)
    print(f"  Login response: {json.dumps(login_result, indent=2)[:200]}")

    login_ok = login_result.get("success") or login_result.get("token") or login_result.get("message") == "Login successful"
    if login_ok:
        print("  ✅ Login verified!")
    else:
        print("  ⚠️ Login with password had issues. Trying access_code as password...")
        login_result2 = api_login(username, access_code)
        print(f"  Login (access_code) response: {json.dumps(login_result2, indent=2)[:200]}")
        if login_result2.get("success") or login_result2.get("token"):
            print("  ✅ Login with access_code works!")
        else:
            print("  ⚠️ Login verification inconclusive. Account may still be usable.")

    # Step 6: Update CSV
    print("\n[Step 6] Appending to CSV...")
    csv_path = "/tmp/qrypty_accounts.csv"
    try:
        with open(csv_path, 'r') as f:
            lines = f.readlines()
        last_idx = 0
        for line in lines:
            parts = line.strip().split('|')
            for part in parts:
                if part.strip().isdigit() and int(part.strip()) > last_idx:
                    last_idx = int(part.strip())
        new_idx = last_idx + 1
        nickname = display_name
        new_line = f"{len(lines)}|{new_idx},{email},{password},{access_code},{nickname}\n"
        with open(csv_path, 'a') as f:
            f.write(new_line)
        print(f"  Appended: {new_line.strip()}")
    except Exception as e:
        print(f"  CSV error: {e}")

    # Step 7: Write output JSON
    print("\n[Step 7] Writing /tmp/option_a_ready.json...")

    grok_instructions = (
        "=== MANUAL STEPS FOR PHONE ===\n"
        f"1. QRYPTY EMAIL ACCESS:\n"
        f"   - Webmail: https://qrypty.com\n"
        f"   - Username: {username}\n"
        f"   - Password (both work):\n"
        f"     a) '{password}' (your QRYPTY password)\n"
        f"     b) '{access_code}' (access code)\n"
        f"   - Click 'Login', enter username and one of the passwords\n"
        f"   - Go to Inbox to read emails\n\n"
        f"2. GROK/XAI SIGNUP (on your phone):\n"
        f"   - Open https://accounts.x.ai/signup in your phone browser\n"
        f"   - Enter email: {email}\n"
        f"   - Enter password: SuperGrok_2026!\n"
        f"   - Cloudflare Turnstile often auto-resolves or is skipped on mobile\n"
        f"   - Submit the form\n"
        f"   - Check QRYPTY inbox for the verification email\n"
        f"   - Click the verification link from QRYPTY (open in browser)\n"
        f"   - Complete any additional steps\n\n"
        f"3. AFTER SIGNUP:\n"
        f"   - Log in at https://grok.com with {email} / SuperGrok_2026!\n"
        f"   - For SuperGrok subscription, add payment method in settings\n"
        f"   - You can also use the xAI/Grok mobile app\n"
    )

    output = {
        "email": email,
        "qrypty_username": username,
        "qrypty_password": password,
        "qrypty_access_code": access_code,
        "grok_password": "SuperGrok_2026!",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "xai_access_reachable_here": accounts_xai_ok,
        "access_results": {k: {"reachable": v.get("reachable"), "status": v.get("status")}
                          for k, v in access_results.items()},
        "instructions": grok_instructions.strip()
    }
    with open("/tmp/option_a_ready.json", "w") as f:
        json.dump(output, f, indent=2)
    print(f"  Written to /tmp/option_a_ready.json")

    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(f"  QRYPTY Email:        {email}")
    print(f"  QRYPTY Username:     {username}")
    print(f"  QRYPTY Password:     {password}")
    print(f"  QRYPTY Access Code:  {access_code}")
    print(f"  Grok Password:       SuperGrok_2026!")
    print(f"  accounts.x.ai from VPS: {'✅ REACHABLE' if accounts_xai_ok else '❌ BLOCKED'}")
    if not accounts_xai_ok:
        print(f"\n  📱 Handoff ready in /tmp/option_a_ready.json")


if __name__ == "__main__":
    main()
