# Feature and Data Status Pattern

Use two independent dimensions when an extensible ledger may depend on optional sources.

## Feature lifecycle

- `enabled`: capability is active; it may collect, validate, display, and score data.
- `disabled`: capability exists but is intentionally inactive; it must not collect, alert, or score.
- `not_implemented`: capability is not yet built. Use this instead of pretending a future feature is merely unavailable.

## Data availability

- `available`: source exists and usable data is present.
- `partial`: source exists but records are incomplete.
- `not_available`: capability is active but the source/data does not exist yet.
- `stale`: data exists but is outside the freshness policy.

Example: Labs can be `feature_status=enabled`, `data_status=not_available`. The UI should report a data gap and exclude labs from scoring; it must not convert the gap to zero, normal, or missed. If the user intentionally pauses the module, use `feature_status=disabled`.

## Event-ledger planning facts

For a personal medication system, an append-only ledger mainly adds auditability, replay/rebuild, idempotency, correction history, provenance, and reconciliation. It also adds migration, consistency, testing, privacy, and storage-growth costs. Measure current state before estimating growth; label event-size projections as estimates until a prototype measures them. Keep existing JSON projections during migration and activate optional modules incrementally.
