from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from .contracts import canonical_json
from .crypto import DeviceKeyPair, sign_payload, verify_payload
from .storage import StateStore


class GrantError(RuntimeError):
    pass


@dataclass(frozen=True)
class GrantRequest:
    task_id: str
    action_id: str
    owner_id: str
    device_id: str
    app: str
    window: str
    action_class: str
    parameter_digest: str
    ttl_seconds: int = 900


@dataclass(frozen=True)
class TaskGrant:
    schema: str
    task_id: str
    action_id: str
    owner_id: str
    device_id: str
    app: str
    window: str
    action_class: str
    parameter_digest: str
    issued_at: str
    expires_at: str
    nonce: str
    issuer_key_id: str


@dataclass(frozen=True)
class SignedGrant:
    grant: TaskGrant
    signature: bytes


class GrantIssuer:
    def __init__(self, store: StateStore, identity: DeviceKeyPair) -> None:
        self.store = store
        self.identity = identity

    def issue(self, request: GrantRequest, now: Optional[datetime] = None) -> SignedGrant:
        now = now or datetime.now(timezone.utc)
        expires = now + timedelta(seconds=request.ttl_seconds)
        nonce = str(uuid.uuid4())
        grant = TaskGrant(
            schema="web-operator/grant/v1",
            task_id=request.task_id,
            action_id=request.action_id,
            owner_id=request.owner_id,
            device_id=request.device_id,
            app=request.app,
            window=request.window,
            action_class=request.action_class,
            parameter_digest=request.parameter_digest,
            issued_at=now.isoformat().replace("+00:00", "Z"),
            expires_at=expires.isoformat().replace("+00:00", "Z"),
            nonce=nonce,
            issuer_key_id=self.identity.fingerprint,
        )
        payload = canonical_json(grant.__dict__).encode("utf-8")
        self.store.record_nonce(
            nonce,
            scope=f"grant:{request.task_id}",
            expires_at=grant.expires_at,
        )
        sig = sign_payload(payload, self.identity.private_key_bytes)
        return SignedGrant(grant=grant, signature=sig)

    def verify(
        self,
        signed: SignedGrant,
        *,
        public_key_bytes: bytes,
        now: Optional[datetime] = None,
        expected_device_id: Optional[str] = None,
    ) -> TaskGrant:
        now = now or datetime.now(timezone.utc)
        payload = canonical_json(signed.grant.__dict__).encode("utf-8")
        try:
            verify_payload(payload, signed.signature, public_key_bytes)
        except Exception as exc:
            raise GrantError("signature invalid") from exc
        expires = datetime.fromisoformat(signed.grant.expires_at.replace("Z", "+00:00"))
        if now >= expires:
            raise GrantError("grant expired")
        if expected_device_id and signed.grant.device_id != expected_device_id:
            raise GrantError("device mismatch")
        # replay: nonce should already exist from issue; a second consume should be app-level
        return signed.grant

    def revoke_device(self, device_id: str) -> None:
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        with self.store.connect() as conn:
            conn.execute(
                "UPDATE devices SET revoked_at=? WHERE device_id=?",
                (now, device_id),
            )
