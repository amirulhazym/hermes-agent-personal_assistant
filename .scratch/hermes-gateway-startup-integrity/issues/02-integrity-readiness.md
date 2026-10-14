# 02 — Truthful integrity-only readiness
Blocked by: 01-startup-integrity.
Changes: `gateway/readiness.py`, `tests/gateway/test_b1_startup_integrity.py`.
TDD: pending => degraded integrity even if state.db accessibility is OK; malformed or stale verified => unverified; no status after known unclean exit => unverified.
Acceptance: preserve existing status interfaces; do not conflate with Telegram adapter polling. Per-profile Telegram readiness is B2, not B1.
