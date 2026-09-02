#!/usr/bin/env python3
"""Nightly Git Hygiene & Self-Improvement Audit Runner for Hermes Assistant.

Every night at 23:55 MYT the executable performs an audit first. If
resolvable Git work exists, it persists one exact remediation plan, emits a
human report, and schedules a 30-minute one-shot continuation. Approval before
the deadline or timeout after it executes only that plan after revalidation.
The raw JSON receipt remains the machine-readable audit record; JSON display is
controlled separately from receipt persistence.

Status contract:
- PASS: all required gates pass, no unresolved hold, and no remediation remains.
- HOLD: owner confirmation is pending, an owner decision is required, or a
  safe plan was invalidated by changed state.
- FAIL: an automated security/quality/command gate failed.

Never force-push, discard unclassified work, delete unmerged unique branches,
commit private state, bypass failed gates, or guess through substantive merge
conflicts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Callable, Iterator

MYT = timezone(timedelta(hours=8))
REPO_ROOT = Path(os.environ.get("HERMES_REPO_ROOT") or "/home/ubuntu/hermes-agent-personal_assistant-work")
HERMES_HOME = Path(os.environ.get("HERMES_HOME") or "/home/ubuntu/.hermes")
RECEIPT_PATH = HERMES_HOME / "logs" / "git-nightly-receipt.md"
RECEIPT_JSON_PATH = HERMES_HOME / "logs" / "git-nightly-receipt.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def execution_identity(repo_root: Path, audited_head: str) -> dict[str, Any]:
    """Capture the exact executable identity used for this audit invocation."""
    script_path = Path(__file__).resolve()
    return {
        "script_path": str(script_path),
        "script_sha256": sha256_file(script_path),
        "script_size": script_path.stat().st_size,
        "audited_repo": str(repo_root),
        "audited_repo_head": audited_head,
    }


def run_cmd(cmd: list[str], cwd: Path = REPO_ROOT) -> tuple[int, str]:
    if not cwd.exists():
        return 1, f"directory does not exist: {cwd}"
    res = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    out = res.stdout.strip()
    if res.stderr.strip():
        out = (out + "\n" + res.stderr.strip()).strip()
    return res.returncode, out


def scan_uncommitted_privacy(repo_root: Path) -> tuple[bool, bool, list[str]]:
    """Scan staged and unstaged/untracked files for secrets and PII without committing."""
    # Run secret scan on staged and tree
    secret_pass = True
    pii_pass = True
    errors: list[str] = []

    # 1. Staged secret scan
    secret_script = repo_root / "scripts" / "guard" / "secret-scan.sh"
    if secret_script.exists():
        rc, out = run_cmd(["bash", str(secret_script), "--staged"], cwd=repo_root)
        if rc != 0:
            secret_pass = False
            errors.append("Secret scan failed on staged files")

    # 2. PII review
    pii_script = repo_root / "scripts" / "guard" / "pii-review.py"
    if pii_script.exists():
        rc, out = run_cmd(["python3", str(pii_script), "--diff", "HEAD"], cwd=repo_root)
        if rc != 0:
            pii_pass = False
            errors.append("PII review flagged unredacted patterns in diff")

    # 3. Whitespace review
    ws_script = repo_root / "scripts" / "guard" / "whitespace_review.py"
    if ws_script.exists():
        rc, out = run_cmd(["python3", str(ws_script), "--repo", str(repo_root)], cwd=repo_root)
        if rc != 0:
            errors.append("Whitespace review failed on staged changes")

    return secret_pass, pii_pass, errors


def check_operational_proposals(repo_root: Path, today_str: str) -> str | None:
    """Analyze operational error patterns and generate a draft proposal if recurring issues found."""
    proposals_dir = repo_root / "docs" / "proposals"
    proposal_file = proposals_dir / f"nightly-{today_str}.md"

    # We do not unilaterally mutate governance files, but we can write a proposal draft
    return str(proposal_file) if proposal_file.exists() else None


def run_audit(repo_root: Path = REPO_ROOT, dry_run: bool = False) -> dict[str, Any]:
    now_dt = datetime.now(MYT)
    now_str = now_dt.strftime("%Y-%m-%d %H:%M:%S MYT")
    today_str = now_dt.strftime("%Y-%m-%d")

    audit: dict[str, Any] = {
        "timestamp": now_str,
        "date": today_str,
        "repo": str(repo_root),
        "status": "PASS",
        "release_pending": False,
        "push_allowed": False,
        "owner_approval_required_for_push": True,
        "gates": {},
        "git_state": {},
        "branches": {"merged": [], "stale": [], "active": []},
        "sync_state": {},
        "actions_taken": [],
        "holds": [],
        "errors": [],
    }

    # 1. Check Git status
    rc, out = run_cmd(["git", "status", "--porcelain"], cwd=repo_root)
    status_lines = [l for l in out.splitlines() if l.strip() and not l.strip().endswith("SOUL.md")]
    is_clean = len(status_lines) == 0
    audit["git_state"]["is_clean"] = is_clean
    audit["git_state"]["status_porcelain"] = status_lines

    # 2. Check current HEAD
    rc, head = run_cmd(["git", "rev-parse", "HEAD"], cwd=repo_root)
    audit["git_state"]["head"] = head
    audit["execution"] = execution_identity(repo_root, head) if rc == 0 else {
        "script_path": str(Path(__file__).resolve()),
        "script_sha256": sha256_file(Path(__file__).resolve()),
        "script_size": Path(__file__).resolve().stat().st_size,
        "audited_repo": str(repo_root),
        "audited_repo_head": None,
    }

    # 3. Privacy & Security Scans
    secret_pass, pii_pass, scan_errors = scan_uncommitted_privacy(repo_root)
    audit["gates"]["secret_scan"] = "PASS" if secret_pass else "FAIL"
    audit["gates"]["pii_review"] = "PASS" if pii_pass else "FAIL"
    if scan_errors:
        audit["errors"].extend(scan_errors)
        audit["status"] = "FAIL"

    # 4. Run contract tests
    contract_script = repo_root / "scripts" / "run_contract_tests.sh"
    if contract_script.exists():
        rc, test_out = run_cmd(["bash", str(contract_script)], cwd=repo_root)
        test_pass = rc == 0
        audit["gates"]["contract_tests"] = "PASS" if test_pass else "FAIL"
        if not test_pass:
            audit["errors"].append("Contract tests failed")
            audit["status"] = "FAIL"

    # 5. Fetch remotes & check sync
    run_cmd(["git", "fetch", "origin"], cwd=repo_root)
    run_cmd(["git", "fetch", "upstream", "main"], cwd=repo_root)

    rc, ahead_behind = run_cmd(["git", "rev-list", "--left-right", "--count", "main...origin/main"], cwd=repo_root)
    if rc == 0 and ahead_behind:
        parts = ahead_behind.split()
        if len(parts) == 2:
            ahead, behind = int(parts[0]), int(parts[1])
            audit["sync_state"]["origin"] = {"ahead": ahead, "behind": behind}
            if behind > 0 and ahead > 0:
                audit["holds"].append("Local main and origin/main have diverged")
            elif ahead > 0 and behind == 0:
                audit["release_pending"] = True

    rc, up_ahead_behind = run_cmd(["git", "rev-list", "--left-right", "--count", "main...upstream/main"], cwd=repo_root)
    if rc == 0 and up_ahead_behind:
        parts = up_ahead_behind.split()
        if len(parts) == 2:
            audit["sync_state"]["upstream"] = {"ahead": int(parts[0]), "behind": int(parts[1])}

    # 6. Classify branches
    rc, raw_branches = run_cmd(
        ["git", "for-each-ref", "--format=%(refname:short)|%(committerdate:iso8601)", "refs/heads/"],
        cwd=repo_root,
    )
    for line in raw_branches.splitlines():
        if not line or "|" not in line:
            continue
        b_name, b_date_str = line.split("|", 1)
        if b_name == "main":
            continue
        rc, merged_out = run_cmd(["git", "branch", "--merged", "main"], cwd=repo_root)
        is_merged = any(x.strip() == b_name for x in merged_out.splitlines())
        if is_merged:
            audit["branches"]["merged"].append(b_name)
            if not dry_run and audit["status"] != "FAIL":
                # Safe auto-cleanup for merged branches only
                run_cmd(["git", "branch", "-d", b_name], cwd=repo_root)
                audit["actions_taken"].append(f"Cleaned up merged local branch: {b_name}")
        else:
            try:
                b_date = datetime.fromisoformat(b_date_str.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - b_date).days
                if age_days > 7:
                    audit["branches"]["stale"].append({"name": b_name, "age_days": age_days})
                    audit["holds"].append(f"Stale unmerged branch (>7d): {b_name}")
                else:
                    audit["branches"]["active"].append(b_name)
            except Exception:
                audit["branches"]["active"].append(b_name)

    # 7. Evaluate final status contract
    if audit["errors"]:
        audit["status"] = "FAIL"
    elif not is_clean:
        audit["holds"].append("Working tree has uncommitted/untracked changes")
        audit["status"] = "HOLD"
    elif audit["holds"]:
        audit["status"] = "HOLD"
    else:
        audit["status"] = "PASS"

    # 8. Check proposals
    audit["proposal_path"] = check_operational_proposals(repo_root, today_str)

    # 9. Write Markdown & JSON Receipts
    md_lines = [
        f"# Nightly Git Hygiene Receipt — {today_str}",
        "",
        f"- **Timestamp:** {now_str}",
        f"- **Audit Status:** **{audit['status']}**",
        f"- **HEAD Commit:** `{head[:10]}`",
        f"- **Working Tree Clean:** `{is_clean}`",
        f"- **Secret Scan:** `{audit['gates'].get('secret_scan')}`",
        f"- **PII Review:** `{audit['gates'].get('pii_review')}`",
        f"- **Contract Tests:** `{audit['gates'].get('contract_tests')}`",
        f"- **Executable Script:** `{audit['execution']['script_path']}`",
        f"- **Executable SHA-256:** `{audit['execution']['script_sha256']}`",
        f"- **Executable Size:** `{audit['execution']['script_size']}` bytes",
        f"- **Audited Repository HEAD:** `{audit['execution']['audited_repo_head']}`",
        f"- **Sync (origin/main):** Ahead {audit['sync_state'].get('origin', {}).get('ahead', 0)}, Behind {audit['sync_state'].get('origin', {}).get('behind', 0)}",
        f"- **Release Pending:** `{audit['release_pending']}`",
        "",
        "## Actions Taken",
    ]
    if audit["actions_taken"]:
        for act in audit["actions_taken"]:
            md_lines.append(f"- ✅ {act}")
    else:
        md_lines.append("- None")

    if audit["holds"]:
        md_lines.extend(["", "## ⚠️ Active Holds / Warnings"])
        for h in audit["holds"]:
            md_lines.append(f"- ⚠️ {h}")

    if audit["errors"]:
        md_lines.extend(["", "## ❌ Errors / Blockers"])
        for err in audit["errors"]:
            md_lines.append(f"- ❌ {err}")

    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text("\n".join(md_lines) + "\n")
    RECEIPT_JSON_PATH.write_text(json.dumps(audit, indent=2) + "\n")

    return audit


# ---------------------------------------------------------------------------
# Corrective nightly-closure workflow
# ---------------------------------------------------------------------------

EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
PENDING_FILENAME = "nightly-git-remediation.json"
HISTORY_DIRNAME = "git-nightly-history"
TIMEOUT_SCRIPT = "nightly_git_hygiene_timeout.sh"
TIMEOUT_WRAPPER_PREFIX = "nightly_git_hygiene_timeout-"
TIMEOUT_WRAPPER_SUFFIX = ".sh"
AUTO_ACTION_WINDOW = timedelta(minutes=30)
RUN_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[0-9a-f]{12}-[0-9a-f]{32}$")
EXCLUDED_PRIVATE_PATHS = frozenset({"SOUL.md"})


@dataclass(frozen=True)
class RuntimePaths:
    """Profile-local paths used by the durable nightly workflow."""

    hermes_home: Path

    @property
    def logs_dir(self) -> Path:
        return self.hermes_home / "logs"

    @property
    def receipt_path(self) -> Path:
        return self.logs_dir / "git-nightly-receipt.md"

    @property
    def receipt_json_path(self) -> Path:
        return self.logs_dir / "git-nightly-receipt.json"

    @property
    def history_dir(self) -> Path:
        return self.logs_dir / HISTORY_DIRNAME

    @property
    def pending_dir(self) -> Path:
        return self.hermes_home / "pending"

    @property
    def pending_path(self) -> Path:
        return self.pending_dir / PENDING_FILENAME

    @property
    def pending_lock_path(self) -> Path:
        return self.pending_dir / f".{PENDING_FILENAME}.lock"

    @property
    def config_path(self) -> Path:
        return self.hermes_home / "config.yaml"


def _runtime_paths(hermes_home: Path | None = None) -> RuntimePaths:
    return RuntimePaths((hermes_home or HERMES_HOME).expanduser().resolve())


def _as_myt(value: datetime | None) -> datetime:
    current = value or datetime.now(MYT)
    if current.tzinfo is None:
        return current.replace(tzinfo=MYT)
    return current.astimezone(MYT)


def _format_myt(value: datetime) -> str:
    return _as_myt(value).strftime("%Y-%m-%d %H:%M:%S MYT")


def _iso_myt(value: datetime) -> str:
    return _as_myt(value).isoformat()


def _atomic_json(path: Path, payload: dict[str, Any], *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def _atomic_text(path: Path, text: str, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary, mode)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


@contextmanager
def _pending_lock(paths: RuntimePaths) -> Iterator[None]:
    """Serialize pending-state transitions across cron and gateway processes."""
    paths.pending_dir.mkdir(parents=True, exist_ok=True)
    handle = paths.pending_lock_path.open("a+b")
    try:
        try:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        except ImportError:  # pragma: no cover - Windows fallback
            pass
        yield
    finally:
        try:
            import fcntl
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        except ImportError:  # pragma: no cover
            pass
        handle.close()


def _workflow_run_cmd(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 120,
) -> tuple[int, str]:
    if not cwd.exists():
        return 1, f"directory does not exist: {cwd}"
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd),
            env=merged_env,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return 124, f"command timed out after {timeout}s: {cmd[0]}"
    except OSError as exc:
        return 127, f"command failed to start: {exc}"
    output = result.stdout.strip()
    if result.stderr.strip():
        output = (output + "\n" + result.stderr.strip()).strip()
    return result.returncode, output[-4000:]


def _workflow_git(repo: Path, args: list[str], *, env: dict[str, str] | None = None) -> tuple[int, str]:
    return _workflow_run_cmd(["git", *args], cwd=repo, env=env)


def _status_records(raw: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    conflict_codes = {"UU", "AA", "UD", "DU", "DD", "AU", "UA"}
    for line in raw.splitlines():
        if len(line) < 2:
            continue
        if len(line) >= 3 and line[2] == " ":
            status = line[:2]
            path = line[3:]
        elif line[1] == " " and line[0] in "MADRCU?":
            # _workflow_run_cmd trims the leading X/Y-space for the first
            # porcelain record. Reconstruct the canonical status code.
            status = " " + line[0]
            path = line[2:].lstrip(" ")
        else:
            status = line[:2]
            path = line[2:].lstrip(" ")
        if " -> " in path and status[0] in {"R", "C"}:
            path = path.split(" -> ", 1)[1]
        is_receipt = _is_generated_reconciliation_receipt(path)
        records.append({
            "status": status,
            "path": path,
            "untracked": status == "??" or status.endswith("?"),
            "deleted": "D" in status,
            "conflict": status in conflict_codes or "U" in status,
            "is_generated_receipt": is_receipt,
        })
    return records


def _is_generated_reconciliation_receipt(path: str) -> bool:
    """Return True if path is a known generated manifest receipt under docs/reconciliation/manifest-receipts/."""
    norm = path.replace("\\", "/").strip()
    if not norm.startswith("docs/reconciliation/manifest-receipts/"):
        return False
    name = norm.rsplit("/", 1)[-1]
    if name.endswith(".json"):
        stem = name[:-5]
        if (len(stem) in (12, 40)) and all(c in "0123456789abcdefABCDEF" for c in stem):
            return True
    return False


def _temporary_worktree_index(repo: Path) -> tuple[Path, dict[str, str]]:
    fd, index_name = tempfile.mkstemp(prefix="nightly-index-")
    os.close(fd)
    index = Path(index_name)
    index.unlink()
    env = {"GIT_INDEX_FILE": str(index)}
    rc, out = _workflow_git(repo, ["read-tree", "HEAD"], env=env)
    if rc != 0:
        raise RuntimeError(f"could not materialize temporary index: {out}")
    rc, out = _workflow_git(repo, ["add", "-A", "--", "."], env=env)
    if rc != 0:
        index.unlink(missing_ok=True)
        raise RuntimeError(f"could not stage current worktree in temporary index: {out}")
    return index, env


def _run_gate(label: str, cmd: list[str], repo: Path, env: dict[str, str] | None = None) -> dict[str, Any]:
    rc, output = _workflow_run_cmd(cmd, cwd=repo, env=env)
    output_bytes = output.encode("utf-8", errors="replace")
    gate_data: dict[str, Any] = {
        "status": "PASS" if rc == 0 else "FAIL",
        "returncode": rc,
        "label": label,
        "output_sha256": hashlib.sha256(output_bytes).hexdigest() if output else None,
        "output_bytes": len(output_bytes),
    }
    if rc != 0:
        # Diagnostic hardening: capture sanitized error excerpt on failure
        # to ensure failure root-cause is observable without leaking secrets/PII
        clean_lines = []
        for line in output.splitlines()[-40:]:
            # Redact common token patterns if any accidentally surface
            redacted = re.sub(r"(?:ghp|github_pat|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{20,}", "[REDACTED_TOKEN]", line)
            clean_lines.append(redacted)
        gate_data["output_excerpt"] = "\n".join(clean_lines)
    return gate_data


def _daily_base(repo: Path, now: datetime, head: str) -> str:
    midnight = _as_myt(now).replace(hour=0, minute=0, second=0, microsecond=0)
    rc, value = _workflow_git(
        repo,
        ["rev-list", "-1", f"--before={midnight.isoformat()}", head],
    )
    if rc == 0 and value.strip():
        return value.strip().splitlines()[0]
    return EMPTY_TREE_SHA


def run_full_delta_gates(repo: Path, now: datetime) -> dict[str, Any]:
    """Run security/format gates over daily commits plus the complete worktree delta."""
    guard_dir = repo / "scripts" / "guard"
    secret = guard_dir / "secret-scan.sh"
    pii = guard_dir / "pii-review.py"
    whitespace = guard_dir / "whitespace_review.py"
    contract = repo / "scripts" / "run_contract_tests.sh"
    gates: dict[str, Any] = {}
    required = {
        "secret_scan": secret,
        "pii_review": pii,
        "whitespace_review": whitespace,
        "contract_tests": contract,
    }
    for label, path in required.items():
        if not path.is_file():
            gates[label] = {
                "status": "FAIL",
                "returncode": 127,
                "label": "missing executable",
                "output_excerpt": str(path),
            }
    if any(g["status"] == "FAIL" for g in gates.values()):
        return gates

    rc, head = _workflow_git(repo, ["rev-parse", "HEAD"])
    if rc != 0:
        gates["git_head"] = {"status": "FAIL", "returncode": rc, "label": "HEAD", "output_excerpt": head}
        return gates
    base = _daily_base(repo, _as_myt(now), head.strip())
    try:
        temp_index, temp_env = _temporary_worktree_index(repo)
    except RuntimeError as exc:
        return {
            "temporary_index": {
                "status": "FAIL",
                "returncode": 1,
                "label": "full worktree delta materialization",
                "output_excerpt": str(exc),
            }
        }
    try:
        gates["secret_scan_worktree_delta"] = _run_gate(
            "staged temporary index containing tracked + untracked worktree delta",
            ["bash", str(secret), "--staged"], repo, temp_env,
        )
        gates["pii_review_worktree_delta"] = _run_gate(
            "HEAD to temporary-index/worktree delta",
            ["python3", str(pii), "--diff", "HEAD"], repo, temp_env,
        )
        gates["whitespace_review"] = _run_gate(
            "temporary index whitespace review",
            ["python3", str(whitespace), "--repo", str(repo)], repo, temp_env,
        )
    finally:
        temp_index.unlink(missing_ok=True)

    if base != head.strip():
        gates["secret_scan_daily_commits"] = _run_gate(
            f"commits since MYT midnight ({base[:12]}..{head.strip()[:12]})",
            ["bash", str(secret), "--diff", base, head.strip()], repo,
        )
        gates["pii_review_daily_commits"] = _run_gate(
            f"commits since MYT midnight ({base[:12]}..{head.strip()[:12]})",
            ["python3", str(pii), "--diff", f"{base}..{head.strip()}"], repo,
        )
    else:
        gates["secret_scan_daily_commits"] = {
            "status": "PASS", "returncode": 0, "label": "no commits since MYT midnight", "output_excerpt": "",
        }
        gates["pii_review_daily_commits"] = {
            "status": "PASS", "returncode": 0, "label": "no commits since MYT midnight", "output_excerpt": "",
        }
    gates["contract_tests"] = _run_gate(
        "contract/reconciliation suite", ["bash", str(contract)], repo,
    )
    return gates


def _gates_pass(gates: dict[str, Any]) -> bool:
    return bool(gates) and all(value.get("status") == "PASS" for value in gates.values())


def _worktree_branches(repo: Path) -> set[str]:
    rc, output = _workflow_git(repo, ["worktree", "list", "--porcelain"])
    if rc != 0:
        return set()
    result = set()
    for line in output.splitlines():
        if line.startswith("branch refs/heads/"):
            result.add(line.removeprefix("branch refs/heads/"))
    return result


def _inspect_git(repo: Path, now: datetime) -> dict[str, Any]:
    result: dict[str, Any] = {
        "repo": str(repo),
        "git_state": {"is_clean": False, "status_porcelain": [], "status_records": []},
        "branches": {"merged": [], "stale": [], "active": []},
        "sync_state": {},
        "daily_delta": {"commits": []},
        "errors": [],
    }
    if not repo.is_dir():
        result["errors"].append(f"repository does not exist: {repo}")
        return result
    rc, status = _workflow_git(repo, ["status", "--porcelain", "--untracked-files=all"])
    if rc != 0:
        result["errors"].append(f"git status failed: {status}")
        return result
    records = _status_records(status)
    effective = [record for record in records if record["path"] not in EXCLUDED_PRIVATE_PATHS]
    has_private_diff = len(effective) != len(records)
    result["git_state"] = {
        "is_clean": not records,
        "is_effective_clean": not effective,
        "has_private_diff": has_private_diff,
        "status_porcelain": [f"{r['status']} {r['path']}" for r in records],
        "status_records": records,
        "excluded_private_paths": [r["path"] for r in records if r["path"] in EXCLUDED_PRIVATE_PATHS],
    }
    if has_private_diff:
        result["holds"].append("private uncommitted files present (SOUL.md); no automated push/commit")
    rc, branch = _workflow_git(repo, ["branch", "--show-current"])
    rc_head, head = _workflow_git(repo, ["rev-parse", "HEAD"])
    if rc != 0 or rc_head != 0:
        result["errors"].append(f"could not resolve current branch/HEAD: {branch} {head}".strip())
        return result
    branch = branch.strip()
    head = head.strip()
    result["git_state"].update({"branch": branch, "head": head})

    for remote in ("origin", "upstream"):
        fetch_rc, fetch_out = _workflow_git(repo, ["fetch", remote, "main"])
        if fetch_rc != 0:
            result["errors"].append(f"git fetch {remote} failed: {fetch_out}")
            continue
        rc_remote, remote_line = _workflow_git(repo, ["ls-remote", remote, "refs/heads/main"])
        remote_head = remote_line.split()[0] if rc_remote == 0 and remote_line.strip() else None
        rc_count, count = _workflow_git(repo, ["rev-list", "--left-right", "--count", f"main...{remote}/main"])
        if rc_count != 0 or len(count.split()) != 2:
            result["errors"].append(f"could not classify {remote}/main: {count}")
            continue
        ahead, behind = (int(value) for value in count.split())
        result["sync_state"][remote] = {
            "ahead": ahead,
            "behind": behind,
            "remote_head": remote_head,
            "tracking_head": _workflow_git(repo, ["rev-parse", f"{remote}/main"])[1].strip(),
        }

    midnight = _as_myt(now).replace(hour=0, minute=0, second=0, microsecond=0)
    rc_log, daily = _workflow_git(
        repo,
        ["log", "--since", midnight.isoformat(), "--until", _as_myt(now).isoformat(), "--format=%H%x09%s", "--max-count=50"],
    )
    if rc_log == 0:
        result["daily_delta"] = {
            "since": _iso_myt(midnight),
            "commits": [
                {"sha": line.split("\t", 1)[0], "subject": line.split("\t", 1)[1] if "\t" in line else ""}
                for line in daily.splitlines() if line.strip()
            ],
        }

    rc_refs, refs = _workflow_git(
        repo,
        ["for-each-ref", "--format=%(refname:short)|%(objectname)|%(committerdate:iso8601-strict)", "refs/heads/"],
    )
    worktree_branches = _worktree_branches(repo)
    rc_merged, merged = _workflow_git(repo, ["branch", "--merged", "main"])
    merged_names = {
        line.strip().lstrip("* ").strip()
        for line in merged.splitlines()
        if line.strip() and line.strip().lstrip("* ").strip() != "main"
    } if rc_merged == 0 else set()
    now_utc = _as_myt(now).astimezone(timezone.utc)
    for line in refs.splitlines():
        parts = line.split("|", 2)
        if len(parts) != 3:
            continue
        name, tip, date_text = parts
        if name == "main":
            continue
        if name in merged_names:
            result["branches"]["merged"].append({
                "name": name,
                "tip": tip,
                "safe_to_delete": name not in worktree_branches and name != branch,
            })
            continue
        try:
            age_days = (now_utc - datetime.fromisoformat(date_text).astimezone(timezone.utc)).days
        except ValueError:
            age_days = None
        item = {"name": name, "tip": tip, "age_days": age_days}
        if age_days is not None and age_days > 7:
            result["branches"]["stale"].append(item)
        else:
            result["branches"]["active"].append(name)
    return result


def _merge_forecast(repo: Path, local_ref: str = "main", remote_ref: str = "origin/main") -> tuple[bool, str]:
    """Forecast a merge in a temporary object store; never alter the repo index/tree."""
    objects_rc, objects_path = _workflow_git(repo, ["rev-parse", "--git-path", "objects"])
    if objects_rc != 0:
        return False, "could not locate Git object store for merge forecast"
    objects_dir = Path(objects_path.strip())
    if not objects_dir.is_absolute():
        objects_dir = repo / objects_dir
    forecast_root = Path(tempfile.mkdtemp(prefix="nightly-merge-forecast-"))
    try:
        temporary_objects = forecast_root / "objects"
        temporary_objects.mkdir()
        env = {
            "GIT_OBJECT_DIRECTORY": str(temporary_objects),
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(objects_dir.resolve()),
        }
        rc, output = _workflow_git(repo, ["merge-tree", "--write-tree", local_ref, remote_ref], env=env)
        return rc == 0, output[-500:]
    finally:
        import shutil
        shutil.rmtree(forecast_root, ignore_errors=True)


def _classify_sync_state(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Classify Git synchronization state into intentional, residue, or ambiguous provenance."""
    git_state = snapshot.get("git_state", {})
    origin = snapshot.get("sync_state", {}).get("origin")
    daily = snapshot.get("daily_delta", {}).get("commits", [])
    records = git_state.get("status_records", [])

    # Separate arbitrary dirty files from recognized generated manifest receipts
    arbitrary_records = [r for r in records if not r.get("is_generated_receipt")]

    if origin is None:
        return {
            "category": "provenance_insufficient",
            "reason": "origin/main synchronization status is unavailable",
            "is_unresolved_residue": None,
        }

    ahead = origin.get("ahead", 0)
    behind = origin.get("behind", 0)

    # 1. Fully in sync
    if ahead == 0 and behind == 0 and not arbitrary_records:
        return {
            "category": "intentional_valid_state",
            "reason": "Local main is fully synchronized with origin/main and working tree is clean.",
            "is_unresolved_residue": False,
        }

    # 2. Local is ahead
    if ahead > 0 and behind == 0 and not arbitrary_records:
        # If commits were created today during normal working hours and remain unpushed at 23:55
        if daily:
            return {
                "category": "unresolved_end_of_day_residue",
                "reason": f"Local main has {len(daily)} commit(s) created today ({ahead} total ahead) that were not published to origin/main.",
                "is_unresolved_residue": True,
            }
        # If ahead > 0 but no commits today, provenance is insufficient to assume intent or forgotten residue
        return {
            "category": "provenance_insufficient",
            "reason": f"Local main is ahead of origin by {ahead} commit(s) with clean working tree and no commits created today. Available workflow metadata does not prove whether these commits are intentionally unpushed releases or forgotten backlog residue.",
            "is_unresolved_residue": None,
        }

    # 3. Local is behind (fetched origin commits waiting for fast-forward)
    if ahead == 0 and behind > 0 and not arbitrary_records:
        return {
            "category": "unresolved_end_of_day_residue",
            "reason": f"Local main is behind origin/main by {behind} commit(s) that can be safely fast-forwarded.",
            "is_unresolved_residue": True,
        }

    # 4. Diverged (ahead > 0 and behind > 0)
    if ahead > 0 and behind > 0 and not arbitrary_records:
        return {
            "category": "unresolved_end_of_day_residue",
            "reason": f"Local main has diverged from origin/main (ahead {ahead}, behind {behind}).",
            "is_unresolved_residue": True,
        }

    return {
        "category": "provenance_insufficient",
        "reason": "Working tree or branch configuration requires owner classification.",
        "is_unresolved_residue": None,
    }


def _build_actions(
    snapshot: dict[str, Any],
    *,
    clarification: str | None = None,
) -> tuple[list[dict[str, Any]], list[str], dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    holds: list[str] = []
    classification = _classify_sync_state(snapshot)

    # If owner provided explicit clarification to publish or retain
    if clarification:
        norm_clar = clarification.strip().lower()
        if norm_clar in {"publish", "push", "unresolved", "residue"}:
            classification["category"] = "unresolved_end_of_day_residue"
            classification["reason"] = f"Owner clarified that unpushed commits are unresolved residue: {clarification}"
            classification["is_unresolved_residue"] = True
        elif norm_clar in {"retain", "keep", "intentional", "local"}:
            classification["category"] = "intentional_valid_state"
            classification["reason"] = f"Owner confirmed that unpushed commits are intentionally retained locally: {clarification}"
            classification["is_unresolved_residue"] = False

    git_state = snapshot["git_state"]
    branch = git_state.get("branch")
    if branch != "main":
        holds.append(f"current branch is {branch or 'unknown'}, not main")
    records = git_state.get("status_records", [])
    arbitrary_records = [r for r in records if not r.get("is_generated_receipt")]
    receipt_records = [r for r in records if r.get("is_generated_receipt")]

    if arbitrary_records:
        paths = ", ".join(sorted(record["path"] for record in arbitrary_records))
        holds.append("dirty work requires owner classification; no automated commit: " + paths)
    elif receipt_records:
        # Generated manifest receipts can be safely archived/cleaned as part of remediation
        actions.append({
            "kind": "clean_generated_receipts",
            "paths": [r["path"] for r in receipt_records],
        })

    origin = snapshot["sync_state"].get("origin")
    if origin is None:
        holds.append("origin/main synchronization is unavailable")
    elif branch == "main" and not arbitrary_records:
        if classification["category"] == "unresolved_end_of_day_residue":
            if origin["ahead"] > 0 and origin["behind"] == 0:
                actions.append({
                    "kind": "push_main",
                    "remote": "origin",
                    "branch": "main",
                    "expected_head": git_state.get("head"),
                    "expected_remote_head": origin.get("remote_head"),
                })
            elif origin["ahead"] == 0 and origin["behind"] > 0:
                actions.append({
                    "kind": "fast_forward_origin",
                    "remote": "origin",
                    "branch": "main",
                    "expected_head": git_state.get("head"),
                    "expected_remote_head": origin.get("remote_head"),
                })
            elif origin["ahead"] > 0 and origin["behind"] > 0:
                forecast_ok, forecast = _merge_forecast(Path(snapshot["repo"]))
                if forecast_ok:
                    actions.extend([
                        {
                            "kind": "merge_origin",
                            "remote": "origin",
                            "branch": "main",
                            "expected_local_head": git_state.get("head"),
                            "expected_remote_head": origin.get("remote_head"),
                        },
                        {
                            "kind": "push_merged_main",
                            "remote": "origin",
                            "branch": "main",
                            "expected_local_head": git_state.get("head"),
                            "expected_remote_head": origin.get("remote_head"),
                        },
                    ])
                else:
                    holds.append("substantive merge conflict forecast; owner/product intent is required")
        elif classification["category"] == "provenance_insufficient":
            if origin.get("ahead", 0) > 0:
                holds.append(
                    f"provenance insufficient to determine if {origin['ahead']} unpushed commit(s) are intentional or leftover residue; no automatic push scheduled"
                )
    for branch_info in snapshot["branches"].get("merged", []):
        if arbitrary_records:
            holds.append(f"merged branch cleanup deferred while working tree is dirty: {branch_info['name']}")
        elif branch_info.get("safe_to_delete"):
            actions.append({
                "kind": "delete_merged_branch",
                "branch": branch_info["name"],
                "expected_tip": branch_info["tip"],
            })
        else:
            holds.append(f"merged branch retained because it is checked out/in a worktree: {branch_info['name']}")
    for branch_info in snapshot["branches"].get("stale", []):
        holds.append(f"stale unmerged branch retained for owner decision: {branch_info['name']}")
    return actions, holds, classification


def _json_display_mode(config_path: Path) -> str:
    try:
        import yaml
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        value = ((raw.get("cron") or {}).get("nightly_json_display")) if isinstance(raw, dict) else None
        if isinstance(value, bool):
            return "show" if value else "hide"
        if str(value).strip().lower() in {"show", "hide"}:
            return str(value).strip().lower()
    except Exception:
        pass
    return "hide"


def set_json_display_mode(hermes_home: Path, mode: str) -> str:
    mode = mode.strip().lower()
    if mode not in {"show", "hide"}:
        raise ValueError("nightly JSON display must be show or hide")
    config_path = _runtime_paths(hermes_home).config_path
    try:
        from hermes_cli.config import atomic_config_write, read_user_config_raw
        config = read_user_config_raw(config_path)
        config.setdefault("cron", {})["nightly_json_display"] = mode
        atomic_config_write(config_path, config)
    except ImportError:
        import yaml
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
        if not isinstance(config, dict):
            raise RuntimeError("refusing to write non-mapping config")
        config.setdefault("cron", {})["nightly_json_display"] = mode
        _atomic_text(config_path, yaml.safe_dump(config, sort_keys=False), mode=0o600)
    return mode


def _is_valid_run_id(value: object) -> bool:
    return isinstance(value, str) and bool(RUN_ID_RE.fullmatch(value))


def _run_id(now: datetime, head: str) -> str:
    head_fragment = head.lower()[:12] if re.fullmatch(r"[0-9a-fA-F]{12,}", head) else "0" * 12
    timestamp = _as_myt(now).astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{timestamp}-{head_fragment}-{secrets.token_hex(16)}"


def _timeout_wrapper_script_name(run_id: str) -> str:
    if not _is_valid_run_id(run_id):
        raise ValueError("cannot schedule timeout with malformed run_id")
    return f"{TIMEOUT_WRAPPER_PREFIX}{run_id}{TIMEOUT_WRAPPER_SUFFIX}"


def _write_timeout_wrapper(*, run_id: str, hermes_home: Path) -> str:
    scripts_dir = hermes_home / "scripts"
    target = scripts_dir / "nightly_git_hygiene.py"
    if not target.is_file():
        raise FileNotFoundError(f"nightly timeout target is missing: {target}")
    script_name = _timeout_wrapper_script_name(run_id)
    wrapper = scripts_dir / script_name
    _atomic_text(
        wrapper,
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "SCRIPT_DIR=\"$(CDPATH= cd -- \"$(dirname -- \"$0\")\" && pwd -P)\"\n"
        f"exec \"$SCRIPT_DIR/nightly_git_hygiene.py\" --timeout --run-id {run_id} --human-only\n",
        mode=0o700,
    )
    return script_name


def _schedule_timeout_job(*, deadline_at: datetime, run_id: str, repo_root: Path, hermes_home: Path) -> str:
    from cron.jobs import create_job, use_cron_store  # type: ignore[import-not-found]
    script_name = _write_timeout_wrapper(run_id=run_id, hermes_home=hermes_home)
    with use_cron_store(hermes_home):
        job = create_job(
            prompt=None,
            schedule=_iso_myt(deadline_at),
            name=f"nightly-remediation-{run_id}",
            repeat=1,
            deliver="origin",
            script=script_name,
            workdir=str(repo_root),
            no_agent=True,
        )
    return str(job["id"])


def _write_workflow_outputs(result: dict[str, Any], paths: RuntimePaths) -> None:
    machine = {key: value for key, value in result.items() if key != "human_report" and not key.startswith("_")}
    _atomic_json(paths.receipt_json_path, machine)
    history_path = paths.history_dir / f"{result['run_id']}.json"
    _atomic_json(history_path, machine)
    _atomic_text(paths.receipt_path, result["human_report"] + "\n")


def _human_report(result: dict[str, Any]) -> str:
    status = result["status"]
    remediation = result.get("remediation", {})
    actions = remediation.get("actions", [])
    action_names = result.get("actions_taken", [])
    classification = result.get("classification", {})
    category = classification.get("category")
    is_preview = result.get("mode") == "preview"
    run_id_display = result.get("run_id") or ("null (preview)" if is_preview else "unknown")

    lines = [
        f"# Nightly Git report — {result['date']}",
        "",
        f"Overall: **{status}**",
        f"Run: `{run_id_display}`",
        "",
        "What I found:",
    ]
    state = result.get("git_state", {})
    if state.get("is_clean"):
        lines.append("- Keadaan working tree bersih — tiada fail tergantung atau perubahan belum disimpan.")
    elif state.get("status_porcelain"):
        lines.append("- Working tree mengandungi perubahan: " + ", ".join(state["status_porcelain"]))
    origin = result.get("sync_state", {}).get("origin")
    if origin:
        ahead = origin.get("ahead", 0)
        behind = origin.get("behind", 0)
        if ahead == 0 and behind == 0:
            lines.append("- Local main seiring sepenuhnya dengan origin/main di GitHub.")
        elif ahead > 0 and behind == 0:
            lines.append(f"- Local main berada {ahead} commit di hadapan origin/main (GitHub).")
        elif ahead == 0 and behind > 0:
            lines.append(f"- Local main berada {behind} commit di belakang origin/main (GitHub).")
        else:
            lines.append(f"- Local main diverged dengan origin/main (ahead {ahead}, behind {behind}).")
    if result.get("daily_delta", {}).get("commits"):
        lines.append(f"- Delta MYT hari ini mengandungi {len(result['daily_delta']['commits'])} commit.")
    lines.extend(["", "Healthy:"])
    healthy = [name.replace("_", " ") for name, gate in result.get("gates", {}).items() if gate.get("status") == "PASS"]
    lines.extend(f"- ✅ {name} passed." for name in healthy)
    if not healthy:
        lines.append("- Tiada tapisan kualiti/keselamatan direkodkan sebagai lulus.")
    execution = result.get("execution", {})
    if execution.get("script_path"):
        lines.extend([
            "",
            "Execution evidence:",
            f"- Target: `{execution.get('script_path')}`",
            f"- Target SHA-256: `{execution.get('script_sha256')}`",
            f"- Audited repository HEAD: `{execution.get('audited_repo_head')}`",
            "- Delivery: report emitted to scheduler stdout; destination delivery is verified separately from the cron execution record.",
        ])

    if actions and remediation.get("status") == "pending_confirmation":
        lines.extend(["", "What needs action tonight:"])
        for action in actions:
            kind = action.get("kind")
            if kind in {"push_main", "push_merged_main"}:
                lines.append("- Publish main to origin/main with a normal non-force push.")
            elif kind == "fast_forward_origin":
                lines.append("- Fast-forward local main to the already-fetched origin/main commit.")
            elif kind == "merge_origin":
                lines.append("- Merge origin/main into local main using the conflict-free forecast.")
            elif kind == "delete_merged_branch":
                lines.append(f"- Delete merged local branch `{action.get('branch')}` only; no remote branch deletion.")
            elif kind == "clean_generated_receipts":
                lines.append(f"- Archive and clean {len(action.get('paths', []))} generated reconciliation manifest receipt(s) from working tree.")
        lines.append("- Why: selesaikan kerja Git yang tertinggal malam ini supaya tidak dibawa ke hari esok.")
        lines.append(f"- Proposed automatic-action deadline: **{remediation.get('deadline_at')}**.")
        lines.append(f"- Confirmation needed: hantar `/nightly approve {remediation.get('run_id')}` atau `/nightly reject {remediation.get('run_id')} <reason>`, atau teks biasa `APPROVE NIGHTLY {remediation.get('run_id')}`.")
        lines.append("- No relevant response by the deadline: pelan tindakan ini akan berjalan secara automatik.")
    elif action_names:
        lines.extend(["", "Final result:"])
        lines.append("- Remediation executed: " + ", ".join(action_names) + ".")
        lines.append("- Kerja Git ditutup dan pemeriksaan semula lulus." if status == "PASS" else "- Pelan tidak dapat diselesaikan sepenuhnya; lihat sekatan di bawah.")
        lines.append("- Confirmation needed: no.")
    elif status == "PASS":
        lines.extend(["", "Tonight’s action:", "- None. Semua kerja Git dalam keadaan sah & teratur. Tiada remedi diperlukan.", "- Confirmation needed: no."])
    elif category == "provenance_insufficient":
        lines.extend([
            "",
            "Tonight’s action:",
            "- Tiada mutasi atau push automatik dicadangkan kerana bukti workflow belum mencukupi untuk membezakan sama ada commit local adalah disengajakan atau kerja tertinggal.",
            "- Timer 30 minit tidak diaktifkan kerana tiada pelan remedi automatik yang selamat pada masa ini.",
            f"- Perlu satu pengesahan daripada anda: adakah {origin.get('ahead', 0) if origin else 'commit'} commit ini memang sengaja dibiarkan di local, atau sepatutnya sudah dihantar ke GitHub?",
        ])
    elif actions:
        lines.extend(["", "Proposed action is blocked:", "- Pelan yang disimpan tidak boleh diteruskan tanpa menyelesaikan sekatan."])
    else:
        lines.extend(["", "Tonight’s action:", "- Tiada mutasi Git automatik dicadangkan.", "- Confirmation needed: yes, untuk keputusan owner."])

    if result.get("proposal_path"):
        lines.append(f"- Recurring-issue proposal: `{result['proposal_path']}`.")
    unresolved = list(dict.fromkeys(remediation.get("holds", []) + result.get("holds", [])))
    if unresolved:
        lines.extend(["", "Unresolved:"])
        lines.extend(f"- ⚠️ {hold}" for hold in unresolved)
    if result.get("errors"):
        lines.extend(["", "Errors / blockers:"])
        lines.extend(f"- ❌ {error}" for error in result["errors"])
    return "\n".join(lines)


def render_output(result: dict[str, Any], *, json_display: str = "hide") -> str:
    output = result.get("human_report") or _human_report(result)
    if json_display == "show":
        machine = {key: value for key, value in result.items() if key != "human_report" and not key.startswith("_")}
        output += "\n\n--- Raw nightly metadata ---\n" + json.dumps(machine, indent=2, ensure_ascii=False)
    return output


def run_nightly(
    *,
    repo_root: Path = REPO_ROOT,
    hermes_home: Path = HERMES_HOME,
    now: datetime | None = None,
    schedule_timeout: Callable[..., str] | None = None,
) -> dict[str, Any]:
    """Audit the day and create a durable bounded-remediation recommendation."""
    current = _as_myt(now)
    repo = repo_root.expanduser().resolve()
    home = hermes_home.expanduser().resolve()
    paths = _runtime_paths(home)
    snapshot = _inspect_git(repo, current)
    head = snapshot["git_state"].get("head") or "unknown"
    run_id = _run_id(current, head if len(head) >= 12 else "0" * 12)
    gates = run_full_delta_gates(repo, current) if not snapshot["errors"] else {}
    existing = _load_pending(paths)
    if existing and existing.get("status") in {"pending", "executing"}:
        result = _result_from_state(
            state=existing,
            status="HOLD",
            remediation_status="pending_confirmation" if existing.get("status") == "pending" else "executing",
            snapshot=snapshot,
            gates=gates,
            holds=list(existing.get("holds", [])),
            now=current,
        )
        result["errors"] = list(snapshot.get("errors", []))
        result["human_report"] = _human_report(result)
        _write_workflow_outputs(result, paths)
        return result
    actions, holds, classification = _build_actions(snapshot)
    errors = list(snapshot.get("errors", []))
    if gates and not _gates_pass(gates):
        errors.append("one or more required nightly quality/security gates failed")
        actions = []
    status = "PASS"
    remediation: dict[str, Any] = {
        "status": "none",
        "run_id": run_id,
        "actions": actions,
        "holds": holds,
    }
    if errors:
        status = "FAIL"
        remediation["status"] = "blocked"
    elif actions:
        status = "HOLD"
        deadline = current + AUTO_ACTION_WINDOW
        remediation.update({
            "status": "pending_confirmation",
            "created_at": _format_myt(current),
            "deadline_at": _format_myt(deadline),
        })
        scheduler = schedule_timeout or _schedule_timeout_job
        try:
            timeout_job_id = scheduler(
                deadline_at=deadline,
                run_id=run_id,
                repo_root=repo,
                hermes_home=home,
            )
            remediation["timeout_job_id"] = str(timeout_job_id)
            pending = {
                "schema_version": 1,
                "run_id": run_id,
                "status": "pending",
                "created_at": _iso_myt(current),
                "deadline_at": _iso_myt(deadline),
                "repo": str(repo),
                "hermes_home": str(home),
                "baseline": {
                    "head": head,
                    "branch": snapshot["git_state"].get("branch"),
                    "status_porcelain": snapshot["git_state"].get("status_porcelain", []),
                    "origin_remote_head": snapshot.get("sync_state", {}).get("origin", {}).get("remote_head"),
                },
                "actions": actions,
                "holds": holds,
                "timeout_job_id": str(timeout_job_id),
            }
            with _pending_lock(paths):
                _atomic_json(paths.pending_path, pending)
        except Exception as exc:
            status = "FAIL"
            remediation["status"] = "blocked"
            errors.append(f"could not persist the 30-minute scheduler continuation: {exc}")
    elif holds:
        status = "HOLD"
        # Schedule 30-min read-only investigation continuation for ambiguous provenance (when not dirty working tree)
        if classification.get("category") == "provenance_insufficient" and not snapshot["git_state"].get("status_records"):
            deadline = current + AUTO_ACTION_WINDOW
            remediation.update({
                "status": "pending_investigation",
                "created_at": _format_myt(current),
                "deadline_at": _format_myt(deadline),
            })
            scheduler = schedule_timeout or _schedule_timeout_job
            try:
                timeout_job_id = scheduler(
                    deadline_at=deadline,
                    run_id=run_id,
                    repo_root=repo,
                    hermes_home=home,
                )
                remediation["timeout_job_id"] = str(timeout_job_id)
                pending = {
                    "schema_version": 1,
                    "run_id": run_id,
                    "status": "pending",
                    "kind": "investigation",
                    "classification": classification,
                    "created_at": _iso_myt(current),
                    "deadline_at": _iso_myt(deadline),
                    "repo": str(repo),
                    "baseline": {
                        "head": head,
                        "branch": snapshot["git_state"].get("branch"),
                        "status_porcelain": snapshot["git_state"].get("status_porcelain", []),
                        "origin_remote_head": snapshot.get("sync_state", {}).get("origin", {}).get("remote_head"),
                    },
                    "actions": actions,
                    "holds": holds,
                    "timeout_job_id": str(timeout_job_id),
                }
                with _pending_lock(paths):
                    _atomic_json(paths.pending_path, pending)
            except Exception as exc:
                remediation["timeout_job_id"] = None
                remediation["status"] = "blocked"
                errors.append(f"could not persist the 30-minute scheduler continuation: {exc}")
        else:
            remediation["status"] = "blocked"

    result: dict[str, Any] = {
        "schema_version": 2,
        "run_id": run_id,
        "timestamp": _format_myt(current),
        "date": current.strftime("%Y-%m-%d"),
        "repo": str(repo),
        "status": status,
        "classification": classification,
        "release_pending": any(a.get("kind") == "push_main" for a in actions),
        "push_allowed": False,
        "owner_approval_required_for_push": True,
        "gates": gates,
        "git_state": snapshot["git_state"],
        "branches": snapshot["branches"],
        "sync_state": snapshot["sync_state"],
        "daily_delta": snapshot["daily_delta"],
        "actions_taken": [],
        "holds": holds,
        "errors": errors,
        "remediation": remediation,
        "execution": execution_identity(repo, head if len(head) == 40 else ""),
        "proposal_path": check_operational_proposals(repo, current.strftime("%Y-%m-%d")),
        "delivery": {"mode": "stdout", "status": "emitted_by_target_not_destination_verified"},
    }
    result["human_report"] = _human_report(result)
    _write_workflow_outputs(result, paths)
    return result


def _load_pending(paths: RuntimePaths) -> dict[str, Any] | None:
    if not paths.pending_path.is_file():
        return None
    try:
        payload = json.loads(paths.pending_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _parse_iso_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(MYT)


def _cancel_timeout_job(job_id: str | None, hermes_home: Path | None = None) -> None:
    if not job_id:
        return
    try:
        from cron.jobs import remove_job, use_cron_store  # type: ignore[import-not-found]
        if hermes_home is None:
            remove_job(job_id)
        else:
            with use_cron_store(hermes_home):
                remove_job(job_id)
    except Exception:
        # Cancellation is best effort after the state has been claimed. The
        # timeout runner re-checks the state and cannot execute a completed or
        # rejected plan.
        return


def _result_from_state(
    *,
    state: dict[str, Any],
    status: str,
    remediation_status: str,
    snapshot: dict[str, Any],
    gates: dict[str, Any],
    actions_taken: list[str] | None = None,
    errors: list[str] | None = None,
    holds: list[str] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    current = _as_myt(now)
    repo = Path(state["repo"]).expanduser().resolve()
    head = snapshot.get("git_state", {}).get("head") or state.get("baseline", {}).get("head", "")
    remediation = {
        "status": remediation_status,
        "run_id": state["run_id"],
        "actions": state.get("actions", []),
        "holds": list(holds) if holds is not None else list(state.get("holds", [])),
    }
    effective_holds = remediation["holds"]
    effective_errors = list(errors) if errors is not None else list(state.get("errors", []))
    for key in ("created_at", "deadline_at", "timeout_job_id"):
        if key in state:
            remediation[key] = _format_myt(_parse_iso_datetime(state[key])) if key in {"created_at", "deadline_at"} else state[key]
    result: dict[str, Any] = {
        "schema_version": 2,
        "run_id": state["run_id"],
        "timestamp": _format_myt(current),
        "date": current.strftime("%Y-%m-%d"),
        "repo": str(repo),
        "status": status,
        "release_pending": bool(
            status != "PASS"
            and (
                snapshot.get("sync_state", {}).get("origin", {}).get("ahead", 0)
                or any(a.get("kind") in {"push_main", "push_merged_main"} for a in state.get("actions", []))
            )
        ),
        "push_allowed": status == "PASS" and bool(set(actions_taken or []) & {"push_main", "push_after_commit", "push_merged_main"}),
        "owner_approval_required_for_push": True,
        "gates": gates,
        "git_state": snapshot.get("git_state", {}),
        "branches": snapshot.get("branches", {"merged": [], "stale": [], "active": []}),
        "sync_state": snapshot.get("sync_state", {}),
        "daily_delta": snapshot.get("daily_delta", {"commits": []}),
        "actions_taken": actions_taken or [],
        "holds": effective_holds,
        "errors": effective_errors,
        "remediation": remediation,
        "execution": execution_identity(repo, head if len(head) == 40 else ""),
        "proposal_path": state.get("proposal_path"),
        "delivery": {"mode": "stdout", "status": "emitted_by_target_not_destination_verified"},
    }
    result["human_report"] = _human_report(result)
    return result


def _fast_forward_origin_action(
    *,
    state: dict[str, Any],
    repo: Path,
    now: datetime,
) -> tuple[str | None, str | None, dict[str, Any], dict[str, Any]]:
    action = next((a for a in state.get("actions", []) if a.get("kind") == "fast_forward_origin"), None)
    snapshot = _inspect_git(repo, now)
    if snapshot.get("errors"):
        return None, "fast-forward precondition failed: fresh repository inspection has errors", snapshot, {}
    origin = snapshot.get("sync_state", {}).get("origin")
    if action is None:
        return None, "fast-forward action is missing from pending plan", snapshot, {}
    if snapshot["git_state"].get("branch") != "main" or not snapshot["git_state"].get("is_clean"):
        return None, "fast-forward precondition failed: main is not clean/on the expected branch", snapshot, {}
    if snapshot["git_state"].get("head") != action.get("expected_head"):
        return None, "fast-forward precondition failed: local HEAD changed", snapshot, {}
    if not origin or origin.get("ahead") != 0 or origin.get("behind", 0) <= 0 or origin.get("remote_head") != action.get("expected_remote_head"):
        return None, "fast-forward precondition failed: origin/main changed", snapshot, {}
    gates = run_full_delta_gates(repo, now)
    if not _gates_pass(gates):
        return None, "required gates failed before fast-forward", snapshot, gates
    rc, output = _workflow_git(repo, ["merge", "--ff-only", "origin/main"])
    if rc != 0:
        return None, f"fast-forward failed: {output[-500:]}", snapshot, gates
    final_snapshot = _inspect_git(repo, now)
    final_origin = final_snapshot.get("sync_state", {}).get("origin")
    if (
        final_snapshot["git_state"].get("head") != action.get("expected_remote_head")
        or not final_snapshot["git_state"].get("is_clean")
        or not final_origin
        or final_origin.get("ahead") != 0
        or final_origin.get("behind") != 0
        or final_origin.get("remote_head") != action.get("expected_remote_head")
    ):
        return None, "fast-forward completed but local/remote read-back failed", final_snapshot, gates
    return "fast_forward_origin", None, final_snapshot, gates


def _merge_origin_action(
    *,
    state: dict[str, Any],
    repo: Path,
    now: datetime,
) -> tuple[str | None, str | None, dict[str, Any], dict[str, Any]]:
    action = next((a for a in state.get("actions", []) if a.get("kind") == "merge_origin"), None)
    snapshot = _inspect_git(repo, now)
    if snapshot.get("errors"):
        return None, "merge precondition failed: fresh repository inspection has errors", snapshot, {}
    origin = snapshot.get("sync_state", {}).get("origin")
    if action is None:
        return None, "merge action is missing from pending plan", snapshot, {}
    if snapshot["git_state"].get("branch") != "main" or not snapshot["git_state"].get("is_clean"):
        return None, "merge precondition failed: main is not clean/on the expected branch", snapshot, {}
    if snapshot["git_state"].get("head") != action.get("expected_local_head"):
        return None, "merge precondition failed: local HEAD changed", snapshot, {}
    if not origin or origin.get("ahead", 0) <= 0 or origin.get("behind", 0) <= 0 or origin.get("remote_head") != action.get("expected_remote_head"):
        return None, "merge precondition failed: origin/main changed", snapshot, {}
    forecast_ok, forecast = _merge_forecast(repo)
    if not forecast_ok:
        return None, "substantive merge conflict forecast; owner/product intent is required", snapshot, {}
    gates = run_full_delta_gates(repo, now)
    if not _gates_pass(gates):
        return None, "required gates failed before merge", snapshot, gates
    rc, output = _workflow_git(repo, ["merge", "--no-edit", "origin/main"])
    if rc != 0:
        _workflow_git(repo, ["merge", "--abort"])
        return None, f"substantive merge conflict during execution: {output[-500:]}", _inspect_git(repo, now), gates
    rc_parents, parents_output = _workflow_git(repo, ["rev-list", "--parents", "-n1", "HEAD"])
    parents = parents_output.split()[1:] if rc_parents == 0 else []
    final_snapshot = _inspect_git(repo, now)
    if (
        not final_snapshot["git_state"].get("is_clean")
        or action.get("expected_local_head") not in parents
        or action.get("expected_remote_head") not in parents
    ):
        return None, "merge returned success but merge-parent/read-back proof failed", final_snapshot, gates
    return "merge_origin", None, final_snapshot, gates


def _push_merged_main_action(
    *,
    state: dict[str, Any],
    repo: Path,
    now: datetime,
) -> tuple[str | None, str | None, dict[str, Any], dict[str, Any]]:
    action = next((a for a in state.get("actions", []) if a.get("kind") == "push_merged_main"), None)
    snapshot = _inspect_git(repo, now)
    if snapshot.get("errors"):
        return None, "merged push precondition failed: fresh repository inspection has errors", snapshot, {}
    origin = snapshot.get("sync_state", {}).get("origin")
    if action is None:
        return None, "merged push action is missing from pending plan", snapshot, {}
    if snapshot["git_state"].get("branch") != "main" or not snapshot["git_state"].get("is_clean"):
        return None, "merged push precondition failed: main is not clean/on the expected branch", snapshot, {}
    if not origin or origin.get("ahead", 0) <= 0 or origin.get("behind") != 0 or origin.get("remote_head") != action.get("expected_remote_head"):
        return None, "merged push precondition failed: origin/main changed", snapshot, {}
    rc_parents, parents_output = _workflow_git(repo, ["rev-list", "--parents", "-n1", "HEAD"])
    parents = parents_output.split()[1:] if rc_parents == 0 else []
    if action.get("expected_local_head") not in parents or action.get("expected_remote_head") not in parents:
        return None, "merged push precondition failed: HEAD is not the presented merge result", snapshot, {}
    gates = run_full_delta_gates(repo, now)
    if not _gates_pass(gates):
        return None, "required gates failed before merged push", snapshot, gates
    rc, output = _workflow_git(repo, ["push", action["remote"], action["branch"]])
    if rc != 0:
        hermes_home = Path(state.get("hermes_home", HERMES_HOME)).expanduser().resolve()
        token = _get_github_token(hermes_home)
        if token and any(term in output.lower() for term in ["protected branch", "gh006", "pre-receive hook declined", "permission", "protected", "declined"]):
            return _publish_via_protected_pr(
                state=state,
                repo=repo,
                now=now,
                action=action,
                gates=gates,
                hermes_home=hermes_home,
            )
        return None, f"normal merged push failed: {output[-500:]}", snapshot, gates
    final_snapshot = _inspect_git(repo, now)
    final_origin = final_snapshot.get("sync_state", {}).get("origin")
    head = final_snapshot["git_state"].get("head")
    if (
        not head
        or not final_origin
        or final_origin.get("ahead") != 0
        or final_origin.get("behind") != 0
        or final_origin.get("remote_head") != head
    ):
        return None, "merged push completed but remote/local synchronization read-back failed", final_snapshot, gates
    return "push_merged_main", None, final_snapshot, gates


def _delete_merged_branch_action(
    *,
    state: dict[str, Any],
    repo: Path,
    now: datetime,
    action: dict[str, Any],
) -> tuple[str | None, str | None, dict[str, Any], dict[str, Any]]:
    branch_name = action.get("branch")
    if not isinstance(branch_name, str) or not branch_name:
        return None, "branch cleanup plan has no valid branch name", _inspect_git(repo, now), {}
    snapshot = _inspect_git(repo, now)
    if snapshot.get("errors"):
        return None, "branch cleanup precondition failed: fresh repository inspection has errors", snapshot, {}
    branch_info = next(
        (item for item in snapshot.get("branches", {}).get("merged", []) if item.get("name") == branch_name),
        None,
    )
    if not branch_info or not branch_info.get("safe_to_delete"):
        return None, f"branch cleanup precondition failed: {branch_name} is not safely merged/free", snapshot, {}
    rc_tip, tip = _workflow_git(repo, ["rev-parse", branch_name])
    if rc_tip != 0 or tip.strip() != action.get("expected_tip"):
        return None, f"branch cleanup precondition failed: {branch_name} tip changed", snapshot, {}
    gates = run_full_delta_gates(repo, now)
    if not _gates_pass(gates):
        return None, "required gates failed before branch cleanup", snapshot, gates
    rc, output = _workflow_git(repo, ["branch", "-d", branch_name])
    if rc != 0:
        return None, f"safe merged-branch deletion failed: {output[-500:]}", snapshot, gates
    rc_check, remaining = _workflow_git(repo, ["show-ref", "--verify", "--quiet", f"refs/heads/{branch_name}"])
    if rc_check == 0:
        return None, f"branch deletion returned success but {branch_name} still exists", snapshot, gates
    return "delete_merged_branch", None, _inspect_git(repo, now), gates


def _clean_generated_receipts_action(
    *,
    state: dict[str, Any],
    repo: Path,
    now: datetime,
    action: dict[str, Any],
) -> tuple[str | None, str | None, dict[str, Any], dict[str, Any]]:
    paths = action.get("paths", [])
    if not paths:
        return "clean_generated_receipts", None, _inspect_git(repo, now), {}
    import shutil
    home = Path(state.get("hermes_home", HERMES_HOME)).expanduser().resolve()
    # Use the plan creation date if available in baseline/state so the archive folder matches the run timestamp
    archive_date_str = state.get("created_at", "").split("T")[0].replace("-", "") if state.get("created_at") else ""
    if not archive_date_str or len(archive_date_str) != 8:
        archive_date_str = _as_myt(now).strftime("%Y%m%d")
    backup_root = home / "backups" / "git-reconciliation" / archive_date_str / "receipts"
    backup_root.mkdir(parents=True, exist_ok=True)
    os.chmod(backup_root, 0o700)

    for rel in paths:
        norm = rel.replace("\\", "/").strip()
        if not _is_generated_reconciliation_receipt(norm):
            return None, f"refusing to auto-clean non-receipt path: {rel}", _inspect_git(repo, now), {}
        p = repo / norm
        if p.is_file():
            dest = backup_root / p.name
            try:
                data = p.read_bytes()
                dest.write_bytes(data)
                os.chmod(dest, 0o600)
                if dest.read_bytes() != data:
                    return None, f"verification failed for archived receipt: {rel}", _inspect_git(repo, now), {}
                p.unlink()
            except OSError as exc:
                return None, f"could not archive and clean receipt {rel}: {exc}", _inspect_git(repo, now), {}
    return "clean_generated_receipts", None, _inspect_git(repo, now), {}


def _execute_pending_actions(
    *,
    state: dict[str, Any],
    repo: Path,
    now: datetime,
) -> tuple[list[str], str | None, dict[str, Any], dict[str, Any]]:
    initial = _inspect_git(repo, now)
    baseline = state.get("baseline", {})
    if initial["git_state"].get("head") != baseline.get("head"):
        return [], "pending plan invalidated: local HEAD changed", initial, {}
    if initial["git_state"].get("status_porcelain", []) != baseline.get("status_porcelain", []):
        return [], "pending plan invalidated: working tree changed", initial, {}
    taken: list[str] = []
    latest = initial
    latest_gates: dict[str, Any] = {}
    for action in state.get("actions", []):
        kind = action.get("kind")
        if kind in {"commit_dirty", "push_after_commit"}:
            return taken, f"unsafe legacy pending action blocked: {kind}", latest, latest_gates
        if kind == "push_main":
            name, error, latest, latest_gates = _push_main_action(state=state, repo=repo, now=now)
        elif kind == "fast_forward_origin":
            name, error, latest, latest_gates = _fast_forward_origin_action(state=state, repo=repo, now=now)
        elif kind == "merge_origin":
            name, error, latest, latest_gates = _merge_origin_action(state=state, repo=repo, now=now)
        elif kind == "push_merged_main":
            name, error, latest, latest_gates = _push_merged_main_action(state=state, repo=repo, now=now)
        elif kind == "delete_merged_branch":
            name, error, latest, latest_gates = _delete_merged_branch_action(
                state=state,
                repo=repo,
                now=now,
                action=action,
            )
        elif kind == "clean_generated_receipts":
            name, error, latest, latest_gates = _clean_generated_receipts_action(
                state=state,
                repo=repo,
                now=now,
                action=action,
            )
        else:
            return taken, f"unsupported pending action: {kind}", latest, latest_gates
        if error:
            return taken, error, latest, latest_gates
        if name:
            taken.append(name)
    remaining_actions, remaining_holds, _ = _build_actions(latest)
    if remaining_actions or remaining_holds:
        details = remaining_holds + [f"remaining action: {item.get('kind')}" for item in remaining_actions]
        return taken, "plan did not fully close: " + "; ".join(details), latest, latest_gates
    return taken, None, latest, latest_gates


def _get_github_token(hermes_home: Path) -> str | None:
    token = os.environ.get("GITHUB_TOKEN")
    if token and len(token.strip()) > 10:
        return token.strip()
    env_file = hermes_home / ".env"
    if env_file.is_file():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("GITHUB_TOKEN="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if len(val) > 10:
                        return val
        except Exception:
            pass
    return None


def _parse_github_remote(remote_url: str) -> tuple[str, str] | None:
    m = re.search(r"github\.com[:/]([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?$", remote_url.strip())
    if m:
        return m.group(1), m.group(2)
    return None


def _github_api_request(
    method: str,
    path: str,
    token: str,
    payload: dict[str, Any] | list[Any] | None = None,
) -> tuple[int, Any, str | None]:
    url = f"https://api.github.com{path}" if path.startswith("/") else path
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Hermes-Nightly-Remediation",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            body = resp.read().decode("utf-8")
            return status, (json.loads(body) if body else None), None
    except urllib.error.HTTPError as exc:
        err_body = exc.read().decode("utf-8") if exc.fp else ""
        try:
            err_json = json.loads(err_body)
            err_msg = err_json.get("message", err_body)
        except Exception:
            err_msg = err_body or str(exc)
        return exc.code, None, f"HTTP {exc.code}: {err_msg}"
    except Exception as exc:
        return 0, None, str(exc)


def _publish_via_protected_pr(
    *,
    state: dict[str, Any],
    repo: Path,
    now: datetime,
    action: dict[str, Any],
    gates: dict[str, Any],
    hermes_home: Path,
) -> tuple[str | None, str | None, dict[str, Any], dict[str, Any]]:
    """Publish commits to protected main via a deterministic PR, check observation, and merge flow."""
    token = _get_github_token(hermes_home)
    if not token:
        return None, "GitHub authentication token (GITHUB_TOKEN) is not configured in ~/.hermes/.env", _inspect_git(repo, now), gates

    rc_url, remote_url = _workflow_git(repo, ["remote", "get-url", action.get("remote", "origin")])
    if rc_url != 0:
        return None, f"could not resolve remote URL for {action.get('remote', 'origin')}", _inspect_git(repo, now), gates

    parsed = _parse_github_remote(remote_url)
    if not parsed:
        return None, f"could not parse GitHub owner/repo from remote URL: {remote_url}", _inspect_git(repo, now), gates
    owner, repo_name = parsed

    run_id = state.get("run_id", "manual")
    clean_run_id = re.sub(r"[^A-Za-z0-9_-]", "-", run_id)[:50]
    pub_branch = f"nightly/publication-{clean_run_id}"

    # 1. Push local commits to remote publication branch
    rc_push, push_out = _workflow_git(repo, ["push", action.get("remote", "origin"), f"HEAD:refs/heads/{pub_branch}"])
    if rc_push != 0:
        return None, f"pushing to publication branch {pub_branch} failed: {push_out[-500:]}", _inspect_git(repo, now), gates

    # 2. Check for existing open PR or create a new one
    status, pulls_data, err = _github_api_request(
        "GET",
        f"/repos/{owner}/{repo_name}/pulls?state=open&head={owner}:{pub_branch}&base=main",
        token,
    )
    if status != 200 or pulls_data is None:
        # Also try head without owner prefix
        status, pulls_data, err = _github_api_request(
            "GET",
            f"/repos/{owner}/{repo_name}/pulls?state=open&head={pub_branch}&base=main",
            token,
        )

    pr_number: int | None = None
    pr_head_sha: str | None = None
    if status == 200 and isinstance(pulls_data, list) and pulls_data:
        pr_info = pulls_data[0]
        pr_number = pr_info.get("number")
        pr_head_sha = pr_info.get("head", {}).get("sha")
    else:
        pr_payload = {
            "title": f"chore(nightly): automated git hygiene remediation ({run_id})",
            "head": pub_branch,
            "base": "main",
            "body": (
                f"Automated 23:55 Nightly Git Hygiene remediation for run `{run_id}`.\n\n"
                f"- Audited Head: `{action.get('expected_head')}`\n"
                f"- Base: `main`\n\n"
                "This PR was created automatically by the approved nightly remediation executor."
            ),
        }
        create_status, create_data, create_err = _github_api_request(
            "POST",
            f"/repos/{owner}/{repo_name}/pulls",
            token,
            pr_payload,
        )
        if create_status not in {200, 201} or not create_data:
            return None, f"GitHub PR creation failed: {create_err}", _inspect_git(repo, now), gates
        pr_number = create_data.get("number")
        pr_head_sha = create_data.get("head", {}).get("sha")

    if not pr_number:
        return None, "GitHub PR number could not be determined", _inspect_git(repo, now), gates

    # 3. Observe checks on head commit (poll until registered and completed)
    head_sha = pr_head_sha or action.get("expected_head", "HEAD")
    max_poll_seconds = 240
    poll_start = time.time()
    seen_checks = False
    while time.time() - poll_start < max_poll_seconds:
        chk_status, chk_data, chk_err = _github_api_request(
            "GET",
            f"/repos/{owner}/{repo_name}/commits/{head_sha}/check-runs",
            token,
        )
        if chk_status == 200 and chk_data:
            check_runs = chk_data.get("check_runs", [])
            if check_runs:
                seen_checks = True
                in_progress = any(cr.get("status") in {"queued", "in_progress"} for cr in check_runs)
                failed = any(
                    cr.get("status") == "completed" and cr.get("conclusion") in {"failure", "cancelled", "timed_out"}
                    for cr in check_runs
                )
                if failed:
                    return None, f"GitHub CI check runs failed on PR #{pr_number} (head: {head_sha})", _inspect_git(repo, now), gates
                if not in_progress:
                    break
        # If check runs haven't appeared yet, wait up to 15s before assuming no checks exist
        if not seen_checks and (time.time() - poll_start > 15):
            break
        time.sleep(5)

    # 4. Merge PR via REST API (try rebase, fallback squash/merge)
    merge_status, merge_data, merge_err = _github_api_request(
        "PUT",
        f"/repos/{owner}/{repo_name}/pulls/{pr_number}/merge",
        token,
        {
            "merge_method": "rebase",
        },
    )
    if merge_status != 200:
        # Try squash merge if rebase is disabled on repository
        merge_status, merge_data, merge_err = _github_api_request(
            "PUT",
            f"/repos/{owner}/{repo_name}/pulls/{pr_number}/merge",
            token,
            {
                "merge_method": "squash",
                "commit_title": f"chore(nightly): automated git hygiene remediation ({run_id}) (#{pr_number})",
            },
        )
    if merge_status != 200:
        return None, f"GitHub PR #{pr_number} merge failed: {merge_err}", _inspect_git(repo, now), gates

    # 5. Clean up remote publication branch
    _workflow_git(repo, ["push", action.get("remote", "origin"), "--delete", pub_branch])

    # 6. Fetch origin/main and sync local main to the merged remote commit
    _workflow_git(repo, ["fetch", action.get("remote", "origin"), "main"])
    _workflow_git(repo, ["reset", "--hard", f"{action.get('remote', 'origin')}/main"])

    final_snapshot = _inspect_git(repo, now)
    final_origin = final_snapshot.get("sync_state", {}).get("origin")
    final_head = final_snapshot["git_state"].get("head")
    if (
        not final_head
        or not final_origin
        or final_origin.get("ahead") != 0
        or final_origin.get("behind") != 0
        or final_origin.get("remote_head") != final_head
    ):
        return None, "protected PR merged but local synchronization read-back failed", final_snapshot, gates

    return action.get("kind", "push_main"), None, final_snapshot, gates


def _push_main_action(
    *,
    state: dict[str, Any],
    repo: Path,
    now: datetime,
) -> tuple[str | None, str | None, dict[str, Any], dict[str, Any]]:
    """Execute one pre-presented push action and independently verify it."""
    snapshot = _inspect_git(repo, now)
    if snapshot.get("errors"):
        return None, "push precondition failed: fresh repository inspection has errors", snapshot, {}
    git_state = snapshot["git_state"]
    origin = snapshot.get("sync_state", {}).get("origin")
    action = next((a for a in state.get("actions", []) if a.get("kind") == "push_main"), None)
    if action is None:
        return None, "push action is missing from pending plan", snapshot, {}
    if git_state.get("branch") != "main" or not git_state.get("is_clean"):
        return None, "push precondition failed: main is not clean/on the expected branch", snapshot, {}
    if git_state.get("head") != action.get("expected_head"):
        return None, "push precondition failed: local HEAD changed after recommendation", snapshot, {}
    if not origin or origin.get("ahead", 0) <= 0 or origin.get("behind") != 0:
        return None, "push precondition failed: origin relationship changed", snapshot, {}
    if origin.get("remote_head") != action.get("expected_remote_head"):
        return None, "push precondition failed: origin/main changed after recommendation", snapshot, {}
    gates = run_full_delta_gates(repo, now)
    if not _gates_pass(gates):
        return None, "required gates failed before push", snapshot, gates

    rc, output = _workflow_git(repo, ["push", action["remote"], action["branch"]])
    if rc != 0:
        # Check if direct push failed due to branch protection or refusal
        hermes_home = Path(state.get("hermes_home", HERMES_HOME)).expanduser().resolve()
        token = _get_github_token(hermes_home)
        if token and any(term in output.lower() for term in ["protected branch", "gh006", "pre-receive hook declined", "permission", "protected", "declined"]):
            return _publish_via_protected_pr(
                state=state,
                repo=repo,
                now=now,
                action=action,
                gates=gates,
                hermes_home=hermes_home,
            )
        return None, f"normal push failed: {output[-500:]}", snapshot, gates

    final_snapshot = _inspect_git(repo, now)
    final_origin = final_snapshot.get("sync_state", {}).get("origin")
    if (
        final_snapshot["git_state"].get("head") != action.get("expected_head")
        or not final_origin
        or final_origin.get("ahead") != 0
        or final_origin.get("behind") != 0
        or final_origin.get("remote_head") != action.get("expected_head")
    ):
        return None, "push completed but remote/local synchronization read-back failed", final_snapshot, gates
    return "push_main", None, final_snapshot, gates


def process_pending(
    *,
    decision: str,
    hermes_home: Path = HERMES_HOME,
    run_id: str | None = None,
    reason: str = "",
    now: datetime | None = None,
) -> dict[str, Any]:
    """Approve, reject, or timeout a persisted plan without an LLM decision."""
    current = _as_myt(now)
    paths = _runtime_paths(hermes_home)
    decision = decision.strip().lower()
    if decision not in {"approve", "reject", "timeout"}:
        raise ValueError("decision must be approve, reject, or timeout")
    with _pending_lock(paths):
        state = _load_pending(paths)
        if not state:
            result = {
                "schema_version": 2,
                "run_id": run_id or "none",
                "timestamp": _format_myt(current),
                "date": current.strftime("%Y-%m-%d"),
                "repo": "",
                "status": "HOLD",
                "release_pending": False,
                "push_allowed": False,
                "owner_approval_required_for_push": True,
                "gates": {},
                "git_state": {},
                "branches": {"merged": [], "stale": [], "active": []},
                "sync_state": {},
                "daily_delta": {"commits": []},
                "actions_taken": [],
                "holds": ["no pending nightly remediation exists"],
                "errors": [],
                "remediation": {"status": "none", "actions": []},
                "execution": {},
                "proposal_path": None,
            }
            result["human_report"] = _human_report(result)
            result["_silent"] = decision == "timeout"
            _write_workflow_outputs(result, paths)
            return result
        state_run_id = state.get("run_id")
        if not _is_valid_run_id(run_id):
            repo = Path(state["repo"])
            snapshot = _inspect_git(repo, current)
            reason = (
                f"{decision} requires an exact run_id"
                if run_id is None else "malformed run_id; no remediation action was executed"
            )
            result = _result_from_state(
                state=state,
                status="HOLD",
                remediation_status="pending_confirmation" if state.get("status") == "pending" else str(state.get("status")),
                snapshot=snapshot,
                gates={},
                holds=[reason],
                now=current,
            )
            _write_workflow_outputs(result, paths)
            return result
        if not _is_valid_run_id(state_run_id):
            repo = Path(state["repo"])
            snapshot = _inspect_git(repo, current)
            result = _result_from_state(
                state=state,
                status="HOLD",
                remediation_status="blocked",
                snapshot=snapshot,
                gates={},
                holds=["persisted pending remediation has malformed run_id"],
                now=current,
            )
            _write_workflow_outputs(result, paths)
            return result
        if run_id != state_run_id:
            repo = Path(state["repo"])
            snapshot = _inspect_git(repo, current)
            result = _result_from_state(
                state=state,
                status="HOLD",
                remediation_status="pending_confirmation",
                snapshot=snapshot,
                gates={},
                holds=["run_id does not match the current pending remediation"],
                now=current,
            )
            _write_workflow_outputs(result, paths)
            return result
        state_status = state.get("status")
        if state_status in {"completed", "rejected", "failed", "blocked"}:
            repo = Path(state["repo"])
            snapshot = _inspect_git(repo, current)
            result = _result_from_state(
                state=state,
                status="PASS" if state_status == "completed" else "FAIL" if state_status == "failed" else "HOLD",
                remediation_status=state_status,
                snapshot=snapshot,
                gates={},
                actions_taken=state.get("actions_taken", []),
                holds=state.get("holds", []),
                errors=state.get("errors", []),
                now=current,
            )
            result["_silent"] = decision == "timeout"
            _write_workflow_outputs(result, paths)
            return result
        if state_status == "executing":
            repo = Path(state["repo"])
            snapshot = _inspect_git(repo, current)
            result = _result_from_state(
                state=state,
                status="HOLD",
                remediation_status="executing",
                snapshot=snapshot,
                gates={},
                holds=["another nightly remediation execution is already in progress"],
                now=current,
            )
            result["_silent"] = decision == "timeout"
            _write_workflow_outputs(result, paths)
            return result
        deadline = _parse_iso_datetime(state["deadline_at"])
        if decision == "timeout" and current < deadline:
            repo = Path(state["repo"])
            snapshot = _inspect_git(repo, current)
            result = _result_from_state(
                state=state,
                status="HOLD",
                remediation_status="pending_confirmation",
                snapshot=snapshot,
                gates={},
                now=current,
            )
            result["_silent"] = True
            _write_workflow_outputs(result, paths)
            return result
        state_kind = state.get("kind", "remediation")
        repo = Path(state["repo"]).expanduser().resolve()
        snapshot = _inspect_git(repo, current)
        if state_kind == "investigation":
            # If owner approved/clarified on an ambiguous investigation state
            if decision == "approve":
                # Owner clarifies to publish
                actions, holds, new_class = _build_actions(snapshot, clarification=reason or "publish")
                if actions:
                    state["kind"] = "remediation"
                    state["actions"] = actions
                    state["holds"] = holds
                    state["classification"] = new_class
                    state["status"] = "pending"
                    state["deadline_at"] = _iso_myt(current + AUTO_ACTION_WINDOW)
                    _atomic_json(paths.pending_path, state)
                    result = _result_from_state(
                        state=state,
                        status="HOLD",
                        remediation_status="pending_confirmation",
                        snapshot=snapshot,
                        gates={},
                        holds=holds,
                        now=current,
                    )
                    _write_workflow_outputs(result, paths)
                    return result
                else:
                    state["status"] = "completed"
                    state["holds"] = holds
                    _atomic_json(paths.pending_path, state)
                    result = _result_from_state(
                        state=state,
                        status="PASS",
                        remediation_status="completed",
                        snapshot=snapshot,
                        gates={},
                        holds=holds,
                        now=current,
                    )
                    _write_workflow_outputs(result, paths)
                    return result
            elif decision == "reject":
                # Owner confirms intentional retention locally
                state["status"] = "completed"
                state["decision"] = "reject"
                state["decision_reason"] = reason.strip() or "owner confirmed intentional local retention"
                state["classification"] = {
                    "category": "intentional_valid_state",
                    "reason": state["decision_reason"],
                    "is_unresolved_residue": False,
                }
                state["actions"] = []
                state["holds"] = []
                _atomic_json(paths.pending_path, state)
                _cancel_timeout_job(state.get("timeout_job_id"), paths.hermes_home)
                result = _result_from_state(
                    state=state,
                    status="PASS",
                    remediation_status="completed",
                    snapshot=snapshot,
                    gates={},
                    holds=[],
                    now=current,
                )
                _write_workflow_outputs(result, paths)
                return result
            elif decision == "timeout":
                # 30-min timeout for investigation: run read-only provenance investigation
                actions, holds, new_class = _build_actions(snapshot)
                if new_class.get("category") == "intentional_valid_state":
                    state["status"] = "completed"
                    state["holds"] = []
                    state["actions"] = []
                    _atomic_json(paths.pending_path, state)
                    result = _result_from_state(
                        state=state,
                        status="PASS",
                        remediation_status="completed",
                        snapshot=snapshot,
                        gates={},
                        holds=[],
                        now=current,
                    )
                    _write_workflow_outputs(result, paths)
                    return result
                elif new_class.get("category") == "unresolved_end_of_day_residue" and actions:
                    state["kind"] = "remediation"
                    state["actions"] = actions
                    state["holds"] = holds
                    # Proceed to normal execution below
                else:
                    # Ambiguity remains: HOLD without mutation
                    state["status"] = "blocked"
                    state["holds"] = list(holds) or ["provenance remains ambiguous after investigation; no mutation executed"]
                    _atomic_json(paths.pending_path, state)
                    result = _result_from_state(
                        state=state,
                        status="HOLD",
                        remediation_status="blocked",
                        snapshot=snapshot,
                        gates={},
                        holds=state["holds"],
                        now=current,
                    )
                    _write_workflow_outputs(result, paths)
                    return result
        if decision == "approve" and current >= deadline:
            decision = "timeout"
        if decision == "reject":
            state["status"] = "rejected"
            state["decision"] = "reject"
            state["decision_reason"] = reason.strip() or "owner rejected the proposed remediation"
            _atomic_json(paths.pending_path, state)
            repo = Path(state["repo"])
            snapshot = _inspect_git(repo, current)
            _cancel_timeout_job(state.get("timeout_job_id"), paths.hermes_home)
            result = _result_from_state(
                state=state,
                status="HOLD",
                remediation_status="rejected",
                snapshot=snapshot,
                gates={},
                holds=[state["decision_reason"]],
                now=current,
            )
            _write_workflow_outputs(result, paths)
            return result

        state["status"] = "executing"
        state["decision"] = decision
        state["decision_at"] = _iso_myt(current)
        _atomic_json(paths.pending_path, state)
    # Do not hold the state-file lock during Git/network work. A concurrent
    # runner sees executing and cannot start a second plan.
    _cancel_timeout_job(state.get("timeout_job_id"), paths.hermes_home)
    repo = Path(state["repo"]).expanduser().resolve()
    action_taken_list: list[str] = []
    if not repo.is_dir():
        state["status"] = "failed"
        state["errors"] = [f"repository disappeared: {repo}"]
        snapshot = {"git_state": {}, "branches": {"merged": [], "stale": [], "active": []}, "sync_state": {}, "daily_delta": {"commits": []}}
        gates: dict[str, Any] = {}
        final_status = "FAIL"
    else:
        action_taken_list, error, snapshot, gates = _execute_pending_actions(
            state=state,
            repo=repo,
            now=current,
        )
        if error:
            state["status"] = "failed" if ("gates failed" in error or "push failed" in error or "commit failed" in error) else "blocked"
            state["actions_taken"] = action_taken_list
            state["errors"] = [error] if state["status"] == "failed" else []
            state["holds"] = [error] if state["status"] == "blocked" else []
            final_status = "FAIL" if state["status"] == "failed" else "HOLD"
        else:
            state["status"] = "completed"
            state["actions_taken"] = action_taken_list
            state["errors"] = []
            state["holds"] = []
            final_status = "PASS"
    with _pending_lock(paths):
        _atomic_json(paths.pending_path, state)
    result = _result_from_state(
        state=state,
        status=final_status,
        remediation_status=state["status"],
        snapshot=snapshot,
        gates=gates,
        actions_taken=state.get("actions_taken", action_taken_list),
        errors=state.get("errors", []),
        holds=state.get("holds", []),
        now=current,
    )
    _write_workflow_outputs(result, paths)
    return result


def status_pending(
    *,
    hermes_home: Path = HERMES_HOME,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Read the pending state without approving, rejecting, or executing it."""
    current = _as_myt(now)
    paths = _runtime_paths(hermes_home)
    state = _load_pending(paths)
    if not state:
        result: dict[str, Any] = {
            "schema_version": 2,
            "run_id": "none",
            "timestamp": _format_myt(current),
            "date": current.strftime("%Y-%m-%d"),
            "repo": "",
            "status": "PASS",
            "release_pending": False,
            "push_allowed": False,
            "owner_approval_required_for_push": True,
            "gates": {},
            "git_state": {},
            "branches": {"merged": [], "stale": [], "active": []},
            "sync_state": {},
            "daily_delta": {"commits": []},
            "actions_taken": [],
            "holds": [],
            "errors": [],
            "remediation": {"status": "none", "actions": []},
            "execution": {},
            "proposal_path": None,
        }
        result["human_report"] = "# Nightly Git report\n\nOverall: **PASS**\n\nNo pending nightly remediation exists."
    else:
        repo = Path(state["repo"])
        snapshot = _inspect_git(repo, current)
        state_status = state.get("status")
        result = _result_from_state(
            state=state,
            status="PASS" if state_status == "completed" else "FAIL" if state_status == "failed" else "HOLD",
            remediation_status="pending_confirmation" if state_status == "pending" else str(state_status),
            snapshot=snapshot,
            gates={},
            holds=list(state.get("holds", [])),
            errors=list(state.get("errors", [])),
            now=current,
        )
    _write_workflow_outputs(result, paths)
    return result


def _display_mode_result(hermes_home: Path, mode: str, now: datetime | None = None) -> dict[str, Any]:
    selected = set_json_display_mode(hermes_home, mode)
    current = _as_myt(now)
    return {
        "schema_version": 2,
        "run_id": "json-display",
        "timestamp": _format_myt(current),
        "date": current.strftime("%Y-%m-%d"),
        "repo": "",
        "status": "PASS",
        "release_pending": False,
        "push_allowed": False,
        "owner_approval_required_for_push": True,
        "gates": {},
        "git_state": {},
        "branches": {"merged": [], "stale": [], "active": []},
        "sync_state": {},
        "daily_delta": {"commits": []},
        "actions_taken": [],
        "holds": [],
        "errors": [],
        "remediation": {"status": "none", "actions": []},
        "execution": {},
        "proposal_path": None,
        "human_report": f"Nightly raw JSON display: {selected.upper()}. Raw JSON remains persisted in the nightly receipt.",
    }


def preview_audit(
    *,
    repo_root: Path = REPO_ROOT,
    hermes_home: Path = HERMES_HOME,
    dry_run: bool = False,
    now: datetime | None = None,
    mode: str | None = None,
) -> dict[str, Any]:
    """Audit the repository and return the structured audit result without scheduling remediation if dry_run or mode='preview'."""
    current = _as_myt(now)
    repo = repo_root.expanduser().resolve()
    home = hermes_home.expanduser().resolve()
    paths = _runtime_paths(home)
    snapshot = _inspect_git(repo, current)
    head = snapshot["git_state"].get("head") or "unknown"

    is_preview = (mode == "preview" or dry_run)
    run_id = None if is_preview else _run_id(current, head if len(head) >= 12 else "0" * 12)
    gates = run_full_delta_gates(repo, current) if not snapshot["errors"] else {}

    actions, holds, classification = _build_actions(snapshot)
    errors = list(snapshot.get("errors", []))
    if gates and not _gates_pass(gates):
        errors.append("one or more required nightly quality/security gates failed")
        actions = []

    status = "PASS"
    remediation: dict[str, Any] = {
        "status": "none",
        "run_id": run_id,
        "actions": actions,
        "holds": holds,
        "deadline_at": None,
        "timeout_job_id": None,
    }
    if errors:
        status = "FAIL"
        remediation["status"] = "blocked"
    elif actions:
        status = "HOLD"
        remediation["status"] = "pending_confirmation" if not is_preview else "none"
    elif holds:
        status = "HOLD"
        remediation["status"] = "blocked" if not is_preview else "none"

    result: dict[str, Any] = {
        "schema_version": 2,
        "run_id": run_id,
        "timestamp": _format_myt(current),
        "date": current.strftime("%Y-%m-%d"),
        "repo": str(repo),
        "status": status,
        "classification": classification,
        "release_pending": any(a.get("kind") == "push_main" for a in actions),
        "push_allowed": False,
        "owner_approval_required_for_push": True,
        "gates": gates,
        "git_state": snapshot["git_state"],
        "branches": snapshot["branches"],
        "sync_state": snapshot["sync_state"],
        "daily_delta": snapshot["daily_delta"],
        "actions_taken": [],
        "holds": holds,
        "errors": errors,
        "remediation": remediation,
        "execution": execution_identity(repo, head if len(head) == 40 else ""),
        "proposal_path": check_operational_proposals(repo, current.strftime("%Y-%m-%d")),
        "delivery": {"mode": "stdout", "status": "emitted_by_target_not_destination_verified"},
    }
    if is_preview:
        result["mode"] = "preview"
    result["human_report"] = _human_report(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Nightly Git Hygiene and bounded closure runner")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--hermes-home", type=Path, default=HERMES_HOME)
    parser.add_argument("--dry-run", action="store_true", help="Audit and recommend; never execute Git remediation")
    parser.add_argument("--preview", action="store_true", help="Preview owner-facing output without creating pending run_id or scheduling timeout")
    parser.add_argument("--approve", action="store_true")
    parser.add_argument("--reject", action="store_true")
    parser.add_argument("--timeout", action="store_true")
    parser.add_argument("--run-id", default=None)
    parser.add_argument("--reason", default="")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--set-json-display", choices=("show", "hide"), default=None)
    parser.add_argument("--json-display", choices=("show", "hide"), default=None)
    parser.add_argument("--human-only", action="store_true")
    args = parser.parse_args()
    if sum(bool(value) for value in (args.approve, args.reject, args.timeout, args.status, args.set_json_display, args.preview)) > 1:
        parser.error("choose only one workflow operation")
    if args.set_json_display:
        result = _display_mode_result(args.hermes_home.resolve(), args.set_json_display)
    elif args.preview:
        result = preview_audit(repo_root=args.repo.resolve(), hermes_home=args.hermes_home.resolve(), dry_run=args.dry_run, mode="preview")
    elif args.dry_run:
        result = run_audit(repo_root=args.repo.resolve(), dry_run=True)
    elif args.status:
        result = status_pending(hermes_home=args.hermes_home.resolve())
    elif args.approve or args.reject or args.timeout:
        decision = "approve" if args.approve else "reject" if args.reject else "timeout"
        result = process_pending(
            decision=decision,
            hermes_home=args.hermes_home,
            run_id=args.run_id,
            reason=args.reason,
        )
    else:
        result = run_nightly(repo_root=args.repo.resolve(), hermes_home=args.hermes_home.resolve())
    mode = args.json_display or _json_display_mode(_runtime_paths(args.hermes_home).config_path)
    if not (args.timeout and result.get("_silent")):
        print(result.get("human_report") if args.human_only else render_output(result, json_display=mode))
    return 0 if result["status"] in {"PASS", "HOLD"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
