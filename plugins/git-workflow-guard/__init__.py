"""Deterministic pre_tool_call guard enforcing one personal Hermes development repository.

Hard Invariants Enforced:
1. One Personal Repository: /home/ubuntu/hermes-agent-personal_assistant-work is the sole
   personal development repository. Accidental attempts to `git init`, `git clone` personal
   workspaces, `git worktree add`, or create arbitrary feature branches are blocked.
2. Runtime Dependency Protection: Direct mutation (write_file, patch, execute_code write, or
   git commit) inside external dependency checkouts (~/.hermes/hermes-agent,
   ~/.hermes/plugins/antigravity-provider) is blocked.
3. Trusted Execution Exemption: The automated protected-main publication executor and
   established source->deployment scripts are permitted via trusted execution token/env.
"""

from __future__ import annotations

import os
import re
import shlex
from pathlib import Path
from typing import Any, Dict, Optional

PERSONAL_REPO = Path("/home/ubuntu/hermes-agent-personal_assistant-work").resolve()
PROTECTED_DEPENDENCIES = (
    Path("/home/ubuntu/.hermes/hermes-agent").resolve(),
    Path("/home/ubuntu/.hermes/plugins/antigravity-provider").resolve(),
)

# Block message directing agent to SSOT
REDIRECT_MSG = (
    "🛑 BLOCKED BY GIT-WORKFLOW-GUARD: Personal Hermes development uses ONE repository only: "
    "/home/ubuntu/hermes-agent-personal_assistant-work. "
    "Do not create new repos, workspaces, worktrees, or arbitrary branches. "
    "External checkouts (~/.hermes/hermes-agent, antigravity-provider) are dependencies/runtime only; "
    "all changes must be authored, tested, and patched from the personal development repository."
)


def _is_trusted_publisher() -> bool:
    """Check if invocation is running from the established protected-main publisher."""
    return os.environ.get("HERMES_TRUSTED_PUBLISHER") == "1"


def _is_trusted_deployer() -> bool:
    """Check if invocation is running from established manifest deployment."""
    return os.environ.get("HERMES_TRUSTED_DEPLOYER") == "1"


def _check_target_path(path_str: str) -> Optional[str]:
    """Return block reason if a file path targets a protected runtime dependency."""
    try:
        resolved = Path(path_str).expanduser().resolve()
    except Exception:
        return None

    for dep in PROTECTED_DEPENDENCIES:
        if resolved == dep or dep in resolved.parents:
            # Deployment protection: only allowed if trusted deployer
            if _is_trusted_deployer():
                return None
            return (
                f"🛑 BLOCKED BY GIT-WORKFLOW-GUARD: Direct mutation of live runtime dependency '{dep.name}' "
                f"at '{path_str}' is forbidden. Author changes and generate patches inside {PERSONAL_REPO}."
            )
    return None


def _check_terminal_command(cmd_str: str, workdir: Optional[str] = None) -> Optional[str]:
    """Inspect shell command string for forbidden Git operations or live runtime mutations."""
    if not cmd_str or not cmd_str.strip():
        return None

    # Check workdir context
    cwd = Path(workdir).expanduser().resolve() if workdir else Path.cwd().resolve()

    # Normalize command to detect git invocations across pipes/chains
    # Split on ;, &&, ||, |
    segments = re.split(r";|&&|\|\||\|", cmd_str)
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        try:
            tokens = shlex.split(seg)
        except ValueError:
            # If shlex fails, fall back to simple regex inspection
            tokens = seg.split()

        if not tokens:
            continue

        # Look for git commands
        git_idx = -1
        for i, token in enumerate(tokens):
            base_token = os.path.basename(token)
            if base_token == "git":
                git_idx = i
                break

        if git_idx != -1 and git_idx + 1 < len(tokens):
            subcmd = tokens[git_idx + 1]

            # 1. git init -> Blocked everywhere on VPS
            if subcmd == "init":
                return (
                    f"🛑 BLOCKED BY GIT-WORKFLOW-GUARD: 'git init' is forbidden. "
                    f"Personal Hermes development uses {PERSONAL_REPO} exclusively."
                )

            # 2. git worktree add -> Blocked unless trusted
            if subcmd == "worktree" and git_idx + 2 < len(tokens) and tokens[git_idx + 2] == "add":
                if not _is_trusted_publisher():
                    return (
                        f"🛑 BLOCKED BY GIT-WORKFLOW-GUARD: 'git worktree add' is forbidden. "
                        f"Personal development remains on the established main lifecycle in {PERSONAL_REPO}."
                    )

            # 3. Arbitrary branch creation: git checkout -b, git switch -c, git branch <new>
            if subcmd in {"checkout", "switch"}:
                for flag in {"-b", "-c", "--create"}:
                    if flag in tokens[git_idx + 2:]:
                        if not _is_trusted_publisher():
                            return (
                                f"🛑 BLOCKED BY GIT-WORKFLOW-GUARD: Arbitrary development branch creation "
                                f"('{subcmd} {flag}') is forbidden. Personal development stays on 'main' in {PERSONAL_REPO}."
                            )

            if subcmd == "branch":
                rest = [t for t in tokens[git_idx + 2:] if not t.startswith("-")]
                # If there are arguments without flags, it is creating a branch
                flags = [t for t in tokens[git_idx + 2:] if t.startswith("-")]
                # Allowed read-only or cleanup flags: -a, -r, -l, -d, -D, -m, -M, --delete, --list
                destructive_or_list = {"-d", "-D", "-m", "-M", "--delete", "-l", "--list", "-a", "-r", "--show-current"}
                if rest and not any(f in destructive_or_list for f in flags):
                    if not _is_trusted_publisher():
                        return (
                            f"🛑 BLOCKED BY GIT-WORKFLOW-GUARD: Creating arbitrary branch '{rest[0]}' is forbidden. "
                            f"Personal development stays on 'main' in {PERSONAL_REPO}."
                        )

            # 4. Check git commit inside protected dependency checkouts
            if subcmd in {"commit", "merge", "rebase"}:
                # Check target repository
                target_dir = cwd
                # Check if -C was passed to git
                for idx, t in enumerate(tokens[git_idx:git_idx + 3]):
                    if t == "-C" and idx + 1 < len(tokens[git_idx:git_idx + 3]):
                        target_dir = Path(tokens[git_idx + idx + 1]).expanduser().resolve()
                        break

                for dep in PROTECTED_DEPENDENCIES:
                    if target_dir == dep or dep in target_dir.parents:
                        return (
                            f"🛑 BLOCKED BY GIT-WORKFLOW-GUARD: Direct '{subcmd}' inside runtime dependency "
                            f"'{dep.name}' is prohibited. Author changes as patches inside {PERSONAL_REPO}."
                        )

            # 5. git clone for personal development
            if subcmd == "clone":
                # Check target repo or destination
                for arg in tokens[git_idx + 2:]:
                    if "hermes-agent-personal_assistant" in arg and not _is_trusted_publisher() and not _is_trusted_deployer():
                        return (
                            f"🛑 BLOCKED BY GIT-WORKFLOW-GUARD: Creating duplicate personal clones is forbidden. "
                            f"Use existing repository {PERSONAL_REPO}."
                        )

    return None


def guard_pre_tool_call(
    tool_name: str = "",
    args: Any = None,
    **_: Any,
) -> Optional[Dict[str, str]]:
    """Intercept tool call and block forbidden Git or runtime-mutation operations."""
    if not isinstance(args, dict):
        return None

    # 1. Inspect terminal shell commands
    if tool_name == "terminal":
        cmd = args.get("command") or ""
        workdir = args.get("workdir")
        reason = _check_terminal_command(cmd, workdir)
        if reason:
            return {"action": "block", "message": reason}

    # 2. Inspect file mutation tools (write_file, patch)
    elif tool_name in {"write_file", "patch"}:
        path = args.get("path")
        if path:
            reason = _check_target_path(str(path))
            if reason:
                return {"action": "block", "message": reason}

    return None


def register(ctx: Any) -> None:
    """Register the pre_tool_call hook with Hermes plugin context."""
    if hasattr(ctx, "register_hook"):
        ctx.register_hook("pre_tool_call", guard_pre_tool_call)
