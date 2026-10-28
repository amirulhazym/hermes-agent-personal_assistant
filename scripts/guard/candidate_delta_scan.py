from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


@dataclass(frozen=True)
class FileIdentity:
    device: int
    inode: int
    mode: int
    size: int
    mtime_ns: int
    ctime_ns: int

    @classmethod
    def from_stat(cls, value: os.stat_result) -> "FileIdentity":
        return cls(
            device=value.st_dev,
            inode=value.st_ino,
            mode=value.st_mode,
            size=value.st_size,
            mtime_ns=value.st_mtime_ns,
            ctime_ns=value.st_ctime_ns,
        )


@dataclass(frozen=True)
class ManifestEntry:
    path: str
    kind: str
    tracked: bool
    sources: frozenset[str]
    identity: FileIdentity | None


@dataclass(frozen=True)
class DeltaManifest:
    repo: Path
    candidate_root: Path | None
    entries: tuple[ManifestEntry, ...]
    digest: str
    excluded_count: int


@dataclass(frozen=True)
class ScanFinding:
    path: str
    rule: str
    count: int = 1


@dataclass(frozen=True)
class ScanResult:
    status: str
    scanned_count: int
    deleted_count: int
    excluded_count: int
    manifest_digest: str
    findings: tuple[ScanFinding, ...]
    errors: tuple[str, ...]


class ManifestError(RuntimeError):
    """Collection failed; callers must map this to a hard FAIL."""


def _escaped(path: str) -> str:
    return json.dumps(path, ensure_ascii=True)


def _git_environment() -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_COMMON_DIR",
    ):
        env.pop(key, None)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return env


def _git_paths(repo: Path, args: list[str]) -> list[bytes]:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=repo,
            env=_git_environment(),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise ManifestError(f"Git query failed ({type(exc).__name__})") from None
    if result.returncode:
        raise ManifestError(f"Git query failed (rc={result.returncode})")
    raw = result.stdout
    if raw and not raw.endswith(b"\0"):
        raise ManifestError("Git path query returned a non-NUL-terminated manifest")
    return [path for path in raw.split(b"\0") if path]


def _safe_relative_path(raw_path: bytes) -> str:
    path = os.fsdecode(raw_path)
    parsed = PurePosixPath(path)
    if parsed.is_absolute() or ".." in parsed.parts or not parsed.parts:
        raise ManifestError(f"invalid Git path={_escaped(path)}")
    return path


def _open_directory_chain(base: Path, components: tuple[str, ...]) -> int:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise ManifestError("platform lacks required no-follow directory-open flags")
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
    fd = os.open(base, flags)
    try:
        for component in components:
            next_fd = os.open(component, flags, dir_fd=fd)
            os.close(fd)
            fd = next_fd
        return fd
    except OSError:
        os.close(fd)
        raise


def _lstat_relative(repo: Path, relative_path: str) -> os.stat_result:
    components = PurePosixPath(relative_path).parts
    if not components:
        raise ManifestError("empty relative path")
    parent_fd = _open_directory_chain(repo, components[:-1])
    try:
        return os.stat(components[-1], dir_fd=parent_fd, follow_symlinks=False)
    finally:
        os.close(parent_fd)


def _validate_candidate_root(repo: Path, candidate_root: Path | None) -> Path | None:
    if candidate_root is None:
        return None
    candidate = candidate_root if candidate_root.is_absolute() else repo / candidate_root
    candidate = Path(os.path.abspath(candidate))
    try:
        relative = candidate.relative_to(repo)
    except ValueError:
        raise ManifestError("candidate root is outside the repository") from None
    if not relative.parts:
        raise ManifestError("candidate root cannot be the repository root")
    if not candidate.exists():
        return None
    try:
        fd = _open_directory_chain(repo, relative.parts)
        os.close(fd)
    except OSError as exc:
        raise ManifestError(f"candidate root is not a no-follow directory ({type(exc).__name__})") from None
    return candidate


def _file_kind(info: os.stat_result, path: str) -> str:
    if stat.S_ISREG(info.st_mode):
        return "file"
    if stat.S_ISLNK(info.st_mode):
        return "symlink"
    raise ManifestError(f"unsupported filesystem node path={_escaped(path)}")


def collect_delta_manifest(repo: Path, candidate_root: Path | None = None) -> DeltaManifest:
    """Collect Git delta paths plus every non-`.git` candidate-root file, no-follow.

    Git discovery is read-only: no index refresh, staging, temporary index,
    object writes, cloning, or checkout operations occur here.
    """
    repo = Path(repo).resolve(strict=True)
    if not repo.is_dir():
        raise ManifestError("repository path is not a directory")
    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo,
            env=_git_environment(),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        raise ManifestError(f"Git root query failed ({type(exc).__name__})") from None
    if top.returncode or Path(top.stdout.strip()).resolve() != repo:
        raise ManifestError("repo must be the Git worktree root")
    candidate_root = _validate_candidate_root(repo, Path(candidate_root) if candidate_root is not None else None)

    tracked_paths = _git_paths(repo, ["diff", "--no-renames", "--name-only", "-z", "HEAD", "--"])
    untracked_paths = _git_paths(repo, ["ls-files", "--others", "--exclude-standard", "-z"])
    records: dict[str, set[str]] = {}
    tracked: set[str] = set()

    def add_git_path(raw_path: bytes, source: str) -> None:
        path = _safe_relative_path(raw_path)
        if ".git" in PurePosixPath(path).parts:
            return
        records.setdefault(path, set()).add(source)
        if source == "tracked":
            tracked.add(path)

    for raw_path in tracked_paths:
        add_git_path(raw_path, "tracked")
    for raw_path in untracked_paths:
        add_git_path(raw_path, "untracked")

    excluded_count = 0

    def walk(directory_fd: int, prefix: str) -> None:
        nonlocal excluded_count
        try:
            with os.scandir(directory_fd) as scan:
                children = sorted(scan, key=lambda item: os.fsencode(item.name))
        except OSError as exc:
            raise ManifestError(f"directory walk failed path={_escaped(prefix)} ({type(exc).__name__})") from None
        for child in children:
            relative = f"{prefix}/{child.name}" if prefix else child.name
            if child.name == ".git":
                excluded_count += 1
                continue
            try:
                info = os.stat(child.name, dir_fd=directory_fd, follow_symlinks=False)
            except OSError as exc:
                raise ManifestError(f"lstat failed path={_escaped(relative)} ({type(exc).__name__})") from None
            if stat.S_ISDIR(info.st_mode):
                flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, "O_CLOEXEC", 0)
                try:
                    child_fd = os.open(child.name, flags, dir_fd=directory_fd)
                    if FileIdentity.from_stat(os.fstat(child_fd)) != FileIdentity.from_stat(info):
                        os.close(child_fd)
                        raise ManifestError(f"directory changed during walk path={_escaped(relative)}")
                    try:
                        walk(child_fd, relative)
                    finally:
                        os.close(child_fd)
                except OSError as exc:
                    raise ManifestError(f"directory open failed path={_escaped(relative)} ({type(exc).__name__})") from None
            elif stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                records.setdefault(relative, set()).add("candidate")
            else:
                raise ManifestError(f"unsupported filesystem node path={_escaped(relative)}")

    if candidate_root is not None:
        root_relative = candidate_root.relative_to(repo).as_posix()
        root_fd = _open_directory_chain(repo, PurePosixPath(root_relative).parts)
        try:
            walk(root_fd, root_relative)
        finally:
            os.close(root_fd)

    entries: list[ManifestEntry] = []
    for path in sorted(records, key=os.fsencode):
        sources = frozenset(records[path])
        absolute = repo / path
        try:
            info = _lstat_relative(repo, path)
        except FileNotFoundError:
            if path in tracked:
                entries.append(ManifestEntry(path, "deleted", True, sources, None))
                continue
            raise ManifestError(f"manifest path disappeared path={_escaped(path)}") from None
        except OSError as exc:
            raise ManifestError(f"lstat failed path={_escaped(path)} ({type(exc).__name__})") from None
        if stat.S_ISDIR(info.st_mode):
            if "candidate" in sources:
                raise ManifestError(f"candidate directory was recorded as file path={_escaped(path)}")
            if candidate_root is not None:
                try:
                    absolute.relative_to(candidate_root)
                except ValueError:
                    raise ManifestError(f"untracked directory needs explicit coverage path={_escaped(path)}") from None
            continue
        kind = _file_kind(info, path)
        entries.append(ManifestEntry(path, kind, path in tracked, sources, FileIdentity.from_stat(info)))

    digest_rows = [
        {
            "path": entry.path,
            "kind": entry.kind,
            "tracked": entry.tracked,
            "sources": sorted(entry.sources),
            "identity": entry.identity.__dict__ if entry.identity else None,
        }
        for entry in entries
    ]
    digest = hashlib.sha256(
        json.dumps(digest_rows, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return DeltaManifest(repo, candidate_root, tuple(entries), digest, excluded_count)


def _read_entry_bytes(manifest: DeltaManifest, entry: ManifestEntry) -> bytes:
    if entry.kind == "deleted" or entry.identity is None:
        raise ManifestError(f"cannot read deleted path={_escaped(entry.path)}")
    components = PurePosixPath(entry.path).parts
    if not components:
        raise ManifestError("empty relative path")
    parent_fd = _open_directory_chain(manifest.repo, components[:-1])
    try:
        try:
            initial = os.stat(components[-1], dir_fd=parent_fd, follow_symlinks=False)
        except OSError as exc:
            raise ManifestError(f"lstat failed path={_escaped(entry.path)} ({type(exc).__name__})") from None
        if FileIdentity.from_stat(initial) != entry.identity:
            raise ManifestError(f"path changed before read={_escaped(entry.path)}")

        if entry.kind == "symlink":
            try:
                target_text = os.readlink(components[-1], dir_fd=parent_fd)
                os.stat(components[-1], dir_fd=parent_fd, follow_symlinks=True)
                final = os.stat(components[-1], dir_fd=parent_fd, follow_symlinks=False)
            except OSError as exc:
                raise ManifestError(f"symlink read/target check failed path={_escaped(entry.path)} ({type(exc).__name__})") from None
            if FileIdentity.from_stat(final) != entry.identity:
                raise ManifestError(f"symlink changed during read={_escaped(entry.path)}")
            return os.fsencode(target_text)

        if entry.kind != "file" or not stat.S_ISREG(initial.st_mode):
            raise ManifestError(f"unsupported file type path={_escaped(entry.path)}")
        flags = os.O_RDONLY | os.O_NOFOLLOW | getattr(os, "O_NONBLOCK", 0) | getattr(os, "O_CLOEXEC", 0)
        try:
            fd = os.open(components[-1], flags, dir_fd=parent_fd)
        except OSError as exc:
            raise ManifestError(f"open failed path={_escaped(entry.path)} ({type(exc).__name__})") from None
        try:
            opened = os.fstat(fd)
            if not stat.S_ISREG(opened.st_mode) or FileIdentity.from_stat(opened) != entry.identity:
                raise ManifestError(f"file changed before read={_escaped(entry.path)}")
            data = bytearray()
            while True:
                chunk = os.read(fd, 1024 * 1024)
                if not chunk:
                    break
                data.extend(chunk)
            final = os.fstat(fd)
            if FileIdentity.from_stat(final) != entry.identity or len(data) != entry.identity.size:
                raise ManifestError(f"file changed during read={_escaped(entry.path)}")
            return bytes(data)
        except OSError as exc:
            raise ManifestError(f"read failed path={_escaped(entry.path)} ({type(exc).__name__})") from None
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)


def _load_rule_module(name: str, filename: str):
    path = Path(__file__).resolve().parent / filename
    module_name = f"_candidate_delta_{name}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError("guard rule module cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _load_allowlist(repo: Path, allowlist: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if allowlist is not None:
        if not isinstance(allowlist, list) or any(not isinstance(item, dict) for item in allowlist):
            raise ValueError("whitespace allowlist must be a list of objects")
        return allowlist
    path = repo / "scripts/guard/intentional-markdown-whitespace.json"
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    if not isinstance(entries, list) or any(not isinstance(item, dict) for item in entries):
        raise ValueError("whitespace allowlist entries must be a list of objects")
    return entries


def _read_only_git_environment() -> dict[str, str]:
    env = os.environ.copy()
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_OBJECT_DIRECTORY", "GIT_ALTERNATE_OBJECT_DIRECTORIES"):
        env.pop(key, None)
    env["GIT_OPTIONAL_LOCKS"] = "0"
    return env


def _tracked_whitespace_findings(repo: Path) -> tuple[list[ScanFinding], list[str]]:
    result = subprocess.run(
        ["git", "diff", "--check", "HEAD", "--"],
        cwd=repo,
        env=_read_only_git_environment(),
        capture_output=True,
        check=False,
    )
    output = (result.stdout + result.stderr).decode("utf-8", "surrogateescape")
    counts: dict[str, int] = {}
    unclassified = 0
    expecting_added_content = False
    diagnostic = re.compile(r"^(.*):[0-9]+: trailing whitespace\.$")
    for line in output.splitlines():
        if expecting_added_content and line.startswith("+"):
            expecting_added_content = False
            continue
        expecting_added_content = False
        if not line:
            continue
        match = diagnostic.fullmatch(line)
        if match:
            path = match.group(1)
            counts[path] = counts.get(path, 0) + 1
            expecting_added_content = True
        elif line.startswith("+"):
            continue
        else:
            unclassified += 1
    findings = [ScanFinding(path, "trailing-whitespace", count) for path, count in counts.items()]
    errors: list[str] = []
    if unclassified or (result.returncode and not findings):
        errors.append(f"tracked diff-check failed rc={result.returncode} unclassified={unclassified}")
    return findings, errors


def scan_manifest(manifest: DeltaManifest, *, allowlist: list[dict[str, Any]] | None = None) -> ScanResult:
    findings: dict[tuple[str, str], int] = {}
    errors: list[str] = []
    scanned_count = 0
    deleted_count = sum(1 for entry in manifest.entries if entry.kind == "deleted")

    try:
        secret_scan = _load_rule_module("secret_scan", "secret_scan.py")
        pii_review = _load_rule_module("pii_review", "pii-review.py")
        whitespace_review = _load_rule_module("whitespace_review", "whitespace_review.py")
        allowed_secret_rules = {str(name) for name, _pattern in secret_scan.RULES}
        allowed_pii_rules = {"email-like", "phone-like"}
        whitespace_allowlist = _load_allowlist(manifest.repo, allowlist)
    except Exception as exc:
        return ScanResult("FAIL", 0, deleted_count, manifest.excluded_count, manifest.digest, (),
                          (f"scanner setup failed ({type(exc).__name__})",))

    def record_detector(entry: ManifestEntry, hits, allowed_rules: set[str], scanner_name: str) -> None:
        try:
            for hit in hits:
                if not isinstance(hit, (tuple, list)) or len(hit) < 2:
                    raise ValueError("invalid detector result shape")
                rule = hit[1]
                if not isinstance(rule, str) or rule not in allowed_rules:
                    raise ValueError("invalid detector rule identifier")
                key = (entry.path, rule)
                findings[key] = findings.get(key, 0) + 1
        except Exception as exc:
            errors.append(f"{scanner_name} scanner failed path={_escaped(entry.path)} ({type(exc).__name__})")

    for entry in manifest.entries:
        if entry.kind == "deleted":
            continue
        try:
            data = _read_entry_bytes(manifest, entry)
        except ManifestError as exc:
            errors.append(f"read failed {exc}")
            continue
        except Exception as exc:
            errors.append(f"read failed path={_escaped(entry.path)} ({type(exc).__name__})")
            continue
        scanned_count += 1
        try:
            record_detector(entry, secret_scan.findings(entry.path, data), allowed_secret_rules, "secret")
        except Exception as exc:
            errors.append(f"secret scanner failed path={_escaped(entry.path)} ({type(exc).__name__})")
        try:
            scope = {"source", "destination"} if entry.path == pii_review.MANIFEST_PATH else None
            record_detector(entry, pii_review.findings(entry.path, data, field_scope=scope), allowed_pii_rules, "PII")
        except Exception as exc:
            errors.append(f"PII scanner failed path={_escaped(entry.path)} ({type(exc).__name__})")
        if not entry.tracked:
            try:
                issues = whitespace_review.issues_from_bytes(entry.path, data, whitespace_allowlist)
                _allowed, unexpected = whitespace_review.evaluate_issues(issues, whitespace_allowlist)
                if unexpected:
                    key = (entry.path, "trailing-whitespace")
                    findings[key] = findings.get(key, 0) + len(unexpected)
            except Exception as exc:
                errors.append(f"whitespace scanner failed path={_escaped(entry.path)} ({type(exc).__name__})")

    tracked_findings, tracked_errors = _tracked_whitespace_findings(manifest.repo)
    for finding in tracked_findings:
        key = (finding.path, finding.rule)
        findings[key] = findings.get(key, 0) + finding.count
    errors.extend(tracked_errors)

    try:
        current = collect_delta_manifest(manifest.repo, manifest.candidate_root)
        if current.digest != manifest.digest or current.excluded_count != manifest.excluded_count:
            errors.append("path manifest or file metadata changed during scan")
    except Exception as exc:
        errors.append(f"post-scan manifest recheck failed ({type(exc).__name__})")

    result_findings = tuple(
        ScanFinding(path, rule, count)
        for (path, rule), count in sorted(findings.items(), key=lambda item: (os.fsencode(item[0][0]), item[0][1]))
    )
    result_errors = tuple(sorted(set(errors)))
    status = "FAIL" if result_findings or result_errors else "PASS"
    return ScanResult(status, scanned_count, deleted_count, manifest.excluded_count, manifest.digest,
                      result_findings, result_errors)
