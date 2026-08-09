#!/usr/bin/env python3
"""
QRYPTY Mail batch creator — uses the working API-based solver.
Paces requests to avoid rate limits (429).
"""
import re, json, csv, time, secrets, sys
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE = "https://qrypty.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 30
OUTPUT = "/tmp/qrypty_accounts.csv"

def parse_chars(svg):
    chars = []
    for m in re.finditer(r'<text x="([\d.]+)" y="([\d.]+)" font-family="monospace" font-size="([\d.]+)"[^>]*fill="(#[\da-fA-F]+)"[^>]*>(.*?)</text>', svg):
        x, y, fs, fill, ch = map(str.strip, [m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)])
        if re.fullmatch(r'[A-Za-z0-9]', ch):
            chars.append({"x": float(x), "y": float(y), "fs": float(fs), "fill": fill.lower(), "ch": ch})
    return chars

def solve(svg):
    m = re.search(r'<text x="140" y="15"[^>]*>(.*?)</text>', svg)
    instr = m.group(1) if m else ""
    chars = parse_chars(svg)
    chars.sort(key=lambda c: c["x"])

    if "TOP row" in instr:
        lm = re.search(r'<line x1="[\d.]+" y1="([\d.]+)" x2="[\d.]+" y2="[\d.]+" stroke="#a6b8c6"[^>]*stroke-dasharray', svg)
        line_y = float(lm.group(1)) if lm else 60
        top = [c for c in chars if c["y"] < line_y]
        return "".join(c["ch"] for c in top)
    if "BOTTOM row" in instr:
        lm = re.search(r'<line x1="[\d.]+" y1="([\d.]+)" x2="[\d.]+" y2="[\d.]+"[^>]*stroke-dasharray', svg)
        line_y = float(lm.group(1)) if lm else 60
        bot = [c for c in chars if c["y"] > line_y]
        return "".join(c["ch"] for c in bot)
    if "BLUE" in instr:
        blue = [c for c in chars if c["fill"] == "#1a6bcc"]
        return "".join(c["ch"] for c in blue)
    if "RED" in instr:
        # Try multiple red shades
        red = [c for c in chars if c["fill"] in ("#cc1a1a", "#e74c3c", "#d32f2f", "#c62828", "#ff0000")]
        if not red:
            # Fallback: find non-dark/non-blue fills
            dark_fills = {"#253542", "#2e404e", "#1a2830", "#4a6a80", "#658195", "#1a6bcc"}
            red = [c for c in chars if c["fill"] not in dark_fills]
        return "".join(c["ch"] for c in red)
    if "GREEN" in instr:
        green = [c for c in chars if c["fill"] in ("#1b8c3a", "#27ae60", "#2ecc71", "#00c853", "#4caf50")]
        return "".join(c["ch"] for c in green)
    if "UNDERLINED" in instr:
        ans = []
        for um in re.finditer(r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)" stroke="#1a6bcc"[^>]*/>', svg):
            mx = (float(um.group(1)) + float(um.group(3))) / 2
            uy = float(um.group(2))
            cands = [c for c in chars if c["y"] < uy]
            if cands:
                near = min(cands, key=lambda c: (c["x"] - mx) ** 2)
                ans.append(near)
        ans.sort(key=lambda c: c["x"])
        return "".join(c["ch"] for c in ans)
    if "SMALLEST" in instr:
        if not chars: return ""
        sm = min(chars, key=lambda c: c["fs"])
        return sm["ch"]
    if "CIRCLES" in instr:
        n = len(re.findall(r'<circle[^>]*fill="none"[^>]*stroke', svg))
        return str(n)
    if "how many" in instr.lower():
        # Count characters
        return str(len(chars))
    return "".join(c["ch"] for c in chars)

def get_challenge():
    req = Request(f"{BASE}/api/auth/challenge?lang=en", headers=UA)
    return json.loads(urlopen(req, timeout=20).read())

def register(username, nickname, cid, ans):
    payload = json.dumps({
        "username": username,
        "display_name": nickname,
        "captcha_id": cid,
        "captcha_answer": ans
    }).encode()
    req = Request(
        f"{BASE}/api/auth/register",
        data=payload,
        headers={**UA, "Content-Type": "application/json"}
    )
    try:
        r = urlopen(req, timeout=20)
        return r.status, json.loads(r.read())
    except HTTPError as e:
        return e.code, e.read().decode()

def make_password():
    words = ["Amir", "Marry", "Jane", "Cloud", "Storm", "Dream", "Light", "Ocean", "Star", "Moon",
             "Aurora", "Phoenix", "Crystal", "Shadow", "Velvet", "Crimson", "Golden", "Silver"]
    return f"{secrets.choice(words)}{secrets.randbelow(900)+100}!{secrets.choice('ABCD')}{secrets.choice('xyz')}"
    # e.g. "Phoenix472!xB"

def main():
    print(f"{'='*55}")
    print(f"  QRYPTY Batch Creator — {TARGET} accounts")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}")

    accounts = []
    consecutive_fails = 0

    for i in range(TARGET):
        username = f"ai-marryjane-{i+1:02d}"
        nickname = f"AI {secrets.choice(['Jane', 'Amy', 'Lee', 'May', 'Sky'])}{secrets.randbelow(100):02d}"
        password = make_password()

        # Get challenge
        try:
            ch = get_challenge()
            svg = ch["image"]
            cid = ch["captcha_id"]
        except Exception as e:
            print(f"  ❌ #{i+1:2d} {username}: Challenge fetch failed — {str(e)[:50]}")
            consecutive_fails += 1
            if consecutive_fails >= 5:
                print(f"\n  ⛔ Too many consecutive failures. Stopping.")
                break
            time.sleep(30)
            continue

        # Solve
        answer = solve(svg)
        if not answer:
            print(f"  ⚠️ #{i+1:2d} {username}: Could not solve captcha (empty answer)")
            consecutive_fails += 1
            time.sleep(5)
            continue

        # Register
        status, resp = register(username, nickname, cid, answer)

        if status == 201:
            access_code = resp.get("access_code") or resp.get("access_code_hash") or ""
            if isinstance(resp, dict):
                access_code = resp.get("access_code", resp.get("access_code_hash", ""))
            # Try to find 32-char hex in response
            if not access_code or len(access_code) != 32:
                resp_str = json.dumps(resp)
                m = re.search(r'"([a-f0-9]{32})"', resp_str)
                if m:
                    access_code = m.group(1)

            accounts.append({
                "username": username,
                "email": f"{username}@qrypty.com",
                "nickname": nickname,
                "password": password,
                "access_code": access_code
            })
            print(f"  ✅ #{i+1:2d} {username}@qrypty.com  |  code: {access_code}  |  pass: {password}")
            consecutive_fails = 0
        elif status == 429:
            # Rate limited — wait and retry
            print(f"  ⏳ #{i+1:2d} {username}: Rate limited (429). Waiting 120s...")
            time.sleep(120)
            # Retry once
            status2, resp2 = register(username, nickname, cid, answer)
            if status2 == 201:
                access_code = ""
                resp_str = json.dumps(resp2)
                m = re.search(r'"([a-f0-9]{32})"', resp_str)
                if m: access_code = m.group(1)
                accounts.append({
                    "username": username,
                    "email": f"{username}@qrypty.com",
                    "nickname": nickname,
                    "password": password,
                    "access_code": access_code
                })
                print(f"  ✅ #{i+1:2d} {username}@qrypty.com  |  code: {access_code}  |  pass: {password}")
                consecutive_fails = 0
            else:
                print(f"  ❌ #{i+1:2d} {username}: Rate limit retry also failed ({status2})")
                consecutive_fails += 1
                # Save for later
                with open("/tmp/qrypty_pending.json", "w") as f:
                    json.dump({"last_index": i, "remaining": TARGET - i}, f)
                break
        elif status == 400:
            resp_str = resp if isinstance(resp, str) else json.dumps(resp)
            if "already" in resp_str.lower() or "taken" in resp_str.lower():
                print(f"  ⚠️ #{i+1:2d} {username}: Username taken")
                # Try with suffix
                alt_user = f"ai-marryjane-{i+1:02d}-x"
                ch2 = get_challenge()
                answer2 = solve(ch2["image"])
                status2, resp2 = register(alt_user, nickname, ch2["captcha_id"], answer2)
                if status2 == 201:
                    access_code = ""
                    m = re.search(r'"([a-f0-9]{32})"', json.dumps(resp2))
                    if m: access_code = m.group(1)
                    accounts.append({
                        "username": alt_user,
                        "email": f"{alt_user}@qrypty.com",
                        "nickname": nickname,
                        "password": password,
                        "access_code": access_code
                    })
                    print(f"  ✅ #{i+1:2d} {alt_user}@qrypty.com  |  code: {access_code}  |  pass: {password}")
                    consecutive_fails = 0
                else:
                    print(f"  ❌ #{i+1:2d} Alt username also failed ({status2})")
                    consecutive_fails += 1
            else:
                print(f"  ❌ #{i+1:2d} {username}: Bad request — {resp_str[:80]}")
                consecutive_fails += 1
        else:
            print(f"  ❌ #{i+1:2d} {username}: HTTP {status} — {str(resp)[:80]}")
            consecutive_fails += 1

        # Pace: 15s between requests to avoid rate limits
        if i < TARGET - 1:
            wait = 15 + secrets.randbelow(10)
            time.sleep(wait)

    # Save CSV
    with open(OUTPUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["No", "Email", "Password", "Access Code", "Nickname"])
        for idx, a in enumerate(accounts, 1):
            w.writerow([idx, a["email"], a["password"], a["access_code"], a["nickname"]])

    print(f"\n{'='*55}")
    print(f"  RESULTS: {len(accounts)}/{TARGET} accounts created")
    print(f"  CSV: {OUTPUT}")
    print(f"  Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}")
    for idx, a in enumerate(accounts, 1):
        print(f"  {idx:2d}. {a['email']:35s}  {a['access_code']}")

if __name__ == "__main__":
    main()
