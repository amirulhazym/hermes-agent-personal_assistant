"""Adaptive Router — selects executors by capability + analytics + cost + domain memory.

The Router:
1. Extracts domain from URL, normalizes (removes www.)
2. Queries CapabilityRegistry for domain requirements
3. Filters executors by capability match
4. Ranks by CostOptimizer (cheapest → fastest → highest success rate)
5. Tries executors in optimal order until one returns VERIFIED
6. Falls back to FallbackPolicy if all fail
7. Logs to AnalyticsDB + DomainMemory for self-optimization

Router NEVER references Crawl4AI, Playwright, or any concrete tool by name.
BrowserExecutor is the abstraction — implementation is swappable.
"""
import time
from typing import Optional
from urllib.parse import urlparse

from fetcher.base import Executor, Document
from fetcher.capability_registry import CapabilityRegistry
from fetcher.cost_optimizer import CostOptimizer


# Executor capability matrix: what each executor CAN do (not what sites need)
_EXECUTOR_PROFILES = {
    "curl_cffi": {"cf_managed": False, "browser": False, "js": False, "captcha": False, "search": True},
    "cloudscraper": {"cf_managed": "simple", "browser": False, "js": False, "captcha": False, "search": True},
    "flaresolverr": {"cf_managed": True, "browser": False, "js": False, "captcha": False, "search": True},
    "browser": {"cf_managed": True, "browser": True, "js": True, "captcha": False, "search": True},
    "browseract": {"cf_managed": True, "browser": True, "js": True, "captcha": True, "search": True},
}


def _domain_key(url: str) -> str:
    """Normalize domain: strip www. for registry lookup."""
    domain = urlparse(url).netloc.lower()
    return domain.lstrip("www.")


class AdaptiveRouter:
    def __init__(
        self,
        executors: dict,
        registry: CapabilityRegistry,
        cost_optimizer: CostOptimizer = None,
        fallback=None,
        analytics=None,
        domain_memory=None,
    ):
        self.executors = executors
        self.registry = registry
        self.cost_opt = cost_optimizer or CostOptimizer(analytics=analytics)
        self.fallback = fallback
        self.analytics = analytics
        self.domain_memory = domain_memory
        self._all_names = list(executors.keys())

    async def fetch(self, url: str, **kwargs) -> Document:
        domain = _domain_key(url)
        domain_caps = self.registry.get_domain_config(domain)
        ordered = self._order(domain, domain_caps)
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
                ok = doc.verification_status == "VERIFIED"
                self._log(domain, exec_name, ok, elapsed)
                if ok:
                    self._record_memory(domain, exec_name, ok, elapsed)
                    return doc
                errors.append(f"{exec_name}: {doc.errors}")
            except Exception as e:
                elapsed = round(time.time() - start, 3)
                self._log(domain, exec_name, False, elapsed)
                errors.append(f"{exec_name}: {str(e)}")

        err_summary = f"all executors failed for {domain}: {'; '.join(errors)}"
        if self.fallback:
            return await self.fallback.respond(url=url, errors=[err_summary])
        return Document(
            source="router", url=url, executor="router",
            verification_status="UNVERIFIED", errors=[err_summary],
        )

    async def search(self, query: str, **kwargs) -> Document:
        from urllib.parse import quote
        return await self.fetch(f"https://www.google.com/search?q={quote(query)}", **kwargs)

    def _order(self, domain: str, domain_caps: dict) -> list:
        capable = [n for n in self._all_names if self._capable(n, domain_caps)]
        if not capable:
            capable = list(self._all_names)
        return self.cost_opt.rank(domain, capable, domain_caps)

    def _capable(self, exec_name: str, domain_caps: dict) -> bool:
        profile = _EXECUTOR_PROFILES.get(exec_name, {})
        if domain_caps.get("cf_managed") and not profile.get("cf_managed"):
            return False
        if domain_caps.get("supports_js") and not profile.get("js"):
            return False
        if domain_caps.get("supports_browser") and not profile.get("browser"):
            return False
        if domain_caps.get("requires_confirmation") and exec_name != "browseract":
            return False
        return True

    def _log(self, domain: str, executor: str, success: bool, latency: float):
        if self.analytics:
            self.analytics.log(domain=domain, executor=executor,
                               success=success, latency=latency,
                               response_size=0)

    def _record_memory(self, domain: str, executor: str, success: bool, latency: float):
        if self.domain_memory:
            self.domain_memory.record(domain=domain, executor=executor,
                                      success=success, latency=latency)
