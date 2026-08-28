#!/usr/bin/env python3
"""Manifest-driven deployment of custom Hermes runtime files.

This lane is separate from the full core runtime-tree deployer. It consumes the
application source-coverage manifest's explicit ``runtime-deploy`` rows and
ignores ``source-only`` rows. The default is a read-only plan; apply requires a
full release SHA and writes only declared paths under ``$HERMES_HOME``.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SHA256_RE = __import__("re").compile(r"^[0-9a-f]{64}$")
COMMIT_RE = __import__("re").compile(r"^[0-9a-f]{40}$")
RUNTIME_ROOT = Path("/home/ubuntu/.hermes")
FORBIDDEN_NAMES = {
    ".env",
    "auth.json",
    "state.db",
    "state.db-shm",
    "state.db-wal",
    "med-status.json",
    "med-schedule.json",
    "dexa_taper.json",
    "med-supply.json",
    "sessions",
    "memories",
    "logs",
}


@dataclass(frozen=True)
class DeploymentPlan:
    entries: tuple[dict[str, Any], ...]
    content_mismatches: tuple[str, ...]
    mode_only: tuple[str, ...]
    missing: tuple[str, ...]
    source_mismatches: tuple[str, ...]


@dataclass(frozen=True)
class ApplyResult:
    rollback_root: Path
    plan: DeploymentPlan


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative(path: str) -> bool:
    parts = Path(path).parts
    return bool(path) and not path.startswith("/") and ".." not in parts and "\\" not in path


def _safe_destination(destination: Path, root: Path) -> None:
    if destination.is_symlink():
        raise RuntimeError(f"refusing symlink destination: {destination}")
    resolved = destination.resolve(strict=False)
    root_resolved = root.resolve()
    if resolved == root_resolved or root_resolved not in resolved.parents:
        raise RuntimeError(f"destination escapes Hermes root: {destination}")
    relative = resolved.relative_to(root_resolved)
    if any(part in FORBIDDEN_NAMES for part in relative.parts):
        raise RuntimeError(f"forbidden runtime destination: {destination}")
    if str(resolved).startswith(str((root_resolved / "hermes-agent").resolve()) + os.sep):
        raise RuntimeError(f"core runtime destination belongs to the separate core deploy lane: {destination}")


def _runtime_entries(manifest: dict[str, Any], root: Path) -> tuple[dict[str, Any], ...]:
    if not isinstance(manifest, dict) or manifest.get("schema_version") != 1:
        raise RuntimeError("custom runtime manifest schema_version must be 1")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("custom runtime manifest entries must be non-empty")
    seen_sources: set[str] = set()
    seen_destinations: set[str] = set()
    runtime: list[dict[str, Any]] = []
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict) or set(entry) != {"source", "source_sha256", "kind", "destination"}:
            raise RuntimeError(f"manifest row {index} shape is invalid")
        source = entry["source"]
        digest = entry["source_sha256"]
        kind = entry["kind"]
        destination = entry["destination"]
        if not isinstance(source, str) or not _safe_relative(source) or source in seen_sources:
            raise RuntimeError(f"manifest row {index} source is invalid or duplicated")
        if not isinstance(digest, str) or not SHA256_RE.fullmatch(digest):
            raise RuntimeError(f"manifest row {index} source hash is invalid")
        seen_sources.add(source)
        if kind == "source-only":
            if destination is not None:
                raise RuntimeError(f"manifest row {index} source-only destination must be null")
            continue
        if kind != "runtime-deploy" or not isinstance(destination, str):
            raise RuntimeError(f"manifest row {index} kind/destination is invalid")
        destination_path = Path(destination)
        _safe_destination(destination_path, root)
        destination_key = str(destination_path.resolve(strict=False))
        if destination_key in seen_destinations:
            raise RuntimeError(f"manifest row {index} destination is duplicated")
        seen_destinations.add(destination_key)
        runtime.append(entry)
    return tuple(runtime)


def build_plan(source_tree: Path, manifest: dict[str, Any], destination_root: Path = RUNTIME_ROOT) -> DeploymentPlan:
    runtime = _runtime_entries(manifest, destination_root)
    content: list[str] = []
    modes: list[str] = []
    missing: list[str] = []
    source_mismatches: list[str] = []
    for entry in runtime:
        source = source_tree / entry["source"]
        destination = Path(entry["destination"])
        if not source.is_file():
            missing.append(entry["source"])
            continue
        if _sha256_file(source) != entry["source_sha256"]:
            source_mismatches.append(entry["source"])
        if not destination.exists():
            missing.append(entry["source"])
            continue
        if not destination.is_file():
            raise RuntimeError(f"existing destination is not a regular file: {destination}")
        if _sha256_file(destination) != entry["source_sha256"]:
            content.append(entry["source"])
        elif (source.stat().st_mode & 0o7777) != (destination.stat().st_mode & 0o7777):
            modes.append(entry["source"])
    return DeploymentPlan(tuple(runtime), tuple(content), tuple(modes), tuple(missing), tuple(source_mismatches))


def apply_manifest(source_tree: Path, manifest: dict[str, Any], release_sha: str) -> ApplyResult:
    if not COMMIT_RE.fullmatch(release_sha):
        raise RuntimeError("--release-sha must be a full 40-character commit SHA")
    plan = build_plan(source_tree, manifest, RUNTIME_ROOT)
    if plan.missing or plan.source_mismatches:
        raise RuntimeError(
            f"preflight failed: missing={list(plan.missing)[:10]} "
            f"source_mismatches={list(plan.source_mismatches)[:10]}"
        )
    rollback_root = RUNTIME_ROOT / "hermes-runtime-rollbacks" / "custom" / release_sha
    rollback_root.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(rollback_root, 0o700)
    changed: list[tuple[Path, Path | None]] = []
    try:
        for entry in plan.entries:
            source = source_tree / entry["source"]
            destination = Path(entry["destination"])
            _safe_destination(destination, RUNTIME_ROOT)
            previous: Path | None = None
            if destination.exists():
                backup = rollback_root / entry["source"]
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(destination, backup)
                previous = backup
                target_mode = destination.stat().st_mode & 0o7777
            else:
                target_mode = 0o755 if source.stat().st_mode & 0o111 else 0o644
            destination.parent.mkdir(parents=True, exist_ok=True)
            fd, temporary_name = tempfile.mkstemp(prefix=f".{destination.name}.", dir=destination.parent)
            temporary = Path(temporary_name)
            try:
                with os.fdopen(fd, "wb") as handle, source.open("rb") as source_handle:
                    shutil.copyfileobj(source_handle, handle)
                    handle.flush()
                    os.fsync(handle.fileno())
                os.chmod(temporary, target_mode)
                os.replace(temporary, destination)
            finally:
                if temporary.exists():
                    temporary.unlink()
            if _sha256_file(destination) != entry["source_sha256"]:
                raise RuntimeError(f"post-write hash mismatch: {entry['source']}")
            changed.append((destination, previous))
    except Exception:
        for destination, previous in reversed(changed):
            if previous is None:
                if destination.exists():
                    destination.unlink()
            else:
                shutil.copy2(previous, destination)
        raise
    return ApplyResult(rollback_root=rollback_root, plan=plan)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-tree", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--release-sha")
    args = parser.parse_args(argv)
    try:
        source_tree = args.source_tree.resolve()
        manifest = json.loads(args.manifest.resolve().read_text(encoding="utf-8"))
        if not source_tree.is_dir():
            raise RuntimeError(f"source tree does not exist: {source_tree}")
        if args.dry_run:
            plan = build_plan(source_tree, manifest, RUNTIME_ROOT)
            if plan.missing or plan.source_mismatches:
                raise RuntimeError(
                    f"preflight failed: missing={list(plan.missing)[:10]} "
                    f"source_mismatches={list(plan.source_mismatches)[:10]}"
                )
            print(
                "CUSTOM DEPLOY PLAN PASS: "
                f"entries={len(plan.entries)} hash_mismatches={len(plan.content_mismatches)} "
                f"mode_only={len(plan.mode_only)} writes=0 deletes=0 restart=0"
            )
        else:
            if not args.release_sha:
                raise RuntimeError("--apply requires --release-sha")
            result = apply_manifest(source_tree, manifest, args.release_sha)
            print(
                "CUSTOM DEPLOY APPLY PASS: "
                f"release_sha={args.release_sha} entries={len(result.plan.entries)} "
                f"rollback={result.rollback_root} deletes=0 restart=0"
            )
    except (OSError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"CUSTOM DEPLOY FAIL: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
