"""CLI — Hermes integration for the Web Research Engine.

Usage:
  python -m fetcher.cli fetch <url>                        # Single fetch
  python -m fetcher.cli search <query>                     # Google search
  python -m fetcher.cli status                             # Executor + analytics status
  python -m fetcher.cli stats [domain]                     # Analytics stats
"""
import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fetcher.capability_registry import CapabilityRegistry
from fetcher.cost_optimizer import CostOptimizer
from fetcher.router import AdaptiveRouter
from fetcher.fallback import FallbackPolicy
from fetcher.analytics import AnalyticsDB
from fetcher.domain_memory import DomainMemory
from fetcher.executors.curl_cffi_executor import CurlCffiExecutor
from fetcher.executors.cloudscraper_executor import CloudscraperExecutor
from fetcher.executors.flaresolverr_executor import FlareSolverrExecutor
from fetcher.executors.crawl4ai_executor import Crawl4AIExecutor


def _build_router():
    analytics = AnalyticsDB()
    memory = DomainMemory()
    reg = CapabilityRegistry()
    executors = {}
    try:
        executors["curl_cffi"] = CurlCffiExecutor()
    except Exception:
        pass
    try:
        executors["cloudscraper"] = CloudscraperExecutor()
    except Exception:
        pass
    try:
        executors["flaresolverr"] = FlareSolverrExecutor()
    except Exception:
        pass
    try:
        executors["browser"] = Crawl4AIExecutor(headless=True, timeout=60, verbose=False)
    except Exception:
        pass
    return AdaptiveRouter(
        executors=executors,
        registry=reg,
        cost_optimizer=CostOptimizer(analytics=analytics),
        fallback=FallbackPolicy(),
        analytics=analytics,
        domain_memory=memory,
    ), analytics


async def cmd_fetch(args):
    if not args:
        print("Usage: cli fetch <url>")
        return
    router, _ = _build_router()
    doc = await router.fetch(args[0])
    print(f"Source:    {doc.source}")
    print(f"Executor:  {doc.executor}")
    print(f"Status:    {doc.verification_status}")
    print(f"Latency:   {doc.latency}s")
    print(f"Confidence: {doc.confidence}")
    print(f"Content:   {len(doc.content or '')} bytes (html) / {len(doc.markdown or '')} chars (markdown)")
    if doc.errors:
        print(f"Errors:    {'; '.join(doc.errors)}")
    if doc.warnings:
        print(f"Warnings:  {'; '.join(doc.warnings)}")
    # Pretty print structured data if any
    if doc.structured_data:
        print(f"\nStructured data: {json.dumps(doc.structured_data, indent=2, default=str)[:1000]}")


async def cmd_search(args):
    if not args:
        print("Usage: cli search <query>")
        return
    router, _ = _build_router()
    doc = await router.search(" ".join(args))
    print(f"Source:    {doc.source}")
    print(f"Executor:  {doc.executor}")
    print(f"Status:    {doc.verification_status}")
    print(f"Content:   {len(doc.content or '')} bytes / {len(doc.markdown or '')} markdown chars")
    if doc.errors:
        print(f"Errors:    {'; '.join(doc.errors)}")


def cmd_status(args):
    analytics = AnalyticsDB()
    reg = CapabilityRegistry()
    print("Hermes Web Research Engine — Status")
    print("===================================")
    print(f"\nCapabilities loaded: {len(reg.list_domains())} domains")
    for d in reg.list_domains():
        pref = reg.get_preferred_executor(d)
        print(f"  {d}: preferred={pref}")
    stats = analytics.get_stats()
    print(f"\nAnalytics: {stats.get('total', 0)} total fetches logged")
    if stats.get('total', 0) > 0:
        print(f"  success rate: {stats.get('success_rate', 0)*100:.0f}%")
    # Check executors
    print("\nExecutors:")
    import subprocess
    checks = {}
    try:
        import curl_cffi; checks["curl_cffi"] = "OK"
    except ImportError:
        checks["curl_cffi"] = "MISSING"
    try:
        import cloudscraper; checks["cloudscraper"] = "OK"
    except ImportError:
        checks["cloudscraper"] = "MISSING"
    try:
        import crawl4ai; checks["crawl4ai"] = "OK"
    except ImportError:
        checks["crawl4ai"] = "MISSING"
    # FlareSolverr: check Docker container
    try:
        r = subprocess.run(["curl", "-s", "-X", "POST", "http://localhost:8191/v1",
                           "-H", "Content-Type: application/json",
                           "-d", '{"cmd":"sessions.list"}'],
                          capture_output=True, text=True, timeout=5)
        checks["flaresolverr (Docker)"] = "OK" if "ok" in r.stdout else "NO RESPONSE"
    except Exception:
        checks["flaresolverr (Docker)"] = "MISSING (Docker not running)"


def cmd_stats(args):
    analytics = AnalyticsDB()
    domain = args[0] if args else None
    if domain:
        stats = analytics.get_stats(domain)
        print(f"Stats for {domain}:")
        print(json.dumps(stats, indent=2))
    else:
        stats = analytics.get_stats()
        print(f"All domains:")
        print(json.dumps(stats, indent=2))


async def main():
    if len(sys.argv) < 2:
        print("Usage: cli fetch|search|status|stats [args...]")
        return
    cmd = sys.argv[1]
    args = sys.argv[2:]
    handlers = {
        "fetch": cmd_fetch,
        "search": cmd_search,
        "status": cmd_status,
        "stats": cmd_stats,
    }
    h = handlers.get(cmd)
    if not h:
        print(f"Unknown command: {cmd}")
        return
    if asyncio.iscoroutinefunction(h):
        await h(args)
    else:
        h(args)


if __name__ == "__main__":
    asyncio.run(main())
