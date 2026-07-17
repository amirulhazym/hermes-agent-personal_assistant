from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Optional

from ..bridge import BridgeControlPlane
from ..contracts import ExecutionLevel
from ..grants import GrantIssuer, GrantRequest, SignedGrant
from ..pc_protocol import ProtocolMessage, WorkerSession, WorkerState


class PcWorkerExecutor:
    """VPS-side control plane for enrolled outbound Windows workers."""

    def __init__(
        self,
        issuer: Optional[GrantIssuer] = None,
        *,
        bridge: Optional[BridgeControlPlane] = None,
        default_device_id: str = "",
    ) -> None:
        self.issuer = issuer or (bridge.issuer if bridge else None)
        self.bridge = bridge
        self.default_device_id = default_device_id
        self.session = WorkerSession()
        self.inbound_listen = False  # hard rule: no inbound listener
        self._last_grant: Optional[SignedGrant] = None

    @property
    def level(self) -> ExecutionLevel:
        return ExecutionLevel.L4

    def capabilities(self) -> frozenset[str]:
        return frozenset({"pc_availability", "pc_grant", "pc_stop", "pc_named_app"})

    def note_worker_message(self, message: ProtocolMessage, now: float) -> WorkerState:
        return self.session.on_message(message, now)

    def sync_session_from_bridge(self, device_id: str) -> None:
        if self.bridge is None:
            return
        st = self.bridge.device_status(device_id)
        self.session.device_id = device_id
        if st.get("online_fresh") or self.bridge.is_device_online(device_id):
            self.session.state = WorkerState.AVAILABLE
        else:
            self.session.state = WorkerState.DISCONNECTED

    def issue_grant(self, request: GrantRequest) -> SignedGrant:
        if self.inbound_listen:
            raise RuntimeError("inbound listener forbidden")
        if self.bridge is not None:
            self.sync_session_from_bridge(request.device_id)
        if self.session.state not in {WorkerState.AVAILABLE, WorkerState.AUTHENTICATED}:
            raise RuntimeError("worker not available")
        if self.issuer is None:
            raise RuntimeError("grant issuer not configured")
        signed = self.issuer.issue(request)
        self._last_grant = signed
        return signed

    async def execute(self, context: Mapping[str, Any], step: Mapping[str, Any]) -> Mapping[str, Any]:
        kind = step.get("kind")
        device_id = str(
            step.get("device_id")
            or self.default_device_id
            or self.session.device_id
            or ""
        )
        if kind == "availability":
            if self.bridge is not None and device_id:
                online = self.bridge.is_device_online(device_id)
                st = self.bridge.device_status(device_id)
                return {
                    "ok": True,
                    "online": online,
                    "state": "available" if online else "disconnected",
                    "device_id": device_id,
                    "status": st,
                }
            return {
                "ok": True,
                "online": self.session.state
                in {WorkerState.AVAILABLE, WorkerState.BUSY, WorkerState.AUTHENTICATED},
                "state": self.session.state.value,
                "device_id": self.session.device_id,
            }
        if kind in {"grant", "named_app", "cua"}:
            if self.bridge is None:
                return {"ok": False, "error": "bridge not configured", "needs_live": True}
            app = str(step.get("app") or step.get("name") or "Notepad")
            window = str(step.get("window") or "")
            action = str(step.get("action") or "launch_and_list")
            # unapproved / privilege actions fail closed
            if action in {"shell", "elevate", "install", "admin"}:
                return {"ok": False, "error": f"privilege action blocked: {action}", "fail_closed": True}
            if not device_id:
                # pick first enrolled online device
                device_id = self._first_online_device() or ""
            if not device_id:
                return {
                    "ok": False,
                    "error": "no enrolled online pc worker",
                    "postpone": True,
                }
            result = self.bridge.run_named_app_task(
                task_id=str(context.get("task_id", "")),
                owner_id=str(context.get("owner_id", "")),
                device_id=device_id,
                app=app,
                window=window,
                action=action,
                timeout_seconds=float(step.get("timeout_seconds") or 120),
            )
            return result
        return {"ok": False, "error": f"unknown pc step {kind}"}

    def _first_online_device(self) -> str:
        if self.bridge is None:
            return ""
        for path in sorted(self.bridge.paths.devices.glob("*.json")):
            if path.name.endswith(".request.json"):
                continue
            device_id = path.stem
            if self.bridge.is_device_online(device_id):
                return device_id
        # also check status files
        for path in sorted(self.bridge.paths.status.glob("*.json")):
            device_id = path.stem
            if self.bridge.is_device_online(device_id):
                return device_id
        return ""

    async def cancel(self, task_id: str) -> None:
        self.session.state = WorkerState.AVAILABLE
