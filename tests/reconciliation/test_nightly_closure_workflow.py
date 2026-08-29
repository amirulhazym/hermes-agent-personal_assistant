from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "nightly_git_hygiene.py"
SPEC = importlib.util.spec_from_file_location("nightly_git_hygiene_closure", MODULE_PATH)
assert SPEC and SPEC.loader
HYGIENE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = HYGIENE
SPEC.loader.exec_module(HYGIENE)

MYT = timezone(timedelta(hours=8))


def git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )
    return result.stdout.strip()


def make_repo(tmp_path: Path) -> tuple[Path, Path, Path]:
    origin = tmp_path / "origin.git"
    upstream = tmp_path / "upstream.git"
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(origin)], check=True)
    subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(upstream)], check=True)
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    git(repo, "config", "user.name", "Test User")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "README.md").write_text("initial\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-q", "-m", "initial")
    git(repo, "remote", "add", "origin", str(origin))
    git(repo, "remote", "add", "upstream", str(upstream))
    git(repo, "push", "-q", "-u", "origin", "main")
    git(repo, "push", "-q", "-u", "upstream", "main")
    return repo, origin, upstream


def add_gate_scripts(repo: Path) -> None:
    guard = repo / "scripts" / "guard"
    guard.mkdir(parents=True, exist_ok=True)
    (guard / "secret-scan.sh").write_text(
        "#!/usr/bin/env bash\nprintf 'SECRET-SCAN PASS: scope=%s\\n' \"$1\"\n",
        encoding="utf-8",
    )
    (guard / "pii-review.py").write_text(
        "print('PII-REVIEW PASS: no heuristic hits')\n",
        encoding="utf-8",
    )
    (guard / "whitespace_review.py").write_text(
        "print('WHITESPACE-REVIEW PASS')\n",
        encoding="utf-8",
    )
    contract = repo / "scripts" / "run_contract_tests.sh"
    contract.write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    for path in [guard / "secret-scan.sh", contract]:
        os.chmod(path, 0o755)
    git(repo, "add", "scripts")
    git(repo, "commit", "-q", "-m", "test gates")
    git(repo, "push", "-q", "origin", "main")


def test_local_ahead_creates_persisted_hold_and_human_report(tmp_path: Path) -> None:
    repo, _origin, _upstream = make_repo(tmp_path)
    add_gate_scripts(repo)
    (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
    git(repo, "add", "feature.txt")
    git(repo, "commit", "-q", "-m", "feature")

    hermes_home = tmp_path / "hermes"
    now = datetime(2026, 8, 30, 23, 55, 0, tzinfo=MYT)
    scheduled: list[dict] = []

    result = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: scheduled.append(kwargs) or "timeout-1",
    )

    assert result["status"] == "HOLD"
    assert result["release_pending"] is True
    assert result["remediation"]["status"] == "pending_confirmation"
    assert result["remediation"]["run_id"]
    assert result["remediation"]["deadline_at"] == "2026-08-31 00:25:00 MYT"
    assert result["remediation"]["actions"] == [
        {
            "kind": "push_main",
            "remote": "origin",
            "branch": "main",
            "expected_head": git(repo, "rev-parse", "HEAD"),
            "expected_remote_head": git(repo, "rev-parse", "origin/main"),
        }
    ]
    assert scheduled and scheduled[0]["run_id"] == result["remediation"]["run_id"]
    assert scheduled[0]["deadline_at"] == now + timedelta(minutes=30)

    pending_path = hermes_home / "pending" / "nightly-git-remediation.json"
    receipt_path = hermes_home / "logs" / "git-nightly-receipt.json"
    assert pending_path.is_file()
    assert receipt_path.is_file()
    pending = json.loads(pending_path.read_text(encoding="utf-8"))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert pending["run_id"] == result["remediation"]["run_id"]
    assert pending["status"] == "pending"
    assert receipt["remediation"]["status"] == "pending_confirmation"

    output = HYGIENE.render_output(result, json_display="hide")
    assert "Nightly Git report" in output
    assert "HOLD" in output
    assert "APPROVE" in output
    assert '"timestamp"' not in output

    shown = HYGIENE.render_output(result, json_display="show")
    assert '"timestamp"' in shown
    assert '"remediation"' in shown


def _make_ahead_case(tmp_path: Path) -> tuple[Path, Path, datetime]:
    repo, _origin, _upstream = make_repo(tmp_path)
    add_gate_scripts(repo)
    (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
    git(repo, "add", "feature.txt")
    git(repo, "commit", "-q", "-m", "feature")
    return repo, tmp_path / "hermes", datetime(2026, 8, 30, 23, 55, tzinfo=MYT)


def test_immediate_approval_executes_and_verifies_normal_push(tmp_path: Path) -> None:
    repo, hermes_home, now = _make_ahead_case(tmp_path)
    scheduled: list[dict] = []
    pending = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: scheduled.append(kwargs) or "timeout-approve",
    )

    result = HYGIENE.process_pending(
        decision="approve",
        run_id=pending["run_id"],
        hermes_home=hermes_home,
        now=now + timedelta(minutes=5),
    )

    assert result["status"] == "PASS"
    assert result["actions_taken"] == ["push_main"]
    assert git(repo, "rev-parse", "origin/main") == git(repo, "rev-parse", "HEAD")
    state = json.loads((hermes_home / "pending" / "nightly-git-remediation.json").read_text())
    assert state["status"] == "completed"
    assert scheduled[0]["run_id"] == pending["run_id"]


def test_explicit_reject_preserves_git_state_and_cancels_execution(tmp_path: Path) -> None:
    repo, hermes_home, now = _make_ahead_case(tmp_path)
    pending = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: "timeout-reject",
    )
    before = git(repo, "rev-parse", "origin/main")

    result = HYGIENE.process_pending(
        decision="reject",
        run_id=pending["run_id"],
        reason="owner keeps the local release unpublished",
        hermes_home=hermes_home,
        now=now + timedelta(minutes=5),
    )

    assert result["status"] == "HOLD"
    assert result["actions_taken"] == []
    assert result["remediation"]["status"] == "rejected"
    assert git(repo, "rev-parse", "origin/main") == before
    state = json.loads((hermes_home / "pending" / "nightly-git-remediation.json").read_text())
    assert state["status"] == "rejected"
    assert state["decision_reason"] == "owner keeps the local release unpublished"


def test_deadline_timeout_executes_without_chat_continuation(tmp_path: Path) -> None:
    repo, hermes_home, now = _make_ahead_case(tmp_path)
    pending = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: "timeout-deadline",
    )

    result = HYGIENE.process_pending(
        decision="timeout",
        run_id=pending["run_id"],
        hermes_home=hermes_home,
        now=now + timedelta(minutes=30),
    )

    assert result["status"] == "PASS"
    assert result["actions_taken"] == ["push_main"]
    assert git(repo, "rev-parse", "origin/main") == git(repo, "rev-parse", "HEAD")

def test_dirty_tracked_work_is_planned_as_commit_then_push(tmp_path: Path) -> None:
    repo, _origin, _upstream = make_repo(tmp_path)
    add_gate_scripts(repo)
    (repo / "README.md").write_text("legitimate daily edit\n", encoding="utf-8")
    hermes_home = tmp_path / "hermes"
    now = datetime(2026, 8, 30, 23, 55, tzinfo=MYT)

    result = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: "timeout-dirty",
    )

    assert result["status"] == "HOLD"
    assert [item["kind"] for item in result["remediation"]["actions"]] == [
        "commit_dirty",
        "push_after_commit",
    ]
    assert result["remediation"]["actions"][0]["paths"] == ["README.md"]
    assert git(repo, "rev-parse", "origin/main") == git(repo, "rev-parse", "HEAD")


def test_approved_dirty_work_commits_exact_paths_then_pushes(tmp_path: Path) -> None:
    repo, _origin, _upstream = make_repo(tmp_path)
    add_gate_scripts(repo)
    (repo / "README.md").write_text("legitimate daily edit\n", encoding="utf-8")
    hermes_home = tmp_path / "hermes"
    now = datetime(2026, 8, 30, 23, 55, tzinfo=MYT)
    pending = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: "timeout-dirty",
    )

    result = HYGIENE.process_pending(
        decision="approve",
        run_id=pending["run_id"],
        hermes_home=hermes_home,
        now=now + timedelta(minutes=5),
    )

    assert result["status"] == "PASS"
    assert result["actions_taken"] == ["commit_dirty", "push_after_commit"]
    assert git(repo, "status", "--porcelain") == ""
    assert git(repo, "rev-parse", "origin/main") == git(repo, "rev-parse", "HEAD")
    assert "chore(nightly): close daily repository hygiene" in git(repo, "log", "-1", "--format=%s")


def test_untracked_work_is_retained_as_owner_hold(tmp_path: Path) -> None:
    repo, _origin, _upstream = make_repo(tmp_path)
    add_gate_scripts(repo)
    (repo / "unknown.txt").write_text("unclassified\n", encoding="utf-8")
    hermes_home = tmp_path / "hermes"
    result = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=datetime(2026, 8, 30, 23, 55, tzinfo=MYT),
        schedule_timeout=lambda **kwargs: "must-not-schedule",
    )

    assert result["status"] == "HOLD"
    assert result["remediation"]["status"] == "blocked"
    assert result["remediation"]["actions"] == []
    assert "unknown.txt" in " ".join(result["holds"])
    assert not (hermes_home / "pending" / "nightly-git-remediation.json").exists()
    assert git(repo, "rev-parse", "origin/main") == git(repo, "rev-parse", "HEAD")


def test_security_failure_blocks_commit_and_push(tmp_path: Path) -> None:
    repo, _origin, _upstream = make_repo(tmp_path)
    add_gate_scripts(repo)
    secret = repo / "scripts" / "guard" / "secret-scan.sh"
    secret.write_text("#!/usr/bin/env bash\nprintf 'SECRET-SCAN FAIL\\n'\nexit 1\n", encoding="utf-8")
    os.chmod(secret, 0o755)
    (repo / "README.md").write_text("unsafe daily edit\n", encoding="utf-8")
    before = git(repo, "rev-parse", "origin/main")

    result = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=tmp_path / "hermes",
        now=datetime(2026, 8, 30, 23, 55, tzinfo=MYT),
        schedule_timeout=lambda **kwargs: "must-not-schedule",
    )

    assert result["status"] == "FAIL"
    assert result["remediation"]["actions"] == []
    assert result["gates"]["secret_scan_worktree_delta"]["status"] == "FAIL"
    assert git(repo, "rev-parse", "origin/main") == before
    assert git(repo, "log", "-1", "--format=%s") == "test gates"


def test_merged_local_branch_is_deleted_only_after_safe_plan(tmp_path: Path) -> None:
    repo, _origin, _upstream = make_repo(tmp_path)
    add_gate_scripts(repo)
    git(repo, "switch", "-c", "merged-old")
    (repo / "merged.txt").write_text("merged\n", encoding="utf-8")
    git(repo, "add", "merged.txt")
    git(repo, "commit", "-q", "-m", "merged work")
    git(repo, "switch", "main")
    git(repo, "merge", "--no-ff", "-q", "-m", "merge old", "merged-old")
    git(repo, "push", "-q", "origin", "main")

    hermes_home = tmp_path / "hermes"
    now = datetime(2026, 8, 30, 23, 55, tzinfo=MYT)
    pending = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: "timeout-branch",
    )

    assert pending["status"] == "HOLD"
    assert [item["kind"] for item in pending["remediation"]["actions"]] == ["delete_merged_branch"]
    assert pending["remediation"]["actions"][0]["branch"] == "merged-old"

    result = HYGIENE.process_pending(
        decision="approve",
        run_id=pending["run_id"],
        hermes_home=hermes_home,
        now=now + timedelta(minutes=5),
    )

    assert result["status"] == "PASS"
    assert result["actions_taken"] == ["delete_merged_branch"]
    assert "merged-old" not in git(repo, "branch", "--format=%(refname:short)").splitlines()


def test_unique_unmerged_stale_branch_is_retained_as_hold(tmp_path: Path) -> None:
    repo, _origin, _upstream = make_repo(tmp_path)
    add_gate_scripts(repo)
    git(repo, "switch", "-c", "unique-stale")
    (repo / "stale.txt").write_text("unique\n", encoding="utf-8")
    git(repo, "add", "stale.txt")
    old_env = os.environ.copy()
    old_env["GIT_AUTHOR_DATE"] = "2026-08-01T12:00:00+0000"
    old_env["GIT_COMMITTER_DATE"] = "2026-08-01T12:00:00+0000"
    git(repo, "commit", "-q", "-m", "unique stale work", env=old_env)
    git(repo, "switch", "main")

    result = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=tmp_path / "hermes",
        now=datetime(2026, 8, 30, 23, 55, tzinfo=MYT),
        schedule_timeout=lambda **kwargs: "must-not-schedule",
    )

    assert result["status"] == "HOLD"
    assert result["remediation"]["status"] == "blocked"
    assert result["remediation"]["actions"] == []
    assert "unique-stale" in " ".join(result["holds"])
    assert "unique-stale" in git(repo, "branch", "--format=%(refname:short)").splitlines()


def _clone_and_push_remote_change(origin: Path, tmp_path: Path, filename: str, content: str, message: str) -> Path:
    peer = tmp_path / ("peer-" + filename.replace(".", "-"))
    subprocess.run(["git", "clone", "-q", str(origin), str(peer)], check=True)
    git(peer, "config", "user.name", "Remote User")
    git(peer, "config", "user.email", "remote@example.invalid")
    (peer / filename).write_text(content, encoding="utf-8")
    git(peer, "add", filename)
    git(peer, "commit", "-q", "-m", message)
    git(peer, "push", "-q", "origin", "main")
    return peer


def test_remote_behind_local_is_fast_forwarded_after_approval(tmp_path: Path) -> None:
    repo, origin, _upstream = make_repo(tmp_path)
    add_gate_scripts(repo)
    _clone_and_push_remote_change(origin, tmp_path, "remote.txt", "remote\n", "remote change")
    hermes_home = tmp_path / "hermes"
    now = datetime(2026, 8, 30, 23, 55, tzinfo=MYT)

    pending = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: "timeout-ff",
    )

    assert pending["status"] == "HOLD"
    assert [item["kind"] for item in pending["remediation"]["actions"]] == ["fast_forward_origin"]
    result = HYGIENE.process_pending(
        decision="approve",
        run_id=pending["run_id"],
        hermes_home=hermes_home,
        now=now + timedelta(minutes=5),
    )
    assert result["status"] == "PASS"
    assert result["actions_taken"] == ["fast_forward_origin"]
    assert git(repo, "rev-parse", "HEAD") == git(repo, "rev-parse", "origin/main")


def test_conflict_free_divergence_is_merged_and_pushed(tmp_path: Path) -> None:
    repo, origin, _upstream = make_repo(tmp_path)
    add_gate_scripts(repo)
    (repo / "local.txt").write_text("local\n", encoding="utf-8")
    git(repo, "add", "local.txt")
    git(repo, "commit", "-q", "-m", "local change")
    _clone_and_push_remote_change(origin, tmp_path, "remote.txt", "remote\n", "remote change")
    hermes_home = tmp_path / "hermes"
    now = datetime(2026, 8, 30, 23, 55, tzinfo=MYT)

    pending = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: "timeout-merge",
    )

    assert pending["status"] == "HOLD"
    assert [item["kind"] for item in pending["remediation"]["actions"]] == [
        "merge_origin",
        "push_merged_main",
    ]
    result = HYGIENE.process_pending(
        decision="approve",
        run_id=pending["run_id"],
        hermes_home=hermes_home,
        now=now + timedelta(minutes=5),
    )
    assert result["status"] == "PASS"
    assert result["actions_taken"] == ["merge_origin", "push_merged_main"]
    assert git(repo, "rev-parse", "HEAD") == git(repo, "rev-parse", "origin/main")
    assert (repo / "local.txt").is_file() and (repo / "remote.txt").is_file()


def test_substantive_divergence_is_hard_stop_without_pending_execution(tmp_path: Path) -> None:
    repo, origin, _upstream = make_repo(tmp_path)
    add_gate_scripts(repo)
    (repo / "README.md").write_text("local conflict\n", encoding="utf-8")
    git(repo, "add", "README.md")
    git(repo, "commit", "-q", "-m", "local conflict")
    _clone_and_push_remote_change(origin, tmp_path, "README.md", "remote conflict\n", "remote conflict")
    hermes_home = tmp_path / "hermes"
    before = git(repo, "rev-parse", "HEAD")

    result = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=datetime(2026, 8, 30, 23, 55, tzinfo=MYT),
        schedule_timeout=lambda **kwargs: "must-not-schedule",
    )

    assert result["status"] == "HOLD"
    assert result["remediation"]["actions"] == []
    assert any("conflict" in hold for hold in result["holds"])
    assert git(repo, "rev-parse", "HEAD") == before
    assert not (hermes_home / "pending" / "nightly-git-remediation.json").exists()


def test_clean_repository_reports_pass_without_creating_remediation(tmp_path: Path) -> None:
    repo, _origin, _upstream = make_repo(tmp_path)
    add_gate_scripts(repo)
    hermes_home = tmp_path / "hermes"
    scheduled: list[dict] = []

    result = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=datetime(2026, 8, 30, 23, 55, tzinfo=MYT),
        schedule_timeout=lambda **kwargs: scheduled.append(kwargs) or "must-not-schedule",
    )

    assert result["status"] == "PASS"
    assert result["remediation"]["status"] == "none"
    assert result["remediation"]["actions"] == []
    assert result["actions_taken"] == []
    assert scheduled == []
    assert not (hermes_home / "pending" / "nightly-git-remediation.json").exists()
    assert "None. No remediation is required." in result["human_report"]


def test_contract_test_failure_is_fail_closed_without_pending_plan(tmp_path: Path) -> None:
    repo, _origin, _upstream = make_repo(tmp_path)
    add_gate_scripts(repo)
    contract = repo / "scripts" / "run_contract_tests.sh"
    contract.write_text("#!/usr/bin/env bash\nprintf 'CONTRACT FAIL\\n'\nexit 7\n", encoding="utf-8")
    os.chmod(contract, 0o755)
    before = git(repo, "rev-parse", "HEAD")

    result = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=tmp_path / "hermes",
        now=datetime(2026, 8, 30, 23, 55, tzinfo=MYT),
        schedule_timeout=lambda **kwargs: "must-not-schedule",
    )

    assert result["status"] == "FAIL"
    assert result["gates"]["contract_tests"]["status"] == "FAIL"
    assert result["remediation"]["actions"] == []
    assert not (tmp_path / "hermes" / "pending" / "nightly-git-remediation.json").exists()
    assert git(repo, "rev-parse", "HEAD") == before


def test_timeout_before_deadline_does_not_execute_or_change_state(tmp_path: Path) -> None:
    repo, hermes_home, now = _make_ahead_case(tmp_path)
    pending = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: "timeout-early",
    )
    before = git(repo, "rev-parse", "origin/main")

    result = HYGIENE.process_pending(
        decision="timeout",
        run_id=pending["run_id"],
        hermes_home=hermes_home,
        now=now + timedelta(minutes=10),
    )

    assert result["status"] == "HOLD"
    assert result["remediation"]["status"] == "pending_confirmation"
    assert result["actions_taken"] == []
    assert git(repo, "rev-parse", "origin/main") == before
    state = json.loads((hermes_home / "pending" / "nightly-git-remediation.json").read_text())
    assert state["status"] == "pending"


def test_pending_deadline_survives_fresh_module_load(tmp_path: Path) -> None:
    repo, hermes_home, now = _make_ahead_case(tmp_path)
    pending = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: "timeout-restart",
    )
    fresh_spec = importlib.util.spec_from_file_location("nightly_git_hygiene_fresh", MODULE_PATH)
    assert fresh_spec and fresh_spec.loader
    fresh = importlib.util.module_from_spec(fresh_spec)
    sys.modules[fresh_spec.name] = fresh
    fresh_spec.loader.exec_module(fresh)

    result = fresh.process_pending(
        decision="timeout",
        run_id=pending["run_id"],
        hermes_home=hermes_home,
        now=now + timedelta(minutes=30),
    )

    assert result["status"] == "PASS"
    assert result["actions_taken"] == ["push_main"]
    assert git(repo, "rev-parse", "origin/main") == git(repo, "rev-parse", "HEAD")


def test_repeated_nightly_audit_reuses_existing_pending_plan(tmp_path: Path) -> None:
    repo, hermes_home, now = _make_ahead_case(tmp_path)
    scheduled: list[dict] = []
    first = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: scheduled.append(kwargs) or "timeout-once",
    )
    second = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now + timedelta(minutes=5),
        schedule_timeout=lambda **kwargs: scheduled.append(kwargs) or "must-not-schedule-twice",
    )

    assert first["remediation"]["status"] == "pending_confirmation"
    assert second["status"] == "HOLD"
    assert second["run_id"] == first["run_id"]
    assert second["remediation"]["deadline_at"] == first["remediation"]["deadline_at"]
    assert len(scheduled) == 1
    state = json.loads((hermes_home / "pending" / "nightly-git-remediation.json").read_text())
    assert state["run_id"] == first["run_id"]
    assert state["status"] == "pending"


def test_json_display_mode_uses_atomic_config_setting(tmp_path: Path) -> None:
    home = tmp_path / "hermes"
    home.mkdir()
    (home / "config.yaml").write_text("display:\n  interface: cli\n", encoding="utf-8")

    assert HYGIENE.set_json_display_mode(home, "show") == "show"
    assert HYGIENE._json_display_mode(home / "config.yaml") == "show"
    assert HYGIENE.set_json_display_mode(home, "hide") == "hide"
    assert HYGIENE._json_display_mode(home / "config.yaml") == "hide"


def test_pending_plan_is_invalidated_when_head_changes(tmp_path: Path) -> None:
    repo, hermes_home, now = _make_ahead_case(tmp_path)
    pending = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: "timeout-invalidated",
    )
    (repo / "late.txt").write_text("new work after recommendation\n", encoding="utf-8")
    git(repo, "add", "late.txt")
    git(repo, "commit", "-q", "-m", "late change")
    before_remote = git(repo, "rev-parse", "origin/main")

    result = HYGIENE.process_pending(
        decision="approve",
        run_id=pending["run_id"],
        hermes_home=hermes_home,
        now=now + timedelta(minutes=5),
    )

    assert result["status"] == "HOLD"
    assert result["actions_taken"] == []
    assert "invalidated" in " ".join(result["holds"])
    assert git(repo, "rev-parse", "origin/main") == before_remote


def test_native_timeout_job_uses_profile_store_and_once_schedule(tmp_path: Path) -> None:
    home = tmp_path / "hermes"
    scripts = home / "scripts"
    scripts.mkdir(parents=True)
    (scripts / HYGIENE.TIMEOUT_SCRIPT).write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    os.chmod(scripts / HYGIENE.TIMEOUT_SCRIPT, 0o755)

    job_id = HYGIENE._schedule_timeout_job(
        deadline_at=datetime(2026, 8, 31, 0, 25, tzinfo=MYT),
        run_id="RUN-SCHEDULE",
        repo_root=tmp_path,
        hermes_home=home,
    )

    jobs = json.loads((home / "cron" / "jobs.json").read_text(encoding="utf-8"))
    job = next(item for item in jobs["jobs"] if item["id"] == job_id)
    assert job["no_agent"] is True
    assert job["script"] == HYGIENE.TIMEOUT_SCRIPT
    assert job["schedule"]["kind"] == "once"
    assert job["schedule"]["run_at"] == "2026-08-31T00:25:00+08:00"
    assert job["repeat"] == {"times": 1, "completed": 0}

    HYGIENE._cancel_timeout_job(job_id, home)
    remaining = json.loads((home / "cron" / "jobs.json").read_text(encoding="utf-8"))
    assert remaining["jobs"] == []


def test_timeout_wrapper_executes_persisted_plan_in_fresh_process(tmp_path: Path) -> None:
    repo, hermes_home, now = _make_ahead_case(tmp_path)
    pending = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: "timeout-wrapper",
    )
    scripts = hermes_home / "scripts"
    scripts.mkdir(parents=True)
    pending_path = hermes_home / "pending" / "nightly-git-remediation.json"
    pending_state = json.loads(pending_path.read_text(encoding="utf-8"))
    pending_state["deadline_at"] = "2026-08-30T00:25:00+08:00"
    pending_path.write_text(json.dumps(pending_state) + "\n", encoding="utf-8")
    target = scripts / "nightly_git_hygiene.py"
    wrapper = scripts / "nightly_git_hygiene_timeout.sh"
    shutil.copy2(MODULE_PATH, target)
    shutil.copy2(REPO_ROOT / "scripts" / "nightly_git_hygiene_timeout.sh", wrapper)
    os.chmod(target, 0o755)
    os.chmod(wrapper, 0o755)
    env = os.environ.copy()
    env["HERMES_HOME"] = str(hermes_home)
    result = subprocess.run(
        [str(wrapper)],
        env=env,
        cwd=str(repo),
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Final result:" in result.stdout
    assert pending["run_id"] in result.stdout
    assert git(repo, "rev-parse", "origin/main") == git(repo, "rev-parse", "HEAD")


def test_timeout_after_completed_plan_is_silent_noop(tmp_path: Path) -> None:
    repo, hermes_home, now = _make_ahead_case(tmp_path)
    pending = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: "timeout-silent",
    )
    completed = HYGIENE.process_pending(
        decision="approve",
        run_id=pending["run_id"],
        hermes_home=hermes_home,
        now=now + timedelta(minutes=5),
    )
    assert completed["status"] == "PASS"

    late_timeout = HYGIENE.process_pending(
        decision="timeout",
        run_id=pending["run_id"],
        hermes_home=hermes_home,
        now=now + timedelta(minutes=30),
    )
    assert late_timeout["status"] == "PASS"
    assert late_timeout.get("_silent") is True
    assert late_timeout["actions_taken"] == ["push_main"]
