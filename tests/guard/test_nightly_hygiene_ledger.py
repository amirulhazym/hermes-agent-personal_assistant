"""RED tests for the 23:55 nightly hygiene truncation + classification ledger.

Bug reproduced 2026-11-19: `_workflow_run_cmd` returned `output[-4000:]`, so any
Git output longer than 4,000 chars silently lost its head. The nightly report
therefore printed "53 fail kerja" every night (the number of lines that survive
a 4,000-char tail), lost 35 real paths, and rendered one path as
`rovider-refresh-…` because the parser reads `line[:2]` as the status code.

These tests pin: full output for parsing, known-local classification, fail-safe
ledger handling, and an owner-facing report that caps the path list without
mangling long paths.
"""
from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "nightly_git_hygiene.py"
SPEC = importlib.util.spec_from_file_location("nightly_git_hygiene_ledger_tests", MODULE_PATH)
assert SPEC and SPEC.loader
HYGIENE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = HYGIENE
SPEC.loader.exec_module(HYGIENE)


def _git(repo: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout.strip()


def _make_repo(tmp_path: Path, n_files: int) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    _git(repo, "add", "README.md")
    _git(repo, "commit", "-q", "-m", "base")
    for i in range(n_files):
        # long-ish names so status output comfortably exceeds 4,000 chars
        d = repo / ".scratch"
        d.mkdir(exist_ok=True)
        (d / f"file-with-a-deliberately-long-name-{i:03d}.md").write_text("x\n", encoding="utf-8")
    return repo


def test_run_cmd_default_cap_is_preserved_but_uncapped_is_available(tmp_path):
    """Default behaviour keeps the 4,000-char cap; callers can opt out."""
    cmd = [sys.executable, "-c", "print('x' * 5000)"]
    _, capped = HYGIENE._workflow_run_cmd(cmd, cwd=tmp_path)
    assert len(capped) == 4000

    _, full = HYGIENE._workflow_run_cmd(cmd, cwd=tmp_path, max_output_chars=None)
    assert len(full) == 5000


def test_inspect_git_sees_every_status_record_above_4000_chars(tmp_path):
    """The audit must parse the full `git status` output, not a 4,000-char tail."""
    repo = _make_repo(tmp_path, n_files=120)
    home = tmp_path / "hermes_home"
    home.mkdir()

    raw = _git(repo, "status", "--porcelain", "--untracked-files=all")
    assert len(raw) > 4000, "fixture must exceed the historical 4,000-char cap"

    snapshot = HYGIENE._inspect_git(repo, HYGIENE._as_myt(None), home=home)
    records = snapshot["git_state"]["status_records"]
    assert len(records) == 120, f"expected 120 records, got {len(records)}"

    paths = {r["path"] for r in records}
    assert ".scratch/file-with-a-deliberately-long-name-000.md" in paths
    # no record may be a fragment of a path (the old `rovider-refresh-…` artefact)
    for path in paths:
        assert path.startswith((".scratch/", "README.md")), f"suspicious path: {path!r}"


def test_scratch_paths_are_known_local_by_default(tmp_path):
    records = HYGIENE._status_records("?? .scratch/foo/bar.md\n?? scripts/new.py")
    ledger = {"approved_prefixes": []}
    result = HYGIENE.classify_status_records(records, ledger)
    assert [r["path"] for r in result["known_local"]] == [".scratch/foo/bar.md"]
    assert [r["path"] for r in result["unclassified"]] == ["scripts/new.py"]
    assert result["tracked_changes"] == []


def test_tracked_change_is_never_classified_known_local(tmp_path):
    records = HYGIENE._status_records(" M scripts/nightly_git_hygiene.py")
    ledger = {"approved_prefixes": ["scripts/"]}
    result = HYGIENE.classify_status_records(records, ledger)
    assert result["known_local"] == []
    assert [r["path"] for r in result["tracked_changes"]] == ["scripts/nightly_git_hygiene.py"]


def test_approved_prefix_covers_untracked_docs(tmp_path):
    records = HYGIENE._status_records("?? docs/superpowers/plans/x.md\n?? docs/random.md")
    ledger = {"approved_prefixes": ["docs/superpowers/"]}
    result = HYGIENE.classify_status_records(records, ledger)
    assert [r["path"] for r in result["known_local"]] == ["docs/superpowers/plans/x.md"]
    assert [r["path"] for r in result["unclassified"]] == ["docs/random.md"]


def test_corrupt_or_missing_ledger_fails_safe(tmp_path):
    home = tmp_path / "hermes_home"
    home.mkdir()
    assert HYGIENE._load_ledger(home) == {"approved_prefixes": []}

    state = home / "state"
    state.mkdir()
    (state / "nightly_git_hygiene_ledger.json").write_text("{not json", encoding="utf-8")
    assert HYGIENE._load_ledger(home) == {"approved_prefixes": []}


def test_approve_prefix_persists_and_is_idempotent(tmp_path):
    home = tmp_path / "hermes_home"
    home.mkdir()
    HYGIENE._approve_prefix(home, "docs/reconciliation/manifest-receipts/")
    HYGIENE._approve_prefix(home, "docs/reconciliation/manifest-receipts/")
    ledger = HYGIENE._load_ledger(home)
    assert ledger["approved_prefixes"] == ["docs/reconciliation/manifest-receipts/"]

    records = HYGIENE._status_records("?? docs/reconciliation/manifest-receipts/a.json")
    result = HYGIENE.classify_status_records(records, ledger)
    assert len(result["known_local"]) == 1


def test_build_actions_holds_only_for_unclassified_paths(tmp_path):
    home = tmp_path / "hermes_home"
    home.mkdir()
    snapshot = {
        "git_state": {
            "branch": "main",
            "head": "a" * 40,
            "is_clean": False,
            "status_porcelain": ["?? .scratch/x.md", "?? scripts/y.py"],
            "status_records": HYGIENE._status_records("?? .scratch/x.md\n?? scripts/y.py"),
        },
        "sync_state": {"origin": {"ahead": 0, "behind": 0, "remote_head": "a" * 40}},
        "daily_delta": {"commits": []},
        "branches": {"retained": []},
        "errors": [],
        "file_classification": HYGIENE.classify_status_records(
            HYGIENE._status_records("?? .scratch/x.md\n?? scripts/y.py"),
            HYGIENE._load_ledger(home),
        ),
    }
    actions, holds, _classification = HYGIENE._build_actions(snapshot)
    joined = " ".join(holds)
    assert "scripts/y.py" in joined
    assert ".scratch/x.md" not in joined


def test_human_report_caps_paths_and_keeps_long_path_intact():
    long_path = "scripts/opencode/" + ("a" * 90) + ".py"
    paths = [long_path] + [f"tests/guard/test_new_{i}.py" for i in range(20)]
    records = [{"status": "??", "path": p, "untracked": True, "deleted": False,
                "conflict": False, "is_generated_receipt": False} for p in paths]
    result = {
        "status": "HOLD",
        "date": "2026-11-19",
        "run_id": "run-test",
        "git_state": {
            "branch": "main",
            "head": "a" * 40,
            "is_clean": False,
            "status_porcelain": [f"?? {p}" for p in paths],
            "status_records": records,
        },
        "sync_state": {"origin": {"ahead": 0, "behind": 0}},
        "daily_delta": {"commits": []},
        "branches": {"retained": []},
        "gates": {},
        "holds": ["dirty work requires owner classification; no automated commit: " + ", ".join(paths)],
        "errors": [],
        "file_summary": {
            "unclassified": len(paths),
            "known_local": 0,
            "tracked_changes": 0,
            "delta": "+21 fail baru berbanding semalam",
        },
    }
    report = HYGIENE._human_report(result)

    assert long_path in report, "long paths must render complete, never truncated"
    listed = [line for line in report.splitlines() if line.startswith("   - ")]
    assert len(listed) <= 8, f"path list must be capped, got {len(listed)}"
    assert "lagi" in report, "capped list must say how many are omitted"
    assert len(report) < 2000, f"report too long for a phone message: {len(report)} chars"
