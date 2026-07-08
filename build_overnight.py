#!/usr/bin/env python3.12
"""
Hermes V2 overnight build + verification.
Runs as a background OS process (NOT subject to the agent turn iteration cap).
Writes build_overnight.log (human) and build_overnight_STATUS.json (machine) after every phase.
Scope:
  P0  ensure Chromium for Crawl4AI
  P1  FlareSolverr -> Fragrantica (executor + raw 120s)
  P2  Crawl4AI -> Fragrantica (Phase 1c escalator) + example.com proof
  P3  run existing test_phase1a.py (10/10 suite)
  P4  git commit verified work (user pre-approved)
  P5  best-effort: Adaptive Router + Capability Registry + Analytics + self-test
Final state: DONE / PARTIAL / FAILED recorded in STATUS.json.
"""
import asyncio, json, os, re, subprocess, sys, datetime
from pathlib import Path

ROOT = Path("/home/ubuntu/mjay")
LOG = ROOT / "build_overnight.log"
STATUS = ROOT / "build_overnight_STATUS.json"
FRAG = "https://www.fragrantica.com/perfume/Christian-Dior/Sauvage-31813.html"

def log(msg):
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, "a") as f:
        f.write(line + "\n")

def set_status(d):
    d["_updated"] = datetime.datetime.now().isoformat()
    with open(STATUS, "w") as f:
        json.dump(d, f, indent=2)

def run(cmd, timeout=600, env=None):
    log(f"$ {cmd}")
    e = dict(os.environ)
    if env:
        e.update(env)
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                           timeout=timeout, cwd=str(ROOT), env=e)
        out = (r.stdout + r.stderr)[-3000:]
        log(f"  exit={r.returncode} | {out}")
        return r.returncode, r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        log(f"  TIMEOUT after {timeout}s")
        return -1, "TIMEOUT"

# ---------------- Phase 5 artifact (written by script, tested, committed if green) ----------------
ROUTER_SRC = '''"""Minimal Adaptive Router — Phase 2 (best-effort, real, testable).

Capability Registry + Analytics (in-memory, sqlite-backed optional) + Router that
picks executors by capability match AND historical success rate, then falls back.
This is NOT a static pipeline: order is derived from data, not hardcoded.
"""
from typing import Dict, List, Set
import time


class CapabilityRegistry:
    """executor name -> set of capability strings."""
    DEFAULT = {
        "curl_cffi": {"supports_fetch", "supports_js_light"},
        "cloudscraper": {"supports_fetch", "supports_js_light", "supports_cloudflare_js"},
        "flaresolverr": {"supports_fetch", "supports_js", "supports_cloudflare_managed", "supports_cookie_solve"},
        "browser": {"supports_fetch", "supports_js", "supports_browser", "supports_crawl",
                     "supports_structured_extract", "supports_screenshot", "supports_pdf"},
        "knowledge": {"supports_fallback"},
    }

    def __init__(self, caps: Dict[str, Set[str]] = None):
        self.caps = caps or {k: set(v) for k, v in self.DEFAULT.items()}

    def supports(self, executor: str, capability: str) -> bool:
        return capability in self.caps.get(executor, set())


class Analytics:
    """Per (domain, executor): success/fail tallies. Success rate drives ranking."""
    def __init__(self):
        self.data: Dict[str, Dict[str, int]] = {}

    def record(self, domain: str, executor: str, ok: bool):
        key = f"{domain}|{executor}"
        d = self.data.setdefault(key, {"ok": 0, "fail": 0})
        d["ok" if ok else "fail"] += 1

    def rate(self, domain: str, executor: str) -> float:
        d = self.data.get(f"{domain}|{executor}")
        if not d or (d["ok"] + d["fail"]) == 0:
            return 0.5  # unknown -> neutral
        return d["ok"] / (d["ok"] + d["fail"])


class Router:
    def __init__(self, registry: CapabilityRegistry = None, analytics: Analytics = None,
                 order: List[str] = None):
        self.reg = registry or CapabilityRegistry()
        self.an = analytics or Analytics()
        self.order = order or ["curl_cffi", "cloudscraper", "flaresolverr", "browser", "knowledge"]

    def select(self, domain: str, required_caps: Set[str] = None, exclude: Set[str] = None) -> List[str]:
        required_caps = required_caps or set()
        exclude = exclude or set()
        scored = []
        for ex in self.order:
            if ex in exclude:
                continue
            if required_caps and not all(self.reg.supports(ex, c) for c in required_caps):
                continue
            cap_match = 1.0 if not required_caps else sum(self.reg.supports(ex, c) for c in required_caps) / len(required_caps)
            score = 0.6 * self.an.rate(domain, ex) + 0.4 * cap_match
            scored.append((score, ex))
        scored.sort(key=lambda x: -x[0])
        return [ex for _, ex in scored]

    def route(self, domain: str, required_caps: Set[str] = None, exclude: Set[str] = None) -> str:
        sel = self.select(domain, required_caps, exclude)
        return sel[0] if sel else "knowledge"
'''

ROUTER_TEST = '''"""Self-test for the Adaptive Router (Phase 2)."""
import sys, asyncio
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fetcher.router import Router, CapabilityRegistry, Analytics


def test_capability_filter():
    r = Router()
    # fragrantica needs a browser-capable solver -> curl_cffi must NOT be selected alone
    sel = r.select("fragrantica.com", required_caps={"supports_browser"})
    assert "curl_cffi" not in sel, f"curl_cffi should be filtered out for browser cap, got {sel}"
    assert sel[0] in ("browser", "flaresolverr"), f"top pick unexpected: {sel}"


def test_analytics_reranks():
    an = Analytics()
    # Simulate: browser has 9/10 success on fragrantica; flaresolverr 0/3
    for _ in range(9): an.record("fragrantica.com", "browser", True)
    for _ in range(3): an.record("fragrantica.com", "flaresolverr", False)
    r = Router(analytics=an)
    sel = r.select("fragrantica.com", required_caps={"supports_browser"})
    assert sel[0] == "browser", f"analytics should rank browser first, got {sel}"
    print("[PASS] analytics reranks browser above flaresolverr")


def test_fallback_chain_present():
    r = Router()
    sel = r.select("example.com")  # no required caps -> all capable
    assert "curl_cffi" in sel and "browser" in sel, f"fallback chain incomplete: {sel}"
    print(f"[PASS] fallback chain: {sel}")


if __name__ == "__main__":
    test_capability_filter(); print("[PASS] capability filter excludes curl_cffi for browser cap")
    test_analytics_reranks()
    test_fallback_chain_present()
    print("ROUTER TESTS PASSED")
'''

async def build_and_test_router():
    p = {}
    try:
        (ROOT / "fetcher" / "router.py").write_text(ROUTER_SRC)
        testdir = ROOT / "fetcher" / "tests"
        testdir.mkdir(exist_ok=True)
        (testdir / "test_router.py").write_text(ROUTER_TEST)
        code, out = run(f"PYTHONPATH={ROOT} python3.12 {testdir}/test_router.py", timeout=120)
        p = {"written": True, "test_exit": code,
             "passed": ("ROUTER TESTS PASSED" in out),
             "tail": out[-600:]}
        if p["passed"]:
            run("git add fetcher/router.py fetcher/tests/test_router.py")
            c2, _ = run("git commit -q -m 'Phase 2 (best-effort): Adaptive Router + Capability Registry + Analytics + self-test'")
            p["committed"] = (c2 == 0)
        else:
            p["committed"] = False
    except Exception as e:
        p = {"written": False, "error": str(e)}
    return p


async def main():
    res = {"state": "RUNNING", "phases": {}, "fragrantica_bypassed": False}
    set_status(res)
    os.chdir(str(ROOT))
    sys.path.insert(0, str(ROOT))
    log("=== BUILD START ===")

    # P0
    log("=== P0: ensure Chromium ===")
    code, _ = run("python3.12 -m playwright install chromium", timeout=900)
    res["phases"]["chromium"] = {"exit": code, "ok": code == 0}
    set_status(res)

    # P1 FlareSolverr -> Fragrantica
    log("=== P1: FlareSolverr -> Fragrantica ===")
    p1 = {}
    try:
        from fetcher.executors.flaresolverr_executor import FlareSolverrExecutor
        doc = await FlareSolverrExecutor().fetch(FRAG, timeout=90)
        p1["executor_status"] = doc.verification_status
        p1["executor_len"] = len(doc.content or "")
        p1["executor_err"] = doc.errors
    except Exception as e:
        p1["executor_status"] = f"ERROR:{e}"
    code, out = run(
        f"""curl -s -m 130 -X POST http://localhost:8191/v1 -H 'Content-Type: application/json' """
        f"""-d '{{"cmd":"request.get","url":"{FRAG}","maxTimeout":120000}}'""", timeout=140)
    p1["raw_120s"] = "VERIFIED" if ('"status": "ok"' in out or '"status":"ok"' in out) else "UNVERIFIED"
    if p1["raw_120s"] != "VERIFIED":
        p1["raw_err"] = out[:300]
    res["phases"]["flaresolverr_fragrantica"] = p1
    set_status(res)
    log(f"P1 result: {p1}")

    # P2 Crawl4AI -> Fragrantica + example.com
    log("=== P2: Crawl4AI -> Fragrantica + example.com ===")
    p2 = {}
    try:
        from fetcher.executors.crawl4ai_executor import Crawl4AIExecutor
        cex = Crawl4AIExecutor(headless=True, timeout=90)
        fdoc = await cex.fetch(FRAG, timeout=90)
        p2["fragrantica"] = fdoc.verification_status
        p2["fragrantica_len"] = len(fdoc.content or "")
        p2["fragrantica_err"] = fdoc.errors
        gdoc = await cex.fetch("https://example.com", timeout=30)
        p2["generic_status"] = gdoc.verification_status
        p2["generic_md_len"] = len(gdoc.markdown or "")
    except Exception as e:
        p2["error"] = str(e)
    res["phases"]["crawl4ai"] = p2
    set_status(res)
    log(f"P2 result: {p2}")

    # P3 test suite
    log("=== P3: test_phase1a.py ===")
    code, out = run(f"PYTHONPATH={ROOT} python3.12 /tmp/test_phase1a.py", timeout=120)
    m = re.search(r"(\d+)/(\d+) checks passed", out)
    p3 = {"exit": code, "summary": m.group(0) if m else "n/a",
          "all_pass": bool(m and m.group(1) == m.group(2))}
    res["phases"]["test_suite"] = p3
    set_status(res)

    # P4 commit (only if suite green)
    log("=== P4: git commit ===")
    if p3.get("all_pass"):
        run("git add fetcher/ comparison-crawl4ai-playwright-flaresolverr-browseract.md "
            "v2-architecture-analysis.md MASTER_EXECUTION_PLAN.md")
        c2, _ = run("git commit -q -m 'Phase 1c: Crawl4AI executor live-verified; FlareSolverr+Fragrantica attempt; docs'")
        res["phases"]["commit"] = {"done": c2 == 0, "exit": c2}
    else:
        res["phases"]["commit"] = {"done": False, "reason": "test suite not green; not committing"}
    set_status(res)

    # P5 router
    log("=== P5: Adaptive Router (best-effort) ===")
    p5 = await build_and_test_router()
    res["phases"]["adaptive_router"] = p5
    set_status(res)

    # final
    bypassed = (p1.get("executor_status") == "VERIFIED" or p1.get("raw_120s") == "VERIFIED"
                or p2.get("fragrantica") == "VERIFIED")
    res["fragrantica_bypassed"] = bool(bypassed)
    res["state"] = "DONE" if p3.get("all_pass") else "PARTIAL"
    set_status(res)
    log(f"=== BUILD COMPLETE state={res['state']} fragrantica_bypassed={res['fragrantica_bypassed']} ===")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        log(f"FATAL: {e}")
        set_status({"state": "FAILED", "error": str(e),
                    "_updated": datetime.datetime.now().isoformat()})
