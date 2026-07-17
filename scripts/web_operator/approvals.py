from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from .contracts import (
    ApprovalBinding,
    ApprovalRecord,
    ApprovalState,
    ActionIntent,
    canonical_json,
)
from .policy import PolicyEngine
from .storage import StateStore


class ApprovalError(RuntimeError):
    pass


def _parse_dt(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    return datetime.fromisoformat(value)


def _fmt(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


class ApprovalStore:
    def __init__(self, store: StateStore, policy: Optional[PolicyEngine] = None) -> None:
        self.store = store
        self.policy = policy or PolicyEngine()

    def issue(
        self,
        binding: ApprovalBinding,
        now: Optional[datetime] = None,
        ttl_seconds: int = 900,
    ) -> ApprovalRecord:
        now = now or datetime.now(timezone.utc)
        expires = now + timedelta(seconds=ttl_seconds)
        action = ActionIntent(
            task_id=binding.task_id,
            action_id=binding.action_id,
            owner_id=binding.owner_id,
            action_class=binding.action_class,
            target=binding.target,
            parameters=dict(binding.parameters),
            state_digest=binding.state_digest,
            created_at=now,
        )
        digest = self.policy.binding_digest(action)
        approval_id = str(uuid.uuid4())
        with self.store.connect() as conn:
            conn.execute(
                """
                INSERT INTO approvals(
                  approval_id, task_id, owner_id, binding_digest, state, expires_at, consumed_at
                ) VALUES (?,?,?,?,?,?,NULL)
                """,
                (
                    approval_id,
                    binding.task_id,
                    binding.owner_id,
                    digest,
                    ApprovalState.ISSUED.value,
                    _fmt(expires),
                ),
            )
        return ApprovalRecord(
            approval_id=approval_id,
            task_id=binding.task_id,
            owner_id=binding.owner_id,
            binding_digest=digest,
            state=ApprovalState.ISSUED,
            expires_at=expires,
            consumed_at=None,
        )

    def consume(
        self,
        approval_id: str,
        owner_id: str,
        binding_digest: str,
        now: Optional[datetime] = None,
    ) -> ApprovalRecord:
        now = now or datetime.now(timezone.utc)
        with self.store.transaction() as conn:
            row = conn.execute(
                "SELECT * FROM approvals WHERE approval_id=?",
                (approval_id,),
            ).fetchone()
            if row is None:
                raise ApprovalError("approval not found")
            if row["owner_id"] != owner_id:
                raise ApprovalError("wrong owner")
            if row["binding_digest"] != binding_digest:
                raise ApprovalError("binding mismatch")
            if row["state"] != ApprovalState.ISSUED.value:
                raise ApprovalError(f"approval state is {row['state']}")
            expires = _parse_dt(row["expires_at"])
            if now >= expires:
                conn.execute(
                    "UPDATE approvals SET state=? WHERE approval_id=?",
                    (ApprovalState.EXPIRED.value, approval_id),
                )
                raise ApprovalError("approval expired")
            consumed = _fmt(now)
            conn.execute(
                "UPDATE approvals SET state=?, consumed_at=? WHERE approval_id=?",
                (ApprovalState.CONSUMED.value, consumed, approval_id),
            )
            return ApprovalRecord(
                approval_id=approval_id,
                task_id=row["task_id"],
                owner_id=row["owner_id"],
                binding_digest=row["binding_digest"],
                state=ApprovalState.CONSUMED,
                expires_at=expires,
                consumed_at=now,
            )

    def expire(self, now: Optional[datetime] = None) -> list[ApprovalRecord]:
        now = now or datetime.now(timezone.utc)
        now_s = _fmt(now)
        expired: list[ApprovalRecord] = []
        with self.store.transaction() as conn:
            rows = conn.execute(
                "SELECT * FROM approvals WHERE state=? AND expires_at<=?",
                (ApprovalState.ISSUED.value, now_s),
            ).fetchall()
            for row in rows:
                conn.execute(
                    "UPDATE approvals SET state=? WHERE approval_id=?",
                    (ApprovalState.EXPIRED.value, row["approval_id"]),
                )
                expired.append(
                    ApprovalRecord(
                        approval_id=row["approval_id"],
                        task_id=row["task_id"],
                        owner_id=row["owner_id"],
                        binding_digest=row["binding_digest"],
                        state=ApprovalState.EXPIRED,
                        expires_at=_parse_dt(row["expires_at"]),
                        consumed_at=None,
                    )
                )
        return expired

    def revoke_task(self, task_id: str) -> int:
        with self.store.connect() as conn:
            cur = conn.execute(
                "UPDATE approvals SET state=? WHERE task_id=? AND state=?",
                (ApprovalState.REVOKED.value, task_id, ApprovalState.ISSUED.value),
            )
            return cur.rowcount
