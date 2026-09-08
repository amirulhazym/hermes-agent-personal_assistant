from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONTEXT_PATH = ROOT / "scripts" / "nightly_autofix_context.py"
MYT = timezone(timedelta(hours=8))


def load_context_module():
    assert CONTEXT_PATH.is_file(), "autofix context collector is missing"
    spec = importlib.util.spec_from_file_location("nightly_autofix_context", CONTEXT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_autofix_context_contains_primary_receipt_and_safe_policy(tmp_path: Path) -> None:
    context = load_context_module()
    hermes_home = tmp_path / "hermes"
    history = hermes_home / "logs" / "git-nightly-history"
    history.mkdir(parents=True)
    run_id = "20260908T155600Z-abcdef123456-0123456789abcdef0123456789abcdef"
    (history / f"{run_id}.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "timestamp": "2026-09-08 23:56:00 MYT",
                "status": "FAIL",
                "errors": ["synthetic failure"],
                "holds": [],
                "actions_taken": [],
                "remediation": {"status": "blocked", "actions": []},
            }
        )
        + "\n",
        encoding="utf-8",
    )

    payload = context.collect_context(
        repo_root=tmp_path / "repo-does-not-exist",
        hermes_home=hermes_home,
        now=datetime(2026, 9, 9, 0, 25, tzinfo=MYT),
    )

    assert payload["primary"]["run_id"] == run_id
    assert payload["primary"]["status"] == "FAIL"
    assert payload["policy"]["mode"] == "autonomous remediation"
    assert payload["policy"]["not_owner_approved"] is True
    assert payload["policy"]["final_verification_time"] == "01:55 MYT"
    assert "safe, reversible" in payload["policy"]["repair_rule"]

    rendered = context.render_context(payload)
    assert "00:25 MYT" in rendered
    assert "synthetic failure" in rendered
    assert "not limited to Git" in rendered


def test_job_spec_is_exactly_thirty_minutes_after_primary_and_agent_mode() -> None:
    context = load_context_module()
    spec = context.autofix_job_spec()

    assert spec["name"] == "nightly-autofix-30m"
    assert spec["schedule"] == "25 0 * * *"
    assert spec["no_agent"] is False
    assert spec["script"] == "nightly_autofix_context.py"
    assert spec["workdir"] == "/home/ubuntu/hermes-agent-personal_assistant-work"
    assert spec["deliver"] == "origin"
    assert "not limited to Git" in spec["prompt"]
    assert "01:55" in spec["prompt"]
