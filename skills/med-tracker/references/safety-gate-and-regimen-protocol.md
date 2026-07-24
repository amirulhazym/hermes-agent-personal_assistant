# Safety Gate Phase 1 — Contract

## Purpose

Prevent syntactically valid but semantically suspicious medication messages from
mutating medication state before a human clarification.

## Authoritative inputs

- `med-schedule.json`: active medication slots, drugs, and timing windows.
- `dexa_taper.json`: date-dependent active dexamethasone dose positions.
- `med_resolve.py`: aliases and current schedule-based resolution.

`med_safety_gate.py` must not duplicate dosage, slot cutoff, or timing-window
rules from those files.

## Decision boundary

`evaluate(message, stated_time, reference)` returns one structured decision:

- `ALLOW`: all medications parse against active regimen, one planned slot, and
  stated time is inside active schedule window.
- `HOLD`: config unavailable, parse incomplete/ambiguous, cross-slot pairing,
  time-window conflict, inactive taper slot, or clinician/hospital change
  language.

For HOLD:

- never invoke `med_confirm.py`;
- never mutate medication status, supply, schedule, taper, or reminder state;
- persist one `OPEN` hold with raw text, parsed mentions, findings, timestamps,
  schedule version/digest, taper phase, and hold ID;
- append JSONL audit;
- trigger `med-tracker` so the agent asks a natural clarification.

## Resolution

`med_hold.py` may close a hold with correction/rejection evidence. It cannot
log medicine or alter regimen. Corrected intake must go through normal
source-backed `med_confirm.py` only after explicit user confirmation.

## Clinician/hospital changes

Clinician/hospital/clinic language is a HOLD and regimen-update candidate, not
an intake write. Phase 1 does not activate schedule/taper changes. Future Phase
2 must create immutable regimen versions and atomically switch an active-regimen
pointer only after full details, impact review, and final approval.

## Verification

Run in candidate workspace:

```bash
python3 -m unittest discover -s hooks/med-auto-confirm -v
python3 hooks/med-auto-confirm/test_hook_chain.py
python3 -m unittest discover -v
python3 -m py_compile hooks/med-auto-confirm/handler.py scripts/med_safety_gate.py scripts/med_hold.py
```

Tests use isolated `HERMES_HOME`; no production medication state is touched.
