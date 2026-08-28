#!/usr/bin/env python3
"""Disk inventory for a temp/scratch root: top items, totals by mtime date,
totals by name-prefix group. Answers "disk penuh, punca mana?" directly.

Usage: python3 tmp_inventory.py [root]     (default root: /tmp)

Verified 2026-08-20: on a Hermes VPS this isolated the cause — 19 Aug = 8.2GB
of 10.5GB /tmp (3x 2.0GB state.db test copies) vs a flat size list that buries
the spike. Pair with: du -x -B1 -d1 /home/ubuntu | sort -rn
"""
import os
import stat
import sys
from collections import defaultdict
from datetime import datetime

root = sys.argv[1] if len(sys.argv) > 1 else "/tmp"
# Permission-denied system dirs (systemd-private-*, snap-private-tmp) pruned by prefix.
PRUNE_PREFIX = ("systemd-private-",)
PRUNE_EXACT = ("snap-private-tmp",)

items = []          # (size, path, mtime)
total = 0
for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [
        d for d in dirnames
        if not d.startswith(PRUNE_PREFIX) and d not in PRUNE_EXACT
    ]
    for f in filenames:
        p = os.path.join(dirpath, f)
        try:
            st = os.lstat(p)
            if stat.S_ISREG(st.st_mode):
                items.append((st.st_size, p, st.st_mtime))
                total += st.st_size
        except OSError:
            pass

items.sort(reverse=True)


def fmt(n):
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}TB"


print(f"TOTAL_REGULAR_FILES={len(items)} TOTAL_BYTES={fmt(total)}")
print("\n== TOP 40 LARGEST ==")
for sz, p, mt in items[:40]:
    print(f"{fmt(sz):>9}  {datetime.fromtimestamp(mt).strftime('%Y-%m-%d')}  {p}")

bydate = defaultdict(int)
byn = defaultdict(int)
groups = {"hermes-*": 0, "gate2-*": 0, "pytest*": 0, "other": 0}
for sz, p, mt in items:
    d = datetime.fromtimestamp(mt).strftime("%Y-%m-%d")
    bydate[d] += sz
    byn[d] += 1
    b = os.path.basename(p)
    if b.startswith("hermes-") or "/hermes-" in p:
        groups["hermes-*"] += sz
    elif b.startswith("gate2-") or "/gate2-" in p:
        groups["gate2-*"] += sz
    elif "pytest" in p:
        groups["pytest*"] += sz
    else:
        groups["other"] += sz

print("\n== TOTAL BY MODIFIED DATE ==")
for d in sorted(bydate):
    print(f"{d}  {fmt(bydate[d]):>9}  files={byn[d]}")

print("\n== TOTAL BY NAME GROUP ==")
for g, v in groups.items():
    print(f"{g:>9}  {fmt(v):>9}")
