#!/usr/bin/env python3
"""Strict JSON source-coverage manifest validator (no deployment)."""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, sys
from pathlib import Path

SHA=re.compile(r"^[0-9a-f]{64}$")
COMMIT=re.compile(r"^[0-9a-f]{7,64}$")

def fail(msg):
    print(f"MANIFEST-VALIDATE FAIL: {msg}")
    return 1

def git_bytes(sha, source):
    try:
        return subprocess.run(["git","show",f"{sha}:{source}"],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout
    except subprocess.CalledProcessError:
        raise ValueError(f"source missing at candidate SHA: {source}")

def validate(manifest_path: str, release_sha: str) -> int:
    p=Path(manifest_path)
    if not p.is_file(): return fail("manifest missing")
    if not COMMIT.fullmatch(release_sha): return fail("release SHA format invalid")
    try:
        subprocess.run(["git","cat-file","-e",f"{release_sha}^{{commit}}"],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    except subprocess.CalledProcessError: return fail("release SHA is not a commit")
    try:
        obj=json.loads(p.read_text(encoding='utf-8'))
    except Exception as exc: return fail(f"JSON parse error ({type(exc).__name__})")
    if not isinstance(obj,dict) or obj.get('schema_version')!=1: return fail("schema_version must be 1")
    if obj.get('candidate_sha') not in (None,'','PENDING_OWNER_RELEASE') and obj.get('candidate_sha') != release_sha:
        return fail("candidate_sha does not match CLI release SHA")
    entries=obj.get('entries')
    if not isinstance(entries,list) or not entries: return fail("entries must be a non-empty list")
    seen_src=set(); seen_dst=set(); parsed=validated=0
    for i,e in enumerate(entries,1):
        parsed+=1
        if not isinstance(e,dict): return fail(f"row {i} is not an object")
        required={'source','source_sha256','kind','destination'}
        if set(e) != required: return fail(f"row {i} keys must be exactly {sorted(required)}")
        src=e['source']; h=e['source_sha256']; kind=e['kind']; dst=e['destination']
        if not isinstance(src,str) or not src or src.startswith('/') or '\\' in src or '..' in Path(src).parts: return fail(f"row {i} unsafe source path")
        if src in seen_src: return fail(f"row {i} duplicate source")
        seen_src.add(src)
        if not isinstance(h,str) or not SHA.fullmatch(h): return fail(f"row {i} invalid source_sha256")
        if kind not in ('runtime-deploy','source-only'): return fail(f"row {i} unknown kind")
        if kind=='runtime-deploy':
            if not isinstance(dst,str) or not dst.startswith('/home/ubuntu/.hermes/') or '..' in Path(dst).parts: return fail(f"row {i} unsafe runtime destination")
            if dst in seen_dst: return fail(f"row {i} duplicate destination")
            seen_dst.add(dst)
        elif dst is not None: return fail(f"row {i} source-only destination must be null")
        try: actual=hashlib.sha256(git_bytes(release_sha,src)).hexdigest()
        except ValueError as exc: return fail(str(exc))
        if actual != h: return fail(f"row {i} hash mismatch for source={src}")
        validated+=1
    if parsed != len(entries) or validated != parsed: return fail("parsed/validated row counts differ")
    print(f"MANIFEST-VALIDATE PASS: parsed={parsed} validated={validated} release_sha={release_sha}")
    return 0

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('manifest'); ap.add_argument('release_sha'); ns=ap.parse_args()
    return validate(ns.manifest,ns.release_sha)
if __name__=='__main__': raise SystemExit(main())
