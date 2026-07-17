from __future__ import annotations

import hashlib
import re
from typing import Optional

from .contracts import (
    ActionClass,
    ActionIntent,
    ApprovalRecord,
    ApprovalState,
    ExecutionLevel,
    PolicyDecision,
    PolicyVerdict,
    TaskRequest,
    canonical_json,
)


_DENY_ALWAYS = {
    ActionClass.INFRASTRUCTURE_CHANGE,
    ActionClass.SHELL_SIDE_EFFECT,
    ActionClass.SECRET_EXPOSURE,
    ActionClass.PAID_SERVICE_ENABLE,
    ActionClass.EXPENSIVE_MODEL_SWITCH,
    ActionClass.UNKNOWN,
}

_PAUSE_ALWAYS = {
    ActionClass.PERSONAL_DATA_ENTRY,
    ActionClass.FORM_SUBMIT,
    ActionClass.EXTERNAL_SEND,
    ActionClass.PUBLIC_POST,
    ActionClass.DOWNLOAD,
    ActionClass.DOWNLOAD_RELEASE,
    ActionClass.UPLOAD,
    ActionClass.CHECKOUT,
    ActionClass.CALENDAR_CHANGE,
    ActionClass.GROUP_ACTION,
    ActionClass.DELETE_OR_OVERWRITE,
    ActionClass.CUA_RUN,
    ActionClass.PRIVATE_TAKEOVER,
}

_ALLOW_ALWAYS = {
    ActionClass.PUBLIC_READ,
    ActionClass.PUBLIC_NAVIGATE,
}


class PolicyEngine:
    def classify_task(self, request: TaskRequest) -> PolicyDecision:
        text = (request.text or "").lower()
        if re.search(r"\b(password|otp|card number|cvv|bank login)\b", text):
            return PolicyDecision(
                verdict=PolicyVerdict.PAUSE,
                action_class=ActionClass.PRIVATE_TAKEOVER,
                reason="secret entry requires private takeover",
                requires_approval=True,
                level=ExecutionLevel.L0,
            )
        if re.search(r"\b(browse|click|navigate|open site|fill form|/browse)\b", text):
            return PolicyDecision(
                verdict=PolicyVerdict.ALLOW,
                action_class=ActionClass.PUBLIC_NAVIGATE,
                reason="interactive web request",
                requires_approval=False,
                level=ExecutionLevel.L2,
            )
        if re.search(r"\b(research|investigate|sources|literature)\b", text):
            return PolicyDecision(
                verdict=PolicyVerdict.ALLOW,
                action_class=ActionClass.PUBLIC_READ,
                reason="research/read request",
                requires_approval=False,
                level=ExecutionLevel.L2,
            )
        return PolicyDecision(
            verdict=PolicyVerdict.PAUSE,
            action_class=ActionClass.UNKNOWN,
            reason="unclear intent",
            requires_approval=True,
            level=ExecutionLevel.L0,
        )

    def classify_action(self, action: ActionIntent) -> PolicyDecision:
        cls = action.action_class
        if cls in _DENY_ALWAYS:
            return PolicyDecision(
                verdict=PolicyVerdict.DENY,
                action_class=cls,
                reason=f"{cls.value} is denied in V1",
                requires_approval=False,
                level=ExecutionLevel.L0,
            )
        if cls == ActionClass.DELETE_OR_OVERWRITE:
            if action.parameters.get("bulk") or action.parameters.get("irreversible"):
                return PolicyDecision(
                    verdict=PolicyVerdict.DENY,
                    action_class=cls,
                    reason="bulk/irreversible deletion denied",
                    requires_approval=False,
                    level=ExecutionLevel.L0,
                )
        if cls in _PAUSE_ALWAYS:
            return PolicyDecision(
                verdict=PolicyVerdict.PAUSE,
                action_class=cls,
                reason=f"{cls.value} requires action-bound approval",
                requires_approval=True,
                level=ExecutionLevel.L0,
            )
        if cls in _ALLOW_ALWAYS:
            level = (
                ExecutionLevel.L1
                if cls == ActionClass.PUBLIC_READ
                else ExecutionLevel.L3
            )
            return PolicyDecision(
                verdict=PolicyVerdict.ALLOW,
                action_class=cls,
                reason=f"{cls.value} allowed within task limits",
                requires_approval=False,
                level=level,
            )
        return PolicyDecision(
            verdict=PolicyVerdict.DENY,
            action_class=ActionClass.UNKNOWN,
            reason="unknown action class denied by default",
            requires_approval=False,
            level=ExecutionLevel.L0,
        )

    def binding_digest(self, action: ActionIntent) -> str:
        payload = {
            "task_id": action.task_id,
            "action_id": action.action_id,
            "owner_id": action.owner_id,
            "action_class": action.action_class.value,
            "target": action.target,
            "parameters": dict(action.parameters),
            "state_digest": action.state_digest,
        }
        raw = canonical_json(payload).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def authorize(
        self,
        action: ActionIntent,
        approval: Optional[ApprovalRecord],
        current_state_digest: str,
    ) -> PolicyDecision:
        decision = self.classify_action(action)
        if decision.verdict == PolicyVerdict.DENY:
            return decision
        if decision.verdict == PolicyVerdict.ALLOW and not decision.requires_approval:
            if current_state_digest and action.state_digest != current_state_digest:
                return PolicyDecision(
                    verdict=PolicyVerdict.PAUSE,
                    action_class=action.action_class,
                    reason="state changed; reapproval required",
                    requires_approval=True,
                    level=ExecutionLevel.L0,
                )
            return decision
        if approval is None:
            return PolicyDecision(
                verdict=PolicyVerdict.PAUSE,
                action_class=action.action_class,
                reason="approval missing",
                requires_approval=True,
                level=ExecutionLevel.L0,
            )
        if approval.state != ApprovalState.CONSUMED and approval.state != ApprovalState.ISSUED:
            return PolicyDecision(
                verdict=PolicyVerdict.DENY,
                action_class=action.action_class,
                reason="approval not usable",
                requires_approval=False,
                level=ExecutionLevel.L0,
            )
        expected = self.binding_digest(action)
        if approval.binding_digest != expected:
            return PolicyDecision(
                verdict=PolicyVerdict.DENY,
                action_class=action.action_class,
                reason="approval binding mismatch",
                requires_approval=False,
                level=ExecutionLevel.L0,
            )
        if action.state_digest != current_state_digest:
            return PolicyDecision(
                verdict=PolicyVerdict.PAUSE,
                action_class=action.action_class,
                reason="material state drift after approval",
                requires_approval=True,
                level=ExecutionLevel.L0,
            )
        return PolicyDecision(
            verdict=PolicyVerdict.ALLOW,
            action_class=action.action_class,
            reason="approved",
            requires_approval=False,
            level=ExecutionLevel.L3
            if action.action_class
            not in {ActionClass.CUA_RUN, ActionClass.PUBLIC_READ}
            else (
                ExecutionLevel.L4
                if action.action_class == ActionClass.CUA_RUN
                else ExecutionLevel.L1
            ),
        )
