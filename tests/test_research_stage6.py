import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts" / "research_stage6.py"


def run_stage6(tmp_path, payload):
    env = os.environ.copy()
    env.pop("HERMES_HOME", None)
    env["HOME"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, str(RUNNER)],
        input=json.dumps(payload),
        text=True,
        capture_output=True,
        env=env,
        check=True,
    )
    return json.loads(result.stdout)


def test_stage6_writes_standard_artifact_and_appends_trace(tmp_path):
    payload = {
        "question": "Compare two research options for a test",
        "slug": "compare-two-research-options",
        "pipeline_stages": ["plan", "search", "extract", "verify", "synthesize"],
        "stage_log": [],
        "report": "# Research report\n\nA deterministic test result.",
        "sources": [{"id": "S1", "title": "Primary source", "url": "https://example.com"}],
        "meta": {"confidence": "medium", "labels": {"validated": 1}},
    }

    first = run_stage6(tmp_path, payload)
    second = run_stage6(tmp_path, payload)

    artifact_dir = Path(first["artifact_dir"])
    trace_path = Path(first["trace_path"])
    assert artifact_dir == (
        tmp_path
        / ".hermes"
        / "research"
        / "artifacts"
        / f"{date.today().isoformat()}-compare-two-research-options"
    )
    assert (artifact_dir / "meta.yaml").is_file()
    assert (artifact_dir / "report.md").read_text() == payload["report"] + "\n"
    assert json.loads((artifact_dir / "sources.json").read_text())["sources"] == payload["sources"]
    assert trace_path == tmp_path / ".hermes" / "logs" / "research_trace.jsonl"
    assert trace_path.is_file()
    records = [json.loads(line) for line in trace_path.read_text().splitlines()]
    assert len(records) == 2
    assert all(record["schema"] == "research-trace/v1" for record in records)
    assert all(record["artifact_dir"] == str(artifact_dir) for record in records)
    assert second["artifact_dir"] == first["artifact_dir"]
