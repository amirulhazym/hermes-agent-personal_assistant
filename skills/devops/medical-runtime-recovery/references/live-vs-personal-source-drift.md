# Live-vs-Personal Source Drift

Use this reference when a medication test in the personal repository disagrees
with the running VPS scripts after a merge, source-closure, or slot-schema
change.

## Diagnostic rule

A failing personal test is not automatically a live medication-engine defect.
Run the same frozen-date probe twice, with the same copied schedule/taper
fixtures:

1. Import the live script set from an isolated `HOME` and record only the
   relevant slot outputs.
2. Import the personal-repository script set from a separate isolated `HOME`
   and record the same outputs.
3. Compare source hashes for the complete coherent slot-change set, not just the
   file named in the failure.

Classify the result:

- **Live correct / personal stale:** live matches the current chart/runtime
  contract, while personal code or assertions use the old slot schema.
- **Both wrong:** the defect is likely in the shared data/consumer contract;
  continue tracing before editing either side.
- **Live wrong / personal correct:** treat live as the urgent runtime defect;
  preserve live state and use the approved live-first recovery workflow.
- **Evidence split:** stop at `UNRESOLVED`; do not choose a dose from familiarity.

## Slot-schema safety

A new medication slot is a schema change. Audit every consumer listed in
`references/dexa-chart-rebase-20260825.md`; a partial copy can leave a working
resolver beside stale chain, confirmation, reminder, or reporting code. A
missing source file is also a closure failure even when the runtime currently
works.

For a date where a slot is deactivated, assert the distinction explicitly:
`0mg` means the slot is inactive; `None` means no active phase or an unresolved
split. Never turn `None` into a static dose or display it as `Nonemg`.

## Pending clinical split

If the authoritative taper data stores a phase split as `null` with a
`pending_pharmacist_confirm` record, software must preserve the safe HOLD and
surface a visible confirmation-required alert. It must not invent a split from
the phase total, an old test, or a stale skill table. The chart/photo remains
higher authority than the derived JSON; a future data correction requires the
owner's primary-source confirmation.

## Verified example (2026-08-28)

The personal Dexa dataflow test expected `C=3mg` on 2026-08-26 and failed with
`4mg`. The live hermetic probe instead resolved the chart-rebased BD schema as
`C=0mg` and `F=4mg`; the live resolver also mapped `dexa --time 14:55` to
`dexamethasone_f` with dosage sourced from `dexa_taper.json`. The failing test
was therefore stale relative to the live Slot-F source, not proof of a live
underdosing bug.

The source inventory found all 10 checked Slot-F-related source files had
non-identical live/personal hashes, and `med_report.py` existed live but was
absent from the personal source. This is a real source-closure defect and must
be reconciled as a coherent set; do not fix it by changing one assertion only.

The same audit found phases 13–14 with `null` morning/2pm splits. The live
`taper_alert.format_dose_change()` rendered `None`/`Nonemg` and emitted no
HOLD marker. That is a separate software alerting defect; resolving it does
not authorize filling the clinical split.

## Privacy and non-mutation

Keep `med-schedule.json`, `med-supply.json`, `dexa_taper.json`, `med-status.json`,
logs, and credentials out of public source. Copy minimum fixtures to a throwaway
`HOME`/`HERMES_HOME`, hash live state before/after any probe, and never invoke a
confirmation writer during diagnosis. Source capture, test correction, live
copy, and clinical-data mutation are separate decisions and gates.
