# Cron Boundary and Transport Separation — 2026-07-29

## Case
The monitored job ran on `*/15 5-22 * * *`. Its previous output was written at `22:45:37 MYT`. The independent health check ran at `04:30:01` and `05:00:01`; the first new job output was written at `05:00:41`.

Observed alert ages were approximately 344 and 374 minutes. These were pre-run/boundary observations, not missed execution: the monitor evaluated the stale previous file before the expected 05:00 run had completed.

## Required algorithm

- Compute both previous and next scheduled occurrences with `croniter`.
- Before `next_run`, do not classify the previous output as a missed current run merely because the next run is near.
- After `next_run`, allow a bounded post-run grace period (normally 2–5 minutes).
- After grace, require output corresponding to the expected occurrence before alerting.
- Test just-before-run, exact-minute, just-after-run, between-run, and off-window cases.

## Boundary distinction

A cron output file proves script execution. It does not prove channel delivery. Track separately:

1. scheduler invocation;
2. script output/exit status;
3. adapter/transport HTTP result;
4. destination-side receipt.

A WhatsApp bridge can be HTTP-alive while transport is disconnected. Health alerts should identify the failing boundary explicitly rather than collapsing cron execution and delivery into one status.
