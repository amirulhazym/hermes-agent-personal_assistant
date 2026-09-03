"""Core contracts: Document, Task, Capability, and the Unified Executor Interface.

All executors return EXACTLY a Document. The interface is stable; implementations
may change. Router depends on these abstractions, never on concrete tools.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import time


@dataclass
class Document:
    """Stable contract returned by EVERY executor. Never change fields without
    updating normalization + consumers (parsers, memory, analytics, RAG)."""

    # ── metadata ──
    source: str = ""                 # executor name
    url: str = ""
    domain: str = ""
    timestamp: float = field(default_factory=time.time)
    executor: str = ""
    latency: float = 0.0             # seconds
    estimated_cost: float = 0.0      # 0.0 for free tools
    verification_status: str = "UNVERIFIED"   # VERIFIED | UNVERIFIED | PARTIAL
    confidence: float = 0.0          # 0.0–1.0
    cache_status: str = "MISS"       # HIT | MISS | BYPASS
    cookies_used: bool = False
    browser_profile: Optional[str] = None
    headers: dict = field(default_factory=dict)

    # ── content ──
    content: Optional[str] = None    # raw HTML / text
    markdown: Optional[str] = None
    structured_data: Optional[dict] = None
    tables: Optional[list] = None
    links: Optional[list] = None
    images: Optional[list] = None
    artifacts: Optional[dict] = None
    screenshots: Optional[list] = None
    attachments: Optional[list] = None
    raw_response: Optional[dict] = None

    # ── diagnostics ──
    errors: Optional[list] = None
    warnings: Optional[list] = None
    telemetry: Optional[dict] = None  # memory_mb, cpu_pct, retry_count,
                                      # fallback_count, proxy_used, extraction_ms,
                                      # normalization_ms, response_size

    def to_dict(self) -> dict:
        out = {}
        for k, v in self.__dict__.items():
            if v is None and k not in ("timestamp", "latency", "estimated_cost", "confidence"):
                continue
            out[k] = v
        return out


@dataclass
class Task:
    """Typed task emitted by Planner (Phase 5)."""
    type: str = "FetchTask"   # SearchTask | FetchTask | CrawlTask | ExtractTask | CompareTask | InteractionTask
    url: Optional[str] = None
    query: Optional[str] = None
    params: dict = field(default_factory=dict)


@dataclass
class Capability:
    name: str = ""
    value: bool = False


class Executor(ABC):
    """Unified Tool Executor Interface. All 8 methods are mandatory.

    Unsupported operations return an UNVERIFIED Document via _unsupported().
    """

    name: str = "base"

    @abstractmethod
    async def fetch(self, url: str, **kwargs) -> Document: ...

    @abstractmethod
    async def search(self, query: str, **kwargs) -> Document: ...

    @abstractmethod
    async def crawl(self, url: str, **kwargs) -> list: ...

    @abstractmethod
    async def extract(self, doc: Document, **kwargs) -> Document: ...

    @abstractmethod
    async def interact(self, url: str, actions: list, **kwargs) -> Document: ...

    @abstractmethod
    async def login(self, url: str, creds: dict, **kwargs) -> Document: ...

    @abstractmethod
    async def solve_captcha(self, url: str, **kwargs) -> Document: ...

    @abstractmethod
    async def snapshot(self, url: str, **kwargs) -> Document: ...

    def _unsupported(self, method: str, url: str = "") -> Document:
        return Document(
            source=self.name,
            url=url,
            executor=self.name,
            verification_status="UNVERIFIED",
            errors=[f"{method} not supported by {self.name}"],
        )
