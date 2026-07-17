import tempfile
import unittest
from pathlib import Path

from scripts.web_operator.artifacts import ArtifactSink, ExecutionEvent, SensitiveEvidenceError
from scripts.web_operator.contracts import ExecutionLevel, OutcomeLabel, TaskState


class MedicalModeTests(unittest.TestCase):
    def test_medical_forbids_ordinary_evidence_files(self):
        root = Path(tempfile.mkdtemp())
        sink = ArtifactSink(root, medical=True)
        with self.assertRaises(SensitiveEvidenceError):
            sink.attach_redacted_evidence("shot.png", b"abc")
        path = sink.finalize(
            task_id="t1",
            state=TaskState.COMPLETED,
            level=ExecutionLevel.L3,
            label=OutcomeLabel.VALIDATED,
            summary="portal read",
            route=["L3"],
        )
        self.assertTrue(path.name.endswith("medical-audit.json"))


if __name__ == "__main__":
    unittest.main()
