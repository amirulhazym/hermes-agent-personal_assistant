#!/usr/bin/env python3
"""
QRYPTY long-running batch creator.
Creates 4 accounts per hour (rate limit), repeats until target reached.
Handles all captcha types. Saves progress to CSV after each batch.
"""
import re, json, csv, time, secrets, sys, os
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError

BASE = "https://qrypty.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
TARGET = int(sys.argv[1]) if len(sys.argv) > 1 else 30
OUTPUT = "/tmp/qrypty_accounts.csv"
MAX_PER_HOUR = 3  # Stay under the 4/hour limit
BATCH_PAUSE = 35  # seconds between attempts (pacing)
HOUR_PAUSE = 3660  # seconds to wait after hitting rate limit (~61 min)

# Already created (from earlier runs)
EXCLUDE = {"ai-marryjane-01", "ai-marryjane-03", "ai-marryjane-04", "ai-marryjane-05"}

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
        return "".join(c["ch"] for c in chars if c["y"] < line_y)
    if "BOTTOM row" in instr:
        lm = re.search(r'<line x1="[\d.]+" y1="([\d.]+)" x2="[\d.]+" y2="[\d.]+"[^>]*stroke-dasharray', svg)
        line_y = float(lm.group(1)) if lm else 60
        return "".join(c["ch"] for c in chars if c["y"] > line_y)
    if "BLUE" in instr:
        return "".join(c["ch"] for c in chars if c["fill"] == "#1a6bcc")
    if "RED" in instr:
        red = [c for c in chars if c["fill"] in ("#cc1a1a", "#e74c3c", "#d32f2f", "#c62828", "#ff0000")]
        if not red:
            dark_fills = {"#253542", "#2e404e", "#1a2830", "#4a6a80", "#658195", "#1a6bcc"}
            red = [c for c in chars if c["fill"] not in dark_fills]
        return "".join(c["ch"] for c in red)
    if "GREEN" in instr:
        return "".join(c["ch"] for c in chars if c["fill"] in ("#1b8c3a", "#27ae60", "#2ecc71", "#00c853", "#4caf50"))
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
    if "WITHOUT line" in instr:
        underlined = set()
        for um in re.finditer(r'<line x1="([\d.]+)" y1="([\d.]+)" x2="([\d.]+)" y2="([\d.]+)" stroke="#1a6bcc"[^>]*/>', svg):
            mx = (float(um.group(1)) + float(um.group(3))) / 2
            uy = float(um.group(2))
            cands = [c for c in chars if c["y"] < uy]
            if cands:
                near = min(cands, key=lambda c: (c["x"] - mx) ** 2)
                underlined.add(near["ch"] + str(near["x"]))
        non_under = [c for c in chars if (c["ch"] + str(c["x"])) not in underlined]
        return "".join(c["ch"] for c in non_under)
    if "SMALLEST" in instr:
        return min(chars, key=lambda c: c["fs"])["ch"] if chars else ""
    if "CIRCLES" in instr:
        return str(len(re.findall(r'<circle[^>]*fill="none"[^>]*stroke', svg)))
    if "SUM" in instr.upper():
        total = sum(int(c["ch"]) for c in chars if c["ch"].isdigit())
        return str(total)
    if "how many" in instr.lower():
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
        return e.code, e.read().decode()

def make_password():
    words = ["Amir", "Marry", "Jane", "Cloud", "Storm", "Dream", "Light", "Ocean", "Star", "Moon",
             "Aurora", "Phoenix", "Crystal", "Shadow", "Velvet", "Crimson", "Golden", "Silver"]
    return f"{secrets.choice(words)}{secrets.randbelow(900)+100}!{secrets.choice('ABCD')}{secrets.choice('xyz')}"

def load_existing():
    """Load already-created accounts from CSV if it exists."""
    accounts = []
    if os.path.exists(OUTPUT):
        with open(OUTPUT, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Handle both 'email' and 'Email' column names
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
    print(f"  QRYPTY Long-Run Batch — Target: {TARGET} accounts")
    print(f"  Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  Rate limit: {MAX_PER_HOUR}/hour, pacing: {BATCH_PAUSE}s between")
    print(f"{'='*55}")

    accounts = load_existing()
    existing_users = {a["email"].split("@")[0] for a in accounts}
    existing_users.update(EXCLUDE)

    if accounts:
        print(f"  Loaded {len(accounts)} existing accounts from CSV")

    attempt = 0
    while len(accounts) < TARGET:
        # Find next available username
        next_num = 1
        while f"ai-marryjane-{next_num:02d}" in existing_users:
            next_num += 1

        username = f"ai-marryjane-{next_num:02d}"
        nickname = f"AI {secrets.choice(['Jane', 'Amy', 'Lee', 'May', 'Sky'])}{next_num:02d}"
        password = make_password()

        # Get challenge
        try:
            ch = get_challenge()
            svg = ch["image"]
            cid = ch["captcha_id"]
        except Exception as e:
            print(f"  ❌ Challenge fetch failed: {str(e)[:50]}")
            time.sleep(30)
            continue

        # Solve
        answer = solve(svg)
        m = re.search(r'<text x="140" y="15"[^>]*>(.*?)</text>', svg)
        instr = m.group(1) if m else "?"

        if not answer:
            print(f"  ⚠️ {username}: Empty answer for [{instr}]")
            time.sleep(5)
            continue

        # Register
        status, resp = register(username, nickname, cid, answer)

        if status == 201:
            # Find access code in response
            access_code = ""
            resp_str = json.dumps(resp)
            m2 = re.search(r'"([a-f0-9]{32})"', resp_str)
            if m2: access_code = m2.group(1)

            accounts.append({
                "email": f"{username}@qrypty.com",
                "password": password,
                "access_code": access_code,
                "nickname": nickname
            })
            existing_users.add(username)
            save_csv(accounts)
            print(f"  ✅ {len(accounts):2d}/{TARGET} {username}@qrypty.com  |  {access_code}  |  {password}")
            attempt += 1

        elif status == 429:
            print(f"\n  ⏳ Rate limited after {attempt} accounts. Waiting {HOUR_PAUSE//60}min...")
            print(f"  Progress: {len(accounts)}/{TARGET} accounts")
            time.sleep(HOUR_PAUSE)
            attempt = 0  # Reset counter for next hour

        elif status == 409:
            print(f"  ⚠️ {username}: Username taken, skipping")
            existing_users.add(username)

        else:
            resp_preview = resp[:100] if isinstance(resp, str) else json.dumps(resp)[:100]
            print(f"  ❌ {username}: HTTP {status} — {resp_preview}")

        # Pacing between requests
        time.sleep(BATCH_PAUSE + secrets.randbelow(10))

    print(f"\n{'='*55}")
    print(f"  DONE: {len(accounts)}/{TARGET} accounts created!")
    print(f"  CSV: {OUTPUT}")
    print(f"  Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}")
    for idx, a in enumerate(accounts, 1):
        print(f"  {idx:2d}. {a['email']:35s}  {a['access_code']}")

if __name__ == "__main__":
    main()
