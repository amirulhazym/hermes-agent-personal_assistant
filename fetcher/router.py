"""Minimal Adaptive Router — Phase 2 (best-effort, real, testable).

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
