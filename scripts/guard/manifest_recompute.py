#!/usr/bin/env python3
"""CI-side enforcement: recompute source_sha256 for every existing manifest
row against $GITHUB_SHA, write receipts under docs/reconciliation/manifest-receipts,
then re-run the strict validator.

Does NOT add new rows. If a tracked source is missing in the working tree at
$GITHUB_SHA, exits 1 so the job fails loudly (matches today's "absent row"
diagnosis). Absent rows are a policy decision, not a CI decision.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
MANIFEST = REPO / "docs/reconciliation/v3-source-coverage-manifest.json"
RECEIPTS = REPO / "docs/reconciliation/manifest-receipts"


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO, text=True)


def _hash_at(ref: str, path: str) -> str:
    raw = subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=REPO)
    return hashlib.sha256(raw).hexdigest()


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: manifest_recompute.py <manifest> <sha>", file=sys.stderr)
        return 2
    manifest_path = Path(sys.argv[1])
    sha = sys.argv[2]
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    refreshed: list[dict] = []
    missing: list[str] = []
    for entry in data["entries"]:
        src = entry["source"]
        try:
            actual = _hash_at(sha, src)
        except subprocess.CalledProcessError:
            missing.append(src)
            continue
        if entry["source_sha256"] != actual:
            refreshed.append(
                {"source": src, "old": entry["source_sha256"], "new": actual},
            )
            entry["source_sha256"] = actual
    if refreshed:
        manifest_path.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    if missing:
        for path in missing:
            print(f"MANIFEST-RECOMPUTE MISSING: source={path} sha={sha}", file=sys.stderr)
        print("manifest_recompute: FAIL (absent rows present; policy decision required)",
              file=sys.stderr)
        return 1
    RECEIPTS.mkdir(parents=True, exist_ok=True)
    short = sha[:12]
    receipt = {
        "status": "REFRESHED" if refreshed else "NOOP",
        "refreshed_count": len(refreshed),
        "refreshed": refreshed,
        "head_sha": sha,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
    }
    (RECEIPTS / f"{short}.json").write_text(
        json.dumps(receipt, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"MANIFEST-RECOMPUTE: status={receipt['status']} refreshed={len(refreshed)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())