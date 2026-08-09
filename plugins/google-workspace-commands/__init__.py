"""google-workspace-commands — Slash commands for Google Workspace.

Registers /gdocs, /gdrive, /gsheet, /gmail, /gworkspace.
Each command delegates the NL instruction to a synchronous subagent
with full Google API + session_search access.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)


def _is_delegate_error(result: str) -> bool:
    """Check if delegate_task returned an error JSON (gateway mode, no parent_agent)."""
    try:
        data = json.loads(result)
        return isinstance(data, dict) and "error" in data
    except (json.JSONDecodeError, TypeError):
        return False


# Module-level ctx reference, set during register()
_CTX = None

# Path to the google_api.py wrapper script
_GAPI = (
    "$HOME/.hermes/skills/productivity/google-workspace/"
    "scripts/google_api.py"
)

_COMMANDS = {
    "gdocs": {
        "description": "Create, read, or manage Google Docs",
        "service": "docs",
    },
    "gdrive": {
        "description": "Search, upload, download, or manage Google Drive files",
        "service": "drive",
    },
    "gsheet": {
        "description": "Read, create, or update Google Sheets",
        "service": "sheets",
    },
    "gmail": {
        "description": "Search, read, or send Gmail emails",
        "service": "gmail",
    },
    "gworkspace": {
        "description": "General Google Workspace operations across all services",
        "service": "workspace",
    },
}

# ---------------------------------------------------------------------------
# Subagent delegation
# ---------------------------------------------------------------------------


def _delegate(name: str, service: str, raw_args: str) -> str | None:
    """Route the user's natural-language instruction to a subagent.

    The subagent runs synchronously: it has full LLM access, the
    google_api.py script, session_search, and web browsing.  When the
    subagent finishes its (typically short) run the result is returned
    inline in the same chat.

    Falls back to a direct subprocess call if the agent tool layer
    isn't available (e.g. the gateway hasn't fully initialised the
    tool registry for this process).
    """
    prompt = raw_args.strip()
    if not prompt:
        return (
            f"📎 /{name} — {_COMMANDS[name]['description']}\n\n"
            "Usage: /{name} <instruction>\n\n"
            "Examples:\n"
            "  /gmail search is:unread from:boss --max 5\n"
            "  /gdrive search \"quarterly report\"\n"
            "  /gsheet get SPREADSHEET_ID \"Sheet1!A1:D10\"\n"
            "  /gdocs create --title \"Meeting Notes\" --body \"...\"\n"
            "  /gworkspace check my unread emails and summarize\n"
        ).format(name=name)

    # Try subagent delegation first — gives us LLM-powered NL processing.
    if _CTX is not None:
        try:
            result = _CTX.dispatch_tool(
                "delegate_task",
                {
                    "goal": _build_goal(service, prompt),
                    "toolsets": ["terminal", "web", "session_search"],
                    "context": _build_context(service, name),
                },
            )
            # delegate_task returns error JSON (not exception) when
            # called from gateway mode (no parent_agent available).
            # Detect this and fall through to direct execution.
            if _is_delegate_error(result):
                logger.debug(
                    "delegate_task unavailable from gateway mode for /%s",
                    name,
                )
            else:
                return _parse_subagent_result(result, name)
        except Exception as exc:
            logger.debug(
                "delegate_task failed for /%s, falling back to direct: %s",
                name,
                exc,
            )

    # Fallback: execute google_api.py directly via subprocess.
    # Simple API operations only — NL instructions resend as regular msg.
    return _direct_fallback(service, prompt)


def _build_goal(service: str, prompt: str) -> str:
    """Construct a focused subagent goal from the user prompt."""
    svc_hint = {
        "docs": "Google Docs — create, read, append text to documents",
        "drive": "Google Drive — search, upload, download, share, manage files/folders",
        "sheets": "Google Sheets — create, read, update, append to spreadsheets",
        "gmail": "Gmail — search, read, send, reply, manage labels",
        "workspace": "All Google Workspace services",
    }
    return (
        f"Execute this Google {svc_hint.get(service, service)} request: "
        f"{prompt}\n\n"
        f"Use the google_api.py script ({_GAPI}) for all API calls. "
        f"Parse JSON output. Return only the final result — concise, "
        f"no meta-commentary."
    )


def _build_context(service: str, name: str) -> str:
    """Provide the subagent with essential execution context."""
    return (
        f"You are handling a /{name} slash command for {service}.\n\n"
        f"CRITICAL — every Google API call goes through:\n"
        f"  {_GAPI}\n\n"
        f"Examples:\n"
        f"  {_GAPI} gmail search \"is:unread\" --max 5\n"
        f"  {_GAPI} drive search \"report\" --max 10\n"
        f"  {_GAPI} sheets get SPREADSHEET_ID \"Sheet1!A1:D10\"\n"
        f"  {_GAPI} docs create --title \"Notes\" --body \"...\"\n"
        f"  {_GAPI} gmail send --to owner@example.invalid --subject \"Hi\" "
        f"--body \"Body text\"\n\n"
        f"Use session_search to find past conversations if the user "
        f"references 'today', 'last session', etc.\n\n"
        f"Return only actionable results. If you need to create a doc "
        f"from conversation context, search sessions first, compose "
        f"content, then call google_api.py to create it."
    )


# ---------------------------------------------------------------------------
# Subagent result parsing
# ---------------------------------------------------------------------------


def _parse_subagent_result(raw: str, name: str) -> str:
    """Extract human-readable text from a delegate_task JSON result."""
    try:
        data = json.loads(raw)
        # delegate_task returns list of results, one per task
        if isinstance(data, list):
            texts = []
            for item in data:
                if isinstance(item, dict):
                    texts.append(item.get("summary", ""))
                elif isinstance(item, str):
                    texts.append(item)
            combined = "\n".join(t for t in texts if t)
            if combined:
                return combined
        if isinstance(data, dict):
            return data.get("summary", raw)
    except (json.JSONDecodeError, TypeError):
        pass
    return str(raw)


# ---------------------------------------------------------------------------
# Direct fallback (subprocess, no LLM)
# ---------------------------------------------------------------------------


def _direct_fallback(service: str, prompt: str) -> str:
    """Run google_api.py directly via subprocess.

    Best-effort for simple operations.  NL-heavy instructions will
    fail gracefully here — the user should resend as a regular
    message when the agent is active.
    """
    import subprocess

    # Try to parse the prompt as a direct google_api.py subcommand.
    cmd = ["python3", _GAPI.replace("$HOME", __import__("os").path.expanduser("~"))]
    parts = prompt.split(maxsplit=2)
    if not parts:
        return f"Empty instruction for /{service}."
    cmd.extend(parts)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            env={**__import__("os").environ, "PATH": "/usr/bin:/usr/local/bin"},
        )
        if result.returncode == 0:
            return result.stdout.strip() or "(empty result)"
        return (
            f"google_api.py exited with code {result.returncode}:\n"
            f"{result.stderr.strip()[:500]}"
        )
    except subprocess.TimeoutExpired:
        return "google_api.py timed out after 30s."
    except FileNotFoundError:
        return "google_api.py not found. Is the google-workspace skill installed?"
    except Exception as exc:
        return f"Direct execution failed: {exc}"


# ---------------------------------------------------------------------------
# Command handler factories
# ---------------------------------------------------------------------------


def _make_handler(name: str, service: str):
    """Return a handler function for the given command name + service."""

    def handler(raw_args: str) -> str | None:
        return _delegate(name, service, raw_args)

    return handler


# ---------------------------------------------------------------------------
# Plugin registration
# ---------------------------------------------------------------------------


def register(ctx) -> None:
    """Register all five Google Workspace slash commands."""
    global _CTX
    _CTX = ctx

    for name, cfg in _COMMANDS.items():
        handler = _make_handler(name, cfg["service"])
        ctx.register_command(
            name,
            handler=handler,
            description=cfg["description"],
            args_hint="<instruction>",
        )
        logger.info(
            "Registered /%s — %s", name, cfg["description"]
        )
