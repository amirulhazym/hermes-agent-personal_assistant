#!/usr/bin/env python3
"""
QRYPTY REST-API account creator — PRIMARY working method (2026-07-13).
No browser needed. Solves ALL captcha types via SVG parsing.
Handles rate limit (429) + bad_captcha retry + already-taken usernames.

Usage:
  python3 qrypt_api_creator.py 30          # create up to 30 accounts
  python3 qrypt_api_creator.py 5 --start 11 # start at ai-marryjane-11

Output: CSV at /tmp/qrypt_accounts.csv (No, Email, Password, Access Code, Nickname)
  Access code is your ONLY login credential — save it.
"""
import re, json, csv, time, secrets, sys, os

BASE = "https://qrypty.com"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
OUTPUT = "/tmp/qrypt_accounts.csv"
EXCLUDE = set()  # add usernames already consumed on the server here

DARK_FILLS = {"#253542", "#2e404e", "#1a2830", "#4a6a80", "#658195", "#1a6bcc"}
BLUE = "#1a6bcc"
RED_SHADES = {"#cc1a1a","#e74c3c","#d32f2f","#c62828","#ff0000","#dc143c","#b22222","#cd5c5c","#ff6347","#ff4500"}
GREEN_SHADES = {"#1b8c3a","#27ae60","#2ecc71","#00c853","#4caf50","#008000","#228b22","#32cd32"}

def parse_chars(svg):
    chars = []
    for m in re.finditer(r'<text x="([\d.]+)" y="([\d.]+)" font-family="monospace" font-size="([\d.]+)"[^>]*font-weight="([\d]+)"[^>]*fill="(#[\da-fA-F]+)"[^>]*>(.*?)</text>', svg):
        x, y, fs, fw, fill, ch = map(str.strip, m.groups())
        if re.fullmatch(r'[A-Za-z0-9]', ch):
            chars.append({"x": float(x), "y": float(y), "fs": float(fs), "fw": int(fw), "fill": fill.lower(), "ch": ch})
    if not chars:  # fallback without font-weight
        for m in re.finditer(r'<text x="([\d.]+)" y="([\d.]+)" font-family="monospace" font-size="([\d.]+)"[^>]*fill="(#[\da-fA-F]+)"[^>]*>(.*?)</text>', svg):
            x, y, fs, fill, ch = map(str.strip, m.groups())
            if re.fullmatch(r'[A-Za-z0-9]', ch):
                chars.append({"x": float(x), "y": float(y), "fs": float(fs), "fw": 400, "fill": fill.lower(), "ch": ch})
    return chars

def solve(svg):
    m = re.search(r'<text x="140" y="15"[^>]*>(.*?)</text>', svg)
    instr = m.group(1) if m else ""
    chars = parse_chars(svg)
    chars.sort(key=lambda c: c["x"])
    if "TOP row" in instr:
        return "".join(c["ch"] for c in chars if c["y"] < 55)
    if "BOTTOM row" in instr:
        return "".join(c["ch"] for c in chars if c["y"] > 55)
    if "BLUE" in instr:
        return "".join(c["ch"] for c in chars if c["fill"] == BLUE)
    if "RED" in instr:
        red = [c for c in chars if c["fill"] in RED_SHADES]
        if not red:
            red = [c for c in chars if c["fill"] not in DARK_FILLS]
        return "".join(c["ch"] for c in red)
    if "GREEN" in instr:
        return "".join(c["ch"] for c in chars if c["fill"] in GREEN_SHADES)
    if "UNDERLINED" in instr or "WITHOUT" in instr:
        underlined = set()
        for um in re.finditer(r'<line[^>]*stroke="#1a6bcc"[^>]*/>', svg):
            mx = (float(um.group(1)) + float(um.group(3))) / 2
            uy = float(um.group(2))
            cands = [c for c in chars if c["y"] < uy]
            if cands:
                underlined.add(chars.index(min(cands, key=lambda c: (c["x"] - mx) ** 2)))
        result = [chars[i] for i in sorted(underlined)] if "UNDERLINED" in instr else [c for i, c in enumerate(chars) if i not in underlined]
        return "".join(c["ch"] for c in result)
    if "BIGGEST" in instr or "LARGEST" in instr:
        return max(chars, key=lambda c: (c["fw"], c["fs"]))["ch"] if chars else ""
    if "SMALLEST" in instr:
        return min(chars, key=lambda c: (c["fw"], c["fs"]))["ch"] if chars else ""
    if "CIRCLES" in instr:
        return str(len(re.findall(r'<circle[^>]*fill="none"[^>]*stroke', svg)))
    if "SQUARES" in instr or "RECTANGLES" in instr:
        rects = re.findall(r'<rect[^>]*width="([\d.]+)"[^>]*height="([\d.]+)"', svg)
        return str(sum(1 for w, h in rects if abs(float(w) - float(h)) < 1 and float(w) < 100))
    if "SUM" in instr.upper():
        return str(sum(int(c["ch"]) for c in chars if c["ch"].isdigit()))
    if "how many" in instr.lower() and chars:
        return str(len(chars))
    return "".join(c["ch"] for c in chars)

def get_challenge():
    from urllib.request import Request, urlopen
    return json.loads(urlopen(Request(f"{BASE}/api/auth/challenge?lang=en", headers=UA), timeout=20).read())

def register(username, nickname, cid, ans):
    from urllib.request import Request, urlopen
    from urllib.error import HTTPError
    import json as _json
    payload = _json.dumps({"username": username, "display_name": nickname, "captcha_id": cid, "captcha_answer": ans}).encode()
    req = Request(f"{BASE}/api/auth/register", data=payload, headers={**UA, "Content-Type": "application/json"})
    try:
        r = urlopen(req, timeout=20)
        return r.status, _json.loads(r.read())
    except HTTPError as e:
        body = e.read().decode()
        try:
            return e.code, _json.loads(body)
        except:
            return e.code, body

def load_existing():
    existing = []
    if os.path.exists(OUTPUT):
        with open(OUTPUT, "r") as f:
            for row in csv.DictReader(f):
                existing.append(row)
    return existing

def save(account):
    write_header = not os.path.exists(OUTPUT)
    with open(OUTPUT, "a", newline="") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["No", "Email", "Password", "Access Code", "Nickname"])
        n = len(load_existing()) + 1
        w.writerow([n, account["email"], account["password"], account["access_code"], account["nickname"]])

def main():
    target = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    start = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[2] == "--start" else 1
    existing = load_existing()
    for e in existing:
        EXCLUDE.add(e.get("Email", "").split("@")[0])
    created = len(existing)
    print(f"QRYPTY API creator — target {target}, start idx {start}, have {created}")

    idx = start
    while created < target:
        username = f"ai-marryjane-{idx:02d}"
        idx += 1
        if username in EXCLUDE:
            continue
        nickname = f"AI Jane{idx-1:02d}"
        password = f"{secrets.token_hex(2).upper()}!{secrets.choice(['Ax','Bx','Cx','Ay','Cz'])}"
        # Try up to 5 captcha attempts
        ok = False
        for attempt in range(5):
            try:
                ch = get_challenge()
            except Exception as e:
                print(f"  challenge fetch failed: {e}")
                time.sleep(5)
                continue
            ans = solve(ch["image"])
            if not ans:
                continue
            status, resp = register(username, nickname, ch["captcha_id"], ans)
            if status == 201:
                save({"email": resp["user"]["email"], "password": password, "access_code": resp.get("access_code", ""), "nickname": nickname})
                print(f"  ✅ {resp['user']['email']}  code={resp.get('access_code','?')[:8]}...")
                created += 1
                ok = True
                time.sleep(20)  # pace to avoid rate limit
                break
            elif status == 429:
                print(f"  ⏳ Rate limited. Waiting 60 min...")
                time.sleep(3600)
                break
            elif status == 409:
                print(f"  ⚠️ {username} taken, skip")
                EXCLUDE.add(username)
                ok = True
                break
            else:
                # bad_captcha or other — retry with fresh challenge
                detail = resp.get("detail", "") if isinstance(resp, dict) else str(resp)
                if "bad_captcha" in detail:
                    continue
                print(f"  ❌ {status}: {detail[:80]}")
                break
        if not ok:
            print(f"  ✋ {username} gave up after 5 tries")

if __name__ == "__main__":
    main()
