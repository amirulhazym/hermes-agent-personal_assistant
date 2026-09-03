"""Cost Optimizer — ranks executors by cost, speed, and success rate.

Ordering principle: cheapest → fastest → highest success rate.
Router uses this to try executors in optimal order.
"""
from typing import Optional


class CostOptimizer:
    """Lightweight ranker for executor ordering.

    cost_free > cost_compute > cost_paid  (cheapest first)
    Within same cost: fastest first.
    If analytics available: prefers higher success rate.
    """

    # Static cost tiers (0 = free compute, 1 = free browser, 2 = paid)
    COST_TIERS = {
        "curl_cffi": 0,
        "cloudscraper": 0,
        "flaresolverr": 0,
        "browser": 0,  # free but browser overhead
        "browseract": 2,  # paid
    }

    # Static speed tiers (0 = fast, 1 = medium, 2 = slow)
    SPEED_TIERS = {
        "curl_cffi": 0,
        "cloudscraper": 0,
        "flaresolverr": 1,
        "browser": 2,
        "browseract": 2,
    }

    def __init__(self, analytics=None):
        self.analytics = analytics

    def rank(self, domain: str, executor_names: list, domain_caps: Optional[dict] = None) -> list:
        """Return executor names in optimal try order for the given domain."""
        scored = []
        for name in executor_names:
            if domain_caps and domain_caps.get("requires_confirmation") and name == "browseract":
                continue  # skip paid unless explicitly configured
            cost = self.COST_TIERS.get(name, 3)
            speed = self.SPEED_TIERS.get(name, 3)
            success_rate = 0.5  # default
            if self.analytics:
                stats = self.analytics.get_stats(domain, name)
                if stats:
                    total = stats.get("total", 0)
                    success = stats.get("success", 0)
                    success_rate = success / max(total, 1)
            # Score: lower is better. Cost dominates, then speed, then success
            # success_rate is inverted so higher success → lower score
            score = (cost * 10000) + (speed * 100) + (1.0 - success_rate) * 10
            scored.append((score, name))
        scored.sort(key=lambda x: x[0])
        return [s[1] for s in scored]
