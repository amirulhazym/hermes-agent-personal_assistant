---
name: live-resource-forensics
description: Use when live RAM/disk usage spikes; attribute the owner.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [resource-forensics, performance, disk-growth, memory-pressure, live-audit]
    related_skills: [debugging-and-error-recovery, systematic-debugging, hermes-live-audit]
---

# Live Resource Forensics

## Purpose

Investigate sudden hardware/resource consumption on a live host without jumping to cleanup, restart, or a convenient but unproven explanation. The output is a causal evidence ledger: what changed, which component owns the change, what is active versus retained, what remains unproven, and what action—if any—needs owner approval.

This skill is especially important when the owner reports *RAM or disk*. Do not let a visible CPU/load spike take over the diagnosis by default; CPU may be collateral work from the same test, migration, indexing, or reconciliation job.

## When to Use

- The owner reports a sudden RAM, swap, disk, CPU, or I/O increase.
- A long-running daemon, gateway, test suite, migration, browser pool, or reconciliation job may be consuming host resources.
- Disk usage changes quickly and the cause could be active writes, temporary artifacts, retained snapshots, or deleted-open files.
- A dashboard symptom needs attribution to an exact process/cgroup before any containment or cleanup.

## Operating rules

1. **Read-only first.** No kill, restart, cleanup, config write, database mutation, cache purge, or test cancellation during diagnosis unless the owner explicitly asks for that action.
2. **Follow the reported dimension first.** Capture RAM available, swap, filesystem free space, and active writers before interpreting CPU.
3. **Baseline before narrative.** Record a timestamped snapshot, then compare against the earliest trustworthy snapshot. If the earlier snapshot omitted `/tmp`, protected roots, or another relevant filesystem, label the exact delta as a data gap.
4. **Process ownership before attribution.** Find the exact PID, parent/child lineage, command line, worktree/home, worker count, and cgroup. A test runner inherited by a gateway is a gateway-owned workload for resource accounting.
5. **Separate active growth from static bulk.** A large retained database, backup, virtual environment, or candidate tree is not proof of the sudden cause. A current writer or newly-created artifact is stronger evidence.
6. **Allocated bytes, not path arithmetic.** For disk, de-duplicate hardlinks by `(st_dev, st_ino)` and report allocated blocks separately from apparent size. Record inode/nlink, ctime, mtime, owner, and mode.
7. **No exact claim from one point.** Sample suspected files/processes more than once and report deltas with timestamps. A single large file proves occupancy, not growth.
8. **No cleanup from size alone.** Before recommending deletion, check active/open ownership, source/evidence uniqueness, retention role, and recovery status. Destructive action requires explicit approval and post-action verification.
9. **Show the evidence behind the verdict.** Use labels such as `PROVEN`, `PARTIAL`, `CORRELATION ONLY`, `UNVERIFIED`, `DATA GAP`, and `NO CHANGE PERFORMED`.

## Investigation phases

### Phase 0 — Freeze scope and snapshot

Capture, with one timestamp:

- `date` in the requested timezone;
- uptime/load and CPU sample;
- RAM total/available/free, swap total/used;
- `df --block-size=1 -P` for the affected filesystem and inode usage;
- PSI for CPU, memory, and I/O;
- short `vmstat`/`iostat` sample;
- top processes by RSS and CPU;
- service/cgroup state and failed units.

Do not start with a fix. The first report should state whether the pressure is RAM, swap, disk, I/O, CPU, or a combination.

### Phase 1 — Attribute RAM and swap

Inspect the process tree, not only the main daemon PID. For a long-running service:

- walk PPID relationships and list descendants;
- sum RSS and swap for the runner plus descendants;
- record exact commands and worker count;
- read cgroup `memory.current`, `memory.swap.current`, peaks, events, and limits;
- check whether the process is under systemd, a container, or a user service;
- distinguish resident pressure from swapped-out pages.

A group of parallel test workers can explain both RAM loss and CPU load. State the workers and their individual RSS, not just “tests are running.”

### Phase 2 — Attribute disk growth

Use the filesystem as authority:

1. Capture `df --block-size=1 -P /` twice with timestamps.
2. Inventory `/tmp`, runtime roots, home roots, backups, snapshots, caches, and repositories using allocated bytes.
3. De-duplicate hardlinks; compare device/inode/nlink for suspected copies.
4. Record ctime and mtime, but do not treat mtime as last-use proof.
5. Check `lsof`/`fuser` for active owners and deleted-but-open files.
6. For SQLite, use read-only metadata/page/journal/WAL probes; do not read private message contents just to explain size.
7. Separate newly-created candidate/test artifacts from old retained DBs, archives, environments, and Git objects.

If a selected group of new artifacts explains the observed free-space delta, state that it *matches* the change while preserving any missing-before-inventory limitation.

### Phase 3 — Correlate with the workload

Correlate timestamps across:

- process start/elapsed time;
- runner command and worktree;
- gateway/daemon logs;
- cron/scheduler activity;
- session/database WAL growth;
- artifact ctime and file-write deltas;
- process I/O counters.

Historical session/process records can identify who initiated a still-live workload, but they are secondary to current `/proc` and filesystem evidence. Report both scopes separately.

### Phase 4 — Verify the causal hypothesis

Form one hypothesis at a time, for example:

> “The RAM/disk spike is caused by a four-worker test runner launched under the gateway because the live PPID tree, worker RSS, worktree, and new artifact sizes align with the before/after delta.”

Test it minimally and read-only:

- sample process RSS/swap/I/O again after a short interval;
- verify the same parent and workers remain active or observe their replacement;
- re-stat the suspected files/directories;
- confirm the service is still healthy and no OOM event occurred.

If the hypothesis is refuted, downgrade it and form a new one. Do not add a cleanup or restart on an unverified theory.

### Phase 5 — Report and containment gate

Lead with the direct verdict. Include:

1. before/after metrics;
2. exact owner PID/command/cgroup;
3. exact largest paths and allocated sizes;
4. active versus retained classification;
5. risk at current headroom;
6. failures/data gaps;
7. what was not changed;
8. one recommended containment action, if needed, with its approval boundary.

If the owner only asked for diagnosis, do not silently stop a workload. Say whether the workload remains active and what explicit instruction would be required to stop it.

## Common failure modes

- **CPU anchoring:** ranking CPU first because load is visually dramatic when the owner reported RAM/disk. Fix: lead with the reported dimension and show all dimensions together.
- **Path double-counting:** summing hardlinked or reflinked copies without inode checks. Fix: allocated-byte scan with hardlink de-duplication.
- **Static-size-as-growth:** calling a large old DB the sudden cause. Fix: ctime/mtime + repeated stat + process ownership.
- **Missing-root overconfidence:** claiming an exact disk delta when the earlier snapshot did not include `/tmp` or protected roots. Fix: label the unmeasured boundary.
- **Main-PID tunnel vision:** attributing only the daemon RSS while its child tests/browsers/workers consume the host. Fix: sum the descendant tree and cgroup.
- **Fix-before-cause:** killing a process or deleting artifacts before preserving ownership and retention evidence. Fix: complete the read-only ledger first.
- **Wrapper retry loop:** retrying a service-guarded command unchanged. Fix: switch to direct `/proc`, `stat`, cgroup, or a separate operator context and record the failed probe.

## Supporting reference

Use `references/resource-spike-forensics.md` for the compact command/evidence recipe, deduplicated disk scan pattern, and owner-facing report fields.