#!/usr/bin/env python3
"""Read-only verifier for a scheduled no-agent executable chain.

This verifier keeps four identities separate:

* the repository HEAD audited by the nightly script;
* the candidate Git blobs for the wrapper and target;
* the runtime files selected by the cron job;
* the implementation identity recorded by the execution receipt.

It never writes, executes the wrapper, changes Git refs, or changes scheduler
state. The CLI returns 0 only when the complete chain and execution receipt
match the supplied candidate SHA.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import stat
import subprocess
from pathlib import Path
from typing import Any


COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _inside(path: Path, root: Path) -> bool:
    resolved = path.resolve(strict=False)
    root_resolved = root.resolve(strict=False)
    return resolved != root_resolved and root_resolved in resolved.parents


def _git_blob(repo_root: Path, commit_sha: str, source: str) -> bytes | None:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"{commit_sha}:{source}"],
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _load_job(jobs_path: Path, job_id: str) -> dict[str, Any] | None:
    data = json.loads(jobs_path.read_text(encoding="utf-8"))
    jobs = data.get("jobs", []) if isinstance(data, dict) else data
    if not isinstance(jobs, list):
        raise ValueError("jobs JSON does not contain a list")
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if str(job.get("id", "")) == job_id or str(job.get("job_id", "")) == job_id:
            return job
    return None


def _resolve_job_script(job: dict[str, Any], scripts_root: Path) -> Path:
    script = job.get("script")
    if not isinstance(script, str) or not script.strip():
        raise ValueError("job script field is missing")
    raw = Path(script)
    resolved = raw.resolve(strict=False) if raw.is_absolute() else (scripts_root / raw).resolve(strict=False)
    if not _inside(resolved, scripts_root):
        raise ValueError(f"job script escapes allowed scripts root: {resolved}")
    return resolved


def _parse_wrapper(wrapper_path: Path, scripts_root: Path) -> tuple[Path, list[str]]:
    if not wrapper_path.is_file() or wrapper_path.is_symlink():
        raise ValueError(f"wrapper is not a regular file: {wrapper_path}")
    if not (wrapper_path.stat().st_mode & stat.S_IXUSR):
        raise ValueError(f"wrapper is not owner-executable: {wrapper_path}")
    commands: list[list[str]] = []
    for line in wrapper_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        try:
            tokens = shlex.split(stripped)
        except ValueError as exc:
            raise ValueError(f"wrapper shell syntax is invalid: {exc}") from exc
        if tokens and tokens[0] == "exec":
            commands.append(tokens)
    if len(commands) != 1 or len(commands[0]) < 2:
        raise ValueError("wrapper must contain exactly one executable exec command")
    tokens = commands[0]
    raw_target = Path(tokens[1])
    target = raw_target.resolve(strict=False) if raw_target.is_absolute() else (wrapper_path.parent / raw_target).resolve(strict=False)
    if not _inside(target, scripts_root):
        raise ValueError(f"wrapper target escapes allowed scripts root: {target}")
    return target, tokens[2:]


def _manifest_entries(manifest_path: Path) -> dict[str, dict[str, Any]]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise ValueError("manifest schema_version must be 1")
    entries = data.get("entries")
    if not isinstance(entries, list):
        raise ValueError("manifest entries must be a list")
    result: dict[str, dict[str, Any]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("source"), str):
            raise ValueError("manifest contains an invalid row")
        result[entry["source"]] = entry
    return result


def _read_receipt(receipt_path: Path) -> dict[str, Any]:
    text = receipt_path.read_text(encoding="utf-8")
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char != "{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and ("git_state" in value or "execution" in value):
            return value
    receipt: dict[str, Any] = {}
    head_match = re.search(r"(?:HEAD Commit|Audited Repository HEAD):\s*`?([0-9a-f]{10,40})", text)
    script_match = re.search(r"Executable Script:\s*`([^`]+)`", text)
    sha_match = re.search(r"Executable SHA-256:\s*`([0-9a-f]{64})`", text)
    if head_match:
        receipt["git_state"] = {"head": head_match.group(1)}
    if script_match or sha_match:
        receipt["execution"] = {
            "script_path": script_match.group(1) if script_match else None,
            "script_sha256": sha_match.group(1) if sha_match else None,
        }
    return receipt


def _candidate_blob_hash(repo_root: Path, candidate_sha: str, source: str) -> str | None:
    blob = _git_blob(repo_root, candidate_sha, source)
    return hashlib.sha256(blob).hexdigest() if blob is not None else None


def verify(
    *,
    repo_root: Path,
    candidate_sha: str,
    jobs_path: Path,
    manifest_path: Path,
    receipt_path: Path,
    scripts_root: Path,
    job_id: str,
    target_source: str,
) -> dict[str, Any]:
    """Return a deterministic, read-only executable-chain verification result."""
    result: dict[str, Any] = {
        "status": "FAIL",
        "candidate_sha": candidate_sha,
        "job_id": job_id,
        "target_source": target_source,
        "candidate": {},
        "job": {},
        "chain": {},
        "manifest": {},
        "receipt": {
            "audited_repo_head": None,
            "execution_script_path": None,
            "execution_script_sha256": None,
        },
        "verdicts": {},
        "holds": [],
        "errors": [],
    }

    if not COMMIT_RE.fullmatch(candidate_sha):
        result["errors"].append("candidate SHA is not a full 40-character commit SHA")
        return result

    wrapper_source = "scripts/nightly_git_hygiene_wrapper.sh"
    candidate_target_hash = _candidate_blob_hash(repo_root, candidate_sha, target_source)
    candidate_wrapper_hash = _candidate_blob_hash(repo_root, candidate_sha, wrapper_source)
    result["candidate"] = {
        "target_source": target_source,
        "target_sha256": candidate_target_hash,
        "wrapper_source": wrapper_source,
        "wrapper_sha256": candidate_wrapper_hash,
    }
    if candidate_target_hash is None:
        result["errors"].append(f"candidate blob absent: {target_source}")
    if candidate_wrapper_hash is None:
        result["errors"].append(f"candidate blob absent: {wrapper_source}")

    try:
        job = _load_job(jobs_path, job_id)
        if job is None:
            raise ValueError(f"job not found: {job_id}")
        result["job"] = {
            "id": job.get("id", job.get("job_id")),
            "name": job.get("name"),
            "enabled": job.get("enabled"),
            "no_agent": job.get("no_agent"),
            "script": job.get("script"),
            "workdir": job.get("workdir"),
        }
        if job.get("no_agent") is not True:
            result["errors"].append("job is not no_agent=true")
        wrapper_path = _resolve_job_script(job, scripts_root)
        wrapper_target, wrapper_args = _parse_wrapper(wrapper_path, scripts_root)
        target_path = wrapper_target
        result["chain"] = {
            "scripts_root": str(scripts_root.resolve()),
            "wrapper_path": str(wrapper_path),
            "wrapper_args": wrapper_args,
            "wrapper_target_path": str(target_path),
            "wrapper_sha256": sha256_file(wrapper_path),
            "target_exists": target_path.is_file() and not target_path.is_symlink(),
            "target_sha256": sha256_file(target_path) if target_path.is_file() and not target_path.is_symlink() else None,
        }
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result["errors"].append(str(exc))

    chain = result["chain"]
    try:
        entries = _manifest_entries(manifest_path)
        wrapper_entry = entries.get(wrapper_source)
        target_entry = entries.get(target_source)
        expected_wrapper_path = str((scripts_root / "nightly_git_hygiene_wrapper.sh").resolve())
        expected_target_path = str((scripts_root / Path(target_source).name).resolve())
        wrapper_manifest_ok = bool(
            wrapper_entry
            and wrapper_entry.get("kind") == "runtime-deploy"
            and wrapper_entry.get("destination") == expected_wrapper_path
            and wrapper_entry.get("source_sha256") == candidate_wrapper_hash
        )
        target_manifest_ok = bool(
            target_entry
            and target_entry.get("kind") == "runtime-deploy"
            and target_entry.get("destination") == expected_target_path
            and target_entry.get("source_sha256") == candidate_target_hash
        )
        result["manifest"] = {
            "wrapper_entry": wrapper_entry,
            "target_entry": target_entry,
            "wrapper_manifest_ok": wrapper_manifest_ok,
            "target_manifest_ok": target_manifest_ok,
        }
        result["verdicts"]["wrapper_manifest"] = "PROVEN" if wrapper_manifest_ok else "FALSE"
        result["verdicts"]["target_manifest"] = "PROVEN" if target_manifest_ok else "FALSE"
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result["errors"].append(str(exc))
        result["verdicts"]["wrapper_manifest"] = "FALSE"
        result["verdicts"]["target_manifest"] = "FALSE"

    current_wrapper_hash = chain.get("wrapper_sha256")
    current_target_hash = chain.get("target_sha256")
    target_path_expected = str((scripts_root / Path(target_source).name).resolve())
    wrapper_target_path_ok = chain.get("wrapper_target_path") == target_path_expected
    current_wrapper_ok = current_wrapper_hash is not None and current_wrapper_hash == candidate_wrapper_hash
    current_target_ok = current_target_hash is not None and current_target_hash == candidate_target_hash
    result["verdicts"]["wrapper_target_path"] = "PROVEN" if wrapper_target_path_ok else "FALSE"
    result["verdicts"]["current_wrapper_matches_candidate"] = "PROVEN" if current_wrapper_ok else "FALSE"
    result["verdicts"]["current_target_matches_candidate"] = "PROVEN" if current_target_ok else "FALSE"

    try:
        receipt = _read_receipt(receipt_path)
        git_state_value = receipt.get("git_state")
        execution_value = receipt.get("execution")
        git_state: dict[str, Any] = git_state_value if isinstance(git_state_value, dict) else {}
        execution: dict[str, Any] = execution_value if isinstance(execution_value, dict) else {}
        audited_head = execution.get("audited_repo_head") or git_state.get("head")
        execution_path = execution.get("script_path")
        execution_hash = execution.get("script_sha256")
        result["receipt"] = {
            "audited_repo_head": audited_head,
            "execution_script_path": execution_path,
            "execution_script_sha256": execution_hash,
            "execution_hash_matches_current_target": execution_hash is not None and execution_hash == current_target_hash,
        }
        historical_ok = bool(
            isinstance(audited_head, str)
            and audited_head == candidate_sha
            and isinstance(execution_path, str)
            and execution_path == chain.get("wrapper_target_path")
            and isinstance(execution_hash, str)
            and SHA256_RE.fullmatch(execution_hash)
            and execution_hash == candidate_target_hash
        )
        historical_partial = execution_hash is None or execution_path is None
        result["verdicts"]["historical_execution_identity"] = (
            "PROVEN" if historical_ok else "PARTIAL" if historical_partial else "FALSE"
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result["errors"].append(f"receipt read failed: {exc}")
        result["verdicts"]["historical_execution_identity"] = "UNKNOWN"

    chain_ok = all(
        [
            not result["errors"],
            result["job"].get("enabled") is True,
            result["job"].get("no_agent") is True,
            wrapper_target_path_ok,
            current_wrapper_ok,
            current_target_ok,
            result["manifest"].get("wrapper_manifest_ok") is True,
            result["manifest"].get("target_manifest_ok") is True,
            result["verdicts"].get("historical_execution_identity") == "PROVEN",
        ]
    )
    if chain_ok:
        result["status"] = "PROVEN"
    elif result["errors"]:
        result["status"] = "FAIL"
    else:
        result["status"] = "HOLD"
        result["holds"].append("executable chain or execution identity does not match candidate")
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Read-only post-closure executable-chain verifier")
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--jobs", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--scripts-root", required=True, type=Path)
    parser.add_argument("--job-id", default="9517378892e3")
    parser.add_argument("--target-source", default="scripts/nightly_git_hygiene.py")
    args = parser.parse_args(argv)
    result = verify(
        repo_root=args.repo.resolve(),
        candidate_sha=args.candidate_sha,
        jobs_path=args.jobs.resolve(),
        manifest_path=args.manifest.resolve(),
        receipt_path=args.receipt.resolve(),
        scripts_root=args.scripts_root.resolve(),
        job_id=args.job_id,
        target_source=args.target_source,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PROVEN" else 1


if __name__ == "__main__":
    raise SystemExit(main())
