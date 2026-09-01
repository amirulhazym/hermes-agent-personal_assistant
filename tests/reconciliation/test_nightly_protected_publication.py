from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "nightly_git_hygiene.py"
SPEC = importlib.util.spec_from_file_location("nightly_git_hygiene_protected", MODULE_PATH)
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
    git(repo, "config", "commit.gpgSign", "false")
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


def _make_ahead_case(tmp_path: Path) -> tuple[Path, Path, datetime]:
    repo, origin, upstream = make_repo(tmp_path)
    add_gate_scripts(repo)
    hermes_home = tmp_path / "hermes"
    hermes_home.mkdir(parents=True, exist_ok=True)
    (hermes_home / ".env").write_text("GITHUB_TOKEN=test_token_123456789012345\n", encoding="utf-8")

    now = datetime(2026, 9, 1, 23, 55, 0, tzinfo=MYT)
    (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
    git(repo, "add", "feature.txt")
    env = os.environ.copy()
    author_date = now.isoformat()
    env["GIT_AUTHOR_DATE"] = author_date
    env["GIT_COMMITTER_DATE"] = author_date
    subprocess.run(["git", "commit", "-q", "-m", "feature"], cwd=str(repo), env=env, check=True)

    scripts = hermes_home / "scripts"
    scripts.mkdir(parents=True, exist_ok=True)
    target = scripts / "nightly_git_hygiene.py"
    shutil.copy2(MODULE_PATH, target)
    os.chmod(target, 0o755)

    return repo, hermes_home, now


def test_protected_main_publication_on_direct_push_refusal(tmp_path: Path, monkeypatch: Any) -> None:
    repo, hermes_home, now = _make_ahead_case(tmp_path)

    real_workflow_git = HYGIENE._workflow_git

    def mock_workflow_git(r: Path, cmd: list[str], env: dict[str, str] | None = None) -> tuple[int, str]:
        if cmd[:3] == ["push", "origin", "main"]:
            return 1, "remote: error: GH006: Protected branch hook declined"
        if cmd[:2] == ["remote", "get-url"]:
            return 0, "https://github.com/amirulhazym/hermes-agent-personal_assistant.git"
        return real_workflow_git(r, cmd, env=env)

    monkeypatch.setattr(HYGIENE, "_workflow_git", mock_workflow_git)

    api_calls: list[tuple[str, str, Any]] = []

    def mock_api_request(method: str, path: str, token: str, payload: Any = None) -> tuple[int, Any, str | None]:
        api_calls.append((method, path, payload))
        if method == "GET" and "/pulls?state=open" in path:
            return 200, [], None
        if method == "POST" and "/pulls" in path:
            return 201, {"number": 42, "head": {"sha": "head_sha_123"}}, None
        if method == "GET" and "/check-runs" in path:
            return 200, {"check_runs": [{"status": "completed", "conclusion": "success"}]}, None
        if method == "PUT" and "/pulls/42/merge" in path:
            origin_repo = tmp_path / "origin.git"
            head_sha = git(repo, "rev-parse", "HEAD")
            subprocess.run(["git", "--git-dir", str(origin_repo), "update-ref", "refs/heads/main", head_sha], check=True)
            return 200, {"merged": True, "sha": head_sha}, None
        return 200, {}, None

    monkeypatch.setattr(HYGIENE, "_github_api_request", mock_api_request)

    pending = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: "timeout-protected",
    )

    result = HYGIENE.process_pending(
        decision="approve",
        run_id=pending["run_id"],
        hermes_home=hermes_home,
        now=now + timedelta(minutes=5),
    )

    assert result["status"] == "PASS"
    assert result["actions_taken"] == ["push_main"]
    assert any(method == "POST" and "/pulls" in path for method, path, _ in api_calls)
    assert any(method == "PUT" and "/merge" in path for method, path, _ in api_calls)


def test_protected_main_publication_stops_on_failing_ci_checks(tmp_path: Path, monkeypatch: Any) -> None:
    repo, hermes_home, now = _make_ahead_case(tmp_path)

    real_workflow_git = HYGIENE._workflow_git

    def mock_workflow_git(r: Path, cmd: list[str], env: dict[str, str] | None = None) -> tuple[int, str]:
        if cmd[:3] == ["push", "origin", "main"]:
            return 1, "remote: error: GH006: Protected branch hook declined"
        if cmd[:2] == ["remote", "get-url"]:
            return 0, "https://github.com/amirulhazym/hermes-agent-personal_assistant.git"
        return real_workflow_git(r, cmd, env=env)

    monkeypatch.setattr(HYGIENE, "_workflow_git", mock_workflow_git)

    def mock_api_request(method: str, path: str, token: str, payload: Any = None) -> tuple[int, Any, str | None]:
        if method == "GET" and "/pulls?state=open" in path:
            return 200, [], None
        if method == "POST" and "/pulls" in path:
            return 201, {"number": 99, "head": {"sha": "fail_sha_123"}}, None
        if method == "GET" and "/check-runs" in path:
            return 200, {"check_runs": [{"status": "completed", "conclusion": "failure"}]}, None
        return 200, {}, None

    monkeypatch.setattr(HYGIENE, "_github_api_request", mock_api_request)

    pending = HYGIENE.run_nightly(
        repo_root=repo,
        hermes_home=hermes_home,
        now=now,
        schedule_timeout=lambda **kwargs: "timeout-protected-fail",
    )

    result = HYGIENE.process_pending(
        decision="approve",
        run_id=pending["run_id"],
        hermes_home=hermes_home,
        now=now + timedelta(minutes=5),
    )

    assert result["status"] == "HOLD"
    assert result["actions_taken"] == []
    assert any("GitHub CI check runs failed" in h for h in result["holds"])
