from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PLUGIN_PATH = ROOT / "plugins" / "nightly-git-closure" / "__init__.py"
SPEC = importlib.util.spec_from_file_location("nightly_git_closure_plugin", PLUGIN_PATH)
assert SPEC and SPEC.loader
PLUGIN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PLUGIN
SPEC.loader.exec_module(PLUGIN)


class FakeContext:
    def __init__(self) -> None:
        self.commands: dict[str, object] = {}
        self.hooks: dict[str, object] = {}

    def register_command(self, name: str, *, handler, description: str, args_hint: str) -> None:
        self.commands[name] = handler

    def register_hook(self, event: str, handler) -> None:
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
    assert hook("approve this unrelated thing") is None


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
