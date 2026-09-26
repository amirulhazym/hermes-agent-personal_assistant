from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path


ANTIGRAVITY_BASE_SHA = "097db5303a610d7e5d75a2fef58d4aefb18436d6"
ANTIGRAVITY_LOCAL_HEAD = "8cccbb6b891164f7aeceb09695e43b4a12d6a83e"
ANTIGRAVITY_LOCAL_COMMIT_PATCH_COUNT = 1
ANTIGRAVITY_LIVE_BASE_PATCH_COUNT = 2
ANTIGRAVITY_PATCH_CHAIN = (
    (
        "patches/antigravity-provider/2026-09-23_local_dependency_commits_base.patch",
        "50ed309a7a9a9a542aec6b361c0280f9317ac839e8d1c8e44ba9b766d1e102c3",
    ),
    (
        "patches/antigravity-provider/2026-09-04_custom_antigravity_features.patch",
        "f5f726808dd1935f9551dea258432c2450be2a013798dd393273042002844520",
    ),
    (
        "patches/antigravity-provider/2026-09-23_gemini_3_8_default.patch",
        "35fa5040e7886cf233614ee2248fcf5cb86d152d905efb8f77f251b7d8c6d016",
    ),
)


def test_antigravity_provider_live_parity_with_main_repo_patch(tmp_path: Path):
    """Verify live checkout parity at the dependency and selective-deploy boundaries."""
    repo = Path(__file__).resolve().parents[2]
    live_agy = Path("/home/ubuntu/.hermes/plugins/antigravity-provider")
    manifest_path = repo / "docs/reconciliation/antigravity-model-refresh-deploy-manifest.json"
    marker_name = "DO_NOT_EDIT_LIVE_RUNTIME.md"

    assert live_agy.exists(), "live antigravity-provider directory must exist"
    assert manifest_path.is_file(), "antigravity selective-deploy manifest must exist"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["upstream_base_sha"] == ANTIGRAVITY_BASE_SHA
    assert manifest["destination_root"] == str(live_agy)
    assert len(manifest["patch_chain"]) == len(ANTIGRAVITY_PATCH_CHAIN)
    assert tuple(
        (item["path"], item["sha256"])
        for item in manifest["patch_chain"]
    ) == ANTIGRAVITY_PATCH_CHAIN
    assert len(manifest["patch_chain"]) > ANTIGRAVITY_LIVE_BASE_PATCH_COUNT

    deployed_sources = [entry["source"] for entry in manifest["entries"]]
    assert deployed_sources
    for entry in manifest["entries"]:
        destination = Path(entry["destination"])
        assert destination == live_agy / entry["source"]
        assert hashlib.sha256(destination.read_bytes()).hexdigest() == entry["sha256"]

    # Rebuild the live dependency commits plus the represented personal overlay
    # from the pinned base. This is the pre-release live checkout state.
    candidate = tmp_path / "antigravity-provider"
    subprocess.run(
        ["git", "clone", "--quiet", "--no-hardlinks", str(live_agy), str(candidate)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "checkout", "--quiet", "--detach", ANTIGRAVITY_BASE_SHA],
        cwd=candidate,
        check=True,
        capture_output=True,
        text=True,
    )

    for index, (relative_patch, expected_sha) in enumerate(ANTIGRAVITY_PATCH_CHAIN):
        patch = repo / relative_patch
        assert patch.is_file(), f"Antigravity patch missing: {patch}"
        assert hashlib.sha256(patch.read_bytes()).hexdigest() == expected_sha
        subprocess.run(["git", "apply", "--check", str(patch)], cwd=candidate, check=True)
        subprocess.run(["git", "apply", str(patch)], cwd=candidate, check=True)
        if index + 1 == ANTIGRAVITY_LOCAL_COMMIT_PATCH_COUNT:
            subprocess.run(["git", "add", "-A"], cwd=candidate, check=True)
            rebuilt_local_tree = subprocess.run(
                ["git", "write-tree"], cwd=candidate, check=True, capture_output=True, text=True
            ).stdout.strip()
            live_local_tree = subprocess.run(
                ["git", "-C", str(live_agy), "rev-parse", f"{ANTIGRAVITY_LOCAL_HEAD}^{{tree}}"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            assert rebuilt_local_tree == live_local_tree

    # Later release overlays are intentionally selective: only manifest-listed
    # production paths were deployed, while their test hunks remain source-only.
    # Apply those exact paths to the reconstructed candidate before comparing its
    # Git tree with a temporary index of the live working tree.
    candidate = tmp_path / "antigravity-provider-selective"
    subprocess.run(
        ["git", "clone", "--quiet", "--no-hardlinks", str(live_agy), str(candidate)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "checkout", "--quiet", "--detach", ANTIGRAVITY_BASE_SHA],
        cwd=candidate,
        check=True,
        capture_output=True,
        text=True,
    )
    for relative_patch, _ in ANTIGRAVITY_PATCH_CHAIN[:ANTIGRAVITY_LIVE_BASE_PATCH_COUNT]:
        patch = repo / relative_patch
        subprocess.run(["git", "apply", str(patch)], cwd=candidate, check=True)
    include_args = [f"--include={source}" for source in deployed_sources]
    for relative_patch, _ in ANTIGRAVITY_PATCH_CHAIN[ANTIGRAVITY_LIVE_BASE_PATCH_COUNT:]:
        patch = repo / relative_patch
        check = subprocess.run(
            ["git", "apply", "--check", *include_args, str(patch)],
            cwd=candidate,
            capture_output=True,
            text=True,
        )
        assert check.returncode == 0, f"Selective Antigravity patch does not apply: {check.stderr}"
        subprocess.run(["git", "apply", *include_args, str(patch)], cwd=candidate, check=True)
    subprocess.run(["git", "add", "-A"], cwd=candidate, check=True)
    expected_tree = subprocess.run(
        ["git", "write-tree"], cwd=candidate, check=True, capture_output=True, text=True
    ).stdout.strip()

    status = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=live_agy,
        check=True,
        capture_output=True,
        text=True,
    )
    unexpected_untracked = [
        line for line in status.stdout.splitlines()
        if line.startswith("?? ") and line[3:] != marker_name
    ]
    assert not unexpected_untracked, f"Unrepresented untracked files in live antigravity checkout: {unexpected_untracked}"

    live_index = tmp_path / "live-index"
    live_env = os.environ.copy()
    live_env["GIT_INDEX_FILE"] = str(live_index)
    subprocess.run(["git", "read-tree", "HEAD"], cwd=live_agy, env=live_env, check=True)
    subprocess.run(
        ["git", "add", "-A", "--", ".", f":(exclude){marker_name}"],
        cwd=live_agy,
        env=live_env,
        check=True,
    )
    live_tree = subprocess.run(
        ["git", "write-tree"], cwd=live_agy, env=live_env, check=True, capture_output=True, text=True
    ).stdout.strip()
    assert live_tree == expected_tree, (
        "Live antigravity checkout has tracked drift outside the represented "
        f"dependency/selective-deploy chain: expected {expected_tree}, got {live_tree}"
    )


def test_antigravity_provider_candidate_reconstruction_chain(tmp_path: Path):
    """Rebuild the Antigravity candidate from the pinned upstream base and ordered SSOT patches."""
    repo = Path(__file__).resolve().parents[2]
    live_agy = Path("/home/ubuntu/.hermes/plugins/antigravity-provider")
    candidate = tmp_path / "antigravity-provider"

    subprocess.run(
        ["git", "clone", "--quiet", "--no-hardlinks", str(live_agy), str(candidate)],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "checkout", "--quiet", "--detach", ANTIGRAVITY_BASE_SHA],
        cwd=candidate,
        check=True,
        capture_output=True,
        text=True,
    )

    # Patch 1 must reproduce the intentional local dependency commits exactly.
    first_rel, first_sha = ANTIGRAVITY_PATCH_CHAIN[0]
    first_patch = repo / first_rel
    assert hashlib.sha256(first_patch.read_bytes()).hexdigest() == first_sha
    subprocess.run(["git", "apply", "--check", str(first_patch)], cwd=candidate, check=True)
    subprocess.run(["git", "apply", str(first_patch)], cwd=candidate, check=True)
    subprocess.run(["git", "add", "-A"], cwd=candidate, check=True)
    rebuilt_local_tree = subprocess.run(
        ["git", "write-tree"], cwd=candidate, check=True, capture_output=True, text=True
    ).stdout.strip()
    live_local_tree = subprocess.run(
        ["git", "-C", str(live_agy), "rev-parse", f"{ANTIGRAVITY_LOCAL_HEAD}^{{tree}}"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert rebuilt_local_tree == live_local_tree
    subprocess.run(["git", "reset", "--mixed", "HEAD"], cwd=candidate, check=True, capture_output=True)

    # The remaining patches are ordered personal overlays on top of that exact dependency state.
    for rel, expected_sha in ANTIGRAVITY_PATCH_CHAIN[1:]:
        patch = repo / rel
        assert patch.is_file(), f"Antigravity patch missing: {patch}"
        assert hashlib.sha256(patch.read_bytes()).hexdigest() == expected_sha
        subprocess.run(["git", "apply", "--check", str(patch)], cwd=candidate, check=True)
        subprocess.run(["git", "apply", str(patch)], cwd=candidate, check=True)

    models_py = (candidate / "src/antigravity_provider/models.py").read_text(encoding="utf-8")
    assert 'DEFAULT_MODEL = "gemini-3.8-flash"' in models_py
    assert '"gemini-3.8-flash"' in models_py
    assert "antigravity-preview-09-2026" not in models_py

    diff_check = subprocess.run(
        ["git", "diff", "--check"], cwd=candidate, capture_output=True, text=True
    )
    assert diff_check.returncode == 0, diff_check.stderr or diff_check.stdout


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
