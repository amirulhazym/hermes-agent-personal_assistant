from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from ..contracts import ExecutionLevel
from ..network import DestinationGuard


class ObservationSuspended(RuntimeError):
    pass


class NativeBrowserExecutor:
    """Sole native Hermes L3 integration surface.

    Live callables are injected after Phase 0 discovery. Without them, methods
    return structured needs_live errors instead of inventing imports.
    """

    def __init__(
        self,
        guard: DestinationGuard,
        *,
        navigate: Optional[Callable[..., Any]] = None,
        snapshot: Optional[Callable[..., Any]] = None,
        click: Optional[Callable[..., Any]] = None,
        type_text: Optional[Callable[..., Any]] = None,
        cleanup: Optional[Callable[..., Any]] = None,
        observation_allowed: Optional[Callable[[], bool]] = None,
    ) -> None:
        self.guard = guard
        self.navigate = navigate
        self.snapshot = snapshot
        self.click = click
        self.type_text = type_text
        self.cleanup = cleanup
        self.observation_allowed = observation_allowed or (lambda: True)
        self.actions = 0

    @property
    def level(self) -> ExecutionLevel:
        return ExecutionLevel.L3

    def capabilities(self) -> frozenset[str]:
        return frozenset(
            {
                "browser_navigate",
                "browser_snapshot",
                "browser_click",
                "browser_type",
                "browser_cleanup",
            }
        )

    def _obs(self) -> None:
        if not self.observation_allowed():
            raise ObservationSuspended("capture suspended during private takeover")

    async def execute(self, context: Mapping[str, Any], step: Mapping[str, Any]) -> Mapping[str, Any]:
        kind = step.get("kind")
        task_id = context.get("task_id")
        self.actions += 1
        try:
            if kind == "navigate":
                url = str(step.get("url", ""))
                self.guard.validate_url(url)
                if self.navigate is None:
                    return {"ok": False, "error": "browser_navigate not wired", "needs_live": True}
                self._obs()
                result = self.navigate(url, task_id)
                return {"ok": True, "kind": kind, "result": result, "action_count": self.actions}
            if kind == "snapshot":
                if self.snapshot is None:
                    return {"ok": False, "error": "browser_snapshot not wired", "needs_live": True}
                self._obs()
                result = self.snapshot(bool(step.get("full", False)), task_id, step.get("user_task"))
                return {"ok": True, "kind": kind, "result": result, "action_count": self.actions}
            if kind == "click":
                if self.click is None:
                    return {"ok": False, "error": "browser_click not wired", "needs_live": True}
                self._obs()
                result = self.click(str(step.get("ref", "")), task_id)
                return {"ok": True, "kind": kind, "result": result, "action_count": self.actions}
            if kind == "type":
                if self.type_text is None:
                    return {"ok": False, "error": "browser_type not wired", "needs_live": True}
                self._obs()
                result = self.type_text(str(step.get("ref", "")), str(step.get("text", "")), task_id)
                return {"ok": True, "kind": kind, "result": result, "action_count": self.actions}
            return {"ok": False, "error": f"unknown browser step {kind}"}
        except ObservationSuspended as exc:
            return {"ok": False, "error": str(exc), "suspended": True}

    async def cancel(self, task_id: str) -> None:
        if self.cleanup is not None:
            self.cleanup(task_id)
