#!/usr/bin/env python3
"""Hermes Nightly Git 01:55 MYT Secondary Closure Verification & Recovery Watchdog.

Runs deterministically at 01:55 MYT via Hermes cron (no_agent=True).
Inspects the preceding 23:55 MYT primary Nightly Git run, verifies whether
all actions/continuations/sync completed correctly, and safely recovers
the same run if deterministic remediation is required.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

# Import shared functions from nightly_git_hygiene
SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import nightly_git_hygiene as hygiene

REPO_ROOT = hygiene.REPO_ROOT
HERMES_HOME = hygiene.HERMES_HOME
MYT = hygiene.MYT


def _find_primary_run_for_watchdog(
    paths: hygiene.RuntimePaths,
    now: datetime,
) -> tuple[str | None, dict[str, Any] | None]:
    """Find the exact primary 23:55 run from the previous evening.

    If watchdog runs at 01:55 on Day D, the primary run was at 23:55 on Day D-1.
    We look for the latest natural run in the history directory matching Day D-1,
    or the latest overall run before now.
    """
    now_myt = hygiene._as_myt(now)
    # Primary target date is previous calendar day if now is early morning (e.g. 01:55)
    if now_myt.hour < 12:
        target_date_str = (now_myt.date() - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        target_date_str = now_myt.date().strftime("%Y-%m-%d")

    history_dir = paths.history_dir
    if not history_dir.is_dir():
        return None, None

    candidate_files = []
    for f in history_dir.glob("*.json"):
        if f.name == "none.json":
            continue
        candidate_files.append(f)

    # Sort descending by mtime / filename
    candidate_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    # First pass: find run with matching target date in JSON payload
    for cf in candidate_files:
        try:
            data = json.loads(cf.read_text(encoding="utf-8"))
            if data.get("date") == target_date_str:
                return data.get("run_id"), data
        except Exception:
            continue

    # Second pass: if target date not found, take the most recent history run
    for cf in candidate_files:
        try:
            data = json.loads(cf.read_text(encoding="utf-8"))
            if data.get("run_id"):
                return data.get("run_id"), data
        except Exception:
            continue

    return None, None


def run_watchdog(
    *,
    repo_root: Path = REPO_ROOT,
    hermes_home: Path = HERMES_HOME,
    now: datetime | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    current = hygiene._as_myt(now)
    paths = hygiene._runtime_paths(hermes_home)
    repo = Path(repo_root).resolve()

    primary_run_id, primary_data = _find_primary_run_for_watchdog(paths, current)
    target_date_str = (current.date() - timedelta(days=1) if current.hour < 12 else current.date()).strftime("%Y-%m-%d")

    # Initial state
    watchdog_result: dict[str, Any] = {
        "schema_version": 2,
        "watchdog_execution_at": hygiene._format_myt(current),
        "primary_date": target_date_str,
        "primary_run_id": primary_run_id,
        "primary_status": primary_data.get("status") if primary_data else "MISSING",
        "owner_decision": "NOT REQUIRED",
        "continuation_state": "NOT REQUIRED",
        "primary_remediation": "NONE",
        "secondary_recovery": "NONE",
        "protected_publication": "N/A",
        "final_repo_state": "UNKNOWN",
        "final_delivery": "UNKNOWN",
        "secondary_result": "PASS",
        "errors": [],
        "details": {},
    }

    # Inspect current repository state
    snapshot = hygiene._inspect_git(repo, current)
    origin_sync = snapshot.get("sync_state", {}).get("origin", {})
    is_clean = snapshot.get("git_state", {}).get("is_clean", False)
    ahead = origin_sync.get("ahead", 0)
    behind = origin_sync.get("behind", 0)
    is_synced = (ahead == 0 and behind == 0)

    watchdog_result["final_repo_state"] = "CLEAN+SYNCED" if (is_clean and is_synced) else "NOT CLEAN"

    # State H: Primary missing entirely
    if not primary_data or not primary_run_id:
        watchdog_result["secondary_result"] = "FAIL"
        watchdog_result["errors"].append(f"No primary 23:55 Nightly run found for date {target_date_str}")
        _format_and_record_watchdog(watchdog_result, paths)
        return watchdog_result

    primary_status = primary_data.get("status")
    remediation = primary_data.get("remediation", {})
    rem_status = remediation.get("status", "none")
    pending_state = hygiene._load_pending(paths)

    # Check if there is a pending remediation file on disk
    if pending_state and pending_state.get("run_id") == primary_run_id:
        # Check AFK / timeout status
        deadline_str = pending_state.get("deadline_at")
        deadline = hygiene._parse_iso_datetime(deadline_str) if deadline_str else None
        watchdog_result["owner_decision"] = "NO RESPONSE"
        watchdog_result["continuation_state"] = "PENDING"

        if deadline and current >= deadline:
            # The 30m window expired. Has it fired?
            if not dry_run:
                # Recover/resume the same run
                rec_res = hygiene.process_pending(
                    decision="timeout",
                    hermes_home=hermes_home,
                    run_id=primary_run_id,
                    now=current,
                )
                if rec_res.get("status") == "PASS":
                    watchdog_result["continuation_state"] = "FIRED"
                    watchdog_result["secondary_recovery"] = "AFK AUTOFIX COMPLETED VIA WATCHDOG"
                    watchdog_result["secondary_result"] = "PASS"
                    # Re-inspect git
                    final_snap = hygiene._inspect_git(repo, current)
                    fin_origin = final_snap.get("sync_state", {}).get("origin", {})
                    fin_clean = final_snap.get("git_state", {}).get("is_clean", False)
                    watchdog_result["final_repo_state"] = "CLEAN+SYNCED" if (fin_clean and fin_origin.get("ahead") == 0 and fin_origin.get("behind") == 0) else "NOT CLEAN"
                else:
                    watchdog_result["secondary_result"] = "HOLD" if rec_res.get("status") == "HOLD" else "FAIL"
                    watchdog_result["errors"].extend(rec_res.get("errors", []))
            else:
                watchdog_result["secondary_recovery"] = "DRY RUN - WOULD EXECUTE TIMEOUT AUTOFIX"
                watchdog_result["secondary_result"] = "HOLD"
        else:
            watchdog_result["continuation_state"] = "IN PROGRESS"
            watchdog_result["secondary_result"] = "HOLD"

    elif primary_status == "PASS":
        # State A: Primary PASS
        # Verify repo is clean + synced
        if is_clean and is_synced:
            watchdog_result["secondary_result"] = "PASS"
            watchdog_result["secondary_recovery"] = "NONE"
        else:
            watchdog_result["secondary_result"] = "HOLD"
            watchdog_result["errors"].append("Repo is not clean and synced despite primary PASS")

    elif primary_status == "HOLD":
        # Check if it was safe residue that was completed earlier
        if rem_status == "completed":
            watchdog_result["primary_remediation"] = "COMPLETE"
            watchdog_result["secondary_result"] = "PASS" if (is_clean and is_synced) else "HOLD"
        elif rem_status == "rejected":
            watchdog_result["owner_decision"] = "REJECT"
            watchdog_result["secondary_result"] = "HOLD"
        elif rem_status == "blocked":
            # State E / G: Ambiguous or blocked
            # Check if it was blocked by transient fetch error or HEAD.json
            p_errors = primary_data.get("errors", [])
            is_fetch_error = any("git fetch" in str(e) and "cannot lock ref" in str(e) for e in p_errors)
            has_head_receipt = any("HEAD.json" in str(h) for h in primary_data.get("holds", []))

            if (is_fetch_error or has_head_receipt) and not dry_run:
                # State F: Transient failure recovery
                # Re-run inspection or remediation safely
                recovery_res = hygiene.run_nightly(
                    repo_root=repo,
                    hermes_home=hermes_home,
                    now=current,
                )
                if recovery_res.get("status") in ("PASS", "HOLD"):
                    watchdog_result["secondary_recovery"] = "TRANSIENT ERROR RECOVERED"
                    watchdog_result["secondary_result"] = "RECOVERED" if recovery_res.get("status") == "PASS" else "HOLD"
                else:
                    watchdog_result["secondary_result"] = "FAIL"
                    watchdog_result["errors"].extend(recovery_res.get("errors", []))
            else:
                watchdog_result["secondary_result"] = "HOLD"
        else:
            watchdog_result["secondary_result"] = "HOLD"

    elif primary_status == "FAIL":
        p_errors = primary_data.get("errors", [])
        is_transient = any("cannot lock ref" in str(e) or "HEAD.json" in str(e) for e in p_errors)
        if is_transient and not dry_run:
            recovery_res = hygiene.run_nightly(
                repo_root=repo,
                hermes_home=hermes_home,
                now=current,
            )
            if recovery_res.get("status") == "PASS":
                watchdog_result["secondary_recovery"] = "TRANSIENT PRIMARY FAIL RECOVERED"
                watchdog_result["secondary_result"] = "RECOVERED"
            else:
                watchdog_result["secondary_result"] = "FAIL"
                watchdog_result["errors"].extend(recovery_res.get("errors", []))
        else:
            # Gate failure (Secret/PII/Contract) - do not bulldoze
            watchdog_result["secondary_result"] = "FAIL"
            watchdog_result["errors"].extend(p_errors)

    _format_and_record_watchdog(watchdog_result, paths)
    return watchdog_result


def _format_and_record_watchdog(result: dict[str, Any], paths: hygiene.RuntimePaths) -> None:
    lines = [
        f"# Nightly Closure Verification — {result['primary_date']}",
        "",
        f"Primary run: `{result['primary_run_id']}`",
        f"Primary result: {result['primary_status']}",
        f"Owner decision: {result['owner_decision']}",
        f"30m continuation: {result['continuation_state']}",
        f"Primary remediation: {result['primary_remediation']}",
        f"Secondary recovery: {result['secondary_recovery']}",
        f"Protected publication: {result['protected_publication']}",
        f"Final repo: {result['final_repo_state']}",
        f"Final delivery: {result['final_delivery']}",
        f"Secondary result: **{result['secondary_result']}**",
    ]
    if result.get("errors"):
        lines.append("")
        lines.append("Errors / notes:")
        for err in result["errors"]:
            lines.append(f"- ⚠️ {err}")

    report = "\n".join(lines)
    result["human_report"] = report

    # Persist watchdog receipt
    watchdog_receipt_path = paths.logs_dir / "git-nightly-watchdog-receipt.json"
    watchdog_md_path = paths.logs_dir / "git-nightly-watchdog-receipt.md"
    try:
        hygiene._atomic_json(watchdog_receipt_path, {k: v for k, v in result.items() if k != "human_report"})
        hygiene._atomic_text(watchdog_md_path, report + "\n")
    except Exception:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Nightly Git Closure Watchdog (01:55 MYT)")
    parser.add_argument("--repo", type=Path, default=REPO_ROOT)
    parser.add_argument("--hermes-home", type=Path, default=HERMES_HOME)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--human-only", action="store_true")
    args = parser.parse_args()

    result = run_watchdog(
        repo_root=args.repo.resolve(),
        hermes_home=args.hermes_home.resolve(),
        dry_run=args.dry_run,
    )
    print(result.get("human_report", ""))
    return 0 if result.get("secondary_result") in ("PASS", "RECOVERED", "HOLD") else 1


if __name__ == "__main__":
    sys.exit(main())
