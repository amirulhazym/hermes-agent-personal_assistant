"""Authenticated owner controls for nightly Git remediation."""

from __future__ import annotations

import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any


_APPROVE_RE = re.compile(r"^\s*APPROVE\s+NIGHTLY(?:\s+([A-Za-z0-9][A-Za-z0-9._-]{0,127}))?\s*$", re.IGNORECASE)
_REJECT_RE = re.compile(r"^\s*(?:REJECT|HOLD|CANCEL)\s+NIGHTLY(?:\s+([A-Za-z0-9][A-Za-z0-9._-]{0,127}))?(?:\s+(.+?))?\s*$", re.IGNORECASE)


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


def _usage() -> str:
    return (
        "Usage: /nightly status | approve [RUN_ID] | reject [RUN_ID] [reason] | "
        "json show|hide\n"
        "Plain text is also accepted: APPROVE NIGHTLY RUN_ID or REJECT NIGHTLY RUN_ID reason."
    )


def _handle(raw_args: str) -> str:
    try:
        parts = shlex.split(raw_args.strip())
    except ValueError:
        return _usage()
    if not parts or parts[0].lower() == "status":
        return _run_target(["--status", "--human-only"])
    command = parts[0].lower()
    if command in {"approve", "yes"}:
        args = ["--approve"]
        if len(parts) > 1:
            args += ["--run-id", parts[1]]
        if len(parts) > 2:
            return _usage()
        args.append("--human-only")
        return _run_target(args)
    if command in {"reject", "hold", "cancel", "no"}:
        args = ["--reject"]
        if len(parts) > 1:
            args += ["--run-id", parts[1]]
        if len(parts) > 2:
            args += ["--reason", " ".join(parts[2:])]
        args.append("--human-only")
        return _run_target(args)
    if command == "json" and len(parts) == 2 and parts[1].lower() in {"show", "hide"}:
        return _run_target(["--set-json-display", parts[1].lower(), "--human-only"])
    return _usage()


def _event_text(event: Any) -> str | None:
    if isinstance(event, str):
        return event
    text = getattr(event, "text", None)
    return text if isinstance(text, str) else None


def _rewrite_control(event: Any = None, **_kwargs: Any) -> dict[str, str] | None:
    """Rewrite exact approval text only; mutation remains behind normal auth."""
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
    return None


def register(ctx) -> None:
    ctx.register_command(
        "nightly",
        handler=_handle,
        description="Inspect and control bounded nightly Git remediation",
        args_hint="status|approve|reject|json",
    )
    ctx.register_hook("pre_gateway_dispatch", _rewrite_control)
