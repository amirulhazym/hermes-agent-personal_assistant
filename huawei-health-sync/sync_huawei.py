#!/usr/bin/env python3
"""Huawei Health (Watch Fit 4 Pro) -> local JSON puller.

Read-only. Stdlib only. Tokens live in ~/secrets/huawei_tokens.json (0600).

Exit codes: 0 ok | 2 auth expired (re-login needed) | 3 other failure
"""
from __future__ import annotations

import gc
import json
import os
import sys
import time
import traceback
from datetime import datetime

BASE = os.path.expanduser("~/hermes-huawei-sync")
VENDOR = os.path.join(BASE, "vendor")
DATA = os.path.join(BASE, "data")
LOGS = os.path.join(BASE, "logs")
SECRETS = os.path.expanduser("~/secrets/huawei_tokens.json")

sys.path.insert(0, VENDOR)
sys.path.insert(0, BASE)
import client  # noqa: E402
import workout_reconstructor as wrec  # noqa: E402

MYT = datetime.now().astimezone()
BMR_KCAL = 1449
PAL_FLOOR_KCAL = round(BMR_KCAL * 0.15, 2)          # 217.35
LEGACY_PAL_1_20_TDEE = round(BMR_KCAL * 1.20, 1)    # 1738.8
STALE_THRESHOLD_MIN = 180
MAX_RETRIES = 3


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line)
    try:
        os.makedirs(LOGS, exist_ok=True)
        with open(os.path.join(LOGS, "sync.log"), "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError:
        pass


def write_atomic(path: str, payload: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1, ensure_ascii=False)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def save_tokens(payload: dict) -> None:
    tmp = SECRETS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
        fh.flush()
        os.fsync(fh.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, SECRETS)


def load_tokens() -> "client.Tokens":
    data = json.load(open(SECRETS, encoding="utf-8"))
    return client.Tokens(**data, on_change=lambda t: save_tokens(t.as_dict))


def call_with_retry(fn, label: str):
    delay = 2
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return fn()
        except client.HuaweiConnectionError as exc:
            if attempt == MAX_RETRIES:
                raise
            log(f"{label}: connection error ({exc}); retry {attempt}/{MAX_RETRIES} in {delay}s")
            time.sleep(delay)
            delay *= 2


def ensure_fresh(tokens) -> None:
    if tokens.needs_rotation():
        log("rotating access token")
        client.refresh_tokens(tokens)


def num(value):
    return None if value is None else float(value)


def build_payload(cli, today_int: int, now: datetime) -> dict:
    fetched_at = now.isoformat(timespec="seconds")
    prov = lambda endpoint, raw: {  # noqa: E731
        "endpoint": endpoint,
        "raw_field": raw,
        "source_device": "Huawei Watch Fit 4 Pro",
        "fetched_at": fetched_at,
    }

    stat = call_with_retry(lambda: cli.sports_stat(today_int, today_int), "sports_stat")
    health = call_with_retry(
        lambda: cli.health_stat(today_int, today_int, (7, 9, 11, 12)), "health_stat")
    try:
        extra = wrec.reconstruct(cli, today_int)
    except client.HuaweiError as exc:
        extra = {"workouts": [], "workout_kcal_gap": None, "body_weight_kg": None,
                 "spo2_pct": None, "raw_counts": {}, "error": f"{type(exc).__name__}: {exc}"}

    stat_rows = stat.get("sportStat") or []
    basic = (stat_rows[0].get("sportBasicInfo") if stat_rows else None) or {}
    exer = (stat_rows[0].get("exerciseTimeBasic") if stat_rows else None) or {}
    active_h = (stat_rows[0].get("activeHourBasic") if stat_rows else None) or {}

    hr_row = (health.get("heartRateTotal") or [{}])[0].get("heartRateBasic") or {}
    sleep = (health.get("professionalSleepTotal") or [{}])[0].get("professionalSleep") or {}
    stress = (health.get("stressTotal") or [{}])[0].get("stressBasic") or {}

    steps = basic.get("steps")
    active_kcal = round(float(basic.get("calorie")) / 1000.0, 1) if basic.get("calorie") is not None else None
    sleep_total = sleep.get("allSleepTime")
    resting_hr = hr_row.get("lastRestHeartRate")

    # latest record stamp (ms epoch) across returned records
    stamps = [r.get("generateTime") or r.get("version") for r in
              (stat_rows + (health.get("heartRateTotal") or []) +
               (health.get("professionalSleepTotal") or [])) if isinstance(r, dict)]
    stamps = [s for s in stamps if isinstance(s, (int, float)) and s > 10**12]
    latest_ms = max(stamps) if stamps else None

    stale_min = None
    if latest_ms:
        stale_min = int((now.timestamp() - latest_ms / 1000) / 60)

    is_stale = bool(
        (stale_min is not None and stale_min > STALE_THRESHOLD_MIN)
        or (steps == 0 and now.hour >= 10)
    )

    device_active = active_kcal if active_kcal is not None else None
    candidate_tdee = (round(BMR_KCAL + max(PAL_FLOOR_KCAL, device_active), 1)
                      if device_active is not None else None)

    return {
        "schema_version": "1.0.0",
        "date_myt": now.strftime("%Y-%m-%d"),
        "fetched_at": fetched_at,
        "sync_status": {
            "auth_state": "VALID",
            "cloud_last_record_at": (datetime.fromtimestamp(latest_ms / 1000).astimezone()
                                     .isoformat(timespec="seconds") if latest_ms else None),
            "staleness_minutes": stale_min,
            "is_stale": is_stale,
            "stale_threshold_minutes": STALE_THRESHOLD_MIN,
            "source": "latest record generateTime (getSyncVersions deferred)",
        },
        "metrics": {
            "active_kcal": {"value": active_kcal, "unit": "kcal",
                            "semantics": "active_expenditure_only_excludes_bmr",
                            "provenance": prov("/dataQuery/sport/v2/getSportsStat", "sportBasicInfo.calorie")},
            "steps": {"value": steps, "unit": "steps",
                      "provenance": prov("/dataQuery/sport/v2/getSportsStat", "sportBasicInfo.steps")},
            "distance_m": {"value": basic.get("distance"), "unit": "meters",
                           "provenance": prov("/dataQuery/sport/v2/getSportsStat", "sportBasicInfo.distance")},
            "active_minutes": {"value": exer.get("totalMidHighIntensity"), "unit": "minutes",
                               "provenance": prov("/dataQuery/health/getHealthStat", "exerciseIntensityBasic.totalMidHighIntensity")},
            "active_hours": {"value": active_h.get("countActiveHour"), "unit": "hours",
                             "provenance": prov("/dataQuery/sport/v2/getSportsStat", "activeHourBasic.countActiveHour")},
            "sleep": {
                "total_minutes": sleep_total,
                "deep_minutes": sleep.get("deepSleepTime"),
                "light_minutes": sleep.get("lightSleepTime"),
                "rem_minutes": sleep.get("dreamTime"),
                "awake_minutes": sleep.get("awakeTime"),
                "sleep_score": sleep.get("sleepScore"),
                "efficiency_pct": sleep.get("sleepEfficiency"),
                "provenance": prov("/dataQuery/health/getHealthStat", "professionalSleep"),
            },
            "heart_rate": {
                "resting_bpm": resting_hr,
                "min_bpm": hr_row.get("minHeartRate"),
                "max_bpm": hr_row.get("maxHeartRate"),
                "last_bpm": hr_row.get("lastHeartRate"),
                "avg_resting_bpm": hr_row.get("avgRestingHeartRate"),
                "provenance": prov("/dataQuery/health/getHealthStat", "heartRateBasic"),
            },
            "stress": {
                "mean_score": stress.get("meanScore"),
                "last_score": stress.get("lastScore"),
                "max_score": stress.get("maxScore"),
                "provenance": prov("/dataQuery/health/getHealthStat", "stressBasic"),
            },
        },
        "workouts": extra.get("workouts") or [],
        "workout_kcal_gap": extra.get("workout_kcal_gap"),
        "workout_excluded_blocks": extra.get("excluded_blocks") or [],
        "workout_source_counts": extra.get("source_counts"),
        "body_weight_kg": extra.get("body_weight_kg"),
        "body_weight_measured_date": extra.get("body_weight_measured_date"),
        "spo2_avg": extra.get("spo2_avg"),
        "spo2_latest": extra.get("spo2_latest"),
        "biometrics_provenance": {
            "body_weight_kg": "/dataQuery/health/getHealthData type=8 (today, else <=14d lookback)",
            "spo2_avg": "/dataQuery/health/getHealthData type=16 (multi-sample daily average)",
            "spo2_latest": "/dataQuery/health/getHealthData type=16 (last sample)",
        },
        "tdee_calibration": {
            "bmr_kcal": BMR_KCAL,
            "pal_floor_kcal": PAL_FLOOR_KCAL,
            "device_active_kcal": device_active,
            "candidate_tdee_kcal": candidate_tdee,
            "legacy_pal_1_20_tdee_kcal": LEGACY_PAL_1_20_TDEE,
            "delta_vs_pal_1_20_kcal": (round(candidate_tdee - LEGACY_PAL_1_20_TDEE, 1)
                                       if candidate_tdee is not None else None),
            "note": "PAL floor rule: TDEE = BMR + max(PAL_floor, device_active). 7-day lock before changing tracker formula.",
        },
    }


def main() -> int:
    now = datetime.now().astimezone()
    os.makedirs(DATA, exist_ok=True)
    tokens = load_tokens()

    try:
        ensure_fresh(tokens)
    except client.HuaweiApiError as exc:
        if exc.code == client.RT_INVALID_CODE:
            write_atomic(os.path.join(DATA, "status.json"),
                         {"auth_state": "EXPIRED", "at": now.isoformat(timespec="seconds"),
                          "resultCode": exc.code})
            log(f"AUTH EXPIRED resultCode={exc.code} -> re-login required")
            return 2
        log(f"refresh failed resultCode={exc.code}: {str(exc)[:160]}")
        return 3
    except client.HuaweiError as exc:
        log(f"refresh connection failure: {str(exc)[:160]}")
        return 3

    cli = client.HuaweiHealthClient(tokens)
    today_int = int(now.strftime("%Y%m%d"))

    try:
        payload = build_payload(cli, today_int, now)
    except client.HuaweiApiError as exc:
        if exc.code in client.AUTH_FAILED_CODES:
            log(f"auth failed resultCode={exc.code}; refreshing once and retrying")
            try:
                client.refresh_tokens(tokens)
                payload = build_payload(cli, today_int, now)
            except client.HuaweiApiError as exc2:
                log(f"retry failed resultCode={exc2.code}")
                return 2 if exc2.code == client.RT_INVALID_CODE else 3
        elif exc.code == client.RT_INVALID_CODE:
            write_atomic(os.path.join(DATA, "status.json"),
                         {"auth_state": "EXPIRED", "at": now.isoformat(timespec="seconds"),
                          "resultCode": exc.code})
            log("AUTH EXPIRED -> re-login required")
            return 2
        else:
            log(f"API error resultCode={exc.code}: {str(exc)[:160]}")
            return 3
    except Exception:  # noqa: BLE001
        log("unexpected failure:\n" + traceback.format_exc()[-800:])
        return 3

    gc.collect()
    daily_path = os.path.join(DATA, f"{payload['date_myt']}.json")
    write_atomic(daily_path, payload)
    write_atomic(os.path.join(DATA, "latest.json"), payload)
    write_atomic(os.path.join(DATA, "status.json"),
                 {"auth_state": "VALID", "at": payload["fetched_at"],
                  "is_stale": payload["sync_status"]["is_stale"],
                  "staleness_minutes": payload["sync_status"]["staleness_minutes"]})

    m = payload["metrics"]
    log("OK kcal={} steps={} stale={}min".format(
        m["active_kcal"]["value"], m["steps"]["value"],
        payload["sync_status"]["staleness_minutes"]))
    return 0


if __name__ == "__main__":
    try:
        _rc = main()
    finally:
        try:
            import resource
            log(f"RSS_KB={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss}")
        except Exception:  # noqa: BLE001
            pass
    raise SystemExit(_rc)
