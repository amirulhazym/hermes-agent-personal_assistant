import asyncio
import tempfile
import unittest
from pathlib import Path

from scripts.web_operator.adapters.http import HttpExecutor
from scripts.web_operator.adapters.native_browser import NativeBrowserExecutor
from scripts.web_operator.adapters.research import ResearchExecutor
from scripts.web_operator.approvals import ApprovalStore
from scripts.web_operator.config import OperatorConfig
from scripts.web_operator.contracts import ExecutionLevel, TaskRequest
from scripts.web_operator.coordinator import WebOperator
from scripts.web_operator.network import DestinationGuard
from scripts.web_operator.policy import PolicyEngine
from scripts.web_operator.storage import StateStore


class FakeResearch(ResearchExecutor):
    async def execute(self, context, step):
        return {"ok": True, "empty": True, "needs_interactive": True, "kind": "search"}


class FakeBrowser(NativeBrowserExecutor):
    def __init__(self, guard):
        super().__init__(guard, navigate=lambda url, task_id=None: {"navigated": url})

    async def execute(self, context, step):
        return {"ok": True, "kind": step.get("kind"), "result": {"navigated": True}}


class RoutingTests(unittest.TestCase):
    def test_l2_to_l3_escalation_path(self):
        root = Path(tempfile.mkdtemp())
        store = StateStore(root / "s.db")
        policy = PolicyEngine()
        approvals = ApprovalStore(store, policy)
        guard = DestinationGuard(fixture_mode=True, deny_private=False)
        op = WebOperator(
            config=OperatorConfig(state_dir=str(root)),
            store=store,
            policy=policy,
            approvals=approvals,
            guard=guard,
            executors={
                ExecutionLevel.L1: HttpExecutor(guard),
                ExecutionLevel.L2: FakeResearch(),
                ExecutionLevel.L3: FakeBrowser(guard),
            },
            artifact_root=root / "artifacts",
        )
        result = asyncio.run(
            op.submit(
                TaskRequest(
                    owner_id="o1",
                    channel="telegram",
                    text="browse https://example.com and click pricing",
                )
            )
        )
        self.assertIn(result["state"], {"completed", "failed"})
        self.assertTrue(any(lvl in result["route"] for lvl in ("L2", "L3")))


if __name__ == "__main__":
    unittest.main()
