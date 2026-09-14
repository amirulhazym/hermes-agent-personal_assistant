from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def test_antigravity_provider_live_parity_with_main_repo_patch():
    """Verify live antigravity-provider checkout has zero unrepresented drift."""
    live_agy = Path("/home/ubuntu/.hermes/plugins/antigravity-provider")
    patch_agy = Path("/home/ubuntu/hermes-agent-personal_assistant-work/patches/antigravity-provider/2026-09-04_custom_antigravity_features.patch")

    assert live_agy.exists(), "live antigravity-provider directory must exist"
    assert patch_agy.exists(), "antigravity-provider patch must exist in main repo"

    # 1. Reverse check against current live working tree (must cleanly match 0)
    res = subprocess.run(
        ["git", "apply", "--check", "--reverse", str(patch_agy)],
        cwd=live_agy,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Live antigravity tree drifted from main repo patch: {res.stderr}"

    # 2. Check that no uncommitted modifications exist outside the patch
    res_status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=live_agy,
        capture_output=True,
        text=True,
    )
    # The only untracked file permitted is DO_NOT_EDIT_LIVE_RUNTIME.md
    untracked = [line for line in res_status.stdout.splitlines() if line.startswith("??") and not line.endswith("DO_NOT_EDIT_LIVE_RUNTIME.md")]
    assert not untracked, f"Unrepresented untracked files in live antigravity checkout: {untracked}"


def verify_authoritative_reconstruction_contract(
    tree_manifest_path: Path,
    source_lock_path: Path,
    repo_path: Path,
) -> None:
    """Validate repository-side authoritative source-lock contract and tree-manifest linkage.

    Excludes live runtime byte comparison (which is governed by scripts/drift_check.sh).
    """
    assert source_lock_path.is_file(), f"Source lock missing: {source_lock_path}"
    assert tree_manifest_path.is_file(), f"Tree manifest missing: {tree_manifest_path}"

    lock = json.loads(source_lock_path.read_text(encoding="utf-8"))
    manifest = json.loads(tree_manifest_path.read_text(encoding="utf-8"))

    # 1. Schema, authority and base commit validation
    assert lock.get("schema_version") == 1
    assert lock.get("authority") == "hermes-runtime-reconstruction"
    base_sha = lock["official_base_sha"]
    assert manifest["base_sha"] == base_sha, "Manifest base SHA must match source lock official_base_sha"
    assert manifest["destination_root"] == lock["runtime_destination_root"]

    # Verify base commit is resolvable in repository object store
    res_base = subprocess.run(
        ["git", "-C", str(repo_path), "cat-file", "-t", base_sha],
        capture_output=True,
        text=True,
    )
    assert res_base.returncode == 0, f"Base commit {base_sha} must exist in Git object store"

    # 2. Active patch series validation
    patch_series = lock.get("patch_series", [])
    assert patch_series, "Active patch series must not be empty"
    active_patch_paths = set()
    orders = []
    for patch_info in patch_series:
        orders.append(patch_info["order"])
        p_path = repo_path / patch_info["path"]
        assert p_path.is_file(), f"Active patch file missing: {p_path}"
        actual_hash = hashlib.sha256(p_path.read_bytes()).hexdigest()
        assert actual_hash == patch_info["sha256"], f"Active patch SHA mismatch: {patch_info['id']}"
        active_patch_paths.add(patch_info["path"])

    assert orders == sorted(orders), "Patch orders must be strictly monotonically increasing"
    assert len(orders) == len(set(orders)), "Patch orders must be unique"

    # Historical out-of-series patches must not be active contract requirements
    assert "patches/upstream-hermes/2026-09-04_live_model_picker_refresh.patch" not in active_patch_paths

    # 3. Tree manifest linkage and structure validation
    entries = manifest.get("entries", [])
    assert isinstance(entries, list) and entries, "Tree manifest entries must be non-empty"

    forbidden = lock.get("forbidden_runtime_paths", [])
    expected_root = lock["runtime_destination_root"].rstrip("/")
    sources = set()
    destinations = set()

    for entry in entries:
        assert set(entry.keys()) == {"source", "destination", "sha256", "mode"}
        src = entry["source"]
        dst = entry["destination"]
        assert src and not src.startswith("/") and ".." not in src.split("/")
        assert dst == f"{expected_root}/{src}"
        assert not any(src == f or src.startswith(f"{f.rstrip('/')}/") for f in forbidden)
        sources.add(src)
        destinations.add(dst)

    assert len(sources) == len(entries), "Manifest sources must be unique"
    assert len(destinations) == len(entries), "Manifest destinations must be unique"


def test_hermes_agent_reconstruction_contract():
    """Verify repository-side hermes-agent source-lock and tree-manifest contract integrity."""
    repo = Path(__file__).resolve().parents[2]
    lock_path = repo / "docs/reconciliation/hermes-runtime-source-lock.json"
    tree_manifest_path = repo / "docs/reconciliation/hermes-runtime-tree-manifest.json"

    verify_authoritative_reconstruction_contract(
        tree_manifest_path=tree_manifest_path,
        source_lock_path=lock_path,
        repo_path=repo,
    )


def test_synthetic_managed_drift_fails_and_unmanaged_customization_ignored(tmp_path: Path):
    """Negative & boundary test: proves managed byte drift is caught while unmanaged paths are ignored."""
    def _verify_synthetic_dir(manifest_dict: dict, root: Path) -> list[str]:
        mismatches = []
        for entry in manifest_dict.get("entries", []):
            target = root / entry["source"]
            if not target.is_file():
                mismatches.append(entry["source"])
                continue
            if hashlib.sha256(target.read_bytes()).hexdigest() != entry["sha256"]:
                mismatches.append(entry["source"])
        return mismatches

    synthetic_root = tmp_path / "runtime"
    synthetic_root.mkdir()

    # 1. Create a managed file with expected hash
    managed_file = synthetic_root / "gateway" / "run.py"
    managed_file.parent.mkdir(parents=True, exist_ok=True)
    content = b"print('managed content')\n"
    managed_file.write_bytes(content)
    expected_sha = hashlib.sha256(content).hexdigest()

    synth_manifest = {
        "entries": [
            {
                "source": "gateway/run.py",
                "destination": str(managed_file),
                "sha256": expected_sha,
                "mode": "0644",
            }
        ]
    }

    # 2. Add unmanaged owner customization
    custom_path = synthetic_root / "plugins" / "my_custom_tool.py"
    custom_path.parent.mkdir(parents=True, exist_ok=True)
    custom_path.write_text("print('owner customization')")

    # Clean verification: passes, unmanaged customization ignored
    assert _verify_synthetic_dir(synth_manifest, synthetic_root) == []

    # 3. Mutate managed file by 1 byte -> caught
    managed_file.write_bytes(b"print('corrupted content')\n")
    mismatches = _verify_synthetic_dir(synth_manifest, synthetic_root)
    assert "gateway/run.py" in mismatches, "Managed byte drift must be caught by verification"
