# 01 — Medical Appointment Registration & Validation

**What to build:** Register the 19 October 2026 MRI appointment at Hospital Kuala Lumpur into `appointments.json` with early morning time window (08:00 - 10:00) and LRT commute notes, verified via `med_appointments.py`.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Add entry with date "2026-10-19", time "08:00 - 10:00", location "Hospital Kuala Lumpur (HKL)", purpose "MRI Scan (Brain/Neuro)" and transit notes.
- [ ] Run `python3 ~/.hermes/scripts/med_appointments.py --upcoming` and confirm the new appointment is displayed with correct days_until.
