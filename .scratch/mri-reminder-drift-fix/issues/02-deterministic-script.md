# 02 — Deterministic MRI Reminder Script & Wrappers

**What to build:** Create a deterministic Python script and shell wrappers under `~/.hermes/scripts/` (and checked into SSOT `scripts/`) to emit concise, high-visibility reminder messages across all reminder stages without requiring any LLM inference.

**Blocked by:** 01 — Medical Appointment Registration & Validation

**Status:** ready-for-agent

- [ ] Create `scripts/mri_reminder.py` supporting `--stage` options (`catchup`, `day3_evening`, `day2_morning`, `day2_evening`, `day1_morning`, `day1_evening`).
- [ ] Create shell wrappers under `~/.hermes/scripts/` for each cron slot (since Hermes `no_agent` scripts resolve to executable files without command-line arguments in the script field).
- [ ] Verify each wrapper outputs expected text and exits 0.
