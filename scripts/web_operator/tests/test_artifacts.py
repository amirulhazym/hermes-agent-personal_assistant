import tempfile
import unittest
from pathlib import Path

from scripts.web_operator.artifacts import ArtifactSink, ExecutionEvent, SensitiveEvidenceError
from scripts.web_operator.contracts import ExecutionLevel, OutcomeLabel, TaskState


class ArtifactTests(unittest.TestCase):
    def test_secretish_blocked(self):
        root = Path(tempfile.mkdtemp())
        sink = ArtifactSink(root)
        with self.assertRaises(SensitiveEvidenceError):
            sink.record_event(
                ExecutionEvent(ts="t", kind="x", detail={"password": "nope"})
            )

    def test_finalize_ordinary(self):
        root = Path(tempfile.mkdtemp())
        sink = ArtifactSink(root)
        sink.record_event(ExecutionEvent(ts="t", kind="start", detail={"url": "https://example.com?x=1"}))
        path = sink.finalize(
            task_id="t1",
            state=TaskState.COMPLETED,
            level=ExecutionLevel.L2,
            label=OutcomeLabel.VALIDATED,
            summary="ok",
            route=["L2"],
        )
        self.assertTrue(path.exists())


if __name__ == "__main__":
    unittest.main()
