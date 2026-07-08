"""Capability Registry — loads per-domain YAML and provides capability queries.

Maps domain requirements to executor capabilities. Both domain requirements
and executor capabilities are extensible (currently 16 capability types).
Router consults this to select appropriate executors; it never hardcodes
domain-specific logic.
"""
import os
import yaml
from typing import Any, Optional


class CapabilityRegistry:
    def __init__(self, path: Optional[str] = None):
        if path is None:
            path = os.path.join(os.path.dirname(__file__), "config", "capabilities.yaml")
        self.path = os.path.expanduser(path)
        self._domains: dict[str, dict] = {}
        self._global: dict[str, bool] = {}
        self.load()

    def load(self):
        if not os.path.exists(self.path):
            self._domains = {}
            self._global = {}
            return
        with open(self.path) as f:
            data = yaml.safe_load(f) or {}
        self._global = data.get("capabilities", {})
        self._domains = data.get("domains", {})

    def get_domain_config(self, domain: str) -> dict:
        """Get full domain config merged with global defaults.
        Automatically handles www. prefix variations."""
        base = dict(self._global)
        # Try exact domain first, then without www., then with www.
        for try_domain in (domain, domain.lstrip("www."), f"www.{domain.lstrip('www.')}"):
            if try_domain in self._domains:
                config = dict(self._domains[try_domain])
                base.update(config)
                return base
        return base

    def get_capability(self, domain: str, cap: str) -> any:
        return self.get_domain_config(domain).get(cap, self._global.get(cap, False))

    def get_preferred_executor(self, domain: str) -> str:
        return self.get_domain_config(domain).get("preferred_executor", "curl_cffi")

    def get_cache_ttl(self, domain: str) -> int:
        return self.get_domain_config(domain).get("cache_ttl", 3600)

    def has_capability(self, domain: str, cap: str) -> bool:
        return bool(self.get_capability(domain, cap))

    def requires_confirmation(self, domain: str) -> bool:
        return bool(self.get_capability(domain, "requires_confirmation"))

    def list_domains(self) -> list:
        return list(self._domains.keys())

    def reload(self):
        self.load()
