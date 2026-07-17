from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Optional

from .adapters.base import Executor
from .artifacts import ArtifactSink, ExecutionEvent
from .approvals import ApprovalStore
from .config import OperatorConfig
from .contracts import (
    ActionClass,
    ActionIntent,
    ExecutionLevel,
    OutcomeLabel,
    PolicyVerdict,
    TaskRequest,
    TaskState,
)
from .network import DestinationGuard
from .policy import PolicyEngine
from .storage import StateStore


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ts(dt: Optional[datetime] = None) -> str:
    dt = dt or _now()
    return dt.isoformat().replace("+00:00", "Z")


@dataclass
class RunBudget:
    max_actions: int
    max_active_seconds: int
    actions: int = 0
    active_seconds: float = 0.0

    def charge_action(self) -> None:
        self.actions += 1
        if self.actions > self.max_actions:
            raise RuntimeError("L3 action budget exceeded")

    def charge_time(self, seconds: float) -> None:
        self.active_seconds += seconds
        if self.active_seconds > self.max_active_seconds:
            raise RuntimeError("L3 active time budget exceeded")


@dataclass
class WebOperator:
    config: OperatorConfig
    store: StateStore
    policy: PolicyEngine
    approvals: ApprovalStore
    guard: DestinationGuard
    executors: Mapping[ExecutionLevel, Executor] = field(default_factory=dict)
    artifact_root: Optional[Path] = None

    def __post_init__(self) -> None:
        root = Path(self.config.state_dir).expanduser()
        root.mkdir(parents=True, exist_ok=True)
        if self.artifact_root is None:
            self.artifact_root = root / "artifacts"
        self.artifact_root.mkdir(parents=True, exist_ok=True)

    def _route_for_text(self, text: str) -> list[ExecutionLevel]:
        low = text.lower()
        if re.search(r"\b(click|fill form|navigate|browse|/browse)\b", low):
            return [ExecutionLevel.L2, ExecutionLevel.L3]
        if re.search(r"\b(research|extract|summarize|read)\b", low):
            return [ExecutionLevel.L1, ExecutionLevel.L2]
        return [ExecutionLevel.L2]

    async def submit(self, request: TaskRequest) -> dict[str, Any]:
        task_id = request.task_id or str(uuid.uuid4())
        self.store.create_task(task_id, request.owner_id, TaskState.RUNNING.value)
        decision = self.policy.classify_task(request)
        route = [lvl.value for lvl in self._route_for_text(request.text)]
        medical = request.sensitivity.value == "medical"
        sink = ArtifactSink(
            self.artifact_root / task_id,
            medical=medical,
            guard=self.guard,
            retention_days=self.config.retention_days,
        )
        sink.record_event(
            ExecutionEvent(
                ts=_ts(),
                kind="task_start",
                level=decision.level.value,
                detail={"channel": request.channel, "route": route},
            )
        )
        if decision.verdict == PolicyVerdict.DENY:
            self.store.update_task(task_id, TaskState.FAILED.value)
            path = sink.finalize(
                task_id=task_id,
                state=TaskState.FAILED,
                level=ExecutionLevel.L0,
                label=OutcomeLabel.REJECTED,
                summary=decision.reason,
                route=route,
                error=decision.reason,
            )
            return {
                "task_id": task_id,
                "state": TaskState.FAILED.value,
                "label": OutcomeLabel.REJECTED.value,
                "summary": decision.reason,
                "route": route,
                "artifact_path": str(path) if path else "",
            }
        if decision.verdict == PolicyVerdict.PAUSE:
            self.store.update_task(task_id, TaskState.WAITING_APPROVAL.value)
            path = sink.finalize(
                task_id=task_id,
                state=TaskState.WAITING_APPROVAL,
                level=ExecutionLevel.L0,
                label=OutcomeLabel.PENDING,
                summary=decision.reason,
                route=route,
            )
            return {
                "task_id": task_id,
                "state": TaskState.WAITING_APPROVAL.value,
                "label": OutcomeLabel.PENDING.value,
                "summary": decision.reason,
                "route": route,
                "requires_approval": True,
                "artifact_path": str(path) if path else "",
            }

        budget = RunBudget(
            max_actions=self.config.max_l3_actions,
            max_active_seconds=self.config.max_l3_active_seconds,
        )
        last_level = ExecutionLevel.L0
        results: list[dict[str, Any]] = []
        empty_l2 = False
        for level in self._route_for_text(request.text):
            executor = self.executors.get(level)
            last_level = level
            if executor is None:
                results.append({"ok": False, "error": f"no executor for {level.value}", "needs_live": True})
                continue
            if level == ExecutionLevel.L3:
                budget.charge_action()
            step = self._default_step(request, level, empty_l2=empty_l2)
            outcome = await executor.execute(
                {"task_id": task_id, "owner_id": request.owner_id},
                step,
            )
            results.append(dict(outcome))
            sink.record_event(
                ExecutionEvent(
                    ts=_ts(),
                    kind="step",
                    level=level.value,
                    detail={
                        "ok": bool(outcome.get("ok")),
                        "needs_live": bool(outcome.get("needs_live")),
                        "error": str(outcome.get("error", ""))[:120],
                    },
                )
            )
            if level == ExecutionLevel.L2 and (
                not outcome.get("ok") or outcome.get("empty") or outcome.get("needs_interactive")
            ):
                empty_l2 = True
                # auto-escalate reason logged
                sink.record_event(
                    ExecutionEvent(
                        ts=_ts(),
                        kind="escalate",
                        level=ExecutionLevel.L3.value,
                        detail={"reason": "L2 insufficient; escalate to L3"},
                    )
                )
                if ExecutionLevel.L3 not in self._route_for_text(request.text):
                    l3 = self.executors.get(ExecutionLevel.L3)
                    if l3 is not None:
                        budget.charge_action()
                        outcome = await l3.execute(
                            {"task_id": task_id, "owner_id": request.owner_id},
                            self._default_step(request, ExecutionLevel.L3, empty_l2=True),
                        )
                        results.append(dict(outcome))
                        last_level = ExecutionLevel.L3

        ok_any = any(r.get("ok") for r in results)
        needs_live = any(r.get("needs_live") for r in results)
        state = TaskState.COMPLETED if ok_any else TaskState.FAILED
        label = (
            OutcomeLabel.PARTIAL
            if needs_live and ok_any
            else (OutcomeLabel.VALIDATED if ok_any else OutcomeLabel.UNTESTED)
        )
        summary = "completed" if ok_any else "failed or needs live wiring"
        if needs_live and not ok_any:
            summary = "live Hermes callables not wired in this environment"
            label = OutcomeLabel.UNTESTED
        self.store.update_task(task_id, state.value)
        path = sink.finalize(
            task_id=task_id,
            state=state,
            level=last_level,
            label=label,
            summary=summary,
            route=route,
            error="" if ok_any else summary,
        )
        return {
            "task_id": task_id,
            "state": state.value,
            "label": label.value,
            "summary": summary,
            "route": route,
            "results": results,
            "artifact_path": str(path) if path else "",
            "budget": {"actions": budget.actions, "active_seconds": budget.active_seconds},
        }

    def _default_step(
        self, request: TaskRequest, level: ExecutionLevel, *, empty_l2: bool = False
    ) -> dict[str, Any]:
        if level == ExecutionLevel.L1:
            # best-effort URL extraction
            m = re.search(r"https?://\S+", request.text)
            return {"method": "GET", "url": m.group(0) if m else "https://example.com"}
        if level == ExecutionLevel.L2:
            return {"kind": "search", "query": request.text, "limit": 5}
        if level == ExecutionLevel.L3:
            m = re.search(r"https?://\S+", request.text)
            return {
                "kind": "navigate",
                "url": m.group(0) if m else "https://example.com",
                "reason": "interactive" if empty_l2 else "requested",
            }
        return {}

    async def cancel(self, task_id: str) -> dict[str, Any]:
        self.store.update_task(task_id, TaskState.CANCELLED.value)
        for ex in self.executors.values():
            await ex.cancel(task_id)
        self.approvals.revoke_task(task_id)
        return {"task_id": task_id, "state": TaskState.CANCELLED.value}

    async def status(self, task_id: str) -> dict[str, Any]:
        row = self.store.get_task(task_id)
        if row is None:
            return {"task_id": task_id, "state": "missing"}
        return {
            "task_id": row["task_id"],
            "owner_id": row["owner_id"],
            "state": row["state"],
            "updated_at": row["updated_at"],
        }

    def authorize_action(self, action: ActionIntent, state_digest: str) -> Any:
        return self.policy.authorize(action, None, state_digest)
