"""Integration test for T11 chain-consistency check inside the med hook.

Sets a TEMP STATUS_FILE + warning log (never the live ~/.hermes) and verifies
that a contradictory stated time is flagged, while a consistent one is not.
"""
import importlib.util
import json
import os
import pathlib
import tempfile
from pathlib import Path

SPEC = str(Path(__file__).resolve().parent / "handler.py")
spec = importlib.util.spec_from_file_location("mah_chain", SPEC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

TODAY = "2026-07-11"
tmpdir = tempfile.mkdtemp()
status = pathlib.Path(tmpdir) / "med-status.json"
warnlog = pathlib.Path(tmpdir) / "warnings.jsonl"
mod.STATUS_FILE = status
mod.CHAIN_WARN_LOG = warnlog

# Seed slot A confirmed at 06:00 today.
status.write_text(json.dumps({
    "meds": {"A": {TODAY: {"actual_time": "06:00", "overall": "completed"}}}
}))

fails = []

# 1) Contradiction: user claims B at 21:00 (chain expects 07:00 from A=06:00).
mod._check_chain_consistency("B", "21:00", TODAY)
txt = warnlog.read_text(encoding="utf-8") if warnlog.exists() else ""
if "contradicts" not in txt:
    fails.append(f"expected contradiction warning, got: {txt!r}")

# 2) Consistent: B at 08:00 -> no warning.
if warnlog.exists():
    warnlog.unlink()
mod._check_chain_consistency("B", "08:00", TODAY)
txt2 = warnlog.read_text(encoding="utf-8") if warnlog.exists() else ""
if txt2.strip():
    fails.append(f"expected no warning for consistent time, got: {txt2!r}")

# 3) No-time message -> no warning.
if warnlog.exists():
    warnlog.unlink()
mod._check_chain_consistency("B", None, TODAY)
txt3 = warnlog.read_text(encoding="utf-8") if warnlog.exists() else ""
if txt3.strip():
    fails.append(f"expected no warning when time is None, got: {txt3!r}")

if fails:
    print("FAILURES:", fails)
    raise SystemExit(1)
print("ALL T11 HOOK TESTS PASSED")
