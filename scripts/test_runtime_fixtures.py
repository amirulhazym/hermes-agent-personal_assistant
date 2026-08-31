"""Small synthetic runtime fixtures for hermetic medication-chain tests.

The production runtime keeps regimen and supply JSON outside public Git. These
fixtures cover only the structural fields exercised by the tests and are
written into each test's temporary HOME; they never read or modify live state.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _drug(drug_id: str, *, dosage: str = "1 tablet", required: bool = True) -> dict[str, Any]:
    return {
        "drug": drug_id,
        "drug_id": drug_id,
        "dosage": dosage,
        "required": required,
    }


def _schedule() -> dict[str, Any]:
    return {
        "version": "test-fixture",
        "meds": {
            "A": {
                "time": "06:00",
                "drugs": [_drug("akurit_2"), _drug("pyridoxine")],
            },
            "B": {
                "time": "08:00",
                "drugs": [_drug("levetiracetam_b"), _drug("dexamethasone_1")],
            },
            "C": {
                "time": "12:00",
                "drugs": [
                    _drug("dexamethasone_2", dosage="4mg"),
                    _drug("calcium", dosage="500mg"),
                    _drug("calcitriol"),
                ],
            },
            "D": {
                "time": "16:00",
                "drugs": [_drug("dexamethasone_3", dosage="4mg")],
            },
            "E": {
                "time": "20:00",
                "drugs": [_drug("levetiracetam_e")],
            },
            "F": {
                "time": "14:00",
                "drugs": [_drug("dexamethasone_f", dosage="4mg")],
            },
        },
    }


def _taper() -> dict[str, Any]:
    return {
        "version": "test-fixture",
        "active_slots_by_freq": {
            "TDS": ["A", "B", "C", "D", "E"],
            "BD": ["A", "B", "C", "E", "F"],
            "OD": ["A", "B", "E"],
            "STOP": ["A", "E"],
        },
        "phases": [
            {
                "start": "2026-08-01",
                "end": "2026-08-11",
                "freq": "TDS",
                "total_mg": 12,
                "dose_morning": 4,
                "dose_midday": 4,
                "dose_afternoon": 4,
            },
            {
                "start": "2026-08-12",
                "end": "2026-08-25",
                "freq": "TDS",
                "total_mg": 11,
                "dose_morning": 4,
                "dose_midday": 4,
                "dose_afternoon": 3,
            },
            {
                "start": "2026-08-26",
                "end": "2026-09-08",
                "freq": "BD",
                "total_mg": 10,
                "dose_morning": 6,
                "dose_midday": 0,
                "dose_afternoon": 0,
                "dose_2pm": 4,
            },
        ],
    }


def _supply() -> dict[str, Any]:
    return {
        "version": "test-fixture",
        "drugs": {
            "calcium": {"current": 10, "warning_threshold": 2, "name": "test-calcium", "slot": "C"},
            "calcitriol": {"current": 20, "warning_threshold": 2, "name": "test-calcitriol", "slot": "C"},
        },
    }


def write_runtime_fixtures(hermes_home: Path, *, include_supply: bool = False) -> None:
    """Write only synthetic fixture data into an isolated test HOME."""
    hermes_home.mkdir(parents=True, exist_ok=True)
    (hermes_home / "med-schedule.json").write_text(
        json.dumps(_schedule(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (hermes_home / "dexa_taper.json").write_text(
        json.dumps(_taper(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if include_supply:
        (hermes_home / "med-supply.json").write_text(
            json.dumps(_supply(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
