# Spec: Decommission Auto-Supply Tracking & Eliminate Fabricated Medication Counts

## Problem Statement

The medication subsystem inadvertently produced a false critical supply alert (`STOCK OUT: Levetiracetam (pagi)`) during regular medication confirmation. Investigation revealed that on 2026-07-07, an earlier AI agent fabricated an initial supply count of 95 pills (`current: 95`) and hardcoded note `"Still sufficient (95 pills)"` for `levetiracetam_b`, despite explicit user statements that exact pill counts are not tracked and that all medications were fully restocked by the hospital clinic (IPR).

Subsequently, confirmation of daily Slot B intakes triggered an automated, silent decrement of this fabricated counter via `med_supply.decrement()`. Over 36 intake events between 2026-08-22 and 2026-09-26, the counter decreased to 0, which triggered a passive `STOCK OUT` alert in `med_confirm.py` during an unrelated Slot A confirmation.

The user does not track pill inventory by software numbers; clinical supplies are replenished via hospital appointments. Maintaining automated decrement logic over untracked inventory creates hallucinated deficits, misleading warnings, and severe cognitive distraction.

## Solution

1. **Decommission Auto-Supply Decrement & Alerts in Confirmation Flow:**
   - Remove automatic calls to `med_supply.decrement()` from `med_confirm.py`.
   - Remove passive `supply_alerts` generation and propagation from `med_confirm.py`.
   - Keep manual inventory queries intact in `med_supply.py` if explicitly requested, but remove any automatic decrements during standard dosage confirmation.
2. **Clean Runtime Supply State (`~/.hermes/med-supply.json`):**
   - Reset `levetiracetam_b.current` to `null` (untracked mode).
   - Sanitize all text fields in `~/.hermes/med-supply.json` to purge fabricated numbers and replace them with factual hospital restock notes.
   - Ensure all active medications consistently use `current: null`.
3. **Institutionalize Anti-Fabrication Constraints:**
   - Add explicit prohibitions in `anti-fabrication-guardrails` and `med-tracker` forbidding any autonomous guessing, estimation, or recording of numeric inventory counts without explicit physical count disclosure by the user.

## User Stories

1. As a patient recovering on a complex medication regimen, I want confirming my scheduled medication doses to record completion accurately without triggering false "STOCK OUT" warnings, so that I am not alarmed by non-existent medication shortages.
2. As a patient whose medications are supplied by hospital pharmacy appointments, I want the system to treat all medication inventory as untracked by default (`current: null`), so that software counters do not drift out of sync with my real physical supply.
3. As a developer/operator, I want `med_confirm.py` to decouple intake confirmation from supply decrements, so that confirmation transactions focus purely on schedule state and Domino Chain timing without mutating inventory state.
4. As an operator auditing system integrity, I want all legacy hallucinated pill figures (such as 95 pills or 36 pills) purged from runtime state files, so that future sessions and cron reports do not cite fabricated historical figures.
5. As an operator, I want strict guardrail rules encoded in the agent skills, so that no current or future AI model fabricates numeric inventory values or assumes untracked counts.

## Implementation Decisions

1. **Decouple Intake Confirmation from Supply Decrement:**
   - Modify `scripts/med_confirm.py` to remove calls to `med_supply.decrement()` in `confirm_slot()` and `confirm_drug()`.
   - Remove `supply_alerts` checking and inclusion in the confirmation return dictionary.
   - Clean compound confirmation flow in `scripts/med_confirm.py` (`confirm_compound`) to prevent supply file mutation.
2. **Runtime Data Sanitization:**
   - Take an atomic timestamped backup of `~/.hermes/med-supply.json`.
   - Set `current: null` across all medication entries in `~/.hermes/med-supply.json`.
   - Scrub notes in `levetiracetam_b` and any other drug entries to eliminate references to fabricated pill quantities.
3. **Anti-Fabrication Guardrails & Skill Codification:**
   - Update `skills/software-development/anti-fabrication-guardrails/SKILL.md` and `skills/med-tracker/SKILL.md` to document the incident and formalize the prohibition against automated or inferred inventory numbers.
4. **Preserve Test Integrity:**
   - Update existing test suites (`test_cc_atomic.py`, `test_runtime_fixtures.py`, etc.) to align with decoupled confirmation and untracked supply models.

## Testing Decisions

- Unit tests must verify external behavior: confirming a slot or drug updates `med-status.json` and returns success without touching `med-supply.json` or decrementing any counts.
- Regression tests must verify that `med_confirm.py` output contains no `supply_alerts` or false `STOCK OUT` messages.
- Test suites must execute in isolated temporary directories (`HOME` sandbox) without mutating live state.

## Out of Scope

- Removing `med_supply.py` CLI manual query capabilities (`--check`, `--upcoming`).
- Modifying clinical schedule timings, Domino Chain logic, or Dexa taper schedules.
- Changing `med-status.json` schema.

## Further Notes

All changes in SSOT repository `/home/ubuntu/hermes-agent-personal_assistant-work` must satisfy quality gates (secret scan, PII review, contract tests) before publication.
