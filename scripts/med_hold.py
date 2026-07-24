#!/usr/bin/env python3
"""Inspect and resolve structured medication safety holds.

This command never writes medication status, supply, schedule, taper, or reminder
state. Resolution records why a prior HOLD was closed; an intake correction must
still travel through normal source-backed med_confirm.py after user confirmation.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

MYT = ZoneInfo("Asia/Kuala_Lumpur")
HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
HOLDS_FILE = HOME / "med-holds.json"
AUDIT_FILE = HOME / "logs" / "med-safety-audit.jsonl"


def load() -> dict:
    try:
        return json.loads(HOLDS_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "holds": []}


def save(data: dict) -> None:
    tmp = HOLDS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, HOLDS_FILE)


def audit(event: dict) -> None:
    AUDIT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_FILE.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, sort_keys=True, ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--open", action="store_true", help="show newest open hold")
    parser.add_argument("--resolve", metavar="HOLD_ID")
    parser.add_argument("--outcome", choices=("CORRECTED", "CONFIRMED_ACTUAL_INTAKE", "REJECTED"))
    parser.add_argument("--note")
    args = parser.parse_args()
    data = load()
    holds = data.get("holds", [])

    if args.open:
        open_holds = [h for h in holds if h.get("status") == "OPEN"]
        print(json.dumps(open_holds[-1] if open_holds else {"ok": True, "open_hold": None}, indent=2))
        return 0

    if not args.resolve or not args.outcome or not args.note:
        parser.error("use --open, or --resolve HOLD_ID --outcome ... --note ...")
    if args.outcome == "CONFIRMED_ACTUAL_INTAKE":
        parser.error("This outcome requires a separate source-backed med_confirm.py call after user confirmation.")

    for hold in holds:
        if hold.get("hold_id") != args.resolve:
            continue
        if hold.get("status") != "OPEN":
            print(json.dumps({"ok": False, "error": "HOLD_NOT_OPEN", "hold_id": args.resolve}))
            return 1
        resolution = {
            "outcome": args.outcome,
            "note": args.note,
            "resolved_at": datetime.now(MYT).isoformat(),
            "state_mutated": False,
        }
        hold["status"] = "RESOLVED"
        hold["resolution"] = resolution
        save(data)
        audit({"event_type": "MED_SAFETY_HOLD_RESOLVED", "hold_id": args.resolve, "resolution": resolution})
        print(json.dumps({"ok": True, "hold_id": args.resolve, "resolution": resolution}))
        return 0
    print(json.dumps({"ok": False, "error": "HOLD_NOT_FOUND", "hold_id": args.resolve}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
