# 03 — Cron Jobs Conversion to no_agent Mode

**What to build:** Convert all remaining MRI reminder cron jobs (`68c062a89b0f`, `df78d57ca3d2`, `700fe515b860`, `dfbecf0057ca`, `f12456e25abb`) to `no_agent: true` with their corresponding scripts and cleared model snapshots.

**Blocked by:** 02 — Deterministic MRI Reminder Script & Wrappers

**Status:** ready-for-agent

- [ ] Update each job in `~/.hermes/cron/jobs.json` to have `no_agent: true`, point to its wrapper script, and set model/provider snapshots to null.
- [ ] Run drift check via `cron_model_drift_axes` to verify zero drift errors engage for these jobs.
- [ ] Verify `hermes cron list` shows all 5 jobs in scheduled state with `no_agent: true`.
