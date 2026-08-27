#!/usr/bin/env python3
"""
dexa_taper_lookup.py — Authoritative Dexamethasone dosage lookup.

Root-cause fix (2026-08-12): med-schedule.json dexa entries are STATIC
snapshots frozen at last_updated=2026-07-05 (Phase 5: 5/5/4). They drift
from the real taper every 2 weeks. All dexa dosage labels must instead be
computed from dexa_taper.json by date → active phase.

This module is the single source of truth. med_resolve.py and med_confirm.py
import get_dexa_dose(slot, date) so they NEVER read stale static dosage.

Slot → phase key mapping:
    B (morning, 08:00)  -> dose_morning
    C (midday,  12:00)  -> dose_midday
    D (afternoon,16:00) -> dose_afternoon
"""

from datetime import datetime, date
import os
from pathlib import Path
from zoneinfo import ZoneInfo

HERMES_HOME = Path.home() / ".hermes"
TAPER_FILE = HERMES_HOME / "dexa_taper.json"
MYT = ZoneInfo("Asia/Kuala_Lumpur")

SLOT_TO_KEY = {
    "B": "dose_morning",
    "C": "dose_midday",
    "D": "dose_afternoon",
    "F": "dose_2pm",
}

_DEXA_DRUG_PREFIX = "dexamethasone"


def _today_str() -> str:
    # Honour CHAIN_CALC_NOW_MYT (chain_calc freeze pattern) so date-aware
    # lookups stay consistent under frozen-time tests/probes.
    frozen = os.environ.get("CHAIN_CALC_NOW_MYT")
    if frozen:
        return str(frozen)[:10]
    return datetime.now(MYT).strftime("%Y-%m-%d")


def get_active_phase(taper: dict, date_str: str | None = None) -> dict | None:
    """Return the taper phase active on date_str (defaults to today)."""
    if date_str is None:
        date_str = _today_str()
    for phase in taper.get("phases", []):
        start = phase.get("start")
        if not start:
            continue
        end = phase.get("end") or "9999-12-31"
        if start <= date_str <= end:
            return phase
    return None


def get_next_phase(taper: dict, date_str: str | None = None) -> dict | None:
    """Return the phase AFTER the active one on date_str (None if last)."""
    if date_str is None:
        date_str = _today_str()
    phases = taper.get("phases", [])
    for i, phase in enumerate(phases):
        start = phase.get("start")
        if not start:
            continue
        end = phase.get("end") or "9999-12-31"
        if start <= date_str <= end:
            if i + 1 < len(phases):
                return phases[i + 1]
            return None
    return None


def get_dexa_dose(slot: str, date_str: str | None = None) -> int | None:
    """
    Return authoritative dexa mg for a slot on a given date.

    Respects taper frequency-based slot deactivation: if the active phase's
    frequency deactivates the slot (e.g. BD phase drops slot D), returns 0.

    Returns:
        int  -> dose in mg (0 means explicitly zero / slot inactive)
        None -> slot is not a dexa slot, or no active phase, or taper missing
    """
    slot = (slot or "").upper()
    if slot not in SLOT_TO_KEY:
        return None
    try:
        taper = json_load_taper()
    except Exception:
        return None
    if not taper or "phases" not in taper:
        return None
    phase = get_active_phase(taper, date_str)
    if not phase:
        return None
    # Frequency-based slot deactivation (e.g. BD drops D, OD drops C/D)
    freq = phase.get("freq", "TDS")
    active_slots = taper.get("active_slots_by_freq", {}).get(freq, ["B", "C", "D"])
    if slot not in active_slots:
        return 0
    key = SLOT_TO_KEY[slot]
    return phase.get(key, 0)


def json_load_taper() -> dict:
    import json
    try:
        with open(TAPER_FILE) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def is_dexa_drug(drug_id: str) -> bool:
    return (drug_id or "").lower().startswith(_DEXA_DRUG_PREFIX)
