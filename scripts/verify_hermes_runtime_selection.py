#!/usr/bin/env python3
"""Verify live bytes for an explicitly selected Hermes runtime manifest.

This is a read-only release gate. It validates the candidate source tree and
manifest through the normal Hermes reconstruction contract, then compares only
manifest-declared live destinations. Unmanaged live files are intentionally
outside this verifier's scope.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from deploy_hermes_runtime import _validate_source_tree  # noqa: E402


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
def compare_live_hashes(entries: list[dict[str, Any]]) -> tuple[str, ...]:
    """Return manifest source paths whose live destination bytes do not match."""
    mismatches: list[str] = []
    for entry in entries:
        source = str(entry["source"])
        destination = Path(entry["destination"])
        expected = str(entry["sha256"])
        if not destination.is_file() or _sha256_file(destination) != expected:
            mismatches.append(source)
    return tuple(mismatches)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-tree", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--lock", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        source_tree = args.source_tree.resolve()
        manifest = args.manifest.resolve()
        lock_path = args.lock.resolve()
        if not source_tree.is_dir():
            raise RuntimeError(f"source tree does not exist: {source_tree}")
        _lock, tree = _validate_source_tree(source_tree, manifest, lock_path)
        mismatches = compare_live_hashes(tree["entries"])
        if mismatches:
            print(
                "RUNTIME SELECTION VERIFY FAIL: "
                f"mismatches={len(mismatches)} paths={list(mismatches)}"
            )
            return 1
        print(
            "RUNTIME SELECTION VERIFY PASS: "
            f"entries={len(tree['entries'])} mismatches=0"
        )
        return 0
    except (OSError, RuntimeError, json.JSONDecodeError, KeyError) as exc:
        print(f"RUNTIME SELECTION VERIFY FAIL: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
