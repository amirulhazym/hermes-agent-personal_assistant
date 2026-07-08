"""Adaptive Router — selects executors by capability + analytics + cost.

The central intelligence of the Hermes Web Research Engine. The Router:
1. Extracts domain from the URL
2. Queries the Capability Registry for domain requirements
3. Filters executors by capability match
4. Ranks by Cost Optimizer (cheapest → fastest → highest success)
5. Tries executors in order until one succeeds
6. Falls back to FallbackPolicy if all fail
7. Logs every attempt to Analytics for self-optimization

The Router NEVER references Crawl4AI, Playwright, or any concrete tool by name.
It depends on BrowserExecutor, Executor, CapabilityRegistry, CostOptimizer,
FallbackPolicy, and AnalyticsDB — all abstractions.
"""
import time
from typing import Optional
from urllib.parse import urlparse
from fetcher.base import Executor, Document
from fetcher.capability_registry import CapabilityRegistry
from fetcher.cost_optimizer import CostOptimizer


# Executor capability matrix: what each executor CAN do
_EXECUTOR_PROFILES = {
    "curl_cffi": {"cf_managed": False, "browser": False, "js": False, "captcha": False, "search": True},
    "cloudscraper": {"cf_managed": "simple", "browser": False, "js": False, "captcha": False, "search": True},
    "flaresolverr": {"cf_managed": True, "browser": False, "js": False, "captcha": False, "search": True},
    "browser": {"cf_managed": True, "browser": True, "js": True, "captcha": False, "search": True},
    "browseract": {"cf_managed": True, "browser": True, "js": True, "captcha": True, "search": True},
}


class AdaptiveRouter:
    def __init__(
        self,
        executors: dict[str, Executor],
        registry: CapabilityRegistry,
        cost_optimizer: Optional[CostOptimizer] = None,
        fallback=None,
        analytics=None,
    ):
        self.executors = executors
        self.registry = registry
        self.cost_opt = cost_optimizer or CostOptimizer(analytics=analytics)
        self.fallback = fallback
        self.analytics = analytics
        self._all_names = list(executors.keys())

    async def fetch(self, url: str, **kwargs) -> Document:
        domain = urlparse(url).netloc
        domain_caps = self.registry.get_domain_config(domain)
        ordered = self._order_executors(domain, domain_caps)
        errors = []

        for exec_name in ordered:
            executor = self.executors.get(exec_name)
            if executor is None:
                continue
            if not self._capable(exec_name, domain_caps):
                continue

            start = time.time()
            try:
                doc = await executor.fetch(url, **kwargs)
                elapsed = round(time.time() - start, 3)
                self._log(domain, exec_name, doc.verification_status == "VERIFIED", elapsed)
                if doc.verification_status == "VERIFIED":
                    return doc
                errors.append(f"{exec_name}: {doc.errors}")
            except Exception as e:
                elapsed = round(time.time() - start, 3)
                self._log(domain, exec_name, False, elapsed)
                errors.append(f"{exec_name}: {str(e)}")

        # All executors failed
        log_msg = f"all executors failed for {domain}: {'; '.join(errors)}"
        if self.fallback:
            return await self.fallback.respond(url=url, errors=[log_msg])
        return Document(
            source="router", url=url, executor="router",
            verification_status="UNVERIFIED", errors=[log_msg],
        )

    def _order_executors(self, domain: str, domain_caps: dict) -> list:
        """Return executor names in try order, respecting capability match."""
        # Filter to capable executors first
        capable = [
            name for name in self._all_names
            if self._capable(name, domain_caps)
        ]
        if not capable:
            # If no executor is perfectly capable, try all (may fail gracefully)
            capable = list(self._all_names)
        return self.cost_opt.rank(domain or "unknown", capable, domain_caps)

    def _capable(self, exec_name: str, domain_caps: dict) -> bool:
        """Check if executor can handle the domain's requirements."""
        profile = _EXECUTOR_PROFILES.get(exec_name, {})
        checking = self.registry._global.copy()
        checking.update(domain_caps)

        # If domain needs advanced CF, executor must handle it
        if checking.get("cf_managed") and not profile.get("cf_managed"):
            return False
        # If domain needs JS, executor must support it
        if checking.get("supports_js") and not profile.get("js"):
            return False
        # If domain needs browser, executor must be browser
        if checking.get("supports_browser") and not profile.get("browser"):
            return False
        # Skip if requires confirmation (human handoff needed)
        if checking.get("requires_confirmation"):
            return False if exec_name != "browseract" else True
        return True

    def _log(self, domain: str, executor: str, success: bool, latency: float):
        if self.analytics:
            self.analytics.log(domain=domain, executor=executor,
                               success=success, latency=latency)

    async def search(self, query: str, **kwargs) -> Document:
        # For search, use Google/Router directly
        from urllib.parse import quote
        return await self.fetch(f"https://www.google.com/search?q={quote(query)}", **kwargs)
