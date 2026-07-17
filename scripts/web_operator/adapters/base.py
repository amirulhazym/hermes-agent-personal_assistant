from __future__ import annotations

from typing import Any, Mapping, Protocol, runtime_checkable

from ..contracts import ExecutionLevel


@runtime_checkable
class Executor(Protocol):
    @property
    def level(self) -> ExecutionLevel: ...

    def capabilities(self) -> frozenset[str]: ...

    async def execute(self, context: Mapping[str, Any], step: Mapping[str, Any]) -> Mapping[str, Any]: ...

    async def cancel(self, task_id: str) -> None: ...
