from __future__ import annotations

import enum
import json
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional


class ExecutionLevel(str, enum.Enum):
    L0 = "L0"
    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"


class ActionClass(str, enum.Enum):
    PUBLIC_READ = "public_read"
    PUBLIC_NAVIGATE = "public_navigate"
    PERSONAL_DATA_ENTRY = "personal_data_entry"
    FORM_SUBMIT = "form_submit"
    EXTERNAL_SEND = "external_send"
    PUBLIC_POST = "public_post"
    DOWNLOAD = "download"
    DOWNLOAD_RELEASE = "download_release"
    UPLOAD = "upload"
    CHECKOUT = "checkout"
    CALENDAR_CHANGE = "calendar_change"
    GROUP_ACTION = "group_action"
    DELETE_OR_OVERWRITE = "delete_or_overwrite"
    INFRASTRUCTURE_CHANGE = "infrastructure_change"
    SHELL_SIDE_EFFECT = "shell_side_effect"
    SECRET_EXPOSURE = "secret_exposure"
    PAID_SERVICE_ENABLE = "paid_service_enable"
    EXPENSIVE_MODEL_SWITCH = "expensive_model_switch"
    CUA_RUN = "cua_run"
    PRIVATE_TAKEOVER = "private_takeover"
    UNKNOWN = "unknown"


class TaskState(str, enum.Enum):
    CREATED = "created"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    WAITING_TAKEOVER = "waiting_takeover"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    HANDOFF = "handoff"


class ApprovalState(str, enum.Enum):
    ISSUED = "issued"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    REVOKED = "revoked"


class OutcomeLabel(str, enum.Enum):
    VALIDATED = "VALIDATED"
    UNTESTED = "UNTESTED"
    REJECTED = "REJECTED"
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"


class SensitivityMode(str, enum.Enum):
    ORDINARY = "ordinary"
    MEDICAL = "medical"
    FINANCIAL = "financial"


class PolicyVerdict(str, enum.Enum):
    ALLOW = "allow"
    PAUSE = "pause"
    DENY = "deny"
    HANDOFF = "handoff"


def _json_default(obj: Any) -> Any:
    if isinstance(obj, enum.Enum):
        return obj.value
    if isinstance(obj, datetime):
        if obj.tzinfo is None:
            obj = obj.replace(tzinfo=timezone.utc)
        return obj.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if is_dataclass(obj):
        return asdict(obj)
    raise TypeError(f"Object of type {type(obj)!r} is not JSON serializable")


def canonical_json(obj: Any) -> str:
    if is_dataclass(obj) and not isinstance(obj, type):
        payload = asdict(obj)
    elif isinstance(obj, Mapping):
        payload = dict(obj)
    else:
        payload = obj
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_json_default)


@dataclass(frozen=True)
class TaskRequest:
    schema: str = "web-operator/task/v1"
    task_id: str = ""
    owner_id: str = ""
    channel: str = ""
    text: str = ""
    sensitivity: SensitivityMode = SensitivityMode.ORDINARY
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class ActionIntent:
    schema: str = "web-operator/action/v1"
    task_id: str = ""
    action_id: str = ""
    owner_id: str = ""
    action_class: ActionClass = ActionClass.UNKNOWN
    target: str = ""
    parameters: Mapping[str, Any] = field(default_factory=dict)
    state_digest: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass(frozen=True)
class PolicyDecision:
    schema: str = "web-operator/policy/v1"
    verdict: PolicyVerdict = PolicyVerdict.DENY
    action_class: ActionClass = ActionClass.UNKNOWN
    reason: str = ""
    requires_approval: bool = False
    level: ExecutionLevel = ExecutionLevel.L0


@dataclass(frozen=True)
class ApprovalBinding:
    schema: str = "web-operator/approval-binding/v1"
    task_id: str = ""
    action_id: str = ""
    owner_id: str = ""
    action_class: ActionClass = ActionClass.UNKNOWN
    target: str = ""
    parameters: Mapping[str, Any] = field(default_factory=dict)
    state_digest: str = ""


@dataclass(frozen=True)
class ApprovalRecord:
    schema: str = "web-operator/approval/v1"
    approval_id: str = ""
    task_id: str = ""
    owner_id: str = ""
    binding_digest: str = ""
    state: ApprovalState = ApprovalState.ISSUED
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    consumed_at: Optional[datetime] = None


@dataclass(frozen=True)
class SessionIdentity:
    schema: str = "web-operator/session-identity/v1"
    site: str = ""
    account: str = ""
    profile: str = "default"
    execution_device: str = "vps"


@dataclass(frozen=True)
class FileDescriptor:
    schema: str = "web-operator/file/v1"
    filename: str = ""
    content_type: str = ""
    size_bytes: int = 0
    sha256: str = ""
    source: str = ""
    purpose: str = ""


@dataclass(frozen=True)
class OperatorResult:
    schema: str = "web-operator/result/v1"
    task_id: str = ""
    state: TaskState = TaskState.FAILED
    level: ExecutionLevel = ExecutionLevel.L0
    label: OutcomeLabel = OutcomeLabel.PENDING
    summary: str = ""
    route: list[str] = field(default_factory=list)
    artifact_path: str = ""
    error: str = ""
