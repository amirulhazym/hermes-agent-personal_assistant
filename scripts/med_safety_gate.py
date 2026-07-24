#!/usr/bin/env python3
"""Deterministic medication intake gate.

This module is deliberately side-effect-light:
- evaluate() reads active schedule/taper and returns an ALLOW/HOLD decision.
- persist_hold() is the only HOLD-side write: structured ledger + JSONL audit.
- no function here can write medication status, supply, reminders, or regimen.

The active schedule and taper are the clinical-routing source of truth. This
module must not carry a second copy of slot windows or taper timing.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

MYT = ZoneInfo("Asia/Kuala_Lumpur")
HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
SCHEDULE_FILE = HERMES_HOME / "med-schedule.json"
TAPER_FILE = HERMES_HOME / "dexa_taper.json"
HOLDS_FILE = HERMES_HOME / "med-holds.json"
AUDIT_FILE = HERMES_HOME / "logs" / "med-safety-audit.jsonl"
TRIGGER_FILE = HERMES_HOME / "triggered_skills.txt"
PARSER_VERSION = "safety-gate-phase1.1"

CHANGE_RE = re.compile(
    r"\b(doctor|doktor|hospital|hosp|clinic|klinik|ward|discharge|consultant|"
    r"specialist)\b.*\b(tukar|change|ubah|stop|start|naik|turun|reduce|increase|"
    r"dose|dos|routine|regimen|arahan|instruction|suruh)\b"
    r"|\b(tukar|change|ubah|stop|start|naik|turun|reduce|increase)\b.*\b"
    r"(doctor|doktor|hospital|hosp|clinic|klinik|ward|discharge|consultant|specialist)\b",
    re.IGNORECASE,
)


def _read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _digest(data: dict) -> str:
    return hashlib.sha256(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def _hm_minutes(value: str) -> int | None:
    try:
        h, m = value.split(":", 1)
        h_i, m_i = int(h), int(m)
        if not 0 <= h_i <= 23 or not 0 <= m_i <= 59:
            return None
        return h_i * 60 + m_i
    except (AttributeError, ValueError):
        return None


def _window_contains(window: str, time_hm: str) -> bool | None:
    """Return None for malformed/no window, otherwise inclusive containment."""
    try:
        start, end = re.split(r"\s*[–-]\s*", window.strip(), maxsplit=1)
    except ValueError:
        return None
    start_m, end_m, actual_m = _hm_minutes(start), _hm_minutes(end), _hm_minutes(time_hm)
    if start_m is None or end_m is None or actual_m is None:
        return None
    return start_m <= actual_m <= end_m


def _active_taper_phase(taper: dict, date_iso: str) -> dict | None:
    for phase in taper.get("phases", []):
        start, end = phase.get("start"), phase.get("end")
        if not start:
            continue
        if start <= date_iso and (end is None or date_iso <= end):
            return phase
    return None


def _active_dexa_slots(phase: dict | None) -> set[str] | None:
    """Return active dexa slots from taper phase. None means no taper authority."""
    if not phase:
        return None
    times = phase.get("times")
    if not isinstance(times, list):
        return None
    # Schedule is canonical slot naming; taper time tells which dose positions exist.
    by_time = {"08:00": "B", "12:00": "C", "14:00": "D", "16:00": "D"}
    return {by_time[t] for t in times if t in by_time}


def load_regimen_snapshot(reference: datetime) -> dict:
    schedule = _read_json(SCHEDULE_FILE)
    taper = _read_json(TAPER_FILE)
    if not schedule.get("meds"):
        return {"ok": False, "error": "ACTIVE_SCHEDULE_UNAVAILABLE"}
    if not taper.get("phases"):
        return {"ok": False, "error": "ACTIVE_TAPER_UNAVAILABLE"}
    phase = _active_taper_phase(taper, reference.date().isoformat())
    if phase is None:
        return {"ok": False, "error": "ACTIVE_TAPER_PHASE_UNAVAILABLE"}
    active_dexa = _active_dexa_slots(phase)
    if active_dexa is None:
        return {"ok": False, "error": "ACTIVE_TAPER_PHASE_INVALID"}
    return {
        "ok": True,
        "schedule": schedule,
        "schedule_version": schedule.get("version", "unknown"),
        "schedule_digest": _digest(schedule),
        "taper_digest": _digest(taper),
        "taper_phase_id": phase.get("id"),
        "active_dexa_slots": sorted(active_dexa),
    }


def _alias_phrases() -> dict[str, str | list[str]]:
    """Load single and compound aliases from canonical resolver."""
    try:
        import med_resolve
        aliases = dict(med_resolve.ALIASES)
        aliases.update(getattr(med_resolve, "COMPOUND_ALIASES", {}))
        return aliases
    except Exception:
        return {}


def _mentions(message: str, time_hm: str, snapshot: dict) -> list[dict]:
    """Resolve every distinct known alias phrase against current schedule."""
    try:
        import med_resolve
    except Exception:
        return []
    aliases = _alias_phrases()
    found: list[dict] = []
    occupied: list[tuple[int, int]] = []
    # longest-first prevents e.g. "letram pagi" plus "letram" double-counting.
    for phrase in sorted(aliases, key=len, reverse=True):
        if len(phrase) < 2:
            continue
        pat = re.compile(r"(?<![a-z0-9])" + re.escape(phrase) + r"(?![a-z0-9])", re.I)
        for match in pat.finditer(message):
            span = match.span()
            if any(span[0] >= a and span[1] <= b for a, b in occupied):
                continue
            result = med_resolve.resolve(phrase, time_24h=time_hm)
            if not result.get("ok"):
                continue
            occupied.append(span)
            if result.get("compound"):
                components = result.get("components", [])
                for component in components:
                    found.append({
                        "source": message[span[0]:span[1]],
                        "compound_id": result.get("compound_id"),
                        "compound_complete": True,
                        "drug_id": component["drug_id"],
                        "drug": component["drug"],
                        "slot": component["slot"] or None,
                        "ambiguous": False,
                        "candidates": [],
                    })
            else:
                found.append({
                    "source": message[span[0]:span[1]],
                    "drug_id": result["drug_id"],
                    "drug": result["drug"],
                    "slot": result["slot"] or None,
                    "ambiguous": bool(result.get("ambiguous")),
                    "candidates": result.get("all_matches", []),
                })
    # Exact canonical drug IDs may be typed but not appear in aliases.
    known_ids = {
        d.get("drug_id"): (slot, d.get("drug"))
        for slot, data in snapshot["schedule"].get("meds", {}).items()
        for d in data.get("drugs", [])
    }
    for did, (slot, drug) in known_ids.items():
        if did and re.search(r"(?<![a-z0-9_])" + re.escape(did) + r"(?![a-z0-9_])", message, re.I):
            if not any(m["drug_id"] == did for m in found):
                found.append({"source": did, "drug_id": did, "drug": drug, "slot": slot, "ambiguous": False, "candidates": []})
    # Explicit component wording has same semantic bundle as CC shorthand.
    # Preserve separate drug IDs while making the pair lunch-relative together.
    compound_members = [m for m in found if m["drug_id"] in {"calcium", "calcitriol"} and m.get("slot") == "C"]
    if {m["drug_id"] for m in compound_members} == {"calcium", "calcitriol"}:
        for member in compound_members:
            member.setdefault("compound_id", "cc")
            member.setdefault("compound_complete", True)
    return found


def is_regimen_change(message: str) -> bool:
    return bool(CHANGE_RE.search(message or ""))


def evaluate(message: str, stated_time: str, reference: datetime) -> dict:
    """Pure decision. Returns structured ALLOW or HOLD; never mutates files."""
    reference = reference.astimezone(MYT) if reference.tzinfo else reference.replace(tzinfo=MYT)
    snapshot = load_regimen_snapshot(reference)
    base = {
        "decision": "HOLD",
        "parser_version": PARSER_VERSION,
        "raw_message": message,
        "stated_time": stated_time,
        "evaluated_at": reference.isoformat(),
        "findings": [],
        "mentions": [],
        "regimen": {
            "schedule_version": snapshot.get("schedule_version"),
            "schedule_digest": snapshot.get("schedule_digest"),
            "taper_digest": snapshot.get("taper_digest"),
            "taper_phase_id": snapshot.get("taper_phase_id"),
        },
    }
    if not snapshot.get("ok"):
        base["findings"].append({"rule_id": "CONFIG_ACTIVE_SCHEDULE", "expected": "readable active med-schedule.json", "observed": snapshot.get("error"), "reason": "Safety gate cannot evaluate active regimen."})
        return base
    mentions = _mentions(message, stated_time, snapshot)
    base["mentions"] = mentions
    if CHANGE_RE.search(message):
        base["findings"].append({"rule_id": "REGIMEN_CHANGE_REPORTED", "expected": "intake report only", "observed": "clinician/hospital change language", "reason": "Route to regimen-change proposal; do not auto-log intake."})
        return base
    if not mentions:
        base["findings"].append({"rule_id": "MEDICATION_PARSE_INCOMPLETE", "expected": "at least one active-regimen medication", "observed": "no resolvable medication", "reason": "Cannot safely identify intake."})
        return base
    if any(m["ambiguous"] for m in mentions):
        base["findings"].append({"rule_id": "MEDICATION_PARSE_AMBIGUOUS", "expected": "one resolved active-regimen medication", "observed": "multiple candidates", "reason": "Clarification required before logging."})
    unslotted = [m["drug_id"] for m in mentions if not m.get("slot")]
    if unslotted:
        base["findings"].append({"rule_id": "UNSLOTTED_MEDICATION", "expected": "a planned intake slot", "observed": unslotted, "reason": "PRN or unslotted medication requires explicit agent handling; do not auto-log."})
    slots = {m["slot"] for m in mentions if m["slot"]}
    if len(slots) > 1:
        base["findings"].append({"rule_id": "CROSS_SLOT_COMBINATION", "expected": "one planned intake slot per confirmation", "observed": sorted(slots), "reason": "Multiple slot medications reported together."})
    active_dexa = set(snapshot.get("active_dexa_slots") or [])
    for mention in mentions:
        did, slot = mention["drug_id"], mention["slot"]
        if did.startswith("dexamethasone") and active_dexa is not None and slot not in active_dexa:
            base["findings"].append({"rule_id": "TAPER_INACTIVE_SLOT", "expected": sorted(active_dexa), "observed": slot, "reason": "Dexamethasone slot inactive in current taper phase."})
        # CC is a lunch-relative compound. Its timing must never move Dexa.
        if mention.get("compound_id") == "cc":
            continue
        window = snapshot["schedule"].get("meds", {}).get(slot or "", {}).get("window")
        contained = _window_contains(window, stated_time) if window else None
        if contained is False:
            base["findings"].append({"rule_id": "SCHEDULE_TIME_WINDOW", "expected": window, "observed": stated_time, "reason": f"Reported time outside active Slot {slot} window."})
    if base["findings"]:
        return base
    base["decision"] = "ALLOW"
    return base


def _append_jsonl(path: Path, record: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n")


def persist_hold(decision: dict) -> dict:
    """Persist a resolvable HOLD. This is the only permitted HOLD side-effect."""
    if decision.get("decision") != "HOLD":
        raise ValueError("Only HOLD decisions can be persisted")
    now = datetime.now(MYT).isoformat()
    hold = {
        "hold_id": str(uuid.uuid4()),
        "status": "OPEN",
        "created_at": now,
        "decision": decision,
        "resolution": None,
    }
    existing = _read_json(HOLDS_FILE)
    holds = existing.get("holds", []) if isinstance(existing.get("holds", []), list) else []
    holds.append(hold)
    tmp = HOLDS_FILE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"version": 1, "holds": holds}, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, HOLDS_FILE)
    _append_jsonl(AUDIT_FILE, {"event_type": "MED_SAFETY_HOLD", "state_mutated": False, "hold": hold})
    # Gateway's mandatory triggered-skill loader makes this decision visible to agent.
    prior = TRIGGER_FILE.read_text(encoding="utf-8") if TRIGGER_FILE.exists() else ""
    names = {line.strip() for line in prior.splitlines() if line.strip()}
    names.add("med-tracker")
    TRIGGER_FILE.write_text("\n".join(sorted(names)) + "\n", encoding="utf-8")
    return hold


def latest_open_hold() -> dict | None:
    holds = _read_json(HOLDS_FILE).get("holds", [])
    for hold in reversed(holds if isinstance(holds, list) else []):
        if hold.get("status") == "OPEN":
            return hold
    return None
