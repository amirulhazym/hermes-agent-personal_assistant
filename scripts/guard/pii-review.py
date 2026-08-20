#!/usr/bin/env python3
"""Heuristic PII screen; matching values are never printed.

This is a review gate, not proof of privacy. It intentionally looks only for
high-signal email addresses and international phone forms; dates, versions,
IPs and arbitrary numeric IDs are not phone evidence.

Exit 0: no review-required hit. Exit 2: review required.
"""
from __future__ import annotations
import argparse, re, subprocess, sys
from pathlib import Path

EMAIL = re.compile(rb"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Za-z]{2,})\b")
PHONE = re.compile(rb"(?<![A-Za-z0-9])\+[1-9](?:[ ()-]*[0-9]){7,14}(?![0-9])")
MANIFEST_PATH = 'docs/reconciliation/hermes-runtime-tree-manifest.json'
MANIFEST_PATH_FIELDS = re.compile(
    rb'("(?:source|destination)"\s*:\s*")[^"\\]*(")'
)
PLACEHOLDER_DOMAINS={b"example.com",b"example.org",b"example.net",b"example.invalid",b"invalid"}

def paths():
    raw=subprocess.run(["git","ls-files","-z"],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
    return [p for p in raw.split(b"\0") if p and not any(p.startswith(x) for x in (b".git/",b"__pycache__/",b"node_modules/",b"venv/",b".venv/"))]

def findings(path, data, *, field_scope=None):
    if path == MANIFEST_PATH and field_scope == {'source', 'destination'}:
        data = MANIFEST_PATH_FIELDS.sub(
            rb'\1\2',
            data,
        )
    out=[]
    for m in EMAIL.finditer(data):
        domain=m.group(1).lower()
        if domain not in PLACEHOLDER_DOMAINS: out.append((path,"email-like"))
    if PHONE.search(data): out.append((path,"phone-like"))
    return out

def scan_tree():
    out=[]
    for raw in paths():
        path=raw.decode('utf-8','replace')
        try: data=Path(path).read_bytes()
        except OSError:
            print(f'PII-REVIEW ERROR: unreadable path={path}',file=sys.stderr); return None
        out.extend(findings(path,data))
    return out

def scan_diff(spec):
    raw=subprocess.run(['git','diff','--no-ext-diff','--unified=0',spec,'--'],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
    out=[]; current='<unknown>'
    for line in raw.splitlines():
        if line.startswith(b'+++ b/'): current=line[6:].decode('utf-8','replace')
        elif line.startswith(b'+') and not line.startswith(b'+++'):
            scope = {'source', 'destination'} if current == MANIFEST_PATH else None
            out.extend(findings(current, line[1:], field_scope=scope))
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--tree',action='store_true'); ap.add_argument('--diff'); ns=ap.parse_args()
    if bool(ns.tree)==bool(ns.diff): print('PII-REVIEW ERROR: choose exactly one of --tree or --diff BASE..HEAD',file=sys.stderr); return 2
    found=scan_tree() if ns.tree else scan_diff(ns.diff)
    if found is None: return 2
    for path,name in sorted(set(found)): print(f'PII-REVIEW REVIEW_REQUIRED: path={path} rule={name}')
    if found: return 2
    print('PII-REVIEW PASS: no heuristic hits'); return 0

if __name__=='__main__': raise SystemExit(main())
