from __future__ import annotations

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


def test_hermes_agent_live_parity_with_main_repo_patches():
    """Verify live hermes-agent checkout has zero unrepresented drift."""
    live_core = Path("/home/ubuntu/.hermes/hermes-agent")
    patch_picker = Path("/home/ubuntu/hermes-agent-personal_assistant-work/patches/upstream-hermes/2026-09-04_live_model_picker_refresh.patch")

    assert live_core.exists(), "live hermes-agent directory must exist"
    assert patch_picker.exists(), "model picker refresh patch must exist in main repo"

    # Reverse check against live working tree
    res = subprocess.run(
        ["git", "apply", "--check", "--reverse", str(patch_picker)],
        cwd=live_core,
        capture_output=True,
        text=True,
    )
    assert res.returncode == 0, f"Live hermes-agent tree drifted from main repo patch: {res.stderr}"

    # Check that no uncommitted modifications exist outside tracked patch
    res_status = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=live_core,
        capture_output=True,
        text=True,
    )
    untracked = [line for line in res_status.stdout.splitlines() if line.startswith("??") and not line.endswith("DO_NOT_EDIT_LIVE_RUNTIME.md")]
    assert not untracked, f"Unrepresented untracked files in live hermes-agent checkout: {untracked}"
