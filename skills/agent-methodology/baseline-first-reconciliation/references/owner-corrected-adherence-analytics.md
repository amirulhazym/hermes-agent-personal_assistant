# Owner-Corrected Adherence vs Raw Medication State

Use this reference when analysing historical medication adherence from a persisted state file that may contain stale, incomplete, or semantically wrong records.

## Core rule

Never equate `med-status.json` with physical adherence. Keep two separate outputs:

1. **Raw-record view** — exactly what the persisted state says.
2. **Owner-corrected adherence view** — the owner's direct correction of what was actually taken, with uncertainty preserved.

A correction may change the adherence classification used for analysis, but must not silently overwrite the raw medical history. If a historical backfill is desired, get explicit approval and preserve the pre-edit artifact.

## Classification vocabulary

For each date + slot + drug, use one of:

- `TAKEN_RECORDED` — raw state records taken with a time.
- `EXPLICITLY_SKIPPED` — raw state records skipped and includes a reason/owner decision.
- `UNRECORDED` — no raw state entry; do not call this a physical miss.
- `OWNER_CONFIRMED_TAKEN_TIME_UNKNOWN` — owner says it was taken but cannot provide the time; do not invent one.
- `OWNER_CORRECTED_TAKEN` — owner says the raw skipped/partial classification is wrong and the dose was taken.
- `CONFLICT_UNRESOLVED` — raw and owner evidence conflict and the owner has not resolved it.

## Timing semantics

Do not infer that every schedule window has identical clinical strictness. The owner’s documented regimen/contract must identify which medicines are strict-time and which can be taken late without making the day non-compliant. A late non-strict companion dose can keep a slot/day complete even when a stale window-based gate marked it partial.

For conditional/optional drugs, do not count absence as a missed required dose unless the condition was active and the drug was required that day.

## Historical metrics

- Keep today outside the historical denominator until the day is complete.
- Report both `owner-corrected adherence` and `raw logging completeness` when they differ.
- For a corrected day, show the exact reason and provenance instead of silently changing the percentage.
- A missing time is a data-quality limitation, not permission to estimate from neighbouring slots.

## Case fixture — 2026-08-16 correction

The raw state initially classified three historical dates as incomplete:

- `2026-07-19` Slot C: raw state said Calcium + Calcitriol skipped; owner corrected that CC was taken late. For adherence analysis: **complete**; raw state remains a reconciliation discrepancy.
- `2026-07-21` Slot E: no raw Levetiracetam record; owner corrected that it was taken, but the time is unknown. For adherence analysis: **complete / time unknown**; raw logging remains incomplete.
- `2026-07-30` Slot C: owner confirmed CC was intentionally skipped. For adherence analysis: **incomplete / explicit skip**.

The corrected historical result for the checked period `2026-07-02..2026-08-15` is `44/45` complete days (`97.8%`), with one confirmed incomplete day. This fixture is an interpretation regression case, not a substitute for re-reading the live state file.
