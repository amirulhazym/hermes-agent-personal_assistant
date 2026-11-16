#!/usr/bin/env python3
"""Huawei Health (Watch Fit 4 Pro) -> local JSON puller.

Read-only. Stdlib only. Tokens live in ~/secrets/huawei_tokens.json (0600).

Modes (Phase 5, owner SOP 2026-11-16):
  (no args)              sync today -> data/YYYY-MM-DD.json + data/latest.json
  --date YYYYMMDD        sync one historical day -> data/YYYY-MM-DD.json only
  --finalize-yesterday   re-sync yesterday (late-night activity after the 22:30 cron)
  --annotate DATE HH:MM "Label"
                         store an owner-confirmed modality in
                         data/workout_annotations.json, then sync that date

Exit codes: 0 ok | 2 auth expired (re-login needed) | 3 other failure
"""
from __future__ import annotations

import argparse
import gc
import json
import os
import sys
import time
import traceback
from datetime import datetime, timedelta

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
SETTLING_MIN = 30                                   # watch->cloud settling window
SCHEMA_VERSION = "1.1.0"
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


def settling_state(workouts: list, now: datetime) -> tuple[bool, str | None]:
    """True when a workout block ended < SETTLING_MIN minutes ago (cloud still updating)."""
    for workout in workouts or []:
        end = workout.get("end")
        if not end:
            continue
        try:
            end_dt = datetime.fromisoformat(end)
        except ValueError:
            continue
        if end_dt.tzinfo is None:
            end_dt = end_dt.astimezone()
        if (now - end_dt) < timedelta(minutes=SETTLING_MIN):
            return True, (f"Workout ended <{SETTLING_MIN}m ago; cloud aggregates may still "
                          "update")
    return False, None


def build_payload(cli, target_int: int, now: datetime, is_today: bool) -> dict:
    fetched_at = now.isoformat(timespec="seconds")
    date_str = datetime.strptime(str(target_int), "%Y%m%d").strftime("%Y-%m-%d")
    prov = lambda endpoint, raw: {  # noqa: E731
        "endpoint": endpoint,
        "raw_field": raw,
        "source_device": "Huawei Watch Fit 4 Pro",
        "fetched_at": fetched_at,
    }

    stat = call_with_retry(lambda: cli.sports_stat(target_int, target_int), "sports_stat")
    health = call_with_retry(
        lambda: cli.health_stat(target_int, target_int, (7, 9, 11, 12)), "health_stat")
    try:
        extra = wrec.reconstruct(cli, target_int, annotations=wrec.load_annotations())
    except client.HuaweiError as exc:
        extra = {"workouts": [], "workout_kcal_gap": None, "workout_active_pool": {},
                 "body_weight_kg": None, "spo2_avg": None, "source_counts": {},
                 "error": f"{type(exc).__name__}: {exc}"}

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
    if latest_ms and is_today:
        stale_min = int((now.timestamp() - latest_ms / 1000) / 60)

    is_stale = bool(
        is_today and ((stale_min is not None and stale_min > STALE_THRESHOLD_MIN)
                      or (steps == 0 and now.hour >= 10))
    )

    settling, settling_reason = settling_state(extra.get("workouts") or [], now)
    if not is_today:
        settling, settling_reason = False, None

    device_active = active_kcal if active_kcal is not None else None
    candidate_tdee = (round(BMR_KCAL + max(PAL_FLOOR_KCAL, device_active), 1)
                      if device_active is not None else None)

    return {
        "schema_version": SCHEMA_VERSION,
        "date_myt": date_str,
        "fetched_at": fetched_at,
        "is_historical": not is_today,
        "sync_settling": settling,
        "sync_settling_reason": settling_reason,
        "sync_status": {
            "auth_state": "VALID",
            "cloud_last_record_at": (datetime.fromtimestamp(latest_ms / 1000).astimezone()
                                     .isoformat(timespec="seconds") if latest_ms else None),
            "staleness_minutes": stale_min,
            "is_stale": is_stale,
            "stale_threshold_minutes": STALE_THRESHOLD_MIN,
            "source": ("latest record generateTime (getSyncVersions deferred)"
                       if is_today else "historical backfill; staleness not evaluated"),
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
        "workout_active_pool": extra.get("workout_active_pool") or {},
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


def write_annotation(date_str: str, hhmm: str, label: str) -> str:
    path = wrec.annotations_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    data = wrec.load_annotations()
    key = f"{date_str}_{hhmm}"
    data[key] = label
    write_atomic(path, data)
    return key


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Huawei Health cloud sync")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--date", metavar="YYYYMMDD", help="sync one historical day (no latest.json write)")
    group.add_argument("--finalize-yesterday", action="store_true",
                       help="re-sync yesterday so late-night activity is captured")
    group.add_argument("--annotate", nargs=3, metavar=("DATE", "HH:MM", "LABEL"),
                       help="store an owner-confirmed modality then sync that date")
    return parser.parse_args(argv)


def resolve_target(args: argparse.Namespace, now: datetime) -> tuple[int, bool]:
    """Return (target YYYYMMDD int, is_today)."""
    today_int = int(now.strftime("%Y%m%d"))
    if args.date:
        return int(args.date), int(args.date) == today_int
    if args.finalize_yesterday:
        yesterday = (now - timedelta(days=1)).strftime("%Y%m%d")
        return int(yesterday), False
    if args.annotate:
        target = int(args.annotate[0].replace("-", ""))
        return target, target == today_int
    return today_int, True


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    now = datetime.now().astimezone()
    os.makedirs(DATA, exist_ok=True)

    if args.annotate:
        date_arg, hhmm, label = args.annotate
        date_str = datetime.strptime(date_arg.replace("-", ""), "%Y%m%d").strftime("%Y-%m-%d")
        key = write_annotation(date_str, hhmm, label)
        log(f"annotation saved {key}={label}")

    target_int, is_today = resolve_target(args, now)
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

    try:
        payload = build_payload(cli, target_int, now, is_today)
    except client.HuaweiApiError as exc:
        if exc.code in client.AUTH_FAILED_CODES:
            log(f"auth failed resultCode={exc.code}; refreshing once and retrying")
            try:
                client.refresh_tokens(tokens)
                payload = build_payload(cli, target_int, now, is_today)
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
    if is_today:
        write_atomic(os.path.join(DATA, "latest.json"), payload)
        write_atomic(os.path.join(DATA, "status.json"),
                     {"auth_state": "VALID", "at": payload["fetched_at"],
                      "is_stale": payload["sync_status"]["is_stale"],
                      "staleness_minutes": payload["sync_status"]["staleness_minutes"]})

    m = payload["metrics"]
    pool = payload.get("workout_active_pool") or {}
    log("OK date={} kcal={} steps={} workout_active={} walk_raw={} walk_capped={} settling={}".format(
        payload["date_myt"], m["active_kcal"]["value"], m["steps"]["value"],
        pool.get("workout_active_kcal"), pool.get("raw_walk_kcal"),
        pool.get("walk_capped"), payload.get("sync_settling")))
    print(f"WROTE {daily_path}" + ("" if is_today else " (historical: latest.json untouched)"))
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
