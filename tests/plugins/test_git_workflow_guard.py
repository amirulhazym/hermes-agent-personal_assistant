from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add plugins dir to sys.path
plugins_dir = Path("/home/ubuntu/hermes-agent-personal_assistant-work/plugins")
if str(plugins_dir) not in sys.path:
    sys.path.insert(0, str(plugins_dir))

from importlib import import_module
guard_mod = import_module("git-workflow-guard")
guard_pre_tool_call = guard_mod.guard_pre_tool_call


def test_blocks_git_init():
    res = guard_pre_tool_call("terminal", {"command": "git init my-new-repo"})
    assert res is not None
    assert res.get("action") == "block"
    assert "git init" in res.get("message", "").lower()


def test_blocks_arbitrary_branch_creation():
    for cmd in ["git checkout -b feature-test", "git switch -c new-idea", "git branch my-test"]:
        res = guard_pre_tool_call("terminal", {"command": cmd})
        assert res is not None, f"Failed to block: {cmd}"
        assert res.get("action") == "block"
        assert "forbidden" in res.get("message", "").lower()


def test_blocks_worktree_add():
    res = guard_pre_tool_call("terminal", {"command": "git worktree add ../wt-test"})
    assert res is not None
    assert res.get("action") == "block"
    assert "worktree add" in res.get("message", "").lower()


def test_blocks_duplicate_clone():
    res = guard_pre_tool_call("terminal", {"command": "git clone https://github.com/amirulhazym/hermes-agent-personal_assistant.git clone-2"})
    assert res is not None
    assert res.get("action") == "block"
    assert "duplicate personal clones" in res.get("message", "").lower()


def test_blocks_commit_in_runtime_dependency():
    res = guard_pre_tool_call("terminal", {"command": "git commit -m 'direct edit'", "workdir": "/home/ubuntu/.hermes/hermes-agent"})
    assert res is not None
    assert res.get("action") == "block"
    assert "direct 'commit' inside runtime dependency" in res.get("message", "").lower()


def test_blocks_direct_write_file_in_runtime_dependency():
    for target in [
        "/home/ubuntu/.hermes/hermes-agent/gateway/run.py",
        "/home/ubuntu/.hermes/plugins/antigravity-provider/src/antigravity_provider/models.py",
    ]:
        res = guard_pre_tool_call("write_file", {"path": target, "content": "foo"})
        assert res is not None, f"Failed to block write_file to {target}"
        assert res.get("action") == "block"
        assert "direct mutation of live runtime dependency" in res.get("message", "").lower()


def test_blocks_direct_patch_in_runtime_dependency():
    res = guard_pre_tool_call("patch", {"path": "/home/ubuntu/.hermes/hermes-agent/agent/turn.py", "old_string": "a", "new_string": "b"})
    assert res is not None
    assert res.get("action") == "block"
    assert "direct mutation of live runtime dependency" in res.get("message", "").lower()


def test_allows_normal_git_operations_in_personal_repo():
    allowed_cmds = [
        "git status -sb",
        "git diff origin/main",
        "git log -n 5 --oneline",
        "git fetch --prune origin",
        "git add .",
        "git commit -m 'legitimate work'",
        "git branch -l",
        "git branch -a",
        "git branch -d merged-test",
    ]
    for cmd in allowed_cmds:
        res = guard_pre_tool_call("terminal", {"command": cmd, "workdir": "/home/ubuntu/hermes-agent-personal_assistant-work"})
        assert res is None, f"Incorrectly blocked legitimate command: {cmd}"


def test_allows_trusted_publisher_branch_operations():
    with patch.dict(os.environ, {"HERMES_TRUSTED_PUBLISHER": "1"}):
        res = guard_pre_tool_call("terminal", {"command": "git checkout -b nightly/publication-12345"})
        assert res is None, "Trusted publisher was blocked"


def test_allows_trusted_deployer_direct_mutation():
    with patch.dict(os.environ, {"HERMES_TRUSTED_DEPLOYER": "1"}):
        res = guard_pre_tool_call("write_file", {"path": "/home/ubuntu/.hermes/hermes-agent/gateway/run.py", "content": "foo"})
        assert res is None, "Trusted deployer was blocked"
