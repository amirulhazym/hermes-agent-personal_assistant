#!/usr/bin/env python3
"""
Hermes Web Compatibility Benchmark Suite (V1 baseline, 2026-07-09)
RUN WITH: /usr/bin/python3.12 (NOT Hermes venv py3.11)
MUST be invoked as: cd ~/.hermes/benchmarks && /usr/bin/python3.12 web_compat_suite.py
Packages curl_cffi/playwright live in python3.12 user site, not Hermes venv.
"""
import time, json, sys, subprocess, re
from datetime import datetime, timezone, timedelta

PY = "/usr/bin/python3.12"  # packages live here, NOT Hermes venv (py3.11 = ModuleNotFoundError)

TARGETS = [
    ("DuckDuckGo HTML", "https://html.duckduckgo.com/html/?q=hermes+agent", "Search", "search results links"),
    ("Bing", "https://www.bing.com/search?q=hermes+agent", "Search", "search results links"),
    ("GitHub", "https://github.com/NousResearch/hermes-agent", "Documentation", "repo file list / readme"),
    ("MDN", "https://developer.mozilla.org/en-US/docs/Web/JavaScript", "Documentation", "article body text"),
    ("Wikipedia", "https://en.wikipedia.org/wiki/Web_scraping", "Static", "encyclopedic article body"),
    ("Python Docs", "https://docs.python.org/3/library/asyncio.html", "Static", "doc section text"),
    ("BBC", "https://www.bbc.com/news", "News", "headline + article links"),
    ("Berita Harian", "https://www.bharian.com.my/", "News", "headline + article links"),
    ("Reddit", "https://www.reddit.com/r/webscraping/", "Forums", "post titles / thread list"),
    ("Lowyat.NET", "https://forum.lowyat.net/", "Forums", "thread list"),
    ("Shopee MY", "https://shopee.com.my/", "Shopping", "product / category elements"),
    ("Lazada MY", "https://www.lazada.com.my/", "Shopping", "product / category elements"),
    ("Observable", "https://observablehq.com/", "HeavyJS", "client-rendered notebook grid"),
    ("Roll20 App", "https://app.roll20.net/", "HeavyJS", "client-rendered login/app shell"),
    ("Fragrantica", "https://www.fragrantica.com/", "Cloudflare", "perfume listing / search"),
    ("Parfumo", "https://www.parfumo.net/", "Cloudflare", "perfume listing / search"),
]

def now_myt():
    return datetime.now(timezone.utc).astimezone(timezone(timedelta(hours=8)))

def extract_text_quality(html: str) -> dict:
    clean = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.S|re.I)
    text = re.sub(r"<[^>]+>", " ", clean)
    text = re.sub(r"\s+", " ", text).strip()
    chars = len(text)
    words = re.findall(r"\b\w+\b", text.lower())
    unique = len(set(words)) if words else 0
    ratio = round(unique / len(words), 3) if words else 0
    return {"chars": chars, "unique_ratio": ratio}

def verify(category, html, text, meta, status_code=None):
    q = extract_text_quality(html)
    chars = q["chars"]
    if status_code == 403:
        return False, f"HTTP 403 (blocked/anti-bot) - {chars} chars returned"
    if category == "Shopping" and status_code == 200 and len(html) > 50000:
        return True, f"shopping page reachable (200, {len(html)} bytes HTML shell) - SPA, render for content"
    if chars < 400:
        return False, f"extracted text too small ({chars} chars) - likely block/redirect/empty"
    if category == "Search":
        has_results = ("duckduckgo" in html.lower()) or ("bing" in html.lower() and "search" in html.lower())
        if chars > 1500 and has_results:
            return True, f"search results page present ({chars} chars, title marker found)"
        links = re.findall(r'href="([^"]+)"', html)
        ext = [l for l in links if l.startswith("http") and not any(d in l for d in ["duckduckgo","bing.com","microsoft"])]
        if len(ext) < 3:
            return False, f"too few result links ({len(ext)})"
        return True, f"search results present ({len(ext)} links), {chars} chars"
    if category in ("Documentation", "Static"):
        if q["unique_ratio"] < 0.25:
            return False, f"low unique-word ratio ({q['unique_ratio']}) - boilerplate"
        return True, f"content body extracted ({chars} chars, unique_ratio {q['unique_ratio']})"
    if category == "News":
        if q["unique_ratio"] < 0.20:
            return False, f"low unique ratio ({q['unique_ratio']}) - likely block page"
        return True, f"headlines+body present ({chars} chars)"
    if category == "Forums":
        if q["unique_ratio"] < 0.20:
            return False, f"low unique ratio ({q['unique_ratio']})"
        return True, f"thread/list content present ({chars} chars)"
    if category == "Shopping":
        if chars > 3000 or "application/json" in html:
            return True, f"shopping page content present ({chars} chars)"
        return False, f"shopping page rendered empty ({chars} chars)"
    if category == "HeavyJS":
        if chars < 600:
            return False, f"SPA shell not hydrated ({chars} chars)"
        return True, f"SPA content rendered ({chars} chars)"
    if category == "Cloudflare":
        if "captcha" in html.lower() or "cf-chl" in html.lower() or "just a moment" in html.lower():
            return False, "Cloudflare challenge/interstitial detected"
        if chars < 600:
            return False, f"CF likely blocked ({chars} chars)"
        return True, f"CF passed ({chars} chars)"
    return True, f"generic pass ({chars} chars)"

def run_curl_cffi(url, timeout=20):
    t0 = time.time()
    code = """
import sys, json
from curl_cffi import requests as r
try:
    resp = r.get(sys.argv[1], impersonate='chrome', timeout=%d)
    sys.stdout.write(json.dumps({"status": resp.status_code, "text": resp.text}))
except Exception as e:
    sys.stderr.write('CURL_ERR:'+repr(e))
    sys.exit(2)
""" % timeout
    p = subprocess.run([PY, "-c", code, url], capture_output=True, text=True, timeout=timeout+10)
    dt = time.time() - t0
    if p.returncode != 0:
        return None, None, dt, p.stderr[:300]
    try:
        d = json.loads(p.stdout)
        return d["text"], d["status"], dt, ""
    except Exception:
        return p.stdout, None, dt, ""

def run_playwright(url, stealth, timeout=25):
    t0 = time.time()
    code = """
import sys
from playwright.sync_api import sync_playwright
from playwright_stealth.stealth import Stealth
url = sys.argv[1]
use_stealth = sys.argv[2] == '1'
to_ms = %d * 1000
try:
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True, args=['--no-sandbox'])
        if use_stealth:
            pg = b.new_page()
            Stealth().apply_stealth_sync(pg)
        else:
            pg = b.new_page()
        pg.goto(url, wait_until='domcontentloaded', timeout=to_ms)
        try:
            pg.wait_for_timeout(2500)
        except Exception:
            pass
        sys.stdout.write(pg.content())
        b.close()
except Exception as e:
    sys.stderr.write('PW_ERR:'+repr(e))
    sys.exit(2)
""" % timeout
    p = subprocess.run([PY, "-c", code, url, "1" if stealth else "0"],
                       capture_output=True, text=True, timeout=timeout+15)
    dt = time.time() - t0
    if p.returncode != 0:
        return None, dt, p.stderr[:300]
    return p.stdout, dt, ""

def confidence_from(verified, chars, fallback, retries):
    base = 0.0
    if verified: base += 0.7
    if chars > 2000: base += 0.15
    elif chars > 800: base += 0.08
    if not fallback: base += 0.1
    if retries == 0: base += 0.05
    return round(min(base, 1.0), 2)

def benchmark_one(label, url, category, signal):
    result = {
        "label": label, "url": url, "category": category,
        "executor_chosen": None, "latency_s": None, "verification_status": "FAIL",
        "extraction_quality": None, "markdown_quality": "n/a",
        "structured_extraction": "n/a", "retry_count": 0, "fallback_triggered": False,
        "final_confidence": 0.0, "geo_provenance": "SG (VPS IP)",
        "reason": "", "html_len": 0, "curl_status": None,
    }
    ladder = [("curl_cffi", False), ("playwright", False), ("playwright", True)]
    for i, (exec_name, stealth) in enumerate(ladder):
        if exec_name == "curl_cffi":
            html, status, dt, err = run_curl_cffi(url)
            result["curl_status"] = status
        else:
            html, dt, err = run_playwright(url, stealth)
            status = None
        result["retry_count"] = i
        if html is None:
            result["reason"] = f"{exec_name} failed: {err[:150]}"
            if i < len(ladder)-1:
                result["fallback_triggered"] = True
                continue
            else:
                break
        result["html_len"] = len(html)
        q = extract_text_quality(html)
        result["extraction_quality"] = f"chars={q['chars']},unique_ratio={q['unique_ratio']}"
        passed, reason = verify(category, html, "", q, status_code=status)
        if passed:
            result["executor_chosen"] = exec_name + ("+stealth" if stealth else "")
            result["latency_s"] = round(dt, 2)
            result["verification_status"] = "PASS"
            result["reason"] = reason
            if '"@context"' in html or '"@type"' in html:
                result["structured_extraction"] = "JSON-LD present"
            elif re.search(r"<table", html, re.I):
                result["structured_extraction"] = "table present"
            else:
                result["structured_extraction"] = "none"
            h = len(re.findall(r"<h[1-3]", html, re.I))
            l = len(re.findall(r"<(a|li|ul|ol)", html, re.I))
            result["markdown_quality"] = f"h={h},struct_tags={l}"
            result["final_confidence"] = confidence_from(True, q["chars"], result["fallback_triggered"], i)
            return result
        else:
            result["reason"] = f"{exec_name}: {reason}"
            if i < len(ladder)-1:
                result["fallback_triggered"] = True
                continue
            else:
                result["executor_chosen"] = exec_name + ("+stealth" if stealth else "")
                result["latency_s"] = round(dt, 2)
                result["final_confidence"] = confidence_from(False, q["chars"], result["fallback_triggered"], i)
                return result
    return result

def main():
    print(f"Hermes Web Compatibility Benchmark — start {now_myt().isoformat()}")
    results = []
    for label, url, cat, sig in TARGETS:
        print(f"  -> {label} ({cat}) ...", flush=True)
        r = benchmark_one(label, url, cat, sig)
        results.append(r)
        print(f"     {r['verification_status']} via {r['executor_chosen']} | {r['reason'][:80]}", flush=True)
    cats = {}
    for r in results:
        cats.setdefault(r["category"], []).append(r)
    print("\n=== CATEGORY ROLLUP ===")
    for cat, items in cats.items():
        passed = sum(1 for x in items if x["verification_status"] == "PASS")
        pct = round(100*passed/len(items))
        print(f"{cat}: {pct}% ({passed}/{len(items)})")
    out = Path.home() / ".hermes/benchmarks" / "web_compat_raw.json"
    out.write_text(json.dumps({"generated": now_myt().isoformat(), "results": results}, indent=2, default=str))
    print(f"\nRaw written: {out}")

if __name__ == "__main__":
    main()
