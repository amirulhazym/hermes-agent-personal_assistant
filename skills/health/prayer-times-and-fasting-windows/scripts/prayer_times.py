#!/usr/bin/env python3
"""Fetch JAKIM e-solat prayer times for one zone.

VERIFIED 2026-11-13 against:
  https://www.e-solat.gov.my/index.php?r=esolatApi/takwimsolat&period=today&zone=SGR01
which returned prayerTime[0] with hijri/date/day/imsak/fajr/syuruk/dhuha/dhuhr/asr/maghrib/isha.

Usage:
  python3 prayer_times.py                    # today, SGR01 (Selangor/Petaling - Puchong)
  python3 prayer_times.py --zone SGR01
  python3 prayer_times.py --date 13-11-2026  # UNTESTED period=date path; verify the response first

Only period=today is proven. If --date fails, fall back to period=today or the e-solat UI.
"""
import argparse
import json
import sys
import urllib.request

BASE = "https://www.e-solat.gov.my/index.php"
DEFAULT_ZONE = "SGR01"  # Selangor / Petaling - Puchong
KEYS = ("imsak", "fajr", "syuruk", "dhuha", "dhuhr", "asr", "maghrib", "isha")


def build_url(zone: str, date: str | None = None) -> str:
    # Built by hand: urlencode() would escape the '/' in esolatApi/takwimsolat.
    if date:
        return f"{BASE}?r=esolatApi/takwimsolat&period=date&zone={zone}&date={date}"
    return f"{BASE}?r=esolatApi/takwimsolat&period=today&zone={zone}"


def fetch(zone: str, date: str | None = None) -> dict:
    url = build_url(zone, date)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=25) as resp:
        raw = resp.read().decode("utf-8", "replace")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        print(f"NON-JSON RESPONSE from {url}\n{raw[:800]}", file=sys.stderr)
        raise
    return data


def main() -> int:
    ap = argparse.ArgumentParser(description="JAKIM e-solat prayer times")
    ap.add_argument("--zone", default=DEFAULT_ZONE, help="e-solat zone code, default SGR01")
    ap.add_argument("--date", default=None, help="DD-MM-YYYY (UNTESTED path)")
    args = ap.parse_args()

    data = fetch(args.zone, args.date)
    rows = data.get("prayerTime") or []
    if not rows:
        print(f"status={data.get('status')!r} zone={data.get('zone')!r} -> no prayerTime rows")
        print(json.dumps(data)[:800])
        return 1

    row = rows[0]
    print(f"zone={data.get('zone')} date={row.get('date')} day={row.get('day')} hijri={row.get('hijri')}")
    print("hijri month check -> Ramadan is month 9; e.g. 1448-06-03 = Jamadilakhir, NOT Ramadan")
    for k in KEYS:
        print(f"  {k:8s} {row.get(k)}")
    print(f"serverTime={data.get('serverTime')} status={data.get('status')!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
