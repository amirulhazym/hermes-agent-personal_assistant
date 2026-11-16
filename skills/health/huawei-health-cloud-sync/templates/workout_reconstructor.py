#!/usr/bin/env python3
"""Reconstruct workouts (and biometrics) that never appear in /dataQuery/sport/*.

Template extracted from a working implementation (verified 2026-11-15, Huawei MY account,
Watch Fit 4 Pro on HarmonyOS 6.1.0.117). Stdlib only; expects the vendored `client.py`
(`HuaweiHealthClient`, `health_data`, `sports_stat`) importable.

Wire-up:
    import workout_reconstructor as wrec
    extra = wrec.reconstruct(cli, int(datetime.now().strftime("%Y%m%d")))
    payload["workouts"] = extra["workouts"]
    payload["workout_kcal_gap"] = extra["workout_kcal_gap"]
    payload["metrics"]["body_weight_kg"] = {"value": extra["body_weight_kg"], "unit": "kg"}
    payload["metrics"]["spo2_pct"] = {"value": extra["spo2_pct"], "unit": "%"}

Cost: four extra getHealthData pulls per run; the type-7 series is ~256 KB, so peak RSS rises.
Run it only on the end-of-day tick if the memory budget is tight.
"""
from __future__ import annotations

import json
from datetime import datetime

TYPE_EXERCISE_INTENSITY = 12
TYPE_DYNAMIC_HR = 7
TYPE_WEIGHT = 8
TYPE_SPO2 = 16

BLOCK_GAP_MIN = 3
MIN_BLOCK_SAMPLES = 10


def _points(response: dict, day_int: int) -> list[tuple[int, dict]]:
    data = (response or {}).get("data") or {}
    records = data.get(str(day_int)) or data.get(day_int) or []
    out: list[tuple[int, dict]] = []
    for record in records:
        for point in record.get("samplePoints") or []:
            if point.get("startTime"):
                out.append((int(point["startTime"]), point))
    out.sort(key=lambda item: item[0])
    return out


def _point_value(point: dict) -> dict:
    raw = point.get("value")
    if isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return {"value": raw}


def exercise_blocks(response: dict, day_int: int) -> list[dict]:
    stamps = sorted({ms for ms, _ in _points(response, day_int)})
    if not stamps:
        return []
    blocks: list[list[int]] = [[stamps[0]]]
    for prev, cur in zip(stamps, stamps[1:]):
        if (cur - prev) <= BLOCK_GAP_MIN * 60_000:
            blocks[-1].append(cur)
        else:
            blocks.append([cur])
    return [{"start_ms": b[0], "end_ms": b[-1] + 60_000, "duration_min": len(b)}
            for b in blocks if len(b) >= MIN_BLOCK_SAMPLES]


def hr_within(response: dict, day_int: int, start_ms: int, end_ms: int) -> dict | None:
    values: list[float] = []
    for ms, point in _points(response, day_int):
        if start_ms <= ms <= end_ms:
            try:
                values.append(float(_point_value(point).get("value")))
            except (TypeError, ValueError):
                continue
    if not values:
        return None
    return {"samples": len(values), "avg_bpm": round(sum(values) / len(values), 1),
            "max_bpm": int(max(values)), "min_bpm": int(min(values))}


def workout_kcal_gap(stat_row: dict) -> float | None:
    basic = (stat_row or {}).get("sportBasicInfo") or {}
    dimen = (stat_row or {}).get("dimenDailyActivity") or {}
    total = basic.get("calorie")
    if total is None:
        return None
    gap = (float(total) - float(dimen.get("walkCalories") or 0)
           - float(dimen.get("climbCalories") or 0)) / 1000.0
    return round(gap, 1) if gap > 0 else 0.0


def body_weight(response: dict, day_int: int) -> float | None:
    for _, point in _points(response, day_int):
        weight = _point_value(point).get("bodyWeight")
        if weight:
            return float(weight)
    return None


def spo2_avg(response: dict, day_int: int) -> float | None:
    values = []
    for _, point in _points(response, day_int):
        sat = _point_value(point).get("avgSaturation")
        if sat is None:
            continue
        try:
            values.append(float(sat))
        except (TypeError, ValueError):
            continue
    return round(sum(values) / len(values), 1) if values else None


def reconstruct(client, day_int: int) -> dict:
    ex = client.health_data(day_int, day_int, TYPE_EXERCISE_INTENSITY)
    hr = client.health_data(day_int, day_int, TYPE_DYNAMIC_HR)
    wt = client.health_data(day_int, day_int, TYPE_WEIGHT)
    sp = client.health_data(day_int, day_int, TYPE_SPO2)
    rows = (client.sports_stat(day_int, day_int).get("sportStat") or [])

    workouts = []
    for index, block in enumerate(exercise_blocks(ex, day_int)):
        hr_stats = hr_within(hr, day_int, block["start_ms"], block["end_ms"]) or {}
        workouts.append({
            "index": index,
            "start": datetime.fromtimestamp(block["start_ms"] / 1000).astimezone()
                      .isoformat(timespec="seconds"),
            "end": datetime.fromtimestamp(block["end_ms"] / 1000).astimezone()
                    .isoformat(timespec="seconds"),
            "duration_min": block["duration_min"],
            "avg_bpm": hr_stats.get("avg_bpm"),
            "max_bpm": hr_stats.get("max_bpm"),
            "min_bpm": hr_stats.get("min_bpm"),
            "reconstructed": True,
            "kcal_note": "aggregate gap only; per-block split not attempted",
        })

    return {
        "workouts": workouts,
        "workout_kcal_gap": workout_kcal_gap(rows[0] if rows else {}),
        "body_weight_kg": body_weight(wt, day_int),
        "spo2_pct": spo2_avg(sp, day_int),
        "raw_counts": {"exercise": len(_points(ex, day_int)), "hr": len(_points(hr, day_int)),
                       "spo2": len(_points(sp, day_int)), "weight": len(_points(wt, day_int))},
    }
