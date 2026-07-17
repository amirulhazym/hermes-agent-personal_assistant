from __future__ import annotations

from typing import Any, Callable, Mapping, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ..contracts import ExecutionLevel
from ..network import DestinationError, DestinationGuard


class HttpExecutor:
    def __init__(
        self,
        guard: DestinationGuard,
        *,
        max_bytes: int = 2_000_000,
        timeout: int = 20,
        opener: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.guard = guard
        self.max_bytes = max_bytes
        self.timeout = timeout
        self.opener = opener or urlopen

    @property
    def level(self) -> ExecutionLevel:
        return ExecutionLevel.L1

    def capabilities(self) -> frozenset[str]:
        return frozenset({"http_get", "http_head"})

    async def execute(self, context: Mapping[str, Any], step: Mapping[str, Any]) -> Mapping[str, Any]:
        method = str(step.get("method", "GET")).upper()
        if method not in {"GET", "HEAD"}:
            return {"ok": False, "error": "only GET/HEAD allowed"}
        url = str(step.get("url", ""))
        target = self.guard.validate_url(url)
        req = Request(target.url, method=method, headers={"User-Agent": "hermes-web-operator/1.0"})
        try:
            with self.opener(req, timeout=self.timeout) as resp:
                data = b"" if method == "HEAD" else resp.read(self.max_bytes + 1)
                if len(data) > self.max_bytes:
                    return {"ok": False, "error": "response too large"}
                return {
                    "ok": True,
                    "status": getattr(resp, "status", 200),
                    "url": self.guard.normalize_for_artifact(target.url),
                    "bytes": len(data),
                    "content_preview": data[:200].decode("utf-8", errors="replace"),
                }
        except DestinationError as exc:
            return {"ok": False, "error": str(exc)}
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            return {"ok": False, "error": f"http failed: {type(exc).__name__}"}

    async def cancel(self, task_id: str) -> None:
        return None
