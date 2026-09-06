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
import sqlite3
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


def watchdog_execution_identity(repo: Path, audited_head: str) -> dict[str, Any]:
    """Capture the exact secondary executable bytes for this receipt."""
    script_path = Path(__file__).resolve()
    return {
        "script_path": str(script_path),
        "script_sha256": hygiene.sha256_file(script_path),
        "script_size": script_path.stat().st_size,
        "audited_repo": str(repo),
        "audited_repo_head": audited_head,
    }


def _find_primary_run_for_watchdog(
    paths: hygiene.RuntimePaths,
    now: datetime,
) -> tuple[str | None, dict[str, Any] | None]:
    """Find exactly one receipt in the prior 23:55 scheduler window.

    History filename and mtime are mutable storage metadata, not scheduler
    provenance.  A watchdog must therefore never fall back to another date or
    let a newer manual receipt mask the scheduled window's primary.
    """
    now_myt = hygiene._as_myt(now)
    target_date = now_myt.date() - timedelta(days=1) if now_myt.hour < 12 else now_myt.date()
    window_start, window_end = hygiene.primary_scheduled_window(target_date)
    if not paths.history_dir.is_dir():
        return None, None

    candidates: list[tuple[dict[str, Any], datetime]] = []
    for receipt_path in paths.history_dir.glob("*.json"):
        if receipt_path.name == "none.json":
            continue
        try:
            data = json.loads(receipt_path.read_text(encoding="utf-8"))
            run_id = data.get("run_id")
            timestamp = data.get("timestamp")
            if not hygiene._is_valid_run_id(run_id) or not isinstance(timestamp, str):
                continue
            receipt_at = datetime.strptime(timestamp, "%Y-%m-%d %H:%M:%S MYT").replace(tzinfo=MYT)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
        if window_start <= receipt_at <= window_end:
            candidates.append((data, receipt_at))

    if len(candidates) != 1:
        return None, None
    primary, _receipt_at = candidates[0]
    return primary["run_id"], primary


def _verified_repo_state(snapshot: dict[str, Any]) -> tuple[str, list[str]]:
    """Return CLEAN+SYNCED only from explicit successful current inspection."""
    errors = list(snapshot.get("errors", []))
    if errors:
        return "UNKNOWN", errors
    git_state = snapshot.get("git_state", {})
    origin = snapshot.get("sync_state", {}).get("origin")
    if not isinstance(origin, dict):
        return "UNKNOWN", ["origin/main synchronization evidence is unavailable"]
    if git_state.get("branch") != "main":
        return "NOT CLEAN", [f"expected main branch, found {git_state.get('branch')!r}"]
    if not git_state.get("is_clean", False):
        return "NOT CLEAN", ["working tree is not clean"]
    if origin.get("ahead") != 0 or origin.get("behind") != 0:
        return "NOT CLEAN", ["local main is not synchronized with origin/main"]
    remote_head = origin.get("remote_head")
    tracking_head = origin.get("tracking_head")
    if not remote_head or remote_head != tracking_head:
        return "UNKNOWN", ["origin/main remote/tracking identity is missing or disagrees"]
    return "CLEAN+SYNCED", []


def _primary_scheduler_execution_evidence(hermes_home: Path, primary: dict[str, Any]) -> dict[str, str]:
    """Verify the receipt's scheduler binding against the immutable ledger."""
    claimed = primary.get("scheduler_execution")
    if not isinstance(claimed, dict):
        return {"status": "UNKNOWN", "reason": "primary receipt has no scheduler execution binding"}
    execution_id = claimed.get("execution_id")
    if claimed.get("status") != "SCHEDULER_CLAIMED" or not isinstance(execution_id, str):
        return {"status": "UNKNOWN", "reason": "primary receipt scheduler binding is incomplete"}
    db_path = hermes_home / "cron" / "executions.db"
    if not db_path.is_file():
        return {"status": "UNKNOWN", "reason": "cron execution ledger is missing"}
    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            row = conn.execute(
                "SELECT job_id, source, status FROM executions WHERE id=?", (execution_id,)
            ).fetchone()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        return {"status": "UNKNOWN", "reason": f"cron execution ledger unreadable: {exc}"}
    if row is None:
        return {"status": "UNKNOWN", "reason": "bound primary scheduler execution is absent"}
    job_id, source, status = row
    if job_id != hygiene.PRIMARY_NIGHTLY_JOB_ID or source != "builtin":
        return {"status": "UNKNOWN", "reason": "bound execution is not the built-in primary job"}
    if status not in {"claimed", "running", "completed", "failed"}:
        return {"status": "UNKNOWN", "reason": "bound execution has invalid ledger state"}
    return {"status": "VERIFIED", "reason": "primary receipt is bound to built-in scheduler execution"}


def _primary_delivery_evidence(hermes_home: Path, primary_at: datetime) -> dict[str, str]:
    """State the scheduler delivery evidence without pretending it proves receipt."""
    jobs_path = hermes_home / "cron" / "jobs.json"
    if not jobs_path.is_file():
        return {"status": "UNKNOWN", "reason": "no matching primary scheduler record"}
    try:
        raw = json.loads(jobs_path.read_text(encoding="utf-8"))
        jobs = raw.get("jobs", []) if isinstance(raw, dict) else []
        job = next((item for item in jobs if item.get("id") == hygiene.PRIMARY_NIGHTLY_JOB_ID), None)
        if not isinstance(job, dict) or not isinstance(job.get("last_run_at"), str):
            return {"status": "UNKNOWN", "reason": "no matching primary scheduler record"}
        last_run = datetime.fromisoformat(job["last_run_at"]).astimezone(MYT)
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return {"status": "UNKNOWN", "reason": "primary scheduler record is unreadable"}
    window_start, window_end = hygiene.primary_scheduled_window(primary_at.date())
    if not window_start <= last_run <= window_end:
        return {"status": "UNKNOWN", "reason": "primary scheduler record does not match receipt window"}
    if job.get("last_status") != "ok":
        return {"status": "FAILED", "reason": "primary scheduler reports a non-ok run"}
    if job.get("last_delivery_error"):
        return {"status": "FAILED", "reason": "primary scheduler reports delivery error"}
    return {
        "status": "ATTEMPTED_NO_ERROR",
        "reason": "scheduler reports matching ok run with no delivery error; recipient receipt remains unverified",
    }


def _failed_publish_state_is_resumable(
    paths: hygiene.RuntimePaths,
    primary_run_id: str | None,
) -> bool:
    """True when a failed plan for this run died inside publication and may resume."""
    if not primary_run_id:
        return False
    try:
        pending = hygiene._load_pending(paths)
    except Exception:
        return False
    return bool(
        pending
        and pending.get("run_id") == primary_run_id
        and pending.get("status") in {"failed", "blocked"}
        and hygiene._failed_state_is_publish_resumable(pending)
    )


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
        "delivery_evidence": {"status": "UNKNOWN", "reason": "no matching primary scheduler record"},
        "secondary_result": "PASS",
        "errors": [],
        "details": {},
    }

    # Inspect current repository state.  Unknown inspection evidence cannot
    # inherit the healthy numeric defaults used by ordinary dict.get calls.
    snapshot = hygiene._inspect_git(repo, current)
    repo_state, repo_errors = _verified_repo_state(snapshot)
    watchdog_result["execution"] = watchdog_execution_identity(
        repo, str(snapshot.get("git_state", {}).get("head") or "unknown"),
    )
    watchdog_result["final_repo_state"] = repo_state
    watchdog_result["errors"].extend(repo_errors)
    is_clean_and_synced = repo_state == "CLEAN+SYNCED"

    # State H: Primary missing entirely
    if not primary_data or not primary_run_id:
        watchdog_result["secondary_result"] = "FAIL"
        watchdog_result["errors"].append(f"No primary 23:55 Nightly run found for date {target_date_str}")
        _format_and_record_watchdog(watchdog_result, paths)
        return watchdog_result

    primary_at = datetime.strptime(primary_data["timestamp"], "%Y-%m-%d %H:%M:%S MYT").replace(tzinfo=MYT)
    scheduler_evidence = _primary_scheduler_execution_evidence(Path(hermes_home), primary_data)
    watchdog_result["details"]["primary_scheduler_execution"] = scheduler_evidence
    delivery_evidence = _primary_delivery_evidence(Path(hermes_home), primary_at)
    watchdog_result["delivery_evidence"] = delivery_evidence
    watchdog_result["final_delivery"] = delivery_evidence["status"]
    primary_status = primary_data.get("status")
    remediation = primary_data.get("remediation", {})
    rem_status = remediation.get("status", "none")
    pending_state = hygiene._load_pending(paths)

    # Check if there is a pending remediation file on disk
    if pending_state and pending_state.get("run_id") == primary_run_id:
        pending_status = pending_state.get("status")
        if pending_status == "completed":
            # Already remediated (e.g. owner APPROVE executed). Verify only;
            # never re-execute a completed chain (single-mutation rule).
            watchdog_result["owner_decision"] = (
                "APPROVE" if pending_state.get("decision") == "approve" else "NO RESPONSE"
            )
            watchdog_result["continuation_state"] = (
                "FIRED" if pending_state.get("decision") == "timeout" else "NOT REQUIRED"
            )
            watchdog_result["primary_remediation"] = "COMPLETE"
            if is_clean_and_synced:
                watchdog_result["secondary_result"] = "PASS"
                watchdog_result["secondary_recovery"] = "NONE"
            else:
                watchdog_result["secondary_result"] = "HOLD"
                watchdog_result["errors"].append("Repo is not clean and synced despite completed remediation")
            _format_and_record_watchdog(watchdog_result, paths)
            return watchdog_result
        if pending_status == "rejected":
            # Owner rejection is terminal. Preserve it; never execute.
            watchdog_result["owner_decision"] = "REJECT"
            watchdog_result["secondary_result"] = "HOLD"
            _format_and_record_watchdog(watchdog_result, paths)
            return watchdog_result
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
                    final_state, final_errors = _verified_repo_state(final_snap)
                    watchdog_result["final_repo_state"] = final_state
                    watchdog_result["errors"].extend(final_errors)
                    if final_state != "CLEAN+SYNCED":
                        watchdog_result["secondary_result"] = "FAIL"
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
        # State A: a historical PASS is credible only if fresh inspection has
        # explicit current repo evidence.  Never downgrade a failed inspection
        # into HOLD/PASS merely because the prior receipt was green.
        if (
            is_clean_and_synced
            and scheduler_evidence["status"] == "VERIFIED"
            and delivery_evidence["status"] != "FAILED"
        ):
            watchdog_result["secondary_result"] = "PASS"
            watchdog_result["secondary_recovery"] = "NONE"
        else:
            watchdog_result["secondary_result"] = "FAIL"
            if scheduler_evidence["status"] != "VERIFIED":
                watchdog_result["errors"].append(scheduler_evidence["reason"])
            if delivery_evidence["status"] == "FAILED":
                watchdog_result["errors"].append(delivery_evidence["reason"])
            if not is_clean_and_synced:
                watchdog_result["errors"].append("current repository verification failed despite primary PASS")

    elif primary_status == "HOLD":
        # Check if it was safe residue that was completed earlier
        if rem_status == "completed":
            watchdog_result["primary_remediation"] = "COMPLETE"
            watchdog_result["secondary_result"] = "PASS" if is_clean_and_synced else "HOLD"
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
        elif not dry_run and _failed_publish_state_is_resumable(paths, primary_run_id):
            # Same-run publication resume (reuses branch/PR, never duplicates).
            rec_res = hygiene.process_pending(
                decision="timeout",
                hermes_home=hermes_home,
                run_id=primary_run_id,
                now=current,
            )
            if rec_res.get("status") == "PASS":
                watchdog_result["secondary_recovery"] = "PUBLISH CHAIN RECOVERED SAME RUN"
                watchdog_result["secondary_result"] = "RECOVERED"
            else:
                watchdog_result["secondary_result"] = "HOLD" if rec_res.get("status") == "HOLD" else "FAIL"
                watchdog_result["errors"].extend(rec_res.get("errors", []))
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
        f"Delivery evidence: {result['delivery_evidence']['reason']}",
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
