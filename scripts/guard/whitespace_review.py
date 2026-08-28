#!/usr/bin/env python3
"""Fail-closed staged whitespace review with exact Markdown exceptions.

Git's diff checker correctly reports trailing spaces, including intentional
Markdown hard breaks. This wrapper keeps raw git diff --check as the source
signal and permits only pre-reviewed path/line/body-hash entries. Any changed
or new diagnostic remains a failure.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


TRAILING_RE = re.compile(r"^(.+):(\d+): trailing whitespace\.$")
DIAGNOSTIC_RE = re.compile(r"^(.+):(\d+): (.+)\.$")


@dataclass(frozen=True)
class Issue:
    path: str
    line: int
    trailing_ws: int
    body_sha256: str
    kind: str


def parse_git_check_output(output: str) -> list[Issue]:
    """Parse trailing-whitespace headers; body identity is filled by main."""
    return [
        Issue(path=match.group(1), line=int(match.group(2)), trailing_ws=-1, body_sha256="", kind="")
        for line in output.splitlines()
        if (match := TRAILING_RE.match(line))
    ]


def evaluate_issues(
    issues: list[Issue], allowlist: list[dict[str, Any]]
) -> tuple[list[Issue], list[Issue]]:
    allowed: list[Issue] = []
    unexpected: list[Issue] = []
    allowed_keys = {
        (
            str(entry.get("path")),
            int(entry.get("line", -1)),
            int(entry.get("trailing_ws", -1)),
            str(entry.get("body_sha256")),
            str(entry.get("kind")),
        )
        for entry in allowlist
    }
    for issue in issues:
        key = (issue.path, issue.line, issue.trailing_ws, issue.body_sha256, issue.kind)
        (allowed if key in allowed_keys else unexpected).append(issue)
    return allowed, unexpected


def _git_check(repo: Path) -> tuple[int, str]:
    result = subprocess.run(
        ["git", "-C", str(repo), "diff", "--cached", "--check"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout + result.stderr


def _staged_file(repo: Path, path: str) -> bytes:
    result = subprocess.run(
        ["git", "-C", str(repo), "show", f":{path}"],
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"staged path cannot be read: {path}")
    return result.stdout


def _issue_with_identity(repo: Path, issue: Issue, allowlist: list[dict[str, Any]]) -> Issue:
    data = _staged_file(repo, issue.path)
    lines = data.splitlines(keepends=False)
    if issue.line < 1 or issue.line > len(lines):
        return issue
    raw = lines[issue.line - 1]
    body = raw.rstrip(b" \t")
    trailing_ws = len(raw) - len(body)
    body_hash = hashlib.sha256(body).hexdigest()
    kind = "unknown"
    for entry in allowlist:
        if entry.get("path") == issue.path and int(entry.get("line", -1)) == issue.line:
            kind = str(entry.get("kind", "unknown"))
            break
    return Issue(issue.path, issue.line, trailing_ws, body_hash, kind)


def _unexpected_diagnostics(output: str) -> list[str]:
    out: list[str] = []
    for line in output.splitlines():
        if not line or line.startswith("+"):
            continue
        match = DIAGNOSTIC_RE.match(line)
        if match and match.group(3) != "trailing whitespace":
            out.append(line)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument(
        "--allowlist",
        type=Path,
        default=Path("scripts/guard/intentional-markdown-whitespace.json"),
    )
    args = parser.parse_args(argv)
    repo = args.repo.resolve()
    allowlist_path = args.allowlist if args.allowlist.is_absolute() else repo / args.allowlist
    try:
        allowlist_data = json.loads(allowlist_path.read_text(encoding="utf-8"))
        allowlist = allowlist_data["entries"]
        if not isinstance(allowlist, list):
            raise RuntimeError("allowlist entries must be a list")
        raw_rc, raw_output = _git_check(repo)
        parsed = parse_git_check_output(raw_output)
        issues = [_issue_with_identity(repo, issue, allowlist) for issue in parsed]
        allowed, unexpected = evaluate_issues(issues, allowlist)
        unexpected_diagnostics = _unexpected_diagnostics(raw_output)
        if unexpected or unexpected_diagnostics:
            print(
                "WHITESPACE-REVIEW FAIL: "
                f"raw_git_check_rc={raw_rc} allowed={len(allowed)} "
                f"unexpected={len(unexpected) + len(unexpected_diagnostics)}"
            )
            for issue in unexpected:
                print(f"UNEXPECTED path={issue.path} line={issue.line}")
            for diagnostic in unexpected_diagnostics:
                print(f"UNEXPECTED_DIAGNOSTIC {diagnostic}")
            return 1
        print(
            "WHITESPACE-REVIEW PASS: "
            f"raw_git_check_rc={raw_rc} allowed={len(allowed)} unexpected=0"
        )
        return 0
    except (OSError, KeyError, TypeError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"WHITESPACE-REVIEW FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
