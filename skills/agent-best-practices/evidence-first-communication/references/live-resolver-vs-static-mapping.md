# Live Resolver vs Static Mapping — Medication Example (2026-08-17)

## Why this reference exists

A current medication confirmation exposed drift between a static skill table, historical state, and the live runtime. The reusable lesson is general: static aliases and old records are evidence, but they are not authoritative for a new state write when a live resolver is available.

## Raw live evidence captured

Current runtime commands returned:

```text
$ python3 ~/.hermes/scripts/med_resolve.py akurit --time 06:50
{
  "ok": true,
  "drug_id": "akurit_2",
  "slot": "A",
  "drug": "Akurit-2",
  "dosage": "4 tablet"
}

$ python3 ~/.hermes/scripts/med_resolve.py akurit-4 --slot A
{
  "ok": true,
  "drug_id": "akurit_2",
  "slot": "A",
  "drug": "Akurit-2",
  "dosage": "4 tablet"
}
```

The live schedule contained:

```text
med-schedule.json:
  drug:    Akurit-2
  drug_id: akurit_2
  dosage:  4 tablet
  rule:    Akurit-2 mesti perut kosong. 1j sebelum atau 2j selepas makan.
```

The historical `med-status.json` snapshot contained older `akurit_4` entries (2026-07-03 through 2026-07-08) and `akurit_2` entries from 2026-07-09 onward, including the current 2026-08-17 entry. The static `med-tracker` table still described generic `akurit` as `akurit_4`.

## Safe reconciliation recipe

1. Run the live resolver with the user's exact drug wording and stated time.
2. Preserve the raw JSON result; do not manually translate the returned ID.
3. If the result is surprising, inspect the current schedule/registry that defines the canonical ID.
4. Use the live canonical ID for the new write only if the user's wording supports that entity.
5. Do not rewrite historical entries merely to make identifiers uniform.
6. Run a no-write dry-run with the exact source text before writing.
7. If the physical label, prescription, or user-provided identifier conflicts with the live result, hold and ask before logging.
8. Read back the child state and aggregate state after the serialized write.

## Boundary

This file records one runtime's observed alias state; it is not a permanent claim that `akurit` will always resolve to `akurit_2`. Re-run the resolver for future confirmations.
