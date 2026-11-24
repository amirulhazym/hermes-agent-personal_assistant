#!/usr/bin/env python3
"""IF berbuka timing — derived from real diet-log data, not a guessed hour.

Purpose
-------
Slot C in the med chain is CC (Calcium Carbonate + Calcitriol) once the Dexa
midday dose is tapered off (OD phase). CC must be taken WITH food, so its
reminder belongs at fasting-break (berbuka) time — not at "B + 4h".

Owner-locked thresholds (2026-11-23): minimum 16h, optimum 17h, best = average.
  * MIN_FLOOR_H 16.0 — hard floor, never breached, never derived from data
  * TARGET_H    17.0 — optimum berbuka time (the clock the reminder refers to)
  * HEADS_UP_LEAD_H 2.0 — the single alert fires 2h BEFORE berbuka (one message,
    heads-up wording only; it must never claim "ready" before TARGET_H)

History (why these are constants): the old code used `min(fasting_hours)` as the
floor. One sub-floor day (22 Nov, 15.67h) dragged the floor to 15.67h and the
alert claimed "ready berbuka" at 15.8h — below the owner's own 16h minimum.

CLI
---
  python3 if_berbuka.py --json     # stats + today's plan (no side effects)
  python3 if_berbuka.py --check    # reminder text if now >= target, else silent
"""
from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

MYT = timezone(timedelta(hours=8))
DIET_LOG = Path.home() / ".hermes" / "diet-log.json"
TIME_RE = re.compile(r"(\d{1,2}):(\d{2})")

MIN_FLOOR_H = 16.0      # hard floor — earliest legitimate berbuka, never derived from data
TARGET_H = 17.0         # optimum berbuka (owner: minimum 16, optimum 17)
HEADS_UP_LEAD_H = 2.0   # single merged alert fires this many hours before TARGET_H

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], start=1)}


def _load_log() -> dict:
    try:
        return json.loads(DIET_LOG.read_text())
    except Exception:
        return {"logs": {}}


def _parse_hhmm(value: str | None) -> tuple[int, int] | None:
    if not isinstance(value, str):
        return None
    m = TIME_RE.search(value)
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        return None
    return h, mi


def fasting_stats() -> dict:
    """min/median/mean/max of recorded fasting_hours (real, per-day)."""
    logs = _load_log().get("logs", {})
    vals: list[float] = []
    for _d, entry in logs.items():
        fh = entry.get("fasting_hours")
        if isinstance(fh, (int, float)) and 10.0 <= float(fh) <= 30.0:
            vals.append(float(fh))
    if not vals:
        return {"n": 0, "min_h": 17.0, "median_h": 18.6, "mean_h": None,
                "max_h": None, "source": "FALLBACK — no fasting_hours in diet-log"}
    vals.sort()
    n = len(vals)
    median = vals[n // 2] if n % 2 else (vals[n // 2 - 1] + vals[n // 2]) / 2
    return {
        "n": n,
        "min_h": round(vals[0], 2),
        "median_h": round(median, 2),
        "mean_h": round(sum(vals) / n, 2),
        "max_h": round(vals[-1], 2),
        "source": "diet-log.json fasting_hours",
    }


def latest_basis(today: date | None = None) -> dict:
    """Most recent recorded food last_intake before `today`."""
    today = today or datetime.now(MYT).date()
    logs = _load_log().get("logs", {})
    for d in sorted(logs, reverse=True):
        if d >= today.isoformat():
            continue
        raw = logs[d].get("last_intake_time")
        parsed = _parse_hhmm(raw)
        if parsed:
            h, mi = parsed
            return {
                "date": d,
                "time": f"{h:02d}:{mi:02d}",
                "raw": raw,
                "dt": datetime.combine(date.fromisoformat(d), time(h, mi), tzinfo=MYT),
            }
    return {}


def _today_broken_at(today: date) -> str | None:
    """If today's log proves the fast already ended, return the break clock (HH:MM).

    Incident 2026-11-24: the log carried
    `fasting_window: "23 Nov 19:40 -> 24 Nov 13:40"` plus `last_intake_time: "14:15"`,
    but berbuka_plan() kept answering `target 12:40` and the agent told the owner
    "boleh berbuka sekarang" hours after he had eaten. Two independent signals count:
      1. today's fasting_window right-hand side (a real clock, not PENDING)
      2. any food timestamp in today's own entry (not the anchor field of yesterday)
    """
    entry = _load_log().get("logs", {}).get(today.isoformat()) or {}
    for key in ("fasting_window", "eating_window_today"):
        raw = entry.get(key)
        if not isinstance(raw, str) or "->" not in raw:
            continue
        right = raw.split("->")[-1].strip()
        m = re.search(r"(\d{1,2})\s+([A-Za-z]{3})[A-Za-z]*\s+(\d{1,2}):(\d{2})", right)
        if m and MONTHS.get(m.group(2).lower()) == today.month and int(m.group(1)) == today.day:
            return f"{int(m.group(3)):02d}:{m.group(4)}"
        m2 = TIME_RE.search(right)
        if m2 and not m:  # bare HH:MM ("-> 13:40"), today's own window field
            return f"{int(m2.group(1)):02d}:{m2.group(2)}"
    parsed = _parse_hhmm(entry.get("last_intake_time"))
    if parsed:
        return f"{parsed[0]:02d}:{parsed[1]:02d}"
    return None


def berbuka_plan(now: datetime | None = None) -> dict:
    now = now or datetime.now(MYT)
    stats = fasting_stats()
    basis = latest_basis(now.date())
    if not basis:
        return {"ok": False, "reason": "no last_intake_time in diet-log",
                "stats": stats, "target": None, "min_target": None}

    base_dt = basis["dt"]
    # Constants, not data-derived: a single short day must never move the floor.
    min_dt = base_dt + timedelta(hours=MIN_FLOOR_H)
    target_dt = base_dt + timedelta(hours=TARGET_H)
    heads_up_dt = target_dt - timedelta(hours=HEADS_UP_LEAD_H)
    fast_now = (now - base_dt).total_seconds() / 3600.0
    yesterday = (now.date() - timedelta(days=1)).isoformat()
    broken_at = _today_broken_at(now.date())
    return {
        "ok": True,
        "already_broken": broken_at is not None,
        "broken_at": broken_at,
        "basis_stale": basis["date"] != yesterday,
        "basis_date": basis["date"],
        "basis_time": basis["time"],
        "basis_raw": basis["raw"],
        "fast_now_h": round(fast_now, 2),
        "stats": stats,
        "min_target": min_dt.strftime("%H:%M"),
        "median_target": (base_dt + timedelta(hours=stats["median_h"])).strftime("%H:%M"),
        "target": target_dt.strftime("%H:%M"),
        "heads_up": heads_up_dt.strftime("%H:%M"),
        "lead_h": HEADS_UP_LEAD_H,
        "target_dt": target_dt,
        "heads_up_dt": heads_up_dt,
        "min_dt": min_dt,
    }


def berbuka_target_hhmm() -> str | None:
    """Slot-C fire time: 2h before the 17h optimum, so ONE alert carries both.

    Owner decision 2026-11-23: single merged alert, 2h early. It says when berbuka
    is (17h optimum) + CC-after-food + log Window 1 — it must NOT claim "ready"
    before target. The 16h hard floor is a breach line, not a trigger.
    """
    try:
        plan = berbuka_plan()
        if not plan.get("ok") or plan.get("basis_stale"):
            # No trustworthy anchor for today's fast → let the caller fall back
            # instead of nagging at a target derived from an old meal.
            return None
        return plan.get("heads_up")
    except Exception:
        return None


def reminder_text(plan: dict, now: datetime | None = None) -> str | None:
    if not plan.get("ok"):
        return None
    now = now or datetime.now(MYT)
    if now < plan["heads_up_dt"]:
        return None
    st = plan["stats"]
    if now < plan["target_dt"]:
        # Heads-up only — berbuka has not arrived, so never say "ready".
        return (
            f"⏳ Berbuka IF pukul {plan['target']} (17j) — lagi "
            f"{(plan['target_dt'] - now).total_seconds() / 3600.0:.1f}j.\n"
            f"Sekarang baru {plan['fast_now_h']:.1f}j puasa (min 16j, optimum 17j).\n"
            f"Lepas berbuka: Calcium Carbonate 500mg + Calcitriol 1 tab."
        )
    return (
        f"‼️ Waktu Berbuka IF & CC ‼️\n"
        f"Dah {plan['fast_now_h']:.1f}j puasa sejak last makan {plan['basis_date']} "
        f"{plan['basis_time']} — ready berbuka.\n"
        f"Lepas makan: Calcium Carbonate 500mg + Calcitriol 1 tab. "
        f"Stat: median {st['median_h']:.1f}j (n={st['n']})."
    )


def main(argv: list[str]) -> int:
    if "--json" in argv:
        plan = berbuka_plan()
        out = {k: v for k, v in plan.items() if k not in ("target_dt", "min_dt")}
        print(json.dumps(out, indent=2, default=str))
        return 0
    if "--check" in argv:
        text = reminder_text(berbuka_plan())
        if text:
            print(text)
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
