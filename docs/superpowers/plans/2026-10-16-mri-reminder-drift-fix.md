# Implementation Plan: Resilient MRI HKL Reminder Pipeline & Appointment Tracking

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Provide immediate catch-up reminder for the missed 9:00 AM MRI reminder, convert all 5 remaining MRI reminder cron jobs to deterministic `no_agent: true` execution to permanently prevent model drift failures, register the MRI appointment with transit metadata in `appointments.json`, and commit/publish all artifacts to SSOT.

**Architecture:** Use a dedicated deterministic Python script (`mri_reminder.py`) and single-line shell wrappers (`.sh`) under `~/.hermes/scripts/` referenced by cron jobs configured with `no_agent: true`. Update `~/.hermes/appointments.json` to include the MRI appointment for redundancy with `med_appointments.py`. Capture all scripts and tests in the SSOT repository (`/home/ubuntu/hermes-agent-personal_assistant-work`).

**Tech Stack:** Python 3.11, Bash, JSON, Pytest, Git, Hermes cron scheduler.

## Global Constraints
- Sole development SSOT is `/home/ubuntu/hermes-agent-personal_assistant-work`.
- All `no_agent` scripts in Hermes must be valid executable file paths under `~/.hermes/scripts/` without command arguments.
- Redact secrets; no unverified status claims.

---

### Task 1: Register MRI HKL Appointment in `appointments.json`

**Files:**
- Modify: `/home/ubuntu/.hermes/appointments.json`
- Test: `python3 /home/ubuntu/.hermes/scripts/med_appointments.py --upcoming`

- [ ] **Step 1: Backup `~/.hermes/appointments.json`**
  - Run: `cp /home/ubuntu/.hermes/appointments.json /home/ubuntu/.hermes/appointments.json.bak`

- [ ] **Step 2: Add appointment record**
  - Insert object with `id`: 3, `date`: "2026-10-19", `time`: "08:00 - 10:00", `location`: "Hospital Kuala Lumpur (HKL)", `purpose`: "MRI Scan (Brain/Neuro)", `notes`: "Awal pagi (8am - 10am). Gerak dari rumah ke LRT IOI Puchong Jaya ke HKL.", `status`: "upcoming", `reminder_sent`: False.

- [ ] **Step 3: Verify via CLI**
  - Run: `python3 /home/ubuntu/.hermes/scripts/med_appointments.py --upcoming`
  - Expected: Displays MRI HKL appointment with `days_until=3`.

---

### Task 2: Implement Deterministic Script & Shell Wrappers

**Files:**
- Create: `/home/ubuntu/hermes-agent-personal_assistant-work/scripts/mri_reminder.py`
- Create: `/home/ubuntu/.hermes/scripts/mri_reminder.py`
- Create shell wrappers:
  - `/home/ubuntu/.hermes/scripts/mri_day3_evening.sh`
  - `/home/ubuntu/.hermes/scripts/mri_day2_morning.sh`
  - `/home/ubuntu/.hermes/scripts/mri_day2_evening.sh`
  - `/home/ubuntu/.hermes/scripts/mri_day1_morning.sh`
  - `/home/ubuntu/.hermes/scripts/mri_day1_evening.sh`
- Test: `tests/scripts/test_mri_reminder.py`

- [ ] **Step 1: Write unit tests in SSOT repository**
  - Create `tests/scripts/test_mri_reminder.py` asserting correct message output and exit code for each stage.

- [ ] **Step 2: Run test to confirm failure (Red)**
  - Run: `pytest tests/scripts/test_mri_reminder.py`
  - Expected: ModuleNotFoundError / FileNotFoundError.

- [ ] **Step 3: Implement `mri_reminder.py` in SSOT repo and deploy to `~/.hermes/scripts/`**
  - Deterministically formats appointment date, arrival slot (8:00 AM - 10:00 AM), transit route (LRT IOI Puchong Jaya -> HKL), and instructions.

- [ ] **Step 4: Create executable shell wrappers and verify tests pass (Green)**
  - Run: `pytest tests/scripts/test_mri_reminder.py`
  - Expected: All tests PASS.

---

### Task 3: Convert Cron Jobs to `no_agent: true`

**Files:**
- Modify: `/home/ubuntu/.hermes/cron/jobs.json`

- [ ] **Step 1: Backup `~/.hermes/cron/jobs.json`**
  - Run: `cp /home/ubuntu/.hermes/cron/jobs.json /home/ubuntu/.hermes/cron/jobs.json.bak`

- [ ] **Step 2: Update remaining 5 MRI cron jobs**
  - `68c062a89b0f`: script="mri_day3_evening.sh", no_agent=True, provider=None, model=None, provider_snapshot=None, model_snapshot=None
  - `df78d57ca3d2`: script="mri_day2_morning.sh", no_agent=True, provider=None, model=None, provider_snapshot=None, model_snapshot=None
  - `700fe515b860`: script="mri_day2_evening.sh", no_agent=True, provider=None, model=None, provider_snapshot=None, model_snapshot=None
  - `dfbecf0057ca`: script="mri_day1_morning.sh", no_agent=True, provider=None, model=None, provider_snapshot=None, model_snapshot=None
  - `f12456e25abb`: script="mri_day1_evening.sh", no_agent=True, provider=None, model=None, provider_snapshot=None, model_snapshot=None

- [ ] **Step 3: Verify drift guard immunity**
  - Run script checking `cron_model_drift_axes` for all 5 jobs.
  - Expected: Zero drifted axes.

---

### Task 4: Immediate Catch-up Delivery

**Files:**
- Execute: `python3 /home/ubuntu/.hermes/scripts/mri_reminder.py --stage catchup`

- [ ] **Step 1: Deliver catch-up reminder message to Telegram and WhatsApp**
  - Deliver the exact formatted message alerting about the missed 9:00 AM slot and detailing the appointment.

---

### Task 5: SSOT Git Publication via PR Flow

**Files:**
- Tracked changes in `/home/ubuntu/hermes-agent-personal_assistant-work`:
  - `scripts/mri_reminder.py`
  - `tests/scripts/test_mri_reminder.py`
  - `.scratch/mri-reminder-drift-fix/spec.md`
  - `.scratch/mri-reminder-drift-fix/issues/*`
  - `docs/superpowers/plans/2026-10-16-mri-reminder-drift-fix.md`

- [ ] **Step 1: Run security scan & manifest validate**
  - Run: `bash scripts/guard/secret-scan.sh --tree`
  - Run: `python3 scripts/guard/manifest_recompute.py docs/reconciliation/v3-source-coverage-manifest.json HEAD`
  - Run: `bash scripts/guard/manifest-validate.sh docs/reconciliation/v3-source-coverage-manifest.json $(git rev-parse HEAD)`

- [ ] **Step 2: Create feature branch, push, open PR, squash-merge, and clean up**
  - Branch: `feat/mri-reminder-no-agent-drift-fix`
  - PR Title: `feat(cron): deterministic no-agent MRI reminders and appointment registration`
  - Merge and sync local `main` to `origin/main`.
