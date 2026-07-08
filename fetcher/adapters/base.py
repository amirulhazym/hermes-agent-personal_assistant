"""Adapter base — owns ALL domain logic for a site.

Router does NOT hardcode domain behavior. The adapter declares its preferred
executor, retry policy, rate limit, cache TTL, content extractor, normalizer,
and validation rules. Swapping or adding a site = new adapter file only.
"""
from abc import ABC, abstractmethod
from fetcher.base import Document


class Adapter(ABC):
    domain: str = ""
    preferred_executor: str = "curl_cffi"
    max_retries: int = 2
    retry_backoff: float = 1.0
    rate_limit_seconds: float = 1.0
    cache_ttl: int = 3600

    @abstractmethod
    def extract(self, doc: Document) -> dict:
        """Return site-specific structured fields from a Document."""
        ...

    def normalize(self, doc: Document) -> Document:
        """Site-specific Document cleanup. Override if needed."""
        return doc

    def validate(self, data: dict) -> bool:
        """Assert extracted data shape. Override per site."""
        return True

    def run(self, doc: Document) -> dict:
        doc = self.normalize(doc)
        data = self.extract(doc)
        if not self.validate(data):
            doc.warnings = (doc.warnings or []) + [f"validation failed for {self.domain}"]
        return data
