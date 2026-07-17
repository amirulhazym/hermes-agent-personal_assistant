from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Optional


class TakeoverState(str, Enum):
    REQUESTED = "requested"
    SUSPENDING = "suspending"
    EXCLUSIVE = "exclusive"
    RETURNING = "returning"
    CLOSED = "closed"
    DISCONNECTED = "disconnected"
    EXPIRED = "expired"


class TakeoverError(RuntimeError):
    pass


@dataclass
class SuspensionToken:
    task_id: str
    active: bool = True


class ObservationGate:
    def __init__(self) -> None:
        self._suspended: set[str] = set()
        self._producers: list[Callable[[str], None]] = []

    def register_producer(self, fn: Callable[[str], None]) -> None:
        self._producers.append(fn)

    async def suspend(self, task_id: str) -> SuspensionToken:
        self._suspended.add(task_id)
        for producer in self._producers:
            producer(task_id)
        return SuspensionToken(task_id=task_id, active=True)

    async def resume(self, token: SuspensionToken) -> None:
        self._suspended.discard(token.task_id)
        token.active = False

    def assert_suspended(self, task_id: str) -> None:
        if task_id not in self._suspended:
            raise TakeoverError("observation not suspended")

    def is_suspended(self, task_id: str) -> bool:
        return task_id in self._suspended

    def emit(self, task_id: str, channel: str, payload: str) -> None:
        if task_id in self._suspended:
            raise TakeoverError(f"{channel} blocked during takeover")


@dataclass
class TakeoverSession:
    task_id: str
    state: TakeoverState = TakeoverState.REQUESTED
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(seconds=900)
    )
    token: Optional[SuspensionToken] = None


class TakeoverController:
    def __init__(self, gate: ObservationGate, ttl_seconds: int = 900) -> None:
        self.gate = gate
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, TakeoverSession] = {}

    async def grant(self, task_id: str, now: Optional[datetime] = None) -> TakeoverSession:
        now = now or datetime.now(timezone.utc)
        session = TakeoverSession(
            task_id=task_id,
            state=TakeoverState.SUSPENDING,
            expires_at=now + timedelta(seconds=self.ttl_seconds),
        )
        token = await self.gate.suspend(task_id)
        session.token = token
        session.state = TakeoverState.EXCLUSIVE
        self._sessions[task_id] = session
        return session

    async def return_control(self, task_id: str) -> TakeoverSession:
        session = self._require(task_id)
        session.state = TakeoverState.RETURNING
        if session.token:
            await self.gate.resume(session.token)
        session.state = TakeoverState.CLOSED
        return session

    async def disconnect(self, task_id: str) -> TakeoverSession:
        session = self._require(task_id)
        session.state = TakeoverState.DISCONNECTED
        # keep capture disabled until expire/return
        return session

    async def expire(self, task_id: str, now: Optional[datetime] = None) -> TakeoverSession:
        now = now or datetime.now(timezone.utc)
        session = self._require(task_id)
        if now >= session.expires_at or session.state == TakeoverState.DISCONNECTED:
            if session.token and session.token.active:
                await self.gate.resume(session.token)
            session.state = TakeoverState.EXPIRED
        return session

    def _require(self, task_id: str) -> TakeoverSession:
        if task_id not in self._sessions:
            raise TakeoverError("no takeover session")
        return self._sessions[task_id]
