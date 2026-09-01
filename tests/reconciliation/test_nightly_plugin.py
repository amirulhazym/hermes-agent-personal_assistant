from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_PATH = ROOT / "plugins" / "nightly-git-closure" / "__init__.py"
SPEC = importlib.util.spec_from_file_location("nightly_git_closure_plugin", PLUGIN_PATH)
assert SPEC and SPEC.loader
PLUGIN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PLUGIN
SPEC.loader.exec_module(PLUGIN)


class FakeContext:
    def __init__(self) -> None:
        self.commands: dict[str, Callable[..., Any]] = {}
        self.hooks: dict[str, Callable[..., Any]] = {}

    def register_command(self, name: str, *, handler: Callable[..., Any], description: str, args_hint: str) -> None:
        self.commands[name] = handler

    def register_hook(self, event: str, handler: Callable[..., Any]) -> None:
        self.hooks[event] = handler


def test_plugin_registers_authenticated_nightly_controls() -> None:
    ctx = FakeContext()
    PLUGIN.register(ctx)

    assert "nightly" in ctx.commands
    assert "pre_gateway_dispatch" in ctx.hooks


def test_approve_dispatches_exact_pending_command_without_llm(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(PLUGIN, "_run_target", lambda args: calls.append(args) or "approved report")
    ctx = FakeContext()
    PLUGIN.register(ctx)

    response = ctx.commands["nightly"]("approve RUN-123")

    assert response == "approved report"
    assert calls == [["--approve", "--run-id", "RUN-123", "--human-only"]]


def test_reject_dispatches_reason_without_execution(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(PLUGIN, "_run_target", lambda args: calls.append(args) or "rejected report")
    ctx = FakeContext()
    PLUGIN.register(ctx)

    response = ctx.commands["nightly"]("reject RUN-123 owner wants to keep it local")

    assert response == "rejected report"
    assert calls == [[
        "--reject",
        "--run-id",
        "RUN-123",
        "--reason",
        "owner wants to keep it local",
        "--human-only",
    ]]


def test_json_show_hide_are_explicit_and_persisted_via_target(monkeypatch) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(PLUGIN, "_run_target", lambda args: calls.append(args) or "JSON display: show")
    ctx = FakeContext()
    PLUGIN.register(ctx)

    response = ctx.commands["nightly"]("json show")

    assert response == "JSON display: show"
    assert calls == [["--set-json-display", "show", "--human-only"]]


def test_pre_dispatch_only_rewrites_exact_approval_to_slash_command() -> None:
    ctx = FakeContext()
    PLUGIN.register(ctx)
    hook = ctx.hooks["pre_gateway_dispatch"]

    assert hook("APPROVE NIGHTLY RUN-123") == {"action": "rewrite", "text": "/nightly approve RUN-123"}
    assert hook("REJECT NIGHTLY RUN-123 reason") == {"action": "rewrite", "text": "/nightly reject RUN-123 reason"}
    assert hook("SET NIGHTLY GITHUB_TOKEN github_pat_1234567890abcdef1234567890") == {
        "action": "rewrite",
        "text": "/nightly auth github_pat_1234567890abcdef1234567890",
    }
    assert hook("approve this unrelated thing") is None


def test_auth_intake_stores_in_env_and_verifies_without_llm(tmp_path: Path, monkeypatch) -> None:
    fake_home = tmp_path / ".hermes"
    fake_home.mkdir(parents=True)
    fake_env = fake_home / ".env"
    fake_env.write_text("SOME_VAR=123\n", encoding="utf-8")
    monkeypatch.setenv("HERMES_HOME", str(fake_home))

    class FakeResp:
        def __init__(self, data: Any) -> None:
            self._data = json.dumps(data).encode("utf-8")

        def read(self) -> bytes:
            return self._data

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    def fake_urlopen(req, timeout=15):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "check-runs" in url:
            return FakeResp({"total_count": 1})
        if "pulls" in url:
            return FakeResp([{"number": 1}])
        if "ref" in url:
            return FakeResp({"object": {"sha": "abc"}})
        return FakeResp({"full_name": "amirulhazym/hermes-agent-personal_assistant"})

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    ctx = FakeContext()
    PLUGIN.register(ctx)

    test_token = "github_pat_1234567890123456789012345678901234567890"
    res = ctx.commands["nightly"](f"auth {test_token}")

    assert "✅ GITHUB_TOKEN securely saved" in res
    assert "Repository Access: PASS" in res
    assert "Pull Requests API: PASS" in res

    # Verify .env contents
    saved_env = fake_env.read_text(encoding="utf-8")
    assert f"GITHUB_TOKEN={test_token}" in saved_env
    assert "SOME_VAR=123" in saved_env
    assert oct(fake_env.stat().st_mode)[-3:] == "600"


def test_plugin_is_discovered_in_an_isolated_enabled_profile(tmp_path: Path) -> None:
    home = tmp_path / ".hermes"
    plugin_dir = home / "plugins" / "nightly-git-closure"
    plugin_dir.mkdir(parents=True)
    shutil.copy2(PLUGIN_PATH.parent / "plugin.yaml", plugin_dir / "plugin.yaml")
    shutil.copy2(PLUGIN_PATH, plugin_dir / "__init__.py")
    (home / "config.yaml").write_text("plugins:\n  enabled:\n    - nightly-git-closure\n", encoding="utf-8")
    env = os.environ.copy()
    env["HERMES_HOME"] = str(home)
    env["PYTHONPATH"] = "/home/ubuntu/.hermes/hermes-agent"
    probe = (
        "from hermes_cli.plugins import discover_plugins; "
        "from hermes_cli.commands import _iter_plugin_command_entries; "
        "discover_plugins(force=True); "
        "print([entry for entry in _iter_plugin_command_entries() if entry[0] == 'nightly'])"
    )
    result = subprocess.run(
        [sys.executable, "-c", probe],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "nightly" in result.stdout
