#!/usr/bin/env python3
"""Plan or apply an explicit Hermes runtime tree manifest.

The default operation is a read-only plan. Applying requires an exact release
SHA and writes only manifest-declared files under the fixed Hermes source root.
It never deletes undeclared files, touches state, or restarts the gateway.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from reconstruct_hermes_runtime import (  # noqa: E402
    COMMIT_RE,
    _load_lock,
    _repo_root,
    _sha256_file,
    _validate_tree_manifest,
)


RUNTIME_ROOT = Path("/home/ubuntu/.hermes/hermes-agent")


def _validate_source_tree(source_tree: Path, manifest: Path, lock_path: Path) -> tuple[dict, dict]:
    lock = _load_lock(lock_path)
    repo_root = _repo_root(lock_path)
    tree = _validate_tree_manifest(manifest, source_tree, lock)
    if Path(lock["runtime_destination_root"]) != RUNTIME_ROOT:
        raise RuntimeError("source lock runtime root is not the approved Hermes target")
    return lock, tree


def _safe_destination(destination: Path, root: Path) -> None:
    if destination.is_symlink():
        raise RuntimeError(f"refusing symlink destination: {destination}")
    resolved_parent = destination.parent.resolve()
    if root.resolve() not in [resolved_parent, *resolved_parent.parents]:
        raise RuntimeError(f"destination escapes Hermes root: {destination}")


def _destination_matches(
    destination: Path,
    root: Path,
    relative_source: str,
    expected_sha256: str,
) -> bool:
    """Match raw bytes or the Git-normalized worktree representation."""
    if not destination.is_file():
        return False
    if _sha256_file(destination) == expected_sha256:
        return True
    normalized = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "hash-object",
            "--path=" + relative_source,
            str(destination),
        ],
        capture_output=True,
        check=False,
    )
    if normalized.returncode:
        return False
    object_id = normalized.stdout.decode("ascii", errors="replace").strip()
    if not object_id:
        return False
    blob = subprocess.run(
        ["git", "-C", str(root), "cat-file", "blob", object_id],
        capture_output=True,
        check=False,
    )
    return blob.returncode == 0 and hashlib.sha256(blob.stdout).hexdigest() == expected_sha256


def _plan(source_tree: Path, tree: dict) -> None:
    mismatches = 0
    normalized_equivalent = 0
    for entry in tree["entries"]:
        source = source_tree / entry["source"]
        destination = Path(entry["destination"])
        if destination.exists() and not destination.is_file():
            mismatches += 1
        elif destination.is_file() and _sha256_file(destination) != entry["sha256"]:
            if _destination_matches(
                destination,
                RUNTIME_ROOT,
                entry["source"],
                entry["sha256"],
            ):
                normalized_equivalent += 1
            else:
                mismatches += 1
    print(
        "DEPLOY PLAN PASS: "
        f"entries={len(tree['entries'])} current_hash_mismatches={mismatches} "
        f"normalized_equivalent={normalized_equivalent} writes=0 deletes=0 restart=0"
    )


def _apply(source_tree: Path, tree: dict, release_sha: str) -> None:
    if not COMMIT_RE.fullmatch(release_sha):
        raise RuntimeError("--release-sha must be a full 40-character commit SHA")
    root = RUNTIME_ROOT
    root.mkdir(parents=True, exist_ok=True)
    rollback_root = root.parent / "hermes-runtime-rollbacks" / release_sha
    rollback_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(rollback_root, 0o700)
    changed: list[tuple[Path, Path | None]] = []
    try:
        for entry in tree["entries"]:
            source = source_tree / entry["source"]
            destination = Path(entry["destination"])
            _safe_destination(destination, root)
            if destination.exists():
                if not destination.is_file():
                    raise RuntimeError(f"existing destination is not a regular file: {destination}")
                backup = rollback_root / entry["source"]
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, backup)
                previous = backup
            else:
                previous = None
            destination.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
            temporary = Path(temporary_name)
            try:
                with os.fdopen(fd, "wb") as handle, source.open("rb") as source_handle:
                    shutil.copyfileobj(source_handle, handle)
                os.chmod(temporary, int(entry["mode"], 8))
                os.replace(temporary, destination)
            finally:
                if temporary.exists():
                    temporary.unlink()
            changed.append((destination, previous))
    except Exception:
        for destination, previous in reversed(changed):
            if previous is None:
                if destination.exists():
                    destination.unlink()
            else:
                shutil.copy2(previous, destination)
        raise
    print(
        "DEPLOY APPLY PASS: "
        f"release_sha={release_sha} entries={len(tree['entries'])} "
        f"rollback={rollback_root} restart=0"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-tree", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--lock", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--release-sha")
    args = parser.parse_args()
    try:
        source_tree = args.source_tree.resolve()
        manifest = args.manifest.resolve()
        lock_path = args.lock.resolve()
        if not source_tree.is_dir():
            raise RuntimeError(f"source tree does not exist: {source_tree}")
        _, tree = _validate_source_tree(source_tree, manifest, lock_path)
        if args.apply:
            if not args.release_sha:
                raise RuntimeError("--apply requires --release-sha")
            _apply(source_tree, tree, args.release_sha)
        else:
            _plan(source_tree, tree)
    except Exception as exc:
        print(f"DEPLOY FAIL: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
