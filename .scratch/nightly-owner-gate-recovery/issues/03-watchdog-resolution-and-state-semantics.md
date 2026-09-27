# 03 — Repair watchdog primary resolution and repository-state semantics

Blocked by: 02-terminal-state-and-primary-provenance

Vertical slice:
- Add RED test reproducing 23:55 primary -> 00:25 update -> 01:55 lookup.
- Resolve primary using immutable provenance with legacy fallback.
- Distinguish CLEAN+SYNCED, CLEAN+UNSYNCED, DIRTY, UNKNOWN.
- Keep 01:55 schedule/mode and fail-closed scheduler evidence checks.

Acceptance:
- real primary is never MISSING solely because same-run receipt was updated later;
- clean local-ahead owner-pending state is HOLD/CLEAN+UNSYNCED, not NOT CLEAN;
- dirty or unverifiable states remain non-PASS.
