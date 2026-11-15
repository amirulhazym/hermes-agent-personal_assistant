#!/usr/bin/env python3
"""Reconstruct workouts from Huawei cloud series that have no /dataQuery/sport/ record.

Verified 2026-11-15 on Watch Fit 4 Pro (HarmonyOS 6.1.0.117), MY account:
  * getSportsStat(type 0): total vs walk/climb calories -> the unattributed workout kcal.
  * getHealthData(type 12) EXERCISE_INTENSITY: one sample per active minute -> blocks.
  * getHealthData(type 7) DATA_POINT_DYNAMIC_HEARTRATE: 1-min HR during workouts -> avg/max.
  * getHealthData(type 8) WEIGHT_BODYFAT_BROAD: bodyWeight (with 14-day lookback).
  * getHealthData(type 16) BLOOD_OXYGEN_SATURATION: avgSaturation (daily avg + latest).

Hardening rules (owner decision 2026-11-15, Phase 4.5):
  * a block must be >= 30 minutes AND carry >= 100 kcal attributed gap to count as a workout;
  * a block already covered >= 50% by an explicit GPS workout is marked already_logged and
    excluded from gap allocation (no double counting);
  * raw payloads are dropped and gc.collect() is called right after extraction.
"""
from __future__ import annotations

import gc
import json
from datetime import datetime, timedelta

TYPE_EXERCISE_INTENSITY = 12
TYPE_DYNAMIC_HR = 7
TYPE_WEIGHT = 8
TYPE_SPO2 = 16

BLOCK_GAP_MIN = 3
MIN_BLOCK_SAMPLES = 30          # owner rule: >= 30 minutes
MIN_WORKOUT_KCAL = 100.0        # owner rule: >= 100 kcal attributed
GPS_SPORT_TYPES = (3, 4, 9)     # outdoor cycling, running, swimming
OVERLAP_THRESHOLD = 0.5
WEIGHT_LOOKBACK_DAYS = 14
HEALTH_RANGE_MAX_DAYS = 7       # cloud rejects wider getHealthData ranges (verified 1001)


# ── parsing helpers ──────────────────────────────────────────────────────

def _day_records(response: dict, day_int: int) -> list:
    data = (response or {}).get("data") or {}
    return data.get(str(day_int)) or data.get(day_int) or []


def _point_value(point: dict) -> dict:
    raw = point.get("value")
    if isinstance(raw, str) and raw.strip().startswith("{"):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
    return {"value": raw}


def _hr_series(response: dict, day_int: int) -> list[tuple[int, float]]:
    series: list[tuple[int, float]] = []
    for record in _day_records(response, day_int):
        for point in record.get("samplePoints") or []:
            start = point.get("startTime")
            if not start:
                continue
            try:
                value = float(_point_value(point).get("value"))
            except (TypeError, ValueError):
                continue
            series.append((int(start), value))
    series.sort(key=lambda item: item[0])
    return series


def exercise_blocks(response: dict, day_int: int) -> list[dict]:
    stamps = sorted({int(p["startTime"]) for r in _day_records(response, day_int)
                     for p in (r.get("samplePoints") or []) if p.get("startTime")})
    if not stamps:
        return []
    groups: list[list[int]] = [[stamps[0]]]
    for prev, cur in zip(stamps, stamps[1:]):
        if (cur - prev) <= BLOCK_GAP_MIN * 60_000:
            groups[-1].append(cur)
        else:
            groups.append([cur])
    blocks = []
    for group in groups:
        if len(group) < MIN_BLOCK_SAMPLES:
            continue
        blocks.append({"start_ms": group[0], "end_ms": group[-1] + 60_000,
                       "duration_min": len(group), "samples": len(group)})
    return blocks


def hr_within(series: list[tuple[int, float]], start_ms: int, end_ms: int) -> dict | None:
    values = [v for ms, v in series if start_ms <= ms <= end_ms]
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


def _overlap_fraction(block: dict, session_start: int, session_end: int) -> float:
    start = max(block["start_ms"], session_start)
    end = min(block["end_ms"], session_end)
    if end <= start:
        return 0.0
    return (end - start) / max(block["end_ms"] - block["start_ms"], 1)


def gps_sessions(client, day_int: int) -> list[dict]:
    """Explicit /sport/ workouts (GPS types) for the day — used only for overlap checks."""
    try:
        response = client.sports_detail(day_int, day_int, GPS_SPORT_TYPES)
    except Exception:  # noqa: BLE001 - overlap check is best-effort
        return []
    records = (response.get("data") or {})
    flat: list[dict] = []
    for value in records.values():
        if isinstance(value, list):
            flat.extend(value)
    out = []
    for rec in flat:
        start, end = rec.get("startTime"), rec.get("endTime")
        if start and end:
            out.append({"start_ms": int(start), "end_ms": int(end),
                        "sport_type": rec.get("sportType")})
    return out


def body_weight(client, day_int: int) -> tuple[float | None, str | None]:
    """Today's weight, else the most recent record within 14 days."""
    day = datetime.strptime(str(day_int), "%Y%m%d").date()
    # chunk the lookback into <=7-day ranges (cloud rejects wider ranges)
    cursor = day
    for _ in range(0, WEIGHT_LOOKBACK_DAYS, HEALTH_RANGE_MAX_DAYS):
        start = max(cursor - timedelta(days=HEALTH_RANGE_MAX_DAYS - 1),
                    day - timedelta(days=WEIGHT_LOOKBACK_DAYS - 1))
        response = client.health_data(int(start.strftime("%Y%m%d")),
                                      int(cursor.strftime("%Y%m%d")), TYPE_WEIGHT)
        data = (response or {}).get("data") or {}
        for key in sorted(data.keys(), reverse=True):          # newest date first
            for record in data[key]:
                for point in record.get("samplePoints") or []:
                    weight = _point_value(point).get("bodyWeight")
                    if weight:
                        return round(float(weight), 1), key
        del response, data
        gc.collect()
        cursor = start - timedelta(days=1)
        if cursor < day - timedelta(days=WEIGHT_LOOKBACK_DAYS - 1):
            break
    return None, None


def spo2_stats(response: dict, day_int: int) -> tuple[float | None, float | None]:
    values: list[tuple[int, float]] = []
    for record in _day_records(response, day_int):
        for point in record.get("samplePoints") or []:
            sat = _point_value(point).get("avgSaturation")
            if sat is None:
                continue
            try:
                values.append((int(point.get("startTime") or 0), float(sat)))
            except (TypeError, ValueError):
                continue
    if not values:
        return None, None
    values.sort()
    avg = round(sum(v for _, v in values) / len(values), 1)
    return avg, round(values[-1][1], 1)


# ── orchestrator ─────────────────────────────────────────────────────────

def reconstruct(client, day_int: int) -> dict:
    ex = client.health_data(day_int, day_int, TYPE_EXERCISE_INTENSITY)
    hr = client.health_data(day_int, day_int, TYPE_DYNAMIC_HR)
    sp = client.health_data(day_int, day_int, TYPE_SPO2)
    stat = client.sports_stat(day_int, day_int)
    rows = stat.get("sportStat") or []
    gap = workout_kcal_gap(rows[0] if rows else {})

    blocks = exercise_blocks(ex, day_int)
    hr_series = _hr_series(hr, day_int)
    gps = gps_sessions(client, day_int)

    # drop bulky payloads before any formatting work
    counts = {"exercise_samples": sum(len(r.get("samplePoints") or []) for r in _day_records(ex, day_int)),
              "hr_samples": len(hr_series),
              "spo2_samples": sum(len(r.get("samplePoints") or []) for r in _day_records(sp, day_int))}
    del ex, hr
    gc.collect()

    annotated = []
    for block in blocks:
        overlap = max((_overlap_fraction(block, s["start_ms"], s["end_ms"]) for s in gps),
                      default=0.0)
        annotated.append({**block, "already_logged": overlap >= OVERLAP_THRESHOLD,
                          "overlap": round(overlap, 2)})

    eligible = [b for b in annotated if not b["already_logged"]]
    total_minutes = sum(b["duration_min"] for b in eligible) or 1
    workouts = []
    for index, block in enumerate(eligible):
        attributed = (round(gap * block["duration_min"] / total_minutes, 1)
                      if gap is not None else None)
        if attributed is not None and attributed < MIN_WORKOUT_KCAL:
            continue                                   # owner rule: noise, not a workout
        stats = hr_within(hr_series, block["start_ms"], block["end_ms"])
        workouts.append({
            "index": index,
            "start": datetime.fromtimestamp(block["start_ms"] / 1000).astimezone()
                      .isoformat(timespec="seconds"),
            "end": datetime.fromtimestamp(block["end_ms"] / 1000).astimezone()
                    .isoformat(timespec="seconds"),
            "duration_min": block["duration_min"],
            "active_kcal": attributed,
            "avg_bpm": (stats or {}).get("avg_bpm"),
            "max_bpm": (stats or {}).get("max_bpm"),
            "min_bpm": (stats or {}).get("min_bpm"),
            "hr_samples": (stats or {}).get("samples"),
            "already_logged": False,
            "reconstructed": True,
            "provenance": {
                "duration": "/dataQuery/health/getHealthData type=12",
                "heart_rate": "/dataQuery/health/getHealthData type=7",
                "kcal_allocation": "daily gap apportioned by duration (no per-block kcal in cloud)",
                "source_device": "Huawei Watch Fit 4 Pro",
            },
        })

    sp_avg, sp_latest = spo2_stats(sp, day_int)
    del sp
    gc.collect()
    weight, weight_date = body_weight(client, day_int)
    excluded = [{"start_ms": b["start_ms"], "duration_min": b["duration_min"],
                 "reason": "below_min_kcal_or_minutes"}
                for b in annotated if b not in eligible]
    del stat, rows, hr_series, gps, blocks, annotated, eligible
    gc.collect()

    return {
        "workouts": workouts,
        "workout_kcal_gap": gap,
        "excluded_blocks": excluded,
        "body_weight_kg": weight,
        "body_weight_measured_date": weight_date,
        "spo2_avg": sp_avg,
        "spo2_latest": sp_latest,
        "source_counts": counts,
    }
