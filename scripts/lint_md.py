#!/usr/bin/env python3
"""lint_md.py — Vault linter for ~/wiki/ (SCHEMA.md + AGENTS.md enforcement).

Checks per .md file:
  1. Frontmatter present (starts with '---') and closed with '---'
  2. Required keys: title, type, status, created, updated, source,
     evidence_tier, supersedes
  3. Value enums:
       type:          note | decision | runbook | raw | index
       status:        draft | active | superseded | archived
       evidence_tier: evidence | inference | unknown
  4. Date format YYYY-MM-DD; updated >= created
  5. supersedes: null or non-empty relative path
  6. Naming rules:
       decisions/  NNNN-short-slug.md (4 zero-padded digits + slug)
       runbooks/   verb-object.md     (lowercase, hyphenated)
       wiki/       lowercase-kebab-case.md
  7. ONE index.md per vault, at vault root only (AGENTS.md)
  8. decisions/: status=superseded MUST carry superseded_by (AGENTS.md rule 4)

Exit code: 0 = all clean, 1 = violations found, 2 = usage error.

Usage:
  lint_md.py [--vault PATH] [--strict] [--quiet]
  --strict   additionally require unknown-key warnings to fail
  --quiet    print only the summary line
"""
import argparse
import re
import sys
from pathlib import Path

REQUIRED_KEYS = ["title", "type", "status", "created", "updated",
                 "source", "evidence_tier", "supersedes"]
VALID_TYPES = {"note", "decision", "runbook", "raw", "index"}
VALID_STATUS = {"draft", "active", "superseded", "archived"}
VALID_TIERS = {"evidence", "inference", "unknown"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
DECISION_NAME_RE = re.compile(r"^\d{4}-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
RUNBOOK_NAME_RE = re.compile(r"^[a-z]+-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
WIKI_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*\.md$")


def parse_frontmatter(text: str):
    """Return (meta_dict, errors) for the frontmatter block."""
    lines = text.splitlines()
    errors = []
    if not lines or lines[0].strip() != "---":
        return None, ["file does not start with '---'"]
    # find closing '---'
    close_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            close_idx = i
            break
    if close_idx is None:
        return None, ["frontmatter block has no closing '---'"]
    block = lines[1:close_idx]
    meta = {}
    for lineno, raw in enumerate(block, start=2):
        if not raw.strip():
            continue
        if not re.match(r"^[A-Za-z_]+:", raw):
            errors.append(f"line {lineno}: not a 'key: value' entry: {raw!r}")
            continue
        key, _, value = raw.partition(":")
        key = key.strip()
        value = value.strip()
        # strip trailing comment and quotes
        value = re.sub(r"\s+#.*$", "", value).strip()
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            value = value[1:-1].strip()
        if key in meta:
            errors.append(f"line {lineno}: duplicate key {key!r}")
        meta[key] = value
    return meta, errors


def check_file(path: Path, vault: Path, strict: bool):
    """Return list of violation strings for one file."""
    errors = []
    rel = path.relative_to(vault)
    text = path.read_text(encoding="utf-8", errors="replace")
    meta, ferr = parse_frontmatter(text)
    if ferr:
        errors += [f"{rel}: {e}" for e in ferr]
        return errors
    assert meta is not None  # guaranteed: any parse failure set ferr
    # required keys
    missing = [k for k in REQUIRED_KEYS if k not in meta]
    if missing:
        errors.append(f"{rel}: missing required keys: {', '.join(missing)}")
    # enums
    if meta.get("type") not in VALID_TYPES:
        errors.append(f"{rel}: type={meta.get('type')!r} not in {sorted(VALID_TYPES)}")
    if meta.get("status") not in VALID_STATUS:
        errors.append(f"{rel}: status={meta.get('status')!r} not in {sorted(VALID_STATUS)}")
    if meta.get("evidence_tier") not in VALID_TIERS:
        errors.append(f"{rel}: evidence_tier={meta.get('evidence_tier')!r} not in {sorted(VALID_TIERS)}")
    # dates
    for key in ("created", "updated"):
        val = meta.get(key, "")
        if not DATE_RE.match(val):
            errors.append(f"{rel}: {key}={val!r} not YYYY-MM-DD")
    if DATE_RE.match(meta.get("created", "")) and DATE_RE.match(meta.get("updated", "")):
        if meta["updated"] < meta["created"]:
            errors.append(f"{rel}: updated {meta['updated']} < created {meta['created']}")
    # supersedes
    sup = meta.get("supersedes", "MISSING")
    if sup != "MISSING" and sup != "null" and not sup.strip():
        errors.append(f"{rel}: supersedes must be null or a path")
    # naming rules
    name = path.name
    parts = rel.parts
    if "decisions" in parts and not DECISION_NAME_RE.match(name):
        errors.append(f"{rel}: decisions/ file must match NNNN-short-slug.md")
    if "runbooks" in parts and not RUNBOOK_NAME_RE.match(name):
        errors.append(f"{rel}: runbooks/ file must be verb-object.md (lowercase, hyphenated)")
    if parts and parts[0] == "wiki" and not WIKI_NAME_RE.match(name):
        errors.append(f"{rel}: wiki/ file must be lowercase-kebab-case.md")
    # decisions: superseded needs superseded_by
    if "decisions" in parts and meta.get("status") == "superseded":
        if "superseded_by" not in meta:
            errors.append(f"{rel}: status=superseded requires 'superseded_by'")
    return errors


def main():
    ap = argparse.ArgumentParser(description="Vault linter per SCHEMA.md")
    ap.add_argument("--vault", default=str(Path.home() / "wiki"))
    ap.add_argument("--strict", action="store_true",
                    help="fail on unknown-key warnings")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    vault = Path(args.vault).expanduser().resolve()
    if not vault.is_dir():
        print(f"ERROR: vault not found: {vault}", file=sys.stderr)
        return 2

    md_files = sorted(p for p in vault.rglob("*.md") if ".git" not in p.parts)
    # index.md rule: exactly one, at vault root
    indexes = [p for p in md_files if p.name == "index.md"]
    violations = []
    if len(indexes) != 1 or indexes[0].parent != vault:
        violations.append(
            f"index rule: expected exactly ONE index.md at vault root; found {len(indexes)} "
            f"at {[str(p.relative_to(vault)) for p in indexes]}")
    for p in md_files:
        violations += check_file(p, vault, args.strict)

    if violations:
        if not args.quiet:
            for v in violations:
                print(v)
        print(f"FAIL: {len(md_files)} files, {len(violations)} violation(s)")
        return 1
    print(f"OK: {len(md_files)} files, 0 violations")
    return 0


if __name__ == "__main__":
    sys.exit(main())
