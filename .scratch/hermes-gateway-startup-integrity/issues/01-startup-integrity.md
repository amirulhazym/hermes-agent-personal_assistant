# 01 — Durable startup-integrity incident
Blocked by: owner B1-only approval (received).
Changes: `gateway/lifecycle_ledger.py`, `tests/gateway/test_lifecycle_state_db_check.py`, `tests/gateway/test_b1_startup_integrity.py`.
TDD: simulate forbidden heavy scan, unclean startup pending, clean boot preservation, repeated incident, stale verification, write failure, malformed previous status. Keep real SQLite corruption fixtures.
Acceptance: no DB read/scan on gateway startup; explicit checker preserved; incident-bound atomic `pending` persists; no false verified.
Stop on integrity regression or patch drift. No new worker/cron/restart.
