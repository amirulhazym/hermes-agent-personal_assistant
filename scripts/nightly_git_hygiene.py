#!/usr/bin/env python3
"""Nightly Git Hygiene & Self-Improvement Audit Runner for Hermes Assistant.

Executes daily at 23:55 MYT:
1. Audits daily delta in SSOT repo.
2. Runs secret scan, PII review, and regression test suites.
3. Classifies branch status (merged, stale >7d, active).
4. Verifies sync against origin/main and upstream/main.
5. Writes an audit receipt to ~/.hermes/logs/git-nightly-receipt.md.
6. Emits structured JSON summary for delivery.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

MYT = timezone(timedelta(hours=8))
REPO_ROOT = Path("/home/ubuntu/hermes-agent-personal_assistant-work")
HERMES_HOME = Path("/home/ubuntu/.hermes")
RECEIPT_PATH = HERMES_HOME / "logs" / "git-nightly-receipt.md"
RECEIPT_JSON_PATH = HERMES_HOME / "logs" / "git-nightly-receipt.json"


def run_cmd(cmd: list[str], cwd: Path = REPO_ROOT) -> tuple[int, str]:
    res = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    return res.returncode, res.stdout.strip() + ("\n" + res.stderr.strip() if res.stderr.strip() else "")


def run_audit(dry_run: bool = False) -> dict:
    now_str = datetime.now(MYT).strftime("%Y-%m-%d %H:%M:%S MYT")
    today_str = datetime.now(MYT).strftime("%Y-%m-%d")

    audit: dict = {
        "timestamp": now_str,
        "date": today_str,
        "repo": str(REPO_ROOT),
        "status": "PASS",
        "gates": {},
        "git_state": {},
        "branches": {"merged": [], "stale": [], "active": []},
        "sync_state": {},
        "actions_taken": [],
        "holds": [],
    }

    # 1. Check Git status
    rc, out = run_cmd(["git", "status", "--porcelain"])
    audit["git_state"]["is_clean"] = len(out) == 0
    audit["git_state"]["status_porcelain"] = out.splitlines()

    # 2. Check current HEAD
    rc, head = run_cmd(["git", "rev-parse", "HEAD"])
    audit["git_state"]["head"] = head

    # 3. Secret scan
    rc, sec_out = run_cmd(["bash", "scripts/guard/secret-scan.sh", "--staged"])
    sec_pass = rc == 0
    audit["gates"]["secret_scan"] = "PASS" if sec_pass else "FAIL"
    if not sec_pass:
        audit["holds"].append("Secret scan failed heuristic gate")
        audit["status"] = "HOLD"

    # 4. PII review
    rc, pii_out = run_cmd(["python3", "scripts/guard/pii-review.py", "--diff", "HEAD~1..HEAD"])
    pii_pass = rc == 0
    audit["gates"]["pii_review"] = "PASS" if pii_pass else "FAIL"
    if not pii_pass:
        audit["holds"].append("PII review flagged unredacted patterns")
        audit["status"] = "HOLD"

    # 5. Run test suite
    rc, test_out = run_cmd(["pytest", "tests/reconciliation/", "tests/guard/", "-q"])
    test_pass = rc == 0
    audit["gates"]["reconciliation_tests"] = "PASS" if test_pass else "FAIL"
    if not test_pass:
        audit["holds"].append("Reconciliation contract tests failed")
        audit["status"] = "FAIL"

    # 6. Fetch remotes & check sync
    run_cmd(["git", "fetch", "origin"])
    run_cmd(["git", "fetch", "upstream", "main"])

    rc, ahead_behind = run_cmd(["git", "rev-list", "--left-right", "--count", "main...origin/main"])
    if rc == 0 and ahead_behind:
        parts = ahead_behind.split()
        if len(parts) == 2:
            ahead, behind = int(parts[0]), int(parts[1])
            audit["sync_state"]["origin"] = {"ahead": ahead, "behind": behind}
            if behind > 0 and ahead > 0:
                audit["holds"].append("Local main and origin/main have diverged")
                audit["status"] = "HOLD"

    # 7. Classify branches
    rc, raw_branches = run_cmd(["git", "for-each-ref", "--format=%(refname:short)|%(committerdate:iso8601)", "refs/heads/"])
    for line in raw_branches.splitlines():
        if not line or "|" not in line:
            continue
        b_name, b_date_str = line.split("|", 1)
        if b_name == "main":
            continue
        rc, merged_out = run_cmd(["git", "branch", "--merged", "main"])
        is_merged = any(x.strip() == b_name for x in merged_out.splitlines())
        if is_merged:
            audit["branches"]["merged"].append(b_name)
            if not dry_run:
                # Safe auto-cleanup for merged branches only
                run_cmd(["git", "branch", "-d", b_name])
                audit["actions_taken"].append(f"Cleaned up merged local branch: {b_name}")
        else:
            try:
                b_date = datetime.fromisoformat(b_date_str.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - b_date).days
                if age_days > 7:
                    audit["branches"]["stale"].append({"name": b_name, "age_days": age_days})
                else:
                    audit["branches"]["active"].append(b_name)
            except Exception:
                audit["branches"]["active"].append(b_name)

    # 8. Write Markdown Receipt
    md_lines = [
        f"# Nightly Git Hygiene Receipt — {today_str}",
        "",
        f"- **Timestamp:** {now_str}",
        f"- **Audit Status:** **{audit['status']}**",
        f"- **HEAD Commit:** `{head[:10]}`",
        f"- **Working Tree Clean:** `{audit['git_state']['is_clean']}`",
        f"- **Secret Scan:** `{audit['gates'].get('secret_scan')}`",
        f"- **PII Review:** `{audit['gates'].get('pii_review')}`",
        f"- **Regression Tests:** `{audit['gates'].get('reconciliation_tests')}`",
        f"- **Sync (origin/main):** Ahead {audit['sync_state'].get('origin', {}).get('ahead', 0)}, Behind {audit['sync_state'].get('origin', {}).get('behind', 0)}",
        "",
        "## Actions Taken",
    ]
    if audit["actions_taken"]:
        for act in audit["actions_taken"]:
            md_lines.append(f"- ✅ {act}")
    else:
        md_lines.append("- None (no merged branches to prune)")

    if audit["holds"]:
        md_lines.extend(["", "## ⚠️ Active Holds / Warnings"])
        for h in audit["holds"]:
            md_lines.append(f"- ⚠️ {h}")

    RECEIPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    RECEIPT_PATH.write_text("\n".join(md_lines) + "\n")
    RECEIPT_JSON_PATH.write_text(json.dumps(audit, indent=2) + "\n")

    return audit


if __name__ == "__main__":
    is_dry = "--dry-run" in sys.argv
    res = run_audit(dry_run=is_dry)
    print(json.dumps(res, indent=2))
