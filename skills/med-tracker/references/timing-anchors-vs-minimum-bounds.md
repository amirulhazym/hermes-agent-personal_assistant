# Timing Anchors vs Minimum Safety Bounds

## Incident
On 2026-07-18, live engine output after A at 05:40 was:

```text
A ✅ 05:40 → B ~06:40 → C ~10:40 → D ~14:40 → E ~18:40
```

The engine treated `A → B, min_gap=1h` as an exact propagation rule. That is wrong for this regimen.

## Required semantics

- **Dexa drives the timetable.** Before B is taken, B uses the doctor/taper anchor (normally 08:00). After actual Dexa B, C/D use 4-hour gaps from actual Dexa timestamps.
- **Akurit/Pyridoxine is a lower-bound safety constraint only.** The next intake must be at least one hour after Akurit. It does not automatically shift B/C/D/E.
- Resolve an anchored future dose as:

```text
max(doctor_anchor, all applicable minimum-safe times)
```

Never implement a minimum bound as `next_time = prior_time + gap`.

- **Letram B→E:** derive E from actual morning Letram + ~12h, independently of C/D or late CC.
- Late Calcium/Calcitriol must never move Dexa D.

## Regression contract

1. A=05:40, B pending → B remains 08:00 because 08:00 satisfies A+1h.
2. If A makes 08:00 unsafe → B is the earliest safe time; do not create a generic cascade.
3. Actual Dexa B → C/D each follow actual prior Dexa +4h.
4. Actual Letram B → E follows actual Letram B +~12h.
5. Solver conflict/error → suppress outbound reminder and log diagnostic; never silently fall back to legacy cascade.
6. Active copy/template must not claim: `A lambat = B,C,D,E semua akan geser`.

## Verified legacy fault path

- `scripts/med_chain/rules.json` encoded A→B as `min_gap`.
- `scripts/med_chain/solve.py` propagated `min_gap` identically to a fixed gap.
- `scripts/chain_calc.py` invoked this solver, and production cron called `chain_monitor.sh → chain_calc.py`.

The old test suite passed while asserting the wrong cascade. Passing tests are not evidence of correct regimen semantics until the regression contract above replaces those assertions.
