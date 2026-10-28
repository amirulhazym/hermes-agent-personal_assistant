from __future__ import annotations

import hashlib
import importlib.util
import os
import subprocess
import sys
import tracemalloc
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts/guard/candidate_delta_scan.py"
SPEC = importlib.util.spec_from_file_location("candidate_delta_scan", MODULE_PATH)
assert SPEC and SPEC.loader
SCAN = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = SCAN
SPEC.loader.exec_module(SCAN)

WHITESPACE_PATH = ROOT / "scripts/guard/whitespace_review.py"
WHITESPACE_SPEC = importlib.util.spec_from_file_location("whitespace_review", WHITESPACE_PATH)
assert WHITESPACE_SPEC and WHITESPACE_SPEC.loader
WHITESPACE = importlib.util.module_from_spec(WHITESPACE_SPEC)
sys.modules[WHITESPACE_SPEC.name] = WHITESPACE
WHITESPACE_SPEC.loader.exec_module(WHITESPACE)


def git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        env=env,
        capture_output=True,
    )


def git_storage_snapshot(repo: Path) -> tuple[dict, tuple | None]:
    def git_path(name: str) -> Path:
        raw = subprocess.check_output(
            ["git", "-C", str(repo), "rev-parse", "--git-path", name], text=True
        ).strip()
        path = Path(raw)
        return (path if path.is_absolute() else repo / path).resolve()

    objects = git_path("objects")
    object_snapshot = {
        str(path.relative_to(objects)):
            (path.stat().st_size, path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())
        for path in objects.rglob("*")
        if path.is_file()
    }
    index = git_path("index")
    index_snapshot = (
        (index.stat().st_size, index.stat().st_mtime_ns, hashlib.sha256(index.read_bytes()).hexdigest())
        if index.is_file()
        else None
    )
    return object_snapshot, index_snapshot


def make_repo(tmp_path: Path, name: str = "repo") -> tuple[Path, Path]:
    repo = tmp_path / name
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-q", "-m", "base")
    candidate_root = repo / ".scratch" / "candidate"
    candidate_root.mkdir(parents=True)
    return repo, candidate_root


def test_manifest_covers_tracked_untracked_ignored_nested_repo_and_symlink(tmp_path: Path):
    repo = tmp_path / "repo"
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / ".gitignore").write_text("*.ignored\n", encoding="utf-8")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    (repo / "unstaged.txt").write_text("base\n", encoding="utf-8")
    (repo / "deleted.txt").write_text("base\n", encoding="utf-8")
    git(repo, "add", ".gitignore", "tracked.txt", "unstaged.txt", "deleted.txt")
    git(repo, "commit", "-q", "-m", "base")

    (repo / "tracked.txt").write_text("staged change\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    (repo / "unstaged.txt").write_text("unstaged change\n", encoding="utf-8")
    (repo / "deleted.txt").unlink()
    (repo / "ordinary-untracked.txt").write_text("ordinary\n", encoding="utf-8")
    newline_path = repo / "line\nbreak.txt"
    newline_path.write_text("newline path\n", encoding="utf-8")

    candidate_root = repo / ".scratch" / "candidate"
    candidate_root.mkdir(parents=True)
    (candidate_root / "ignored.ignored").write_text("ignored but in scope\n", encoding="utf-8")
    (candidate_root / "candidate.md").write_text("candidate\n", encoding="utf-8")
    nested = candidate_root / "unborn-repo"
    subprocess.run(["git", "init", "-q", "-b", "main", str(nested)], check=True)
    (nested / "nested.txt").write_text("nested repo content\n", encoding="utf-8")
    outside_target = tmp_path / "outside-target.txt"
    outside_target.write_text("must not be followed\n", encoding="utf-8")
    (candidate_root / "target-link").symlink_to(outside_target)

    before = git_storage_snapshot(repo)
    manifest = SCAN.collect_delta_manifest(repo, candidate_root)
    after = git_storage_snapshot(repo)

    entries = {entry.path: entry for entry in manifest.entries}
    expected = {
        "tracked.txt",
        "unstaged.txt",
        "deleted.txt",
        "ordinary-untracked.txt",
        "line\nbreak.txt",
        ".scratch/candidate/ignored.ignored",
        ".scratch/candidate/candidate.md",
        ".scratch/candidate/unborn-repo/nested.txt",
        ".scratch/candidate/target-link",
    }
    assert expected <= set(entries)
    assert len(entries) == len(manifest.entries), "manifest must deduplicate paths"
    assert entries["tracked.txt"].tracked is True
    assert entries["unstaged.txt"].tracked is True
    assert entries["deleted.txt"].kind == "deleted"
    assert entries[".scratch/candidate/target-link"].kind == "symlink"
    assert not any(".git" in Path(path).parts for path in entries)
    assert str(outside_target) not in entries
    assert before == after, "manifest collection must not mutate the source Git index/object database"
    assert manifest.digest and len(manifest.digest) == 64


def test_scanner_redacts_secret_findings_and_does_not_follow_symlink(tmp_path: Path):
    repo = tmp_path / "scan-repo"
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / ".gitignore").write_text("*.ignored\n", encoding="utf-8")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    git(repo, "add", ".gitignore", "tracked.txt")
    git(repo, "commit", "-q", "-m", "base")

    candidate_root = repo / ".scratch" / "candidate"
    candidate_root.mkdir(parents=True)
    fake_key = "sk-" + ("A" * 48)
    fake_email = "person" + "@" + "research.example"
    (candidate_root / "candidate.txt").write_text(f"{fake_key}\ncontact: {fake_email}\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text(f"{fake_key}\n", encoding="utf-8")
    (candidate_root / "outside-link").symlink_to(outside)

    manifest = SCAN.collect_delta_manifest(repo, candidate_root)
    result = SCAN.scan_manifest(manifest, allowlist=[])

    assert result.status == "FAIL"
    assert any(f.path == ".scratch/candidate/candidate.txt" and f.rule == "openai-key" for f in result.findings)
    assert any(f.path == ".scratch/candidate/candidate.txt" and f.rule == "email-like" for f in result.findings)
    assert not any(f.path == ".scratch/candidate/outside-link" for f in result.findings)
    assert fake_key not in repr(result)
    assert fake_email not in repr(result)


def test_direct_whitespace_helper_uses_exact_allowlist_identity():
    path = ".scratch/candidate/note.md"
    allowlist = [{
        "path": path,
        "line": 1,
        "trailing_ws": 2,
        "body_sha256": hashlib.sha256(b"intentional break").hexdigest(),
        "kind": "markdown-hard-break",
    }]

    approved = WHITESPACE.issues_from_bytes(path, b"intentional break  \n", allowlist)
    allowed, unexpected = WHITESPACE.evaluate_issues(approved, allowlist)
    assert len(allowed) == 1
    assert unexpected == []

    changed = WHITESPACE.issues_from_bytes(path, b"different text  \n", allowlist)
    allowed, unexpected = WHITESPACE.evaluate_issues(changed, allowlist)
    assert allowed == []
    assert len(unexpected) == 1


def test_candidate_walk_fails_closed_if_directory_is_swapped_to_symlink(tmp_path: Path, monkeypatch):
    repo = tmp_path / "race-repo"
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "base.txt").write_text("base\n", encoding="utf-8")
    git(repo, "add", "base.txt")
    git(repo, "commit", "-q", "-m", "base")

    candidate_root = repo / ".scratch" / "candidate"
    nested = candidate_root / "nested"
    nested.mkdir(parents=True)
    (nested / "safe.txt").write_text("inside\n", encoding="utf-8")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "safe.txt").write_text("outside replacement\n", encoding="utf-8")
    (outside / "outside-only.txt").write_text("must not enter manifest\n", encoding="utf-8")

    original_open = SCAN.os.open
    swapped = False

    def swap_before_directory_open(path, flags, *args, **kwargs):
        nonlocal swapped
        if path == "nested" and kwargs.get("dir_fd") is not None and not swapped:
            nested.rename(candidate_root / "nested-original")
            nested.symlink_to(outside, target_is_directory=True)
            swapped = True
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(SCAN.os, "open", swap_before_directory_open)
    with pytest.raises(SCAN.ManifestError, match="directory open failed"):
        SCAN.collect_delta_manifest(repo, candidate_root)

    assert swapped is True
    assert (outside / "outside-only.txt").exists()


def test_manifest_entry_reader_reads_symlink_text_not_target_bytes(tmp_path: Path):
    repo = tmp_path / "read-repo"
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-q", "-m", "base")

    candidate_root = repo / ".scratch" / "candidate"
    candidate_root.mkdir(parents=True)
    regular = candidate_root / "plain.txt"
    regular.write_bytes(b"plain candidate bytes\n")
    fake_key = b"sk-" + (b"A" * 48)
    target = tmp_path / "outside-target.txt"
    target.write_bytes(fake_key)
    link = candidate_root / "link.txt"
    link.symlink_to(target)

    manifest = SCAN.collect_delta_manifest(repo, candidate_root)
    entries = {entry.path: entry for entry in manifest.entries}

    assert SCAN._read_entry_bytes(manifest, entries[".scratch/candidate/plain.txt"]) == b"plain candidate bytes\n"
    link_bytes = SCAN._read_entry_bytes(manifest, entries[".scratch/candidate/link.txt"])
    assert link_bytes == os.fsencode(str(target))
    assert fake_key not in link_bytes


def test_scan_manifest_applies_allowlist_to_untracked_bytes(tmp_path: Path):
    repo = tmp_path / "whitespace-repo"
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    (repo / "tracked.txt").write_text("base\n", encoding="utf-8")
    git(repo, "add", "tracked.txt")
    git(repo, "commit", "-q", "-m", "base")

    candidate_root = repo / ".scratch" / "candidate"
    candidate_root.mkdir(parents=True)
    note = candidate_root / "note.md"
    note.write_bytes(b"intentional break  \n")
    path = ".scratch/candidate/note.md"
    allowlist = [{
        "path": path,
        "line": 1,
        "trailing_ws": 2,
        "body_sha256": hashlib.sha256(b"intentional break").hexdigest(),
        "kind": "markdown-hard-break",
    }]

    passing = SCAN.scan_manifest(SCAN.collect_delta_manifest(repo, candidate_root), allowlist=allowlist)
    assert passing.status == "PASS"
    assert passing.findings == ()

    note.write_bytes(b"changed body  \n")
    failing = SCAN.scan_manifest(SCAN.collect_delta_manifest(repo, candidate_root), allowlist=allowlist)
    assert failing.status == "FAIL"
    assert any(f.path == path and f.rule == "trailing-whitespace" and f.count == 1 for f in failing.findings)


def test_scan_manifest_uses_git_diff_check_for_tracked_whitespace(tmp_path: Path):
    repo = tmp_path / "tracked-whitespace-repo"
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.invalid")
    tracked = repo / "tracked.txt"
    plus_tracked = repo / "+tracked.txt"
    tracked.write_bytes(b"base\n")
    plus_tracked.write_bytes(b"base\n")
    git(repo, "add", "tracked.txt", "+tracked.txt")
    git(repo, "commit", "-q", "-m", "base")

    candidate_root = repo / ".scratch" / "candidate"
    candidate_root.mkdir(parents=True)
    tracked.write_bytes(b"changed body  \n")
    plus_tracked.write_bytes(b"literal:2: trailing whitespace.  \n")

    result = SCAN.scan_manifest(SCAN.collect_delta_manifest(repo, candidate_root), allowlist=[])

    assert result.status == "FAIL"
    assert any(f.path == "tracked.txt" and f.rule == "trailing-whitespace" and f.count == 1 for f in result.findings)
    assert any(f.path == "+tracked.txt" and f.rule == "trailing-whitespace" and f.count == 1 for f in result.findings)


def test_git_query_failure_is_manifest_failure(tmp_path: Path, monkeypatch):
    repo, candidate_root = make_repo(tmp_path, "git-query-failure")
    original_run = SCAN.subprocess.run

    def fail_diff(*args, **kwargs):
        command = args[0]
        if command[:2] == ["git", "diff"]:
            return subprocess.CompletedProcess(command, 23, stdout=b"", stderr=b"synthetic failure")
        return original_run(*args, **kwargs)

    monkeypatch.setattr(SCAN.subprocess, "run", fail_diff)
    with pytest.raises(SCAN.ManifestError, match="rc=23"):
        SCAN.collect_delta_manifest(repo, candidate_root)


def test_unsupported_filesystem_node_fails_closed(tmp_path: Path):
    repo, candidate_root = make_repo(tmp_path, "unsupported-node")
    os.mkfifo(candidate_root / "named-pipe")

    with pytest.raises(SCAN.ManifestError, match="unsupported filesystem node"):
        SCAN.collect_delta_manifest(repo, candidate_root)


def test_unreadable_file_fails_scan(tmp_path: Path, monkeypatch):
    repo, candidate_root = make_repo(tmp_path, "unreadable-file")
    target = candidate_root / "unreadable.txt"
    target.write_text("candidate bytes\n", encoding="utf-8")
    manifest = SCAN.collect_delta_manifest(repo, candidate_root)
    original_open = SCAN.os.open

    def deny_target(path, flags, *args, **kwargs):
        if path == "unreadable.txt" and kwargs.get("dir_fd") is not None:
            raise PermissionError("synthetic inaccessible file")
        return original_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(SCAN.os, "open", deny_target)
    result = SCAN.scan_manifest(manifest, allowlist=[])

    assert result.status == "FAIL"
    assert any("unreadable.txt" in error and "PermissionError" in error for error in result.errors)


def test_missing_file_after_manifest_collection_fails_scan(tmp_path: Path):
    repo, candidate_root = make_repo(tmp_path, "missing-file")
    target = candidate_root / "vanishes.txt"
    target.write_text("candidate\n", encoding="utf-8")
    manifest = SCAN.collect_delta_manifest(repo, candidate_root)
    target.unlink()

    result = SCAN.scan_manifest(manifest, allowlist=[])

    assert result.status == "FAIL"
    assert any("read failed" in error for error in result.errors)
    assert any("path manifest or file metadata changed during scan" in error for error in result.errors)


def test_broken_symlink_fails_scan_without_reading_target(tmp_path: Path):
    repo, candidate_root = make_repo(tmp_path, "broken-link")
    (candidate_root / "broken-link").symlink_to(tmp_path / "missing-target")
    manifest = SCAN.collect_delta_manifest(repo, candidate_root)

    result = SCAN.scan_manifest(manifest, allowlist=[])

    assert result.status == "FAIL"
    assert any("read failed" in error and "broken-link" in error for error in result.errors)


def test_detector_exception_fails_scan_and_redacts_exception_text(tmp_path: Path, monkeypatch):
    repo, candidate_root = make_repo(tmp_path, "detector-error")
    (candidate_root / "candidate.txt").write_text("synthetic detector input\n", encoding="utf-8")
    manifest = SCAN.collect_delta_manifest(repo, candidate_root)
    original_loader = SCAN._load_rule_module

    def loader(name, filename):
        module = original_loader(name, filename)
        if filename == "secret_scan.py":
            def fail_findings(_path, _data):
                raise RuntimeError("do not expose detector exception contents")
            module.findings = fail_findings
        return module

    monkeypatch.setattr(SCAN, "_load_rule_module", loader)
    result = SCAN.scan_manifest(manifest, allowlist=[])

    assert result.status == "FAIL"
    assert any("secret scanner failed" in error for error in result.errors)
    assert "do not expose detector exception contents" not in repr(result)


@pytest.mark.parametrize("mutation", ["add", "remove", "replace"])
def test_path_set_or_metadata_mutation_during_scan_fails_closed(tmp_path: Path, monkeypatch, mutation: str):
    repo, candidate_root = make_repo(tmp_path, f"mutation-{mutation}")
    first = candidate_root / "a-trigger.txt"
    target = candidate_root / "z-target.txt"
    first.write_text("trigger\n", encoding="utf-8")
    target.write_text("original target\n", encoding="utf-8")
    manifest = SCAN.collect_delta_manifest(repo, candidate_root)
    original_reader = SCAN._read_entry_bytes
    mutated = False

    def mutate_after_first_read(current_manifest, entry):
        nonlocal mutated
        data = original_reader(current_manifest, entry)
        if entry.path == ".scratch/candidate/a-trigger.txt" and not mutated:
            mutated = True
            if mutation == "add":
                (candidate_root / "new-during-scan.txt").write_text("added\n", encoding="utf-8")
            elif mutation == "remove":
                target.unlink()
            else:
                replacement = candidate_root / "replacement.tmp"
                replacement.write_text("replacement content\n", encoding="utf-8")
                replacement.replace(target)
        return data

    monkeypatch.setattr(SCAN, "_read_entry_bytes", mutate_after_first_read)
    result = SCAN.scan_manifest(manifest, allowlist=[])

    assert mutated is True
    assert result.status == "FAIL"
    assert result.errors


def test_scan_reads_files_sequentially_with_bounded_peak_memory(tmp_path: Path):
    repo, candidate_root = make_repo(tmp_path, "resource-bound")
    file_count = 35
    file_size = 5 * 1024 * 1024
    for index in range(file_count):
        path = candidate_root / f"part-{index:02d}.bin"
        with path.open("wb") as handle:
            handle.truncate(file_size)
    manifest = SCAN.collect_delta_manifest(repo, candidate_root)

    tracemalloc.start()
    try:
        result = SCAN.scan_manifest(manifest, allowlist=[])
        _current, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()

    total_payload_bytes = file_count * file_size
    assert result.status == "PASS"
    assert result.scanned_count >= file_count
    assert peak_bytes < total_payload_bytes * 0.5, (
        f"peak Python allocation {peak_bytes} suggests candidate bytes are retained together"
    )
