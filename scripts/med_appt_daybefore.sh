#!/bin/bash
# Wrapper for Appointment Reminder (day-before) cron job
# no_agent mode doesn't support args in script field, so this wrapper
# calls the master script with the required --check-tomorrow flag.
exec python3 /home/ubuntu/.hermes/scripts/med_appointments.py --check-tomorrow
