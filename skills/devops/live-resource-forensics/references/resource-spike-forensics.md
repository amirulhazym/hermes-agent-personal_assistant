# Resource Spike Forensics Reference

Reusable read-only recipe for sudden RAM, swap, disk, CPU, or I/O growth.

## 1. Capture a comparable baseline

Record one timestamp and retain raw output for:

```text
TZ=<requested-zone> date '+%Y-%m-%d %H:%M:%S %z'
uptime
free -b
swapon --show
df --block-size=1 -P /
df --inodes -P /
vmstat -w 1 5
iostat -xz 1 5
```

Also read `/proc/pressure/{cpu,memory,io}` and record the active service/cgroup counters: `memory.current`, `memory.swap.current`, peaks, `memory.events`, `pids.current`, and configured limits.

Do not compare a rounded `df -h` line to a later byte-precise line as if it were an exact delta. Keep the original units and label rounding.

## 2. Attribute RAM and swap to a workload

Start with `ps` sorted by RSS and CPU, then walk the PPID tree. For every suspected runner, retain:

```text
PID, PPID, state, RSS, VmSwap, elapsed time, exact command line, cwd, cgroup
```

Sum the runner and descendants. A daemon's main PID can look modest while parallel pytest, browser, compiler, or migration children consume the host.

For cgroup-managed services, read the cgroup counters directly and record whether `MemoryMax`/`MemorySwapMax` are finite. `memory.events` with `oom=0` proves only that no OOM kill has occurred; it does not mean headroom is healthy.

## 3. Attribute disk with inode de-duplication

Use a metadata-only Python walk when `du` output is incomplete or hardlinks/reflinks are possible. Count allocated blocks once per `(st_dev, st_ino)` and report apparent size separately:

```python
from pathlib import Path
seen = set()
allocated = 0
apparent = 0
stack = [Path('/tmp')]
while stack:
    p = stack.pop()
    try:
        s = p.lstat()
    except (FileNotFoundError, PermissionError, OSError):
        continue
    if p.is_file() and not p.is_symlink():
        key = (s.st_dev, s.st_ino)
        if key not in seen:
            seen.add(key)
            allocated += s.st_blocks * 512
            apparent += s.st_size
    elif p.is_dir() and not p.is_symlink():
        try:
            stack.extend(p.iterdir())
        except (FileNotFoundError, PermissionError, OSError):
            pass
print({'unique_files': len(seen), 'allocated': allocated, 'apparent': apparent})
```

For each candidate path, record `stat` metadata: device, inode, nlink, allocated blocks, apparent size, ctime, mtime, owner, and mode. Distinct inode + `nlink=1` proves it is not the same hardlink as the source; it still does not prove who created it.

## 4. Distinguish active growth from retained bulk

Classify each large path:

- `ACTIVE-WRITER` — process/cgroup currently writes or owns it;
- `NEW-ARTIFACT` — created/changed in the incident window and correlated with the workload;
- `STATIC-RETAINED` — large but predates the incident window;
- `DUPLICATE/HARDLINK` — path does not represent extra allocated bytes;
- `OPEN-DELETED` — space may remain allocated until the owner closes it;
- `DATA GAP` — root or before-snapshot was not measurable.

Use `lsof`/`fuser` for open ownership and deleted-open files. A one-time empty result is evidence only for that sample; do not turn it into a global absence claim.

For SQLite, inspect only read-only metadata/page count/WAL/journal size unless private contents are explicitly in scope. A growing live DB and a copied DB snapshot are different causal candidates.

## 5. Correlate with the active job

Match:

```text
process start/elapsed → worktree/cwd → worker count → artifact ctime → file-write counters → gateway/cron log time
```

A recorded process/session command can explain who initiated a run, but current `/proc` and filesystem state prove whether it is still active. Keep historical initiation evidence and current runtime evidence separate.

Sample suspected process/file/cgroup counters again after a short interval. A repeated worker tree plus increasing I/O/artifact size is stronger than a single snapshot.

## 6. Report shape

Use this order:

1. **Verdict:** primary resource dimension and causal owner.
2. **Before/after:** exact timestamps and raw units.
3. **Proven owner:** PID/PPID/cgroup/command/worktree.
4. **RAM:** host availability, swap, descendant RSS/swap, OOM events.
5. **Disk:** filesystem authority, allocated candidate paths, inode identity, active/static classification.
6. **Correlation:** logs/session/job evidence, clearly labelled historical versus live.
7. **Gaps:** inaccessible roots, missing before-inventory, failed probes, unproven writer provenance.
8. **Containment:** one recommended action and the exact approval boundary.
9. **Non-mutation proof:** no kill/restart/cleanup/config/database write performed.

If the owner reports RAM/disk, lead with RAM/disk. Mention CPU only as a separate measurement or collateral effect unless the evidence proves CPU is the primary bottleneck.