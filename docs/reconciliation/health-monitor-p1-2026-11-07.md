# Health Monitor P1 + Playwright driver reclamation — 2026-11-07

Owner-approved scope: **P0 + P1 only**. P2 (source leak fix) and P3 (baseline
optimization / dashboard / RDC / VPS upgrade) were explicitly NOT approved and
were not touched.

## P0 — Reclaimed 17 leaked Playwright driver processes

Evidence before execution (`/tmp/p0/preflight.txt`):

- 17 `playwright/driver/package/cli.js run-driver` processes, all `PPID=1210`
  (Hermes gateway), all state `S` (sleeping, NOT zombie `Z`), all with zero
  child processes, no Chromium/Chrome running, no browser activity in
  gateway/agent logs for 90 minutes.
- Gateway still held both pipe ends for each driver (`fd0`/`fd1` pipes),
  confirming leaked Playwright instance objects inside the gateway — the
  drivers were never stopped, not merely orphaned.
- Aggregate: 1,455 MB swap + ~209 MB RSS.
- Host: swap 1,986/1,987 MB used (≈0 free), MemAvailable 314 MB.

Action: targeted `SIGTERM` to 17 PIDs with per-PID guards (must be PPID 1210,
zero children, age > 12h, cmdline match). No gateway restart, no other process
touched, no SIGKILL needed — all 17 exited within 6 seconds.

After:

| Metric | Before | After |
|---|---|---|
| MemAvailable | 314 MB | 495 MB |
| Mem used | 1,652 MB | 1,471 MB |
| Swap used | 1,986 MB | 527 MB |
| Playwright drivers | 17 | 0 |
| Gateway PID | 1210 | 1210 (unchanged, uptime preserved) |
| OOM events | 0 | 0 |

PIDs terminated: 122452 122453 122518 122556 122565 124161 124175 124218
724323 724358 1090842 1090881 1090910 1091034 1769638 1831309 3892905.

## P1 — Health monitor: swap-aware, severity-aware, change-driven

File: `/home/ubuntu/.hermes/scripts/health_check.py`
Backup: `~/.hermes/scripts/health_check.py.bak.p1-20261107-1250`
(sha256 `772f38df9d2157ecd5b966ddace26214c27ab5cef35de6b4f71d9750a160dbe8`)

New sha256: `79903f2c18ddaa1f5425e5c5ab28f5eec8f8c9b15cde0af74e20608984904648`

### Behaviour change

Old: RAM-only check (`MemAvailable < 500`), re-notify every 3rd failure or
every 30 min → identical alert every 30–45 min with no new information, and
no visibility into swap exhaustion.

New:

- **Memory check covers RAM *and* swap.** RAM threshold unchanged at 500 MB
  (owner decision). Severity: `warning` when avail < 500 MB OR swap used
  ≥ 80%; `critical` when avail < 250 MB OR swap free < 50 MB.
- **Disk** split into warning (>85%) / critical (>92%).
- Alert payload includes both metrics plus a top-3 RSS consumer hint.
- **Notification policy**: immediate on new fault, immediate on fault-set or
  severity change (escalation), otherwise at most once every 6 hours while it
  persists, one recovery message when healthy.
- `--dry-run` (evaluate, no send, no state write) and `--self-test`
  (9 policy scenarios) added.

### Verification performed

- `python3 -m py_compile` → OK.
- `--self-test` → 9/9 PASS (silent while healthy, alert on new/changed/
  escalated, 6h reminder, no spam on detail-only change, single recovery).
- `--dry-run` on live host → `action=alert ... Memory [warning]: RAM 475MB
  avail; swap 526/1988MB (26%)`.
- Live run → notification delivered, state written with `fingerprint` and
  `max_severity`; immediate second run → `action=none` (dedupe proven).
- Cron line unchanged: `*/15 * * * * /usr/bin/python3 .../health_check.py`.

### Known limitation

After P0, MemAvailable is 495 MB — still under the retained 500 MB threshold,
so the monitor correctly reports `warning`. Closing that gap requires P3
(dashboard −186 MB, RDC −209 MB, or VPS upgrade) which is not approved.

## Rollback

```bash
cp ~/.hermes/scripts/health_check.py.bak.p1-20261107-1250 \
   ~/.hermes/scripts/health_check.py
```

No restart required (invoked fresh by system cron every 15 minutes). P0 is not
reversible but required no state change beyond process termination.
