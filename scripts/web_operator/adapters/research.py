from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from ..contracts import ExecutionLevel


class ResearchExecutor:
    """Thin composition adapter around existing search/extract callables."""

    def __init__(
        self,
        *,
        search_fn: Optional[Callable[[str, int], Any]] = None,
        extract_fn: Optional[Callable[[list[str]], Any]] = None,
    ) -> None:
        self.search_fn = search_fn
        self.extract_fn = extract_fn

    @property
    def level(self) -> ExecutionLevel:
        return ExecutionLevel.L2

    def capabilities(self) -> frozenset[str]:
        return frozenset({"web_search", "web_extract"})

    async def execute(self, context: Mapping[str, Any], step: Mapping[str, Any]) -> Mapping[str, Any]:
        kind = step.get("kind")
        if kind == "search":
            if self.search_fn is None:
                return {
                    "ok": False,
                    "error": "search_fn unavailable; wire to live web_search_tool",
                    "needs_live": True,
                }
            query = str(step.get("query", ""))
            limit = int(step.get("limit", 5))
            result = self.search_fn(query, limit)
            return {"ok": True, "kind": "search", "result": result, "backend": "search-cascade"}
        if kind == "extract":
            if self.extract_fn is None:
                return {
                    "ok": False,
                    "error": "extract_fn unavailable; wire to live web_extract_tool",
                    "needs_live": True,
                }
            urls = list(step.get("urls") or [])
            result = self.extract_fn(urls)
            return {"ok": True, "kind": "extract", "result": result, "backend": "hybrid-web"}
        return {"ok": False, "error": f"unknown research step {kind}"}

    async def cancel(self, task_id: str) -> None:
        return None
