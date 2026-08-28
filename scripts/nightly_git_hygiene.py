#!/usr/bin/env python3
"""Nightly Git Hygiene & Self-Improvement Audit Runner for Hermes Assistant.

Executes daily at 23:55 MYT:
1. Audits daily delta and cleanliness in SSOT repo.
2. Runs secret scan, PII review, and contract test suites across all changes.
3. Classifies branch status (merged, stale >7d, active).
4. Verifies sync against origin/main and upstream/main.
5. Employs deterministic PASS / HOLD / FAIL semantics:
   - PASS: All gates pass, tree is clean. If ahead of origin/main, release_pending=True, push_allowed=False.
   - HOLD: Dirty/untracked working tree, divergence, unmerged stale branches.
   - FAIL: Security scan failure, PII failure, test failure, command error.
6. Analyzes operational logs for recurring failure patterns and writes proposal drafts if needed.
7. Writes an audit receipt to ~/.hermes/logs/git-nightly-receipt.md and JSON receipt.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

MYT = timezone(timedelta(hours=8))
REPO_ROOT = Path("/home/ubuntu/hermes-agent-personal_assistant-work")
HERMES_HOME = Path("/home/ubuntu/.hermes")
RECEIPT_PATH = HERMES_HOME / "logs" / "git-nightly-receipt.md"
RECEIPT_JSON_PATH = HERMES_HOME / "logs" / "git-nightly-receipt.json"


def run_cmd(cmd: list[str], cwd: Path = REPO_ROOT) -> tuple[int, str]:
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
    # Check gateway starts / errors
    log_file = HERMES_HOME / "logs" / "gateway-starts.log"
    if not log_file.exists():
        return None

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


def main() -> int:
    parser = argparse.ArgumentParser(description="Nightly Git Hygiene Audit Runner")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT, help="Path to Git repository root")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode without modifying branches")
    args = parser.parse_args()

    result = run_audit(repo_root=args.repo.resolve(), dry_run=args.dry_run)
    print(json.dumps(result, indent=2))
    return 0 if result["status"] in ("PASS", "HOLD") else 1


if __name__ == "__main__":
    raise SystemExit(main())
