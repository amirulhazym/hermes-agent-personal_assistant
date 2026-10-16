# Spec: Resilient MRI HKL Reminder Pipeline & Appointment Tracking

## Problem Statement
The user has a critical MRI scan appointment at Hospital Kuala Lumpur (HKL) on Monday, 19 October 2026. The user requires early morning travel (estimated between 08:00 AM and 10:00 AM) departing from their home via IOI Puchong Jaya LRT to HKL.
On 12 October 2026, cron reminders were created across 16–18 October (morning 09:00 and evening 20:00) using unpinned LLM agent jobs (`no_agent: false`). When the active global model shifted from `openai-codex/gpt-6-luna` to `antigravity/gemini-3.8-flash`, Hermes's spend-safety guard (`cron_model_drift_guard`) halted the first reminder (`7b0b347c2bec` at 09:00 on 16 Oct) to prevent unintended spend, leaving the reminder skipped and the one-shot job consumed.
Additionally, the upcoming appointment was not registered in `~/.hermes/appointments.json`, creating a tracking blindspot for the system's medical appointment tools.

## Solution
1. **Immediate Catch-up Reminder (Q1: A)**: Deliver an immediate catch-up reminder message to WhatsApp and Telegram alerting the user about the MRI HKL appointment on 19 October (estimated 8:00 AM - 10:00 AM) and accounting for the LRT commute.
2. **Deterministic no_agent Conversion (Q2: C)**: Convert all remaining scheduled MRI cron jobs (`68c062a89b0f`, `df78d57ca3d2`, `700fe515b860`, `dfbecf0057ca`, `f12456e25abb`) to deterministic `no_agent: true` jobs powered by a dedicated script. This completely decouples delivery from model providers, eliminating LLM drift errors, zeroing token burn, and guaranteeing delivery at the scheduled times.
3. **Medical Appointment Registration (Q3: A)**: Insert the 19 October 2026 HKL MRI appointment into `~/.hermes/appointments.json` with travel and timing metadata (8:00 AM - 10:00 AM, LRT IOI Puchong Jaya to HKL), synchronizing it with the `med_appointments.py` check suite.

## User Stories
1. As an AI system user recovering from TB Meningitis, I want an immediate catch-up reminder for the missed 9:00 AM notification today, so that I am fully aware of my upcoming MRI appointment.
2. As a user commuting via public transport, I want the reminder to explicitly highlight the early morning arrival window (8:00 AM – 10:00 AM) and the LRT IOI Puchong Jaya travel context, so that I can plan transit without being caught off-guard.
3. As a system operator, I want upcoming reminders to run via `no_agent: true` with a deterministic script, so that future model changes or API token shifts never cause the jobs to be skipped.
4. As a medical tracking user, I want the MRI appointment stored in `appointments.json`, so that `med_appointments.py` (and its daily check) provides automated day-before secondary redundancy.
5. As a Git repository curator, I want the new reminder script, appointment updates, tests, and documentation checked into the SSOT repo (`hermes-agent-personal_assistant-work`), so that the system remains fully reproducible.

## Implementation Decisions
- **Script Location**: Place the deterministic reminder generator at `~/.hermes/scripts/mri_reminder.py` and synchronize it to the SSOT repo under `scripts/mri_reminder.py`.
- **Script Execution**: The script accepts a stage argument (`--stage {day3_evening|day2_morning|day2_evening|day1_morning|day1_evening|catchup}`) and outputs exact, pre-templated text including appointment date, estimated window (8:00 AM – 10:00 AM), transit notes, and hospital details.
- **Cron Job Configuration**: Update jobs `68c062a89b0f`, `df78d57ca3d2`, `700fe515b860`, `dfbecf0057ca`, `f12456e25abb` to:
  - `no_agent: true`
  - `script: "mri_reminder.sh <stage>"` or dedicated wrapper scripts per tick under `~/.hermes/scripts/`
  - `provider: null`, `model: null`, `provider_snapshot: null`, `model_snapshot: null`
- **Immediate Catch-up**: Dispatch the catch-up reminder directly to the target channels (Telegram and WhatsApp).
- **Appointments DB**: Update `~/.hermes/appointments.json` with:
  - `date`: "2026-10-19"
  - `time`: "08:00 - 10:00"
  - `location`: "Hospital Kuala Lumpur (HKL)"
  - `purpose`: "MRI Scan (Brain/Neuro)"
  - `notes`: "Early morning slot (8am-10am). Transit via LRT IOI Puchong Jaya."

## Testing Decisions
- Test script stdout locally across all stages to ensure exact formatting and exit code 0.
- Verify `appointments.json` validates under `python3 ~/.hermes/scripts/med_appointments.py --upcoming`.
- Verify `cron_model_drift_axes` returns empty `[]` for all updated jobs under current and arbitrary provider/model configurations.

## Out of Scope
- Modifying core framework cron scheduler logic (`cron/scheduler.py`).
- Adding external calendar integration.
