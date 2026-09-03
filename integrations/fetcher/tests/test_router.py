"""Self-test for the Adaptive Router (Phase 2)."""
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
