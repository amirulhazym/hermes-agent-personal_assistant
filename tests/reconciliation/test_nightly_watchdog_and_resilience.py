from __future__ import annotations

import importlib.util
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts"

HYGIENE_SPEC = importlib.util.spec_from_file_location("nightly_git_hygiene", SCRIPTS_DIR / "nightly_git_hygiene.py")
assert HYGIENE_SPEC and HYGIENE_SPEC.loader
HYGIENE = importlib.util.module_from_spec(HYGIENE_SPEC)
sys.modules[HYGIENE_SPEC.name] = HYGIENE
HYGIENE_SPEC.loader.exec_module(HYGIENE)

WATCHDOG_SPEC = importlib.util.spec_from_file_location("nightly_git_closure_watchdog", SCRIPTS_DIR / "nightly_git_closure_watchdog.py")
assert WATCHDOG_SPEC and WATCHDOG_SPEC.loader
WATCHDOG = importlib.util.module_from_spec(WATCHDOG_SPEC)
sys.modules[WATCHDOG_SPEC.name] = WATCHDOG
WATCHDOG_SPEC.loader.exec_module(WATCHDOG)

MYT = timezone(timedelta(hours=8))

def _make_repo(tmp_path: Path) -> tuple[Path, Path, datetime]:
    repo = tmp_path / "repo"
    origin = tmp_path / "origin.git"
    upstream = tmp_path / "upstream.git"
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir(parents=True)

    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(upstream)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)

    HYGIENE._workflow_git(repo, ["config", "user.name", "Tester"])
    HYGIENE._workflow_git(repo, ["config", "user.email", "tester@example.com"])
    (repo / "README.md").write_text("# Repo\n", encoding="utf-8")
    HYGIENE._workflow_git(repo, ["add", "README.md"])
    HYGIENE._workflow_git(repo, ["commit", "-m", "initial commit"])

    HYGIENE._workflow_git(repo, ["remote", "add", "origin", str(origin)])
    HYGIENE._workflow_git(repo, ["remote", "add", "upstream", str(upstream)])
    HYGIENE._workflow_git(repo, ["push", "-q", "-u", "origin", "main"])
    HYGIENE._workflow_git(repo, ["push", "-q", "-u", "upstream", "main"])

    # Add dummy gate scripts
    guard = repo / "scripts" / "guard"
    guard.mkdir(parents=True, exist_ok=True)
    (guard / "secret-scan.sh").write_text("#!/usr/bin/env bash\nprintf 'PASS\\n'\n", encoding="utf-8")
    (guard / "secret-scan.sh").chmod(0o755)
    (guard / "pii-review.py").write_text("print('PASS')\n", encoding="utf-8")
    (guard / "whitespace_review.py").write_text("print('PASS')\n", encoding="utf-8")
    contract = repo / "scripts" / "run_contract_tests.sh"
    contract.write_text("#!/usr/bin/env bash\nprintf 'CONTRACT TESTS PASS\\n'\n", encoding="utf-8")
    contract.chmod(0o755)

    HYGIENE._workflow_git(repo, ["add", "scripts/"])
    HYGIENE._workflow_git(repo, ["commit", "-m", "add gate scripts"])
    HYGIENE._workflow_git(repo, ["push", "origin", "main"])
    HYGIENE._workflow_git(repo, ["push", "upstream", "main"])

    now = datetime(2026, 9, 5, 23, 55, 0, tzinfo=MYT)
    return repo, hermes_home, now


def test_watchdog_primary_pass_secondary_pass(tmp_path: Path):
    repo, hermes_home, now = _make_repo(tmp_path)
    # Run primary at 23:55
    res = HYGIENE.run_nightly(repo_root=repo, hermes_home=hermes_home, now=now)
    assert res["status"] == "PASS"

    # Run watchdog at 01:55 next day
    watchdog_now = now + timedelta(hours=2)
    w_res = WATCHDOG.run_watchdog(repo_root=repo, hermes_home=hermes_home, now=watchdog_now)
    assert w_res["secondary_result"] == "PASS"
    assert w_res["primary_run_id"] == res["run_id"]
    assert w_res["primary_status"] == "PASS"
    assert w_res["final_repo_state"] == "CLEAN+SYNCED"


def test_watchdog_recovers_unexecuted_timeout_autofix(tmp_path: Path):
    repo, hermes_home, now = _make_repo(tmp_path)
    # create generated manifest receipt
    receipts_dir = repo / "docs" / "reconciliation" / "manifest-receipts"
    receipts_dir.mkdir(parents=True, exist_ok=True)
    (receipts_dir / "2fe48c3de252.json").write_text('{"status": "REFRESHED"}\n')

    res = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kw: "dummy-timeout-job",
    )
    assert res["status"] == "HOLD"
    assert res["remediation"]["status"] == "pending_confirmation"

    # Watchdog at 01:55 finds pending remediation whose 30m window expired, and executes it
    watchdog_now = now + timedelta(hours=2)
    w_res = WATCHDOG.run_watchdog(repo_root=repo, hermes_home=hermes_home, now=watchdog_now)
    assert w_res["secondary_result"] == "PASS"
    assert "AFK AUTOFIX COMPLETED" in w_res["secondary_recovery"]
    assert not (receipts_dir / "2fe48c3de252.json").exists()


def test_watchdog_primary_missing(tmp_path: Path):
    repo, hermes_home, now = _make_repo(tmp_path)
    # Do not run primary. Run watchdog at 01:55
    watchdog_now = now + timedelta(hours=2)
    w_res = WATCHDOG.run_watchdog(repo_root=repo, hermes_home=hermes_home, now=watchdog_now)
    assert w_res["secondary_result"] == "FAIL"
    assert w_res["primary_status"] == "MISSING"


def test_fetch_remote_with_retry_succeeds_after_transient_error(monkeypatch):
    calls = []
    def fake_workflow_git(repo, args, **kwargs):
        calls.append(args)
        if len(calls) < 2:
            return 1, "error: cannot lock ref 'refs/remotes/origin/main': is at 1111 but expected 2222"
        return 0, "From origin\n * branch main -> FETCH_HEAD"

    monkeypatch.setattr(HYGIENE, "_workflow_git", fake_workflow_git)
    monkeypatch.setattr(HYGIENE.time, "sleep", lambda s: None)

    rc, out = HYGIENE._fetch_remote_with_retry(Path("/tmp"), "origin", "main", max_attempts=3, backoff=0.01)
    assert rc == 0
    assert len(calls) == 2


def test_fetch_remote_with_retry_fails_on_hard_error(monkeypatch):
    calls = []
    def fake_workflow_git(repo, args, **kwargs):
        calls.append(args)
        return 128, "fatal: repository not found"

    monkeypatch.setattr(HYGIENE, "_workflow_git", fake_workflow_git)
    monkeypatch.setattr(HYGIENE.time, "sleep", lambda s: None)

    rc, out = HYGIENE._fetch_remote_with_retry(Path("/tmp"), "origin", "main", max_attempts=3, backoff=0.01)
    assert rc == 128
    assert len(calls) == 1


def test_watchdog_recovers_transient_fetch_primary_failure(tmp_path: Path):
    repo, hermes_home, now = _make_repo(tmp_path)
    paths = HYGIENE._runtime_paths(hermes_home)

    # Primary failed at 23:55 due to transient fetch ref race
    primary_run_id = "20260905T155500Z-test-transient-fail"
    fake_primary = {
        "run_id": primary_run_id,
        "date": now.strftime("%Y-%m-%d"),
        "status": "FAIL",
        "errors": ["git fetch origin failed: error: cannot lock ref 'refs/remotes/origin/main': is at 1111 but expected 2222"],
        "remediation": {"status": "none"},
    }
    HYGIENE._atomic_json(paths.history_dir / f"{primary_run_id}.json", fake_primary)

    # Run watchdog at 01:55
    watchdog_now = now + timedelta(hours=2)
    w_res = WATCHDOG.run_watchdog(repo_root=repo, hermes_home=hermes_home, now=watchdog_now)
    assert w_res["secondary_result"] == "RECOVERED"
    assert "TRANSIENT" in w_res["secondary_recovery"]
    assert w_res["final_repo_state"] == "CLEAN+SYNCED"
