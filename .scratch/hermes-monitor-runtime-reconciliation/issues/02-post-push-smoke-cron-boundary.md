# 02 — Repair post-push smoke cron boundary

**What to build:** Make the existing post-push smoke check work from its real system-cron environment while preserving its current cadence and read-only purpose.

**Blocked by:** 01 — Durable `/xcute` execution foundation.

**Status:** ready-for-agent

- [ ] A cron-like sanitized environment can query the Hermes user service without `Failed to connect to bus`.
- [ ] A successful smoke run refreshes both JSON and Markdown receipts.
- [ ] Gateway active state and PID are read correctly.
- [ ] The five-minute cron cadence and unrelated service lifecycle remain unchanged.
- [ ] Targeted regression tests and release guards pass before publication.
