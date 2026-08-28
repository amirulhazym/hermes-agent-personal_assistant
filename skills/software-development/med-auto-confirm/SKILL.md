---
name: med-auto-confirm
description: Structural fix for the recurring "agent acknowledges med confirmation verbally but never executes med_confirm.py" bug. Auto-logs medication confirmations from inbound messages via a gateway hook BEFORE the agent processes them, so med-status.json is always correct and the reminder cron stops firing duplicates.
---

# med-auto-confirm — Structural Medication Confirmation Hook

## Problem This Solves (verified 2026-07-09)

The agent repeatedly acknowledged "dah makan A" verbally but failed to execute
`med_confirm.py`, leaving `med-status.json` empty for the day. The reminder
cron then read the slot as pending and fired duplicate reminders. Instruction
in prompt (med-tracker skill) was NOT enough — the model skipped the step.

Root cause class: **gap between instruction and execution**. The model is not
a reliable enforcement layer for state mutations.

## Solution

A gateway hook (`~/.hermes/hooks/med-auto-confirm/`) registered for the
`agent:start` event. It fires BEFORE the agent processes the user message and,
as a side-effect, runs `med_confirm.py` if a confirmation is detected and the
slot is not yet logged today.

### Why agent:start (not a pre-response gate)

The Hermes hook infrastructure (`gateway/hooks.py`) **discards return values**
(`emit()` line 191-198) and is **fail-open by design** (line 19: "Errors in
hooks are caught and logged but never block the main pipeline"). There is NO
hook event that can block or rewrite the agent response. `agent:end` fires
AFTER delivery (too late). Therefore a "pre-delivery hard gate" is impossible
with current hook infra. The achievable structural fix is **correct state via
side-effect before the agent reads** — which fully solves the duplicate-reminder
problem because the cron reads state, not the agent's words.

### Files

- `HOOK.yaml` — metadata, `events: [agent:start]`
- `handler.py` — detection + side-effect
- `test_med_auto_confirm.py` — regression harness (runs against TEMP HOME, never live)

## Handler Logic (handler.py)

1. `COMPLETE_RE` — past-tense completion signal (dah makan, sudah, selesai, done, etc.)
2. `_resolve_slot_drug(message, now)` — priority:
   - Explicit slot letter (A-E) via `SLOT_RE`
   - Drug name via `DRUG_MAP` (akurit→A, calcium→C, etc.)
   - Time-disambiguated multi-slot drugs (letram/dexa by hour)
3. `_parse_time(message, now)` — "pukul 6", "6am", "jam 6", "6:00", "0600"
4. `_already_logged(slot, today)` — idempotency check on med-status.json
5. If confirmed + not logged → `subprocess.run([python, med_confirm.py, slot, drug?, --at, time])`
6. Fail-open: any exception → log to stderr, never raise

### Critical testing constraint

`med_confirm.py` hard-codes `Path.home() / ".hermes" / "med-status.json"`
(line 41). It does NOT read an env var. So the test harness MUST:
- Build a temp dir with `.hermes/scripts/med_confirm.py` + `med_resolve.py`
  + `med-schedule.json` + `dexa_taper.json` copied in
- Override `HOME` env var when calling the hook's subprocess
- Patch `subprocess.run` in the test to inject `env={"HOME": tempdir}`

DO NOT patch `mod.STATUS_FILE` alone — med_confirm.py ignores it (this was the
first test attempt's bug; it silently wrote to LIVE state).

## Deploy Procedure

1. Write `HOOK.yaml` + `handler.py` to `~/.hermes/hooks/med-auto-confirm/`
2. Run `python3 test_med_auto_confirm.py` → expect 5/5 PASS
3. Restart gateway (see `gateway-restart` skill) — hook auto-discovered on startup
4. Verify: `python3 -c "from gateway.hooks import HookRegistry; r=HookRegistry(); r.discover_and_load(); print([h['name'] for h in r.loaded_hooks])"` → must include `med-auto-confirm`
5. Live functional verification happens naturally on next real med confirmation

## Regression Test (run after any handler.py change)

```
cd ~/.hermes/hooks/med-auto-confirm && python3 test_med_auto_confirm.py
```

Tests:
1. "A dah ambil 6am" → A logged
2. Time parsed as 06:00
3. Non-confirmation msg → no write
4. "dah makan dexa pagi jam 8" → B logged
5. Idempotent on repeat call

## Incident-Learned Guardrails (2026-07-19)

### Intent must be resolved before drug or slot resolution

A medication token plus a completion-looking word is NOT sufficient evidence of intake. The handler MUST classify message intent before resolving a drug/slot or invoking any write path.

Write only for `CONFIRM_INTAKE`. These intents are hard no-write outcomes:

- `QUESTION`: "boleh ke aku nak makan dexa?", "can I take..."
- `STATUS_QUERY`: "dah log ke?", "logged ke?", "recorded?", "confirm ke?"
- `FUTURE_INTENT`: "nak makan", "akan makan", "japgi makan", "nanti update"
- `CORRECTION`, `DENIAL`, `QUOTE`, `REMINDER_TEXT`, and `AMBIGUOUS`

Negative/status patterns take precedence over generic completion patterns. The word `makan` inside a question must never trigger a write. The word `dah` inside a ledger/status question must never trigger a write.

### One write boundary for all confirmation paths

Slot-level and drug-level confirmation MUST pass the same validated write contract. The contract requires:

- exact original `source_text`;
- `intent == CONFIRM_INTAKE`;
- resolved slot and drug;
- actual intake time and explicit time provenance;
- resolver reason;
- idempotency check.

`confirm_drug()` must not remain an unvalidated bypass around the slot-level `source_text` gate. If the contract cannot be satisfied, return `NO_WRITE` or `NEEDS_CLARIFICATION`.

### Timestamp provenance is mandatory

Never pass `time=None` for a write and let processing time become the intake time. A stored medication time must be one of:

- `USER_STATED`: exact time stated by the user;
- `USER_CONFIRMED_NOW`: only when the message is an unambiguous present-tense confirmation and the current time is explicitly accepted by the contract;
- otherwise no write.

Audit records must preserve processing timestamp separately from intake timestamp.

### Test negative conversational cases, not only positive confirmations

The regression corpus MUST include realistic Manglish questions and status queries containing drug names, plus future plans, corrections, quoted reminder text, pasted chat transcripts, ambiguous `dah makan`, duplicates, and missing times. A passing positive-confirmation suite is not evidence that the detector is safe.

### Required verification sequence after changes

1. Run the adversarial corpus in a temporary HOME/state, never production state.
2. Run shadow mode against representative inbound messages and compare classifications.
3. Prove the state hash is unchanged during shadow mode.
4. Only then enable writes and run one canary confirmation with raw audit output.
5. Report `VERIFIED` only with the command output and state read-back attached.

## Pitfalls

- **Hook cannot block response.** Don't design "gate" logic expecting return-value enforcement.
- **med_confirm.py path is hard-coded to HOME.** Test harness must override HOME, not module vars.
- **Don't run chain_monitor.sh against live state** (pollutes counts) — separate pitfall in med-tracker.
- **Time disambiguation for dexa/letram is hour-based.** If user says "dexa" at 13:00, maps to C.
  Matches med-tracker's resolver rules; keep in sync if those change.

## When NOT to use

If the hook infra gains a pre-response blocking event, this design should be
revisited — a true gate would be cleaner. As of 2026-07-09, agent:start
side-effect is the best available structural fix.
