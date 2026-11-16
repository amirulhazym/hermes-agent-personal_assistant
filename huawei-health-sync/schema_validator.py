#!/usr/bin/env python3
"""Sanity gate for sync_huawei.py output. Exit 0 = pass, 1 = fail.

Usage: python3 schema_validator.py <path-to-json>
"""
from __future__ import annotations

import json
import sys


def check_range(name: str, value, lo: float, hi: float, problems: list[str]) -> None:
    if value is None:
        print(f"  SKIP  {name}: null (no measurement)")
        return
    try:
        v = float(value)
    except (TypeError, ValueError):
        problems.append(f"{name} is not numeric: {value!r}")
        return
    if lo <= v <= hi:
        print(f"  OK    {name}: {v}")
    else:
        problems.append(f"{name} out of bounds [{lo}, {hi}]: {v}")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("USAGE: schema_validator.py <json>")
        return 1
    p = argv[1]
    try:
        d = json.load(open(p, encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL  cannot load {p}: {exc}")
        return 1

    problems: list[str] = []

    print(f"file: {p}")
    for key in ("schema_version", "date_myt", "fetched_at", "sync_status", "metrics", "tdee_calibration"):
        if key in d:
            print(f"  OK    top-level key {key}")
        else:
            problems.append(f"missing top-level key: {key}")

    metrics = d.get("metrics") or {}
    check_range("metrics.active_kcal.value", (metrics.get("active_kcal") or {}).get("value"), 0, 4000, problems)
    check_range("metrics.steps.value", (metrics.get("steps") or {}).get("value"), 0, 100000, problems)
    check_range("metrics.distance_m.value", (metrics.get("distance_m") or {}).get("value"), 0, 200000, problems)
    check_range("metrics.active_minutes.value", (metrics.get("active_minutes") or {}).get("value"), 0, 1440, problems)
    check_range("metrics.active_hours.value", (metrics.get("active_hours") or {}).get("value"), 0, 24, problems)

    sleep = metrics.get("sleep") or {}
    check_range("metrics.sleep.total_minutes", sleep.get("total_minutes"), 0, 1440, problems)
    for part in ("deep_minutes", "light_minutes", "rem_minutes", "awake_minutes"):
        if sleep.get(part) is not None and sleep.get("total_minutes") is not None:
            if float(sleep[part]) > float(sleep["total_minutes"]) + 60:
                problems.append(f"sleep.{part} ({sleep[part]}) exceeds total_minutes ({sleep['total_minutes']})")

    hr = metrics.get("heart_rate") or {}
    resting = hr.get("resting_bpm")
    if resting in (0, None):
        print("  SKIP  metrics.heart_rate.resting_bpm: 0/null (device reports no resting measurement)")
    else:
        check_range("metrics.heart_rate.resting_bpm", resting, 30, 140, problems)
    check_range("metrics.heart_rate.max_bpm", hr.get("max_bpm"), 30, 230, problems)
    check_range("body_weight_kg", d.get("body_weight_kg"), 30, 200, problems)
    spo2 = d.get("spo2_avg")
    if spo2 is not None:
        check_range("spo2_avg", spo2, 70, 100, problems)
    MODALITY_SOURCES = ("user_confirmed", "reconstructed_intensity_hr")
    for idx, w in enumerate(d.get("workouts") or []):
        if not w.get("duration_min") or not w.get("start"):
            problems.append(f"workouts[{idx}] missing duration_min/start")
            continue
        if float(w["duration_min"]) < 30:
            problems.append(f"workouts[{idx}] duration {w['duration_min']} < 30 min filter")
        kcal = w.get("active_kcal")
        if kcal is None or float(kcal) < 100.0:
            problems.append(f"workouts[{idx}] active_kcal {kcal} < 100 kcal filter")
        # Phase 5: gross calories + explicit modality provenance
        gross = w.get("estimated_gross_kcal")
        if gross is None:
            problems.append(f"workouts[{idx}] missing estimated_gross_kcal")
        elif kcal is not None and float(gross) < float(kcal):
            problems.append(f"workouts[{idx}] estimated_gross_kcal {gross} < active_kcal {kcal}")
        elif kcal is not None and float(gross) > float(kcal) * 3 + 400:
            problems.append(f"workouts[{idx}] estimated_gross_kcal implausible: {gross}")
        modality = w.get("modality")
        if not isinstance(modality, str) or not modality.strip():
            problems.append(f"workouts[{idx}] missing modality")
        source = w.get("modality_source")
        if source not in MODALITY_SOURCES:
            problems.append(f"workouts[{idx}] modality_source invalid: {source!r} "
                            f"(expected one of {MODALITY_SOURCES})")
        if source == "user_confirmed" and modality == "unclassified_workout":
            problems.append(f"workouts[{idx}] user_confirmed label cannot be unclassified_workout")

    if "sync_settling" not in d:
        problems.append("missing top-level key: sync_settling")
    elif not isinstance(d.get("sync_settling"), bool):
        problems.append(f"sync_settling must be bool: {d.get('sync_settling')!r}")
    elif d.get("sync_settling") and not d.get("sync_settling_reason"):
        problems.append("sync_settling is true but sync_settling_reason is empty")

    pool = d.get("workout_active_pool")
    if pool is not None and not isinstance(pool, dict):
        problems.append("workout_active_pool must be an object")

    if "devices" in d:
        problems.append("top-level 'devices' must not be written (lean schema)")

    for name, block in (("active_kcal", metrics.get("active_kcal")),
                        ("steps", metrics.get("steps")),
                        ("heart_rate", hr)):
        if isinstance(block, dict) and not block.get("provenance"):
            problems.append(f"{name}: missing provenance")

    tdee = d.get("tdee_calibration") or {}
    if tdee.get("candidate_tdee_kcal") is not None:
        cand = float(tdee["candidate_tdee_kcal"])
        if not (1000 <= cand <= 6000):
            problems.append(f"tdee_calibration.candidate_tdee_kcal implausible: {cand}")
        else:
            print(f"  OK    tdee_calibration.candidate_tdee_kcal: {cand}")

    # Dynamic BMR: must exist, match Mifflin-St Jeor on the recorded basis weight,
    # and reproduce both the PAL floor and the candidate TDEE.
    bmr = tdee.get("bmr_kcal")
    if bmr is None:
        problems.append("tdee_calibration.bmr_kcal missing (dynamic BMR not written)")
    else:
        try:
            bmr_f = float(bmr)
        except (TypeError, ValueError):
            problems.append(f"tdee_calibration.bmr_kcal not numeric: {bmr!r}")
            bmr_f = None
        if bmr_f is not None:
            if not (800 <= bmr_f <= 4000):
                problems.append(f"tdee_calibration.bmr_kcal implausible: {bmr_f}")
            basis = tdee.get("bmr_basis") or {}
            weight = basis.get("weight_kg")
            if weight is None:
                problems.append("tdee_calibration.bmr_basis.weight_kg missing")
            else:
                try:
                    height = float(basis.get("height_cm", 157.0))
                    age = float(basis.get("age_years", 27.0))
                    expected = round(10.0 * float(weight) + 6.25 * height - 5.0 * age + 5.0)
                except (TypeError, ValueError):
                    problems.append(f"tdee_calibration.bmr_basis non-numeric: {basis!r}")
                    expected = None
                if expected is not None:
                    if abs(expected - bmr_f) > 1:
                        problems.append(f"bmr_kcal {bmr_f} != Mifflin-St Jeor {expected} "
                                        f"at {weight} kg")
                    else:
                        print(f"  OK    bmr_kcal {int(bmr_f)} = Mifflin({weight} kg)")
            floor = tdee.get("pal_floor_kcal")
            if floor is None:
                problems.append("tdee_calibration.pal_floor_kcal missing")
            elif abs(float(floor) - round(bmr_f * 0.15, 2)) > 0.01:
                problems.append(f"pal_floor_kcal {floor} != 15% of BMR "
                                f"({round(bmr_f * 0.15, 2)})")
            cand2 = tdee.get("candidate_tdee_kcal")
            device = tdee.get("device_active_kcal")
            if cand2 is not None and device is not None and floor is not None:
                expected_tdee = round(bmr_f + max(float(floor), float(device)), 1)
                if abs(expected_tdee - float(cand2)) > 0.2:
                    problems.append(f"candidate_tdee_kcal {cand2} != BMR + max(floor, "
                                    f"device_active) = {expected_tdee}")
                else:
                    print(f"  OK    TDEE = {int(bmr_f)} + max({floor}, {device}) = {cand2}")

    if problems:
        print("\nFAIL:")
        for prob in problems:
            print(f"  - {prob}")
        return 1
    print("\nPASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
