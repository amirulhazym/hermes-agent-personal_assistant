#!/usr/bin/env python3
"""
QRYPTY Mail batch creator — FINAL fixed version.
Correctly extracts access_code from response, retries bad_captcha with new challenge.
"""
import re, json, csv, time, secrets, sys, os, math
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE = "https://qrypty.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 30
OUTPUT = "/tmp/qrypty_accounts.csv"

# Exclude already-owned/known names (server already has these usernames)
EXCLUDE = {
    "ai-marryjane-01",  # created by manual test, no access code extracted
    "ai-marryjane-02",  # created by batch, no access code
    "ai-marryjane-03",  # ✅ has code
    "ai-marryjane-04",  # ✅ has code
    "ai-marryjane-05",  # ✅ has code
    "ai-marryjane-06",  # created by batch, no access code
    "ai-marryjane-07",  # created by batch, no access code
    "ai-marryjane-08",  # created by batch, no access code
    "ai-marryjane-09",  # created by batch, no access code
    "ai-marryjane-10",  # created manually, ✅ has code
}

def parse_chars(svg):
    """Parse character elements, also extract font-weight."""
    chars = []
    for m in re.finditer(r'<text x="([\d.]+)" y="([\d.]+)" font-family="monospace" font-size="([\d.]+)"[^>]*font-weight="([\d]+)"[^>]*fill="(#[\da-fA-F]+)"[^>]*>(.*?)</text>', svg):
        x, y, fs, fw, fill, ch = map(str.strip, [m.group(1), m.group(2), m.group(3), m.group(4), m.group(5), m.group(6)])
        if re.fullmatch(r'[A-Za-z0-9]', ch):
            chars.append({"x": float(x), "y": float(y), "fs": float(fs), "fw": int(fw), "fill": fill.lower(), "ch": ch})
    # Fallback: try without font-weight
    if not chars:
        for m in re.finditer(r'<text x="([\d.]+)" y="([\d.]+)" font-family="monospace" font-size="([\d.]+)"[^>]*fill="(#[\da-fA-F]+)"[^>]*>(.*?)</text>', svg):
            x, y, fs, fill, ch = map(str.strip, [m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)])
            if re.fullmatch(r'[A-Za-z0-9]', ch):
                chars.append({"x": float(x), "y": float(y), "fs": float(fs), "fw": 400, "fill": fill.lower(), "ch": ch})
    return chars

def solve(svg):
    m = re.search(r'<text x="140" y="15"[^>]*>(.*?)</text>', svg)
    instr = m.group(1) if m else ""
    chars = parse_chars(svg)
    chars.sort(key=lambda c: c["x"])

    # Row-based (TOP / BOTTOM)
    if "TOP row" in instr:
        lm = re.search(r'<line[^>]*stroke-dasharray', svg)
        line_y = float(lm.group(1)) if lm else 55
        return "".join(c["ch"] for c in chars if c["y"] < line_y)
    if "BOTTOM row" in instr:
        lm = re.search(r'<line[^>]*stroke-dasharray', svg)
        line_y = float(lm.group(1)) if lm else 55
        return "".join(c["ch"] for c in chars if c["y"] > line_y)

    # Color-based
    if "BLUE" in instr:
        return "".join(c["ch"] for c in chars if c["fill"] == "#1a6bcc")
    if "RED" in instr:
        known_reds = {"#cc1a1a", "#e74c3c", "#d32f2f", "#c62828", "#ff0000", "#dc143c", "#b22222", "#cd5c5c", "#ff6347", "#ff4500"}
        red = [c for c in chars if c["fill"] in known_reds]
        if not red:
            dark_fills = {"#253542", "#2e404e", "#1a2830", "#4a6a80", "#658195", "#1a6bcc"}
            red = [c for c in chars if c["fill"] not in dark_fills]
        return "".join(c["ch"] for c in red)
    if "GREEN" in instr:
        known_greens = {"#1b8c3a", "#27ae60", "#2ecc71", "#00c853", "#4caf50", "#008000", "#228b22", "#32cd32"}
        return "".join(c["ch"] for c in chars if c["fill"] in known_greens)

    # Line-based (UNDERLINED / WITHOUT line)
    if "UNDERLINED" in instr or "WITHOUT" in instr:
        underline_lines = list(re.finditer(r'<line[^>]*stroke="#1a6bcc"[^>]*/>', svg))
        # Map each underline to its nearest char above it
        underlined_indices = set()
        for um in underline_lines:
            mx = (float(um.group(1)) + float(um.group(3))) / 2
            uy = float(um.group(2))
            cands = [c for c in chars if c["y"] < uy]
            if cands:
                near = min(cands, key=lambda c: (c["x"] - mx) ** 2)
                underlined_indices.add(chars.index(near))
        if "UNDERLINED" in instr:
            result = [chars[i] for i in sorted(underlined_indices)]
        else:
            result = [c for i, c in enumerate(chars) if i not in underlined_indices]
        return "".join(c["ch"] for c in result)

    # Size-based (BIGGEST / SMALLEST)
    if "BIGGEST" in instr or "LARGEST" in instr:
        if not chars: return ""
        # Prefer higher font-weight first, then larger font-size
        best = max(chars, key=lambda c: (c["fw"], c["fs"]))
        return best["ch"]
    if "SMALLEST" in instr:
        if not chars: return ""
        worst = min(chars, key=lambda c: (c["fw"], c["fs"]))
        return worst["ch"]

    # Shape counting
    if "CIRCLES" in instr:
        return str(len(re.findall(r'<circle[^>]*fill="none"[^>]*stroke', svg)))
    if "SQUARES" in instr or "RECTANGLES" in instr:
        all_rects = re.findall(r'<rect[^>]*width="([\d.]+)"[^>]*height="([\d.]+)"', svg)
        # Count rects where width == height and not the background (280x100)
        squares = sum(1 for w, h in all_rects if abs(float(w) - float(h)) < 1 and float(w) < 100)
        return str(squares)

    # Math: SUM of digits
    if "SUM" in instr.upper():
        total = sum(int(c["ch"]) for c in chars if c["ch"].isdigit())
        return str(total)

    # Fallback: if chars exist and a simple question, try all chars
    if "how many" in instr.lower() and chars:
        return str(len(chars))

    return "".join(c["ch"] for c in chars)

def get_challenge():
    req = Request(f"{BASE}/api/auth/challenge?lang=en", headers=UA)
    return json.loads(urlopen(req, timeout=20).read())

def register(username, nickname, cid, ans):
    payload = json.dumps({"username": username, "display_name": nickname, "captcha_id": cid, "captcha_answer": ans}).encode()
    req = Request(f"{BASE}/api/auth/register", data=payload, headers={**UA, "Content-Type": "application/json"})
    try:
        r = urlopen(req, timeout=20)
        return r.status, json.loads(r.read())
    except HTTPError as e:
        body = e.read().decode()
        try: return e.code, json.loads(body)
        except: return e.code, body

def make_password():
    words = ["Amir", "Marry", "Jane", "Cloud", "Storm", "Dream", "Light", "Ocean", "Star", "Moon",
             "Aurora", "Phoenix", "Crystal", "Shadow", "Velvet", "Crimson", "Golden", "Silver"]
    return f"{secrets.choice(words)}{secrets.randbelow(900)+100}!{secrets.choice('ABCD')}{secrets.choice('xyz')}"

def load_csv():
    accounts = []
    if os.path.exists(OUTPUT):
        with open(OUTPUT, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                email = row.get("email") or row.get("Email") or ""
                if email:
                    accounts.append({
                        "email": email,
                        "password": row.get("password") or row.get("Password") or "",
                        "access_code": row.get("access_code") or row.get("Access Code") or "",
                        "nickname": row.get("nickname") or row.get("Nickname") or ""
                    })
    return accounts

def save_csv(accounts):
    with open(OUTPUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["No", "Email", "Password", "Access Code", "Nickname"])
        for idx, a in enumerate(accounts, 1):
            w.writerow([idx, a["email"], a["password"], a["access_code"], a["nickname"]])

def main():
    print(f"{'='*55}")
    print(f"  QRYPTY Batch vFinal — Target: {TARGET} accounts")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}")

    accounts = load_csv()
    existing_users = {a["email"].split("@")[0] for a in accounts if "@" in a["email"]}
    existing_users.update(EXCLUDE)

    if accounts:
        valid = sum(1 for a in accounts if a["access_code"])
        print(f"  CSV has {len(accounts)} accounts ({valid} with access codes)")

    consecutive_429 = 0

    while len(accounts) < TARGET:
        # Find next available username
        next_num = 1
        while f"ai-marryjane-{next_num:02d}" in existing_users:
            next_num += 1

        username = f"ai-marryjane-{next_num:02d}"
        nickname = f"AI {secrets.choice(['Jane','Amy','Lee','May','Sky'])}{next_num:02d}"
        password = make_password()

        # Get challenge + solve + register with retry on bad_captcha
        success = False
        retries = 0
        max_retries = 5

        while not success and retries < max_retries:
            try:
                ch = get_challenge()
                svg = ch["image"]
                cid = ch["captcha_id"]
                answer = solve(svg)
            except Exception as e:
                print(f"  ⚠️ Challenge failed ({str(e)[:40]}), retrying...")
                time.sleep(5)
                retries += 1
                continue

            m = re.search(r'<text x="140" y="15"[^>]*>(.*?)</text>', svg)
            instr = m.group(1) if m else "?"

            if not answer:
                print(f"  ⚠️ {username}: Empty answer [{instr}], retrying...")
                retries += 1
                time.sleep(3)
                continue

            status, resp = register(username, nickname, cid, answer)

            if status == 201:
                # ✓ SUCCESS — extract access code directly
                access_code = ""
                if isinstance(resp, dict):
                    access_code = resp.get("access_code", "")
                if not access_code or len(access_code) != 32:
                    resp_str = json.dumps(resp)
                    m2 = re.search(r'"([A-Za-z0-9]{32})"', resp_str)
                    if m2: access_code = m2.group(1)

                accounts.append({
                    "email": f"{username}@qrypty.com",
                    "password": password,
                    "access_code": access_code,
                    "nickname": nickname
                })
                existing_users.add(username)
                save_csv(accounts)
                print(f"  ✅ {len(accounts):2d}/{TARGET} {username}@qrypty.com  {access_code}")
                success = True
                consecutive_429 = 0
                retries = 0

            elif status == 429:
                print(f"  ⏳ Rate limited (429). Pausing 65 min...")
                consecutive_429 += 1
                save_csv(accounts)
                time.sleep(3900)  # 65 min
                # After waiting, retry the same username
                retries += 1

            elif status == 409:
                resp_str = json.dumps(resp) if isinstance(resp, dict) else str(resp)
                if "username_taken" in resp_str.lower():
                    print(f"  ⚠️ {username}: Taken, skipping")
                    existing_users.add(username)
                    break  # next username
                else:
                    print(f"  ⚠️ {username}: Conflict ({resp_str[:60]}), retrying...")
                    retries += 1
                    time.sleep(10)

            elif status == 400:
                resp_str = json.dumps(resp) if isinstance(resp, dict) else str(resp)
                if "bad_captcha" in resp_str.lower():
                    # Wrong captcha — get a new challenge immediately
                    print(f"  🔄 {username}: Bad captcha [{instr} -> {answer}], new challenge...")
                    retries += 1
                    time.sleep(3)
                    continue  # get new challenge
                else:
                    print(f"  ❌ {username}: HTTP 400 — {resp_str[:80]}")
                    retries += 1
                    time.sleep(15)

            else:
                resp_str = json.dumps(resp) if isinstance(resp, dict) else str(resp)
                print(f"  ❌ {username}: HTTP {status} — {resp_str[:80]}")
                retries += 1
                time.sleep(15)

        if not success:
            print(f"  ✋ {username}: Giving up after {max_retries} retries")
            existing_users.add(username)  # skip this slot

        # Pacing between accounts
        if len(accounts) < TARGET:
            wait = 20 + secrets.randbelow(20)
            time.sleep(wait)

    print(f"\n{'='*55}")
    print(f"  DONE: {len(accounts)} accounts created!")
    print(f"  CSV: {OUTPUT}")
    print(f"{'='*55}")
    for idx, a in enumerate(accounts, 1):
        code = a["access_code"] if a["access_code"] else "<< MISSING >>"
        print(f"  {idx:2d}. {a['email']:35s}  {code}")

if __name__ == "__main__":
    main()
