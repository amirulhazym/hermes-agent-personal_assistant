#!/usr/bin/env python3
"""Hermes Memory Usage Watchdog — no_agent cron script.

Monitors MEMORY.md and USER.md usage against configured limits.
Silent when usage is healthy. Fires alert when threshold crossed.
Uses sentinel file to prevent re-alerting on same alert cycle.

Exit codes: 0 (all good / already alerted), 1 (error reading files)

Design:
- > 95%: 🔴 CRITICAL — fire alert
- 85-95%: 🟡 WARNING — fire alert
- < 75%: healthy — clear sentinel so next alert cycle can fire
- Alert fires 1x per cycle. Sentinel prevents repeat until memory drops below 75%.
"""

import os
import sys
from datetime import datetime
from pathlib import Path

MEMORY_DIR = Path.home() / '.hermes' / 'memories'
SENTINEL = MEMORY_DIR / '.memory_watch_alerted'

# Limits matching ~/.hermes/config.yaml
LIMITS = {
    'MEMORY.md': 9000,
    'USER.md': 1375,
}

# Thresholds
THRESHOLD_CRIT = 0.95  # 95% — 🔴 critical
THRESHOLD_WARN = 0.85  # 85% — 🟡 warning
SILENT_RESET   = 0.75  # Below 75% — clear sentinel, allow re-alert


def check_memory():
    """Check all memory stores and return list of alert strings.

    Returns empty list if all stores are healthy (silent exit).
    """
    alerts = []
    errors = []

    for fname, limit in LIMITS.items():
        fpath = MEMORY_DIR / fname

        if not fpath.exists():
            errors.append(f"⚠️ {fname}: file not found at {fpath}")
            continue
        if not fpath.is_file():
            errors.append(f"⚠️ {fname}: not a regular file")
            continue

        try:
            content = fpath.read_text(encoding='utf-8')
        except Exception as e:
            errors.append(f"⚠️ {fname}: cannot read — {e}")
            continue

        chars = len(content)
        pct = chars / limit * 100

        if pct >= THRESHOLD_CRIT * 100:
            alerts.append(
                f"🔴 {fname}: {chars:,}/{limit:,} chars ({pct:.1f}%) — "
                f"CRITICAL: {limit - chars} chars remaining. "
                f"Memory writes will FAIL at limit."
            )
        elif pct >= THRESHOLD_WARN * 100:
            alerts.append(
                f"🟡 {fname}: {chars:,}/{limit:,} chars ({pct:.1f}%) — "
                f"WARNING: {limit - chars} chars remaining. "
                f"Approaching full capacity."
            )
        elif pct <= SILENT_RESET * 100:
            # Healthy — sentinel will be cleared below
            pass
        else:
            # Between 75-85% — neutral, no alert needed
            pass

    return alerts, errors


def main():
    alerts, errors = check_memory()

    # Handle errors — always surface file read problems
    for e in errors:
        print(e, file=sys.stderr)

    if not alerts:
        # Everything healthy: clear sentinel so next alert cycle can fire
        if SENTINEL.exists():
            try:
                SENTINEL.unlink()
            except OSError:
                pass  # best effort
        return  # silent exit (no output = no delivery in no_agent mode)

    # Check sentinel — prevent re-firing on same cycle
    if SENTINEL.exists():
        return  # already alerted this cycle, stay silent

    # NEW alert cycle — fire and create sentinel
    now = datetime.now().strftime('%Y-%m-%d %H:%M MYT')

    print(f"⟳ Hermes Memory Usage Alert — {now}")
    print()

    for a in alerts:
        print(a)

    if errors:
        print()
        for e in errors:
            print(f"  {e}")

    print()
    print("Action: Consolidate or prune memory entries to free space.")
    print("Run `hermes doctor` to check current state.")

    # Create sentinel to prevent re-alert
    try:
        SENTINEL.write_text(
            f"Alerted at {now}\n"
            f"Cause: {', '.join(a.split(':')[0] for a in alerts)}\n"
        )
    except OSError:
        pass  # best effort — no sentinel = re-alerts next tick, acceptable


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"ERROR: memory_watch.py crashed — {e}", file=sys.stderr)
        sys.exit(1)
