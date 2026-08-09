#!/usr/bin/env python3
"""Deterministic secret scanner with redacted diagnostics.

Only path/rule/category is emitted. Matching bytes are never printed. Matching
is line-scoped deliberately: a punctuation-separated test fixture must not be
joined with adjacent source to manufacture a secret token.
"""
from __future__ import annotations
import argparse
import re
import subprocess
import sys
from pathlib import Path

RULES = [
    ("private-key", re.compile(rb"-----BEGIN (?:RSA|OPENSSH|EC|DSA|PGP|PRIVATE) KEY-----")),
    ("github-token", re.compile(rb"gh[pousr]_[A-Za-z0-9_]{20,}")),
    ("openai-key", re.compile(rb"sk-[A-Za-z0-9]{16,}")),
    ("aws-access-key", re.compile(rb"AKIA[0-9A-Z]{16}")),
    ("telegram-bot-token", re.compile(rb"\bbot[0-9]{8,}:[A-Za-z0-9_-]{20,}\b")),
    ("slack-token", re.compile(rb"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    ("google-api-key", re.compile(rb"AIza[0-9A-Za-z_-]{20,}")),
    ("bearer-token", re.compile(rb"\bBearer\s+[A-Za-z0-9._-]{24,}")),
]

def findings(path: str, data: bytes):
    for line in data.splitlines():
        for name, pattern in RULES:
            if pattern.search(line):
                yield path, name

def git_output(args: list[str]) -> bytes:
    try:
        return subprocess.run(["git", *args], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"SECRET-SCAN ERROR: git input failed ({type(exc).__name__})", file=sys.stderr)
        raise SystemExit(2)

def scan_tree() -> list[tuple[str, str]]:
    raw = git_output(["ls-files", "-z"])
    out=[]
    for raw_path in raw.split(b"\0"):
        if not raw_path: continue
        path = raw_path.decode("utf-8", "surrogateescape")
        try: data=Path(path).read_bytes()
        except OSError as exc:
            print(f"SECRET-SCAN ERROR: unreadable tracked path={path} ({type(exc).__name__})", file=sys.stderr)
            raise SystemExit(2)
        out.extend(findings(path,data))
    return out

def scan_diff(spec: str) -> list[tuple[str, str]]:
    raw = git_output(["diff", "--no-ext-diff", "--unified=0", spec, "--"])
    out=[]; current="<unknown>"
    for line in raw.splitlines():
        if line.startswith(b"+++ b/"): current=line[6:].decode("utf-8", "replace")
        elif line.startswith(b"+") and not line.startswith(b"+++"): out.extend(findings(current,line[1:]))
    return out

def main() -> int:
    ap=argparse.ArgumentParser()
    ap.add_argument("mode", choices=("tree","staged","diff")); ap.add_argument("spec", nargs="?")
    ns=ap.parse_args()
    if ns.mode=="tree": found=scan_tree(); label="tree"
    elif ns.mode=="staged": found=scan_diff("--cached"); label="staged"
    else:
        if not ns.spec: print("SECRET-SCAN ERROR: diff requires BASE..HEAD", file=sys.stderr); return 2
        found=scan_diff(ns.spec); label=ns.spec
    if found:
        for path,rule in sorted(set(found)): print(f"SECRET-SCAN FAIL: path={path} rule={rule}")
        return 1
    print(f"SECRET-SCAN PASS: scope={label}"); return 0

if __name__ == "__main__": raise SystemExit(main())
