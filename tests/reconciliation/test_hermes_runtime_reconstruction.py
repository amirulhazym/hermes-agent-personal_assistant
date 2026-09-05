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
LIVE_BASE = "a9611f3c6f7ff287a4f10f71a77d7c5a808ea1c8"


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


def test_active_runtime_overlays_are_ordered_and_hash_pinned():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    assert lock["patch_series"] == [
        {
            "order": 1,
            "id": "live-runtime-auxiliary-middleware-route",
            "path": "patches/upstream-hermes/2026-08-28_live-auxiliary-middleware-route.patch",
            "sha256": "e6f42cfc76ecf9b8c9c75a665ebe79b7ffc16f708056de3646cef6936b785f41",
            "description": "Current live runtime overlay: route auxiliary sync completions through llm_execution middleware.",
        },
        {
            "order": 2,
            "id": "live-runtime-goal-resume-counter-reset",
            "path": "patches/upstream-hermes/2026-08-28_live-goal-resume-counter-reset.patch",
            "sha256": "52b0827a7c04fa4e2a7e8247597465af6f2666bc61d437eab78c46bde8981e96",
            "description": "Current live runtime overlay: reset goal transport/parse failure counters on resume.",
        },
        {
            "order": 3,
            "id": "candidate-runtime-harden-auxiliary-middleware-fail-closed",
            "path": "patches/upstream-hermes/2026-08-28_harden-auxiliary-middleware-fail-closed.patch",
            "sha256": "afa7cfdfc0c73b179543336496097e3193d2e8b3203031dfd9a29aed9d075eb3",
            "description": "Candidate hardening overlay: fail closed when auxiliary execution middleware raises; not live-applied.",
        },
        {
            "order": 4,
            "id": "candidate-runtime-bounded-main-turn-auto-continue",
            "path": "patches/upstream-hermes/2026-09-05_bounded-main-turn-auto-continue.patch",
            "sha256": "dd6db0f5690297e236d23697cfa27e2b54c09ecc363f894a208446e1933165a8",
            "description": "Live runtime overlay: main CLI/gateway bounded progress-aware continuation after a 300-iteration window; live-applied 2026-09-05.",
        },
    ]


def test_historical_overlays_are_retained_as_source_only():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    historical = {item["path"] for item in lock["historical_source_only_overlays"]}
    assert historical == {
        "patches/upstream-hermes/2026-08-19_pr85505-reset-boundary.patch",
        "patches/upstream-hermes/2026-08-19_c3-unbounded-cycle-safe-lineage.patch",
        "patches/upstream-hermes/2026-08-19_c4-shared-session-identity.patch",
        "patches/upstream-hermes/2026-08-28_live-core-usage-and-billing-route.patch",
    }
