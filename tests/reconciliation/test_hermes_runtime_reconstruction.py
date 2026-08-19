from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
LOCK = REPO / "docs/reconciliation/hermes-runtime-source-lock.json"
TREE = REPO / "docs/reconciliation/hermes-runtime-tree-manifest.json"
RECONSTRUCT = REPO / "scripts/reconstruct_hermes_runtime.py"
LIVE_UPSTREAM = Path("/home/ubuntu/.hermes/hermes-agent")
LIVE_BASE = "a31be48030f60383bf4c1d96ba46bd4b48430218"


def run_reconstruct(output: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO)
    return subprocess.run(
        [
            sys.executable,
            str(RECONSTRUCT),
            "--lock",
            str(LOCK),
            "--tree-manifest",
            str(TREE),
            "--base-repo",
            str(LIVE_UPSTREAM),
            "--output",
            str(output),
            "--validate",
        ],
        cwd=REPO,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_runtime_lock_has_one_authoritative_reconstruction_path():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))

    assert lock["schema_version"] == 1
    assert lock["authority"] == "hermes-runtime-reconstruction"
    assert lock["official_repository"] == "https://github.com/NousResearch/hermes-agent.git"
    assert lock["official_base_sha"] == LIVE_BASE
    assert isinstance(lock["patch_series"], list)
    assert [entry["order"] for entry in lock["patch_series"]] == sorted(
        entry["order"] for entry in lock["patch_series"]
    )
    assert lock["runtime_tree_manifest"] == "docs/reconciliation/hermes-runtime-tree-manifest.json"

    reference_paths = {item["path"] for item in lock["non_authoritative_tracked_paths"]}
    assert "hermes_state.py" in reference_paths
    assert "gateway/slash_commands.py" in reference_paths
    assert all(
        item["disposition"] == "reference-only"
        for item in lock["non_authoritative_tracked_paths"]
    )


def test_reconstruction_from_pinned_local_official_commit(tmp_path: Path):
    result = run_reconstruct(tmp_path / "hermes-agent")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "RECONSTRUCTION PASS" in result.stdout
    assert (tmp_path / "hermes-agent" / "gateway" / "session.py").is_file()
    assert (tmp_path / "hermes-agent" / "hermes_state_common.py").is_file()
    assert not (tmp_path / "hermes-agent" / "state.db").exists()


def test_tree_manifest_is_explicit_and_matches_lock():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    tree = json.loads(TREE.read_text(encoding="utf-8"))

    assert tree["schema_version"] == 1
    assert tree["base_sha"] == lock["official_base_sha"]
    assert tree["destination_root"] == lock["runtime_destination_root"]
    assert tree["entries"]
    assert all(
        set(entry) == {"source", "destination", "sha256", "mode"}
        for entry in tree["entries"]
    )
    assert len({entry["source"] for entry in tree["entries"]}) == len(tree["entries"])
    assert len({entry["destination"] for entry in tree["entries"]}) == len(tree["entries"])
    assert all(
        entry["destination"].startswith("/home/ubuntu/.hermes/hermes-agent/")
        for entry in tree["entries"]
    )


def test_c2_uses_the_pinned_official_reset_boundary_patch():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    assert lock["patch_series"][:1] == [
        {
            "order": 1,
            "id": "official-pr-85505-reset-boundary",
            "path": "patches/upstream-hermes/2026-08-19_pr85505-reset-boundary.patch",
            "sha256": "734a183f5a046d84046bee12d00eed60fb04720187b35dc894473cf74a7c2082",
            "description": "Official NousResearch/Hermes-Agent PR #85505: durable reset markers, legacy reset-child stabilization, reset-aware listing, and resume-boundary fencing.",
        }
    ]


def test_c3_is_ordered_after_c2_and_hash_pinned():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    assert lock["patch_series"][1] == {
        "order": 2,
        "id": "custom-c3-unbounded-cycle-safe-lineage",
        "path": "patches/upstream-hermes/2026-08-19_c3-unbounded-cycle-safe-lineage.patch",
        "sha256": "a3ce5e3447e1bd066144fa2d2391957f701b358aaf6a948978782255b6ba3498",
        "description": "Custom cycle-safe, data-dependent traversal shared by compression-tip and parent-lineage resolution; removes the fixed 100-hop failure and adds 218-hop/cycle regressions.",
    }


def test_c4_is_ordered_after_c3_and_hash_pinned():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    assert lock["patch_series"][2] == {
        "order": 3,
        "id": "custom-c4-shared-session-identity",
        "path": "patches/upstream-hermes/2026-08-19_c4-shared-session-identity.patch",
        "sha256": "8afbfc7e1a5602a8ad0e8388b5538505963164d4c731ad4ab4978eb269a3406c",
        "description": "Custom shared session identity projection: numeric gateway resume uses the same activity-ordered listing policy, resume follows compression continuations only, and search deduplicates only compression edges while retaining physical continuation titles.",
    }
