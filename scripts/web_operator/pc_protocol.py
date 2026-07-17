from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Optional


class WorkerState(str, Enum):
    DISCONNECTED = "disconnected"
    HELLO = "hello"
    AUTHENTICATED = "authenticated"
    AVAILABLE = "available"
    BUSY = "busy"
    STOPPED = "stopped"


ALLOWED_MESSAGES = {
    "hello",
    "challenge",
    "authenticate",
    "heartbeat",
    "availability",
    "grant",
    "grant-accepted",
    "grant-rejected",
    "step-event",
    "result",
    "stop",
    "revoke",
}


@dataclass
class ProtocolMessage:
    type: str
    payload: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.type not in ALLOWED_MESSAGES:
            raise ValueError(f"unknown message type: {self.type}")
        # size bound on serialized-ish payload
        if len(str(self.payload)) > 200_000:
            raise ValueError("payload too large")


@dataclass
class WorkerSession:
    state: WorkerState = WorkerState.DISCONNECTED
    device_id: str = ""
    last_heartbeat: Optional[float] = None

    def on_message(self, message: ProtocolMessage, now: float) -> WorkerState:
        message.validate()
        t = message.type
        if t == "hello":
            self.state = WorkerState.HELLO
            self.device_id = str(message.payload.get("device_id", ""))
        elif t == "authenticate":
            if self.state not in {WorkerState.HELLO, WorkerState.DISCONNECTED}:
                raise ValueError("authenticate out of order")
            self.state = WorkerState.AUTHENTICATED
        elif t == "availability":
            if self.state not in {
                WorkerState.AUTHENTICATED,
                WorkerState.AVAILABLE,
                WorkerState.BUSY,
            }:
                raise ValueError("availability before auth")
            available = bool(message.payload.get("online", False))
            self.state = WorkerState.AVAILABLE if available else WorkerState.AUTHENTICATED
        elif t == "heartbeat":
            self.last_heartbeat = now
        elif t == "grant-accepted":
            self.state = WorkerState.BUSY
        elif t in {"result", "grant-rejected", "stop", "revoke"}:
            if self.state == WorkerState.BUSY:
                self.state = WorkerState.AVAILABLE
        elif t == "stop":
            self.state = WorkerState.STOPPED
        return self.state

    def heartbeat_timeout(self, now: float, timeout_seconds: float = 30.0) -> bool:
        if self.last_heartbeat is None:
            return False
        if now - self.last_heartbeat > timeout_seconds:
            self.state = WorkerState.DISCONNECTED
            return True
        return False
