#!/usr/bin/env python3
"""Reconstruct the Hermes runtime from one official commit plus an ordered patch series.

This is a source/build tool only. It never writes to /home/ubuntu/.hermes and
never reads runtime databases, sessions, logs, or credentials. Deployment is a
separate exact-manifest operation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

OFFICIAL_REPOSITORY = "https://github.com/NousResearch/hermes-agent.git"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
MODE_RE = re.compile(r"^[0-7]{4,6}$")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(value: str) -> bool:
    if not value or value.startswith("/") or "\\" in value:
        return False
    parts = PurePosixPath(value).parts
    return bool(parts) and ".." not in parts and "." not in parts


def _repo_root(lock_path: Path) -> Path:
    result = subprocess.run(
        ["git", "-C", str(lock_path.parent), "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"cannot locate application repository: {result.stderr.strip()}")
    return Path(result.stdout.strip()).resolve()


def _git(repo: Path, *args: str, capture: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        capture_output=capture,
        check=False,
    )


def _verify_commit(repo: Path, expected: str) -> None:
    result = _git(repo, "rev-parse", f"{expected}^{{commit}}")
    if result.returncode or result.stdout.strip() != expected:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"base commit verification failed: {expected}: {detail}")


def _load_lock(lock_path: Path) -> dict[str, Any]:
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if not isinstance(lock, dict) or lock.get("schema_version") != 1:
        raise RuntimeError("source lock schema_version must be 1")
    if lock.get("authority") != "hermes-runtime-reconstruction":
        raise RuntimeError("source lock authority is not hermes-runtime-reconstruction")
    if lock.get("official_repository") != OFFICIAL_REPOSITORY:
        raise RuntimeError("source lock official repository is not the approved NousResearch repository")
    base = lock.get("official_base_sha")
    if not isinstance(base, str) or not COMMIT_RE.fullmatch(base):
        raise RuntimeError("source lock official_base_sha must be a full 40-character SHA")
    if not _safe_relative(lock.get("runtime_tree_manifest", "")):
        raise RuntimeError("source lock runtime_tree_manifest is unsafe")
    destination_root = lock.get("runtime_destination_root")
    if destination_root != "/home/ubuntu/.hermes/hermes-agent":
        raise RuntimeError("runtime destination root is outside the approved Hermes source target")
    series = lock.get("patch_series")
    if not isinstance(series, list):
        raise RuntimeError("source lock patch_series must be a list")
    orders: list[int] = []
    ids: set[str] = set()
    paths: set[str] = set()
    for entry in series:
        if not isinstance(entry, dict):
            raise RuntimeError("patch series entry is not an object")
        required = {"order", "id", "path", "sha256", "description"}
        if set(entry) != required:
            raise RuntimeError(f"patch series keys must be exactly {sorted(required)}")
        order, patch_id, path, sha = entry["order"], entry["id"], entry["path"], entry["sha256"]
        if not isinstance(order, int) or order < 1 or order in orders:
            raise RuntimeError("patch series order must be unique positive integers")
        if not isinstance(patch_id, str) or not patch_id or patch_id in ids:
            raise RuntimeError("patch series id must be unique and non-empty")
        if not isinstance(path, str) or not _safe_relative(path) or not path.endswith(".patch"):
            raise RuntimeError("patch series path is unsafe")
        if path in paths:
            raise RuntimeError("patch series path is duplicated")
        if not isinstance(sha, str) or not SHA256_RE.fullmatch(sha):
            raise RuntimeError("patch series sha256 is invalid")
        orders.append(order)
        ids.add(patch_id)
        paths.add(path)
    if orders != sorted(orders):
        raise RuntimeError("patch series must be sorted by order")
    refs = lock.get("non_authoritative_tracked_paths")
    if not isinstance(refs, list) or not refs:
        raise RuntimeError("non_authoritative_tracked_paths must be a non-empty list")
    for entry in refs:
        if not isinstance(entry, dict) or set(entry) != {"path", "disposition", "reason"}:
            raise RuntimeError("invalid non-authoritative tracked path entry")
        if not _safe_relative(entry["path"]) or entry["disposition"] != "reference-only":
            raise RuntimeError("tracked legacy source must be explicitly reference-only")
    return lock


def _patch_digest(lock: dict[str, Any]) -> str:
    return _sha256_bytes(_canonical_json(lock["patch_series"]))


def _clone_official(repo_url: str, base_sha: str, parent: Path) -> Path:
    clone = parent / "official-base"
    result = subprocess.run(
        [
            "git",
            "clone",
            "--filter=blob:none",
            "--no-checkout",
            "--no-tags",
            "--depth=1",
            repo_url,
            str(clone),
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(f"official base clone failed: {result.stderr.strip()}")
    result = _git(clone, "fetch", "--depth=1", "origin", base_sha)
    if result.returncode:
        raise RuntimeError(f"official base fetch failed: {result.stderr.strip()}")
    _verify_commit(clone, base_sha)
    return clone


def _extract_archive(repo: Path, base_sha: str, output: Path) -> None:
    """Materialize the exact Git tree without applying working-tree filters."""
    output.mkdir(parents=True, exist_ok=False)
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "-z", base_sha],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"cannot read Git tree for extraction: "
            f"{result.stderr.decode('utf-8', errors='replace').strip()}"
        )

    for record in result.stdout.split(b"\0"):
        if not record:
            continue
        metadata, raw_source = record.split(b"\t", 1)
        mode, object_type, object_id = metadata.split(b" ", 2)
        source = raw_source.decode("utf-8", errors="surrogateescape")
        if object_type != b"blob" or mode not in {b"100644", b"100755"}:
            raise RuntimeError(f"unsupported Git tree member: {source}")
        if not _safe_relative(source):
            raise RuntimeError(f"official tree contains unsafe path: {source}")
        target = output / source
        target.parent.mkdir(parents=True, exist_ok=True)
        blob = subprocess.run(
            ["git", "-C", str(repo), "cat-file", "blob", object_id.decode("ascii")],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        if blob.returncode:
            raise RuntimeError(
                f"cannot read Git blob for {source}: "
                f"{blob.stderr.decode('utf-8', errors='replace').strip()}"
            )
        target.write_bytes(blob.stdout)
        os.chmod(target, 0o755 if mode == b"100755" else 0o644)


def _restore_git_modes(repo: Path, base_sha: str, output: Path) -> None:
    result = _git(repo, "ls-tree", "-r", "-z", base_sha)
    if result.returncode:
        raise RuntimeError(f"cannot read official Git tree modes: {result.stderr.strip()}")
    for record in result.stdout.split("\0"):
        if not record:
            continue
        metadata, source = record.split("\t", 1)
        mode = metadata.split(" ", 1)[0]
        target = output / source
        if not target.is_file():
            raise RuntimeError(f"official Git tree file missing after extraction: {source}")
        if mode == "100755":
            os.chmod(target, 0o755)
        elif mode == "100644":
            os.chmod(target, 0o644)
        else:
            raise RuntimeError(f"unsupported official Git file mode {mode}: {source}")


def _apply_series(
    repo_root: Path,
    output: Path,
    lock: dict[str, Any],
    official_base_repo: Path,
) -> None:
    for entry in lock["patch_series"]:
        patch = repo_root / entry["path"]
        if not patch.is_file():
            raise RuntimeError(f"patch is missing from application source: {entry['path']}")
        actual = _sha256_file(patch)
        if actual != entry["sha256"]:
            raise RuntimeError(f"patch hash mismatch: {entry['path']}")
        for check in (True, False):
            args = ["apply"]
            if check:
                args.append("--check")
            args.append(str(patch))
            result = _git(output, *args)
            if result.returncode:
                phase = "check" if check else "apply"
                raise RuntimeError(
                    f"patch {phase} failed for {entry['id']}: "
                    f"{result.stderr.strip()}"
                )
    # ``git apply`` can recreate modified regular files with the process
    # umask (0664 here), even though the official Git tree records 100644.
    # Restore the pinned base-tree modes after the complete ordered series so
    # the deployment manifest describes reproducible Git modes, not host
    # filesystem defaults.
    _restore_git_modes(official_base_repo, lock["official_base_sha"], output)


def _iter_files(root: Path) -> Iterable[Path]:
    for path in sorted(root.rglob("*")):
        if path.is_file():
            yield path


def _entry_for(path: Path, output: Path, destination_root: str) -> dict[str, str]:
    relative = path.relative_to(output).as_posix()
    destination = destination_root.rstrip("/") + "/" + relative
    return {
        "source": relative,
        "destination": destination,
        "sha256": _sha256_file(path),
        "mode": format(path.stat().st_mode & 0o7777, "04o"),
    }


def _write_tree_manifest(path: Path, output: Path, lock: dict[str, Any]) -> dict[str, Any]:
    entries = [_entry_for(item, output, lock["runtime_destination_root"]) for item in _iter_files(output)]
    manifest = {
        "schema_version": 1,
        "base_sha": lock["official_base_sha"],
        "patch_series_digest": _patch_digest(lock),
        "destination_root": lock["runtime_destination_root"],
        "entries": entries,
    }
    manifest["tree_sha256"] = _sha256_bytes(_canonical_json(entries))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _validate_tree_manifest(path: Path, output: Path, lock: dict[str, Any]) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise RuntimeError("runtime tree manifest schema_version must be 1")
    if manifest.get("base_sha") != lock["official_base_sha"]:
        raise RuntimeError("runtime tree manifest base SHA does not match source lock")
    if manifest.get("patch_series_digest") != _patch_digest(lock):
        raise RuntimeError("runtime tree manifest patch-series digest does not match source lock")
    if manifest.get("destination_root") != lock["runtime_destination_root"]:
        raise RuntimeError("runtime tree manifest destination root mismatch")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("runtime tree manifest entries must be non-empty")
    if manifest.get("tree_sha256") != _sha256_bytes(_canonical_json(entries)):
        raise RuntimeError("runtime tree manifest tree hash mismatch")
    expected: dict[str, dict[str, str]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {"source", "destination", "sha256", "mode"}:
            raise RuntimeError("runtime tree manifest entry shape is invalid")
        source = entry["source"]
        if not isinstance(source, str) or not _safe_relative(source):
            raise RuntimeError("runtime tree manifest source path is unsafe")
        if source in expected:
            raise RuntimeError(f"duplicate runtime tree source: {source}")
        destination = entry["destination"]
        expected_destination = lock["runtime_destination_root"].rstrip("/") + "/" + source
        if destination != expected_destination:
            raise RuntimeError(f"runtime destination does not mirror source: {source}")
        if not isinstance(entry["sha256"], str) or not SHA256_RE.fullmatch(entry["sha256"]):
            raise RuntimeError(f"invalid runtime tree hash: {source}")
        if not isinstance(entry["mode"], str) or not MODE_RE.fullmatch(entry["mode"]):
            raise RuntimeError(f"invalid runtime tree mode: {source}")
        if source in lock["forbidden_runtime_paths"] or any(
            source.startswith(item.rstrip("/") + "/") for item in lock["forbidden_runtime_paths"]
        ):
            raise RuntimeError(f"forbidden runtime path in manifest: {source}")
        expected[source] = entry
    actual_paths = {item.relative_to(output).as_posix() for item in _iter_files(output)}
    if actual_paths != set(expected):
        missing = sorted(set(expected) - actual_paths)[:10]
        extra = sorted(actual_paths - set(expected))[:10]
        raise RuntimeError(f"runtime tree path set mismatch: missing={missing} extra={extra}")
    for source, entry in expected.items():
        path_on_disk = output / source
        if _sha256_file(path_on_disk) != entry["sha256"]:
            raise RuntimeError(f"runtime tree hash mismatch: {source}")
        if format(path_on_disk.stat().st_mode & 0o7777, "04o") != entry["mode"]:
            raise RuntimeError(f"runtime tree mode mismatch: {source}")
    return manifest


def reconstruct(
    lock_path: Path,
    tree_manifest_path: Path,
    output: Path,
    base_repo: Path | None,
    validate: bool,
    write_tree: bool,
) -> None:
    lock = _load_lock(lock_path)
    repo_root = _repo_root(lock_path)
    if tree_manifest_path.is_absolute():
        expected_tree_path = tree_manifest_path
    else:
        expected_tree_path = repo_root / tree_manifest_path
    if base_repo is None:
        with tempfile.TemporaryDirectory(prefix="hermes-runtime-reconstruct-") as temp:
            official = _clone_official(lock["official_repository"], lock["official_base_sha"], Path(temp))
            _extract_archive(official, lock["official_base_sha"], output)
            _apply_series(repo_root, output, lock, official)
    else:
        _verify_commit(base_repo, lock["official_base_sha"])
        _extract_archive(base_repo, lock["official_base_sha"], output)
        _apply_series(repo_root, output, lock, base_repo)
    if write_tree:
        _write_tree_manifest(expected_tree_path, output, lock)
    if validate:
        if not expected_tree_path.is_file():
            raise RuntimeError(f"runtime tree manifest is missing: {expected_tree_path}")
        manifest = _validate_tree_manifest(expected_tree_path, output, lock)
        print(
            "RECONSTRUCTION PASS: "
            f"base={lock['official_base_sha']} patches={len(lock['patch_series'])} "
            f"files={len(manifest['entries'])} tree_sha256={manifest['tree_sha256']}"
        )
    else:
        print(
            "RECONSTRUCTION PASS: "
            f"base={lock['official_base_sha']} patches={len(lock['patch_series'])} "
            f"output={output}"
        )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lock", required=True, type=Path)
    parser.add_argument("--tree-manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--base-repo", type=Path)
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--write-tree-manifest", action="store_true")
    args = parser.parse_args()
    try:
        reconstruct(
            args.lock.resolve(),
            args.tree_manifest,
            args.output.resolve(),
            args.base_repo.resolve() if args.base_repo else None,
            args.validate,
            args.write_tree_manifest,
        )
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"RECONSTRUCTION FAIL: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
