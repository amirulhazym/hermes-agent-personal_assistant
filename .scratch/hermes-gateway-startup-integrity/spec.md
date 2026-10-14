# Hermes Gateway Startup Integrity — B1 Candidate Spec

Status: Phase 4 isolated SSOT TDD candidate. Owner lock Q1:A with conditions, Q2:A (B2 only), Q3:A (B3 only). No release authority.

## Problem statement
After an unclean exit, `record_startup()` synchronously executes SQLite `PRAGMA quick_check(1)` before MCP/Telegram startup. A 3+ GiB production state database was associated with an approximately 18-minute startup gap on 14 October 2026. Exact internal scan duration remains unmeasured.

## Solution and user stories
- As an owner, I want messaging startup not to wait on database integrity scans so Telegram can initialize.
- As an operator, I want a persistent, incident-specific integrity status that does not say verified without real evidence.
- As a reviewer, I want real SQLite corruption checks preserved for explicit, separately approved use.

## Implementation decisions
- Keep lifecycle ownership and unclean-exit detection.
- B1 performs **no SQLite read/stat/full scan on startup**; record `pending` for unclean incidents.
- Atomically write `state/gateway-integrity-verification.json` outside `state.db` and outside the lifecycle sentinel.
- Identity: SHA-256 of the old gateway PID, start timestamp, and started_at.
- Clean starts preserve the pending file; new unclean incidents begin pending, never inherit old verified.
- Same-incident recorded `verified` or `failed` must carry method and completion timestamp; otherwise invalid and fail soft to unverified.
- If atomic status persistence fails, log WARNING plus append diagnostic as `unverified`; cannot falsely claim verified.
- The authenticated readiness output includes `integrity_verification`; `state_db` retains its old accessibility-only meaning.
- B2 handles per-profile Telegram readiness; B3 handles alerting.
- No scheduled verification, background worker, repair, process restart, or changes to providers/Telegram/RDC/systemd.
- The official base and ordered 8-entry hash-pinned patch series reconstruct the source. No direct runtime mutation.

## Testing decisions
RED: missing persistent status file and missing readiness check. GREEN: 46 focused tests on isolated candidate and rebuilt output; explicit tiny corrupted SQLite fixtures remain tested. Check both `git apply --check` and reverse patch check. No live SQLite integrity verification.

## Out of scope
B2/B3, job scheduling, database repair, scanner time budgets, publication, CI/PR/merge, live deployment, reboot, restart.

## Remaining risk
Tiny atomic forensic write includes filesystem operations; kernel-level I/O stalls cannot be strictly capped by SQLite busy_timeout. A write failure cannot guarantee durable status; it must be surfaced as unverified for operator review. Full verification itself remains pending separate owner approval.


## Safety correction 2026-10-15
Keep `prior_integrity_incident_id` across clean shutdown and clean startup so a failed atomic verification-status write cannot change `degraded/unverified` into `ok/not_required`. Do not mark new clean boot as unclean. First boot without a prior incident remains `not_required`. Verify incident identity even on later clean boots; never reuse a stale verified record from another incident. Publication remains HOLD.
