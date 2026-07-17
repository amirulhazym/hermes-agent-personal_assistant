import json
import unittest
from datetime import UTC, datetime

from scripts.web_operator.contracts import ActionClass, ActionIntent, canonical_json


class ContractTests(unittest.TestCase):
    def test_canonical_json_is_stable(self):
        action = ActionIntent(
            schema="web-operator/action/v1",
            task_id="task-1",
            action_id="action-1",
            owner_id="owner-1",
            action_class=ActionClass.EXTERNAL_SEND,
            target="https://example.com/send",
            parameters={"recipient": "fixture-owner", "content": "hello"},
            state_digest="a" * 64,
            created_at=datetime(2026, 7, 17, tzinfo=UTC),
        )
        encoded = canonical_json(action)
        self.assertEqual(encoded, canonical_json(action))
        self.assertEqual(json.loads(encoded)["action_class"], "external_send")


if __name__ == "__main__":
    unittest.main()
