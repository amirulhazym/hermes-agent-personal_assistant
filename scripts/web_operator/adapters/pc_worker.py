from __future__ import annotations

from typing import Any, Mapping, Optional

from ..contracts import ExecutionLevel
from ..grants import GrantIssuer, GrantRequest, SignedGrant
from ..pc_protocol import ProtocolMessage, WorkerSession, WorkerState


class PcWorkerExecutor:
    """VPS-side control plane for enrolled outbound Windows workers."""

    def __init__(self, issuer: Optional[GrantIssuer] = None) -> None:
        self.issuer = issuer
        self.session = WorkerSession()
        self.inbound_listen = False  # hard rule: no inbound listener
        self._last_grant: Optional[SignedGrant] = None

    @property
    def level(self) -> ExecutionLevel:
        return ExecutionLevel.L4

    def capabilities(self) -> frozenset[str]:
        return frozenset({"pc_availability", "pc_grant", "pc_stop"})

    def note_worker_message(self, message: ProtocolMessage, now: float) -> WorkerState:
        return self.session.on_message(message, now)

    def issue_grant(self, request: GrantRequest) -> SignedGrant:
        if self.inbound_listen:
            raise RuntimeError("inbound listener forbidden")
        if self.session.state not in {WorkerState.AVAILABLE, WorkerState.AUTHENTICATED}:
            raise RuntimeError("worker not available")
        if self.issuer is None:
            raise RuntimeError("grant issuer not configured")
        signed = self.issuer.issue(request)
        self._last_grant = signed
        return signed

    async def execute(self, context: Mapping[str, Any], step: Mapping[str, Any]) -> Mapping[str, Any]:
        kind = step.get("kind")
        if kind == "availability":
            return {
                "ok": True,
                "online": self.session.state
                in {WorkerState.AVAILABLE, WorkerState.BUSY, WorkerState.AUTHENTICATED},
                "state": self.session.state.value,
                "device_id": self.session.device_id,
            }
        if kind == "grant":
            if self.issuer is None:
                return {"ok": False, "error": "issuer missing", "needs_live": True}
            req = GrantRequest(
                task_id=str(context.get("task_id", "")),
                action_id=str(step.get("action_id", "cua-1")),
                owner_id=str(context.get("owner_id", "")),
                device_id=self.session.device_id or str(step.get("device_id", "")),
                app=str(step.get("app", "")),
                window=str(step.get("window", "")),
                action_class="cua_run",
                parameter_digest=str(step.get("parameter_digest", "")),
            )
            try:
                signed = self.issue_grant(req)
            except Exception as exc:
                return {"ok": False, "error": str(exc)}
            return {
                "ok": True,
                "grant_nonce": signed.grant.nonce,
                "app": signed.grant.app,
                "window": signed.grant.window,
            }
        return {"ok": False, "error": f"unknown pc step {kind}"}

    async def cancel(self, task_id: str) -> None:
        self.session.state = WorkerState.AVAILABLE
