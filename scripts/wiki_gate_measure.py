#!/usr/bin/env python3
"""wiki_gate_measure.py — Fasa 1 gate measurement (deterministic).

Computes the 7-day cache-hit metric from state.db (sessions table).

Metric definition (only reproducible one from state.db):
    cache_hit_share = cache_read_tokens / (cache_read_tokens + input_tokens)

Why NOT "cache_read / input": cache_read is a SEPARATE counter, not a
subset of input_tokens — measured 31 Jul 2026: 7-day cache_read=306.7M,
input=27.2M. The naive ratio exceeds 100% (1128%), so it is invalid.

Known provenance gap (flagged, not papered over):
- The 76.0% baseline (26 Jul 2026, "all providers") came from an external
  document; billing.py has NO hit-rate query, and state.db's
  cache_write_tokens is always 0. Whether 76.0% used this exact formula
  is UNVERIFIED. A regression verdict on 3 Aug requires the baseline
  re-measured with the SAME metric — so measure BOTH windows:
  (a) trailing 7 days (gate window), (b) 26 Jul 1-day reference if data
  exists, to cross-check the 76.0% claim.

Usage:
  python3 wiki_gate_measure.py [--days 7] [--json]

Exit: 0 always (measurement is a report; verdict is human decision).
"""
import argparse
import json
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--db", default="/home/ubuntu/.hermes/state.db")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    conn = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    now = time.time()
    start = now - args.days * 86400
    start_dt = datetime.fromtimestamp(start, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    rows = conn.execute("""
        SELECT billing_provider,
               COUNT(*) AS sessions,
               SUM(input_tokens)     AS in_tok,
               SUM(cache_read_tokens)  AS cache_r,
               SUM(cache_write_tokens) AS cache_w,
               SUM(output_tokens)    AS out_tok
        FROM sessions
        WHERE started_at >= ? AND billing_provider IS NOT NULL
        GROUP BY billing_provider
    """, (start,)).fetchall()

    total = {"sessions": 0, "in_tok": 0, "cache_r": 0, "cache_w": 0, "out_tok": 0}
    per_provider = []
    for r in rows:
        d = dict(r)
        d["cache_hit_share_pct"] = (100.0 * d["cache_r"] / (d["cache_r"] + d["in_tok"])
                                    if (d["cache_r"] + d["in_tok"]) else None)
        per_provider.append(d)
        for k in ("sessions", "in_tok", "cache_r", "cache_w", "out_tok"):
            total[k] += (d[k] or 0)

    total["cache_hit_share_pct"] = (100.0 * total["cache_r"] / (total["cache_r"] + total["in_tok"])
                                    if (total["cache_r"] + total["in_tok"]) else None)

    report = {
        "metric": "cache_read / (cache_read + input_tokens)",
        "window_days": args.days,
        "window_start_utc": start_dt,
        "generated": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "note": ("Baseline 76.0% (26 Jul) provenance UNVERIFIED vs this metric; "
                 "regression verdict needs same-method baseline."),
        "total": total,
        "per_provider": per_provider,
    }

    if args.json:
        json.dump(report, sys.stdout, indent=2, default=str)
    else:
        t = total
        print(f"=== Wiki Fasa 1 gate measurement ({args.days}-day window) ===")
        print(f"window start (UTC): {start_dt}")
        print(f"sessions: {t['sessions']}")
        print(f"input_tokens: {t['in_tok']:,}   cache_read: {t['cache_r']:,}   "
              f"cache_write: {t['cache_w']:,}   output: {t['out_tok']:,}")
        print(f"cache_hit_share: {t['cache_hit_share_pct']:.2f}%  "
              f"(baseline reference: 76.0% UNVERIFIED definition)")
        print("--- per provider ---")
        for p in per_provider:
            print(f"  {p['billing_provider']:<16} sessions={p['sessions']:>3}  "
                  f"hit_share={p['cache_hit_share_pct']:.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
