"""Authenticated owner controls for nightly Git remediation and secure token intake."""

from __future__ import annotations

import json
import os
import re
import shlex
import stat
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


_APPROVE_RE = re.compile(r"^\s*APPROVE\s+NIGHTLY\s+([A-Za-z0-9][A-Za-z0-9._-]{0,127})\s*$", re.IGNORECASE)
_REJECT_RE = re.compile(r"^\s*REJECT\s+NIGHTLY\s+([A-Za-z0-9][A-Za-z0-9._-]{0,127})(?:\s+(.+?))?\s*$", re.IGNORECASE)
_AUTH_RE = re.compile(r"^\s*SET\s+NIGHTLY\s+GITHUB_TOKEN\s+([A-Za-z0-9_]{20,255})\s*$", re.IGNORECASE)


def _hermes_home() -> Path:
    return Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes")).expanduser().resolve()


def _target() -> Path:
    return _hermes_home() / "scripts" / "nightly_git_hygiene.py"


def _run_target(args: list[str]) -> str:
    target = _target()
    if not target.is_file():
        return f"Nightly workflow target is missing: {target}"
    command = [sys.executable, str(target), *args]
    try:
        completed = subprocess.run(
            command,
            cwd=str(target.parent),
            env=os.environ.copy(),
            capture_output=True,
            text=True,
            timeout=180,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return "Nightly workflow command timed out after 180 seconds."
    except OSError as exc:
        return f"Nightly workflow command could not start: {exc}"
    output = (completed.stdout + ("\n" + completed.stderr if completed.stderr else "")).strip()
    return output or f"Nightly workflow exited with code {completed.returncode}."


def _handle_token_intake(raw_token: str) -> str:
    token = raw_token.strip()
    if not token or len(token) < 20 or len(token) > 255 or not re.match(r"^[A-Za-z0-9_]+$", token):
        return "❌ Invalid token format. Expected a valid GitHub fine-grained PAT."

    # 1. Update ~/.hermes/.env
    env_path = _hermes_home() / ".env"
    existing_lines = []
    if env_path.is_file():
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                existing_lines = f.readlines()
        except OSError as e:
            return f"❌ Failed to read .env file: {e}"

    new_lines = []
    found = False
    for line in existing_lines:
        if line.startswith("GITHUB_TOKEN="):
            new_lines.append(f"GITHUB_TOKEN={token}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        if new_lines and not new_lines[-1].endswith("\n"):
            new_lines[-1] += "\n"
        new_lines.append(f"GITHUB_TOKEN={token}\n")

    tmp_env = env_path.parent / (env_path.name + ".intake.tmp")
    try:
        with open(tmp_env, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        os.chmod(tmp_env, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(tmp_env, env_path)
        os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)
    except OSError as e:
        if tmp_env.is_file():
            tmp_env.unlink(missing_ok=True)
        return f"❌ Failed to write .env securely: {e}"

    # 2. Verify with GitHub API in-memory
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Hermes-Nightly-Auth",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    repo_url = "https://api.github.com/repos/amirulhazym/hermes-agent-personal_assistant"
    report_lines = ["✅ GITHUB_TOKEN securely saved to ~/.hermes/.env (mode 0600)."]

    # Test Repo GET
    try:
        req = urllib.request.Request(repo_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            repo_name = data.get("full_name", "unknown")
            report_lines.append(f"• Repository Access: PASS ({repo_name})")
    except Exception as e:
        report_lines.append(f"• Repository Access: FAIL ({e})")

    # Test Pulls GET
    try:
        req = urllib.request.Request(f"{repo_url}/pulls?state=all&per_page=1", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            report_lines.append("• Pull Requests API: PASS")
    except Exception as e:
        report_lines.append(f"• Pull Requests API: FAIL ({e})")

    # Test Git Refs GET
    try:
        req = urllib.request.Request(f"{repo_url}/git/ref/heads/main", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            report_lines.append("• Git Refs API: PASS")
    except Exception as e:
        report_lines.append(f"• Git Refs API: FAIL ({e})")

    # Test Checks GET
    try:
        req = urllib.request.Request(f"{repo_url}/commits/main/check-runs", headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            report_lines.append("• Check Runs API: PASS")
    except Exception as e:
        report_lines.append(f"• Check Runs API: FAIL ({e})")

    report_lines.append("\n🔒 Token verification complete. You may now unsend / delete your token message in chat.")
    return "\n".join(report_lines)


def _usage() -> str:
    return (
        "Usage: /nightly status | approve <RUN_ID> | reject <RUN_ID> [reason] | "
        "auth <TOKEN> | json show|hide\n"
        "Plain text is also accepted: APPROVE NIGHTLY <RUN_ID>, REJECT NIGHTLY <RUN_ID> [reason], "
        "or SET NIGHTLY GITHUB_TOKEN <TOKEN>."
    )


def _handle(raw_args: str) -> str:
    raw = raw_args.strip()
    if not raw or raw.lower() == "status":
        return _run_target(["--status", "--human-only"])

    # Check for auth/token subcommand first (so tokens with weird characters aren't broken by shlex)
    auth_prefix = ("auth ", "token ", "set-token ")
    for pfx in auth_prefix:
        if raw.lower().startswith(pfx):
            token_arg = raw[len(pfx):].strip()
            return _handle_token_intake(token_arg)

    try:
        parts = shlex.split(raw)
    except ValueError:
        return _usage()

    command = parts[0].lower()
    if command == "approve":
        if len(parts) != 2:
            return _usage()
        return _run_target(["--approve", "--run-id", parts[1], "--human-only"])
    if command == "reject":
        if len(parts) < 2:
            return _usage()
        args = ["--reject", "--run-id", parts[1]]
        if len(parts) > 2:
            args += ["--reason", " ".join(parts[2:])]
        args.append("--human-only")
        return _run_target(args)
    if command == "auth" or command == "token":
        if len(parts) != 2:
            return _usage()
        return _handle_token_intake(parts[1])
    if command == "json" and len(parts) == 2 and parts[1].lower() in {"show", "hide"}:
        return _run_target(["--set-json-display", parts[1].lower(), "--human-only"])
    return _usage()


def _event_text(event: Any) -> str | None:
    if isinstance(event, str):
        return event
    text = getattr(event, "text", None)
    return text if isinstance(text, str) else None


def _rewrite_control(event: Any = None, **_kwargs: Any) -> dict[str, str] | None:
    """Rewrite exact approval or token intake text only; mutation remains behind normal auth."""
    text = _event_text(event)
    if text is None:
        return None
    approve = _APPROVE_RE.fullmatch(text)
    if approve:
        run_id = approve.group(1)
        return {"action": "rewrite", "text": "/nightly approve" + (f" {run_id}" if run_id else "")}
    reject = _REJECT_RE.fullmatch(text)
    if reject:
        run_id, reason = reject.groups()
        rewritten = "/nightly reject" + (f" {run_id}" if run_id else "")
        if reason:
            rewritten += " " + reason
        return {"action": "rewrite", "text": rewritten}
    auth_m = _AUTH_RE.fullmatch(text)
    if auth_m:
        token = auth_m.group(1)
        return {"action": "rewrite", "text": f"/nightly auth {token}"}
    return None


def register(ctx) -> None:
    ctx.register_command(
        "nightly",
        handler=_handle,
        description="Inspect and control bounded nightly Git remediation and secure auth intake",
        args_hint="status|approve|reject|auth|json",
    )
    ctx.register_hook("pre_gateway_dispatch", _rewrite_control)
