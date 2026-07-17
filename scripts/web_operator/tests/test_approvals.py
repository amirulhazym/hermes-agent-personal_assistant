import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.web_operator.approvals import ApprovalError, ApprovalStore
from scripts.web_operator.contracts import ActionClass, ApprovalBinding
from scripts.web_operator.policy import PolicyEngine
from scripts.web_operator.storage import StateStore


class ApprovalTests(unittest.TestCase):
    def setUp(self):
        self.db = Path(tempfile.mkstemp(suffix=".db")[1])
        self.store = StateStore(self.db)
        self.policy = PolicyEngine()
        self.approvals = ApprovalStore(self.store, self.policy)

    def test_issue_consume_and_replay(self):
        binding = ApprovalBinding(
            task_id="t1",
            action_id="a1",
            owner_id="o1",
            action_class=ActionClass.EXTERNAL_SEND,
            target="https://example.com",
            parameters={"content": "hi"},
            state_digest="s1",
        )
        now = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)
        issued = self.approvals.issue(binding, now=now, ttl_seconds=900)
        consumed = self.approvals.consume(
            issued.approval_id, "o1", issued.binding_digest, now=now + timedelta(seconds=10)
        )
        self.assertEqual(consumed.state.value, "consumed")
        with self.assertRaises(ApprovalError):
            self.approvals.consume(
                issued.approval_id, "o1", issued.binding_digest, now=now + timedelta(seconds=20)
            )

    def test_expiry(self):
        binding = ApprovalBinding(
            task_id="t1",
            action_id="a1",
            owner_id="o1",
            action_class=ActionClass.FORM_SUBMIT,
            target="https://example.com",
            parameters={},
            state_digest="s1",
        )
        now = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)
        issued = self.approvals.issue(binding, now=now, ttl_seconds=900)
        with self.assertRaises(ApprovalError):
            self.approvals.consume(
                issued.approval_id,
                "o1",
                issued.binding_digest,
                now=now + timedelta(seconds=901),
            )


if __name__ == "__main__":
    unittest.main()
