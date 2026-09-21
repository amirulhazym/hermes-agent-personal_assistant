from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
MONITOR = REPO / "scripts/monitor/drift_check.sh"
MIRROR = REPO / "scripts/drift_check.sh"


def _require_isolation_hooks() -> None:
    text = MONITOR.read_text()
    assert "DRIFT_REPO" in text
    assert "DRIFT_RECEIPT" in text
    assert "DRIFT_DEPLOYED_REFERENCE" in text


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repo, text=True).strip()


def _fixture(tmp_path: Path, live_bytes: bytes) -> tuple[Path, Path, Path]:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "t04@example.invalid"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "T04 Test"], cwd=repo, check=True)

    source = repo / "managed.txt"
    source.write_bytes(b"expected\n")
    destination = tmp_path / "live-managed.txt"
    destination.write_bytes(live_bytes)

    expected_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest = {
        "schema_version": 1,
        "entries": [
            {
                "source": "managed.txt",
                "destination": str(destination),
                "kind": "runtime-deploy",
                "source_sha256": expected_sha,
            }
        ],
    }
    manifest_path = repo / "docs/reconciliation/v3-source-coverage-manifest.json"
    manifest_path.parent.mkdir(parents=True)
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")

    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "fixture"], cwd=repo, check=True)
    deployed_sha = _git(repo, "rev-parse", "HEAD")

    deployed_reference = tmp_path / "deployed-runtime-reference.json"
    deployed_reference.write_text(json.dumps({"deployed_runtime_sha": deployed_sha}) + "\n")
    receipt = tmp_path / "drift-receipt.json"
    return repo, deployed_reference, receipt


def _run_monitor(tmp_path: Path, live_bytes: bytes) -> tuple[subprocess.CompletedProcess[str], dict]:
    _require_isolation_hooks()
    repo, deployed_reference, receipt = _fixture(tmp_path, live_bytes)
    env = {
        **os.environ,
        "DRIFT_REPO": str(repo),
        "DRIFT_RECEIPT": str(receipt),
        "DRIFT_DEPLOYED_REFERENCE": str(deployed_reference),
    }
    result = subprocess.run(
        ["bash", str(MONITOR)],
        cwd=REPO,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert receipt.is_file(), result.stdout + result.stderr
    return result, json.loads(receipt.read_text())


def test_zero_managed_drift_is_pass(tmp_path: Path) -> None:
    result, receipt = _run_monitor(tmp_path, b"expected\n")
    assert result.returncode == 0, result.stdout + result.stderr
    assert receipt["status"] == "PASS"
    assert receipt["drift_total"] == 0
    assert receipt["drift"] == []
    assert "known_drift" not in receipt
    assert "new_drift" not in receipt


def test_any_managed_mismatch_is_fail(tmp_path: Path) -> None:
    result, receipt = _run_monitor(tmp_path, b"unexpected\n")
    assert result.returncode == 1
    assert receipt["status"] == "FAIL"
    assert receipt["drift_total"] == 1
    assert len(receipt["drift"]) == 1
    assert receipt["drift"][0]["source"] == "managed.txt"
    assert "known_drift" not in receipt
    assert "new_drift" not in receipt


def test_no_hardcoded_known_drift_escape_hatch_and_mirror_matches() -> None:
    text = MONITOR.read_text()
    assert "# Known acceptable drift" not in text
    assert "known = {" not in text
    assert MONITOR.read_bytes() == MIRROR.read_bytes()
