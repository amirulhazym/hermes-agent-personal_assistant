# Implementation Plan: Decommission Auto-Supply Tracking & Eliminate Fabricated Medication Counts

- **Date:** 2026-09-27
- **Feature Slug:** `decommission-med-auto-supply`
- **Spec:** `.scratch/decommission-med-auto-supply/spec.md`
- **Tickets:**
  - `.scratch/decommission-med-auto-supply/issues/01-decouple-confirm-supply.md`
  - `.scratch/decommission-med-auto-supply/issues/02-sanitize-runtime-supply.md`
  - `.scratch/decommission-med-auto-supply/issues/03-codify-anti-fabrication-rules.md`

## Proposed Changes

### 1. `scripts/med_confirm.py`
- Remove import and call of `med_supply.decrement` in `confirm_slot` (around line 398) and `confirm_drug` (around line 574).
- Remove `supply_alerts` population logic (around lines 416–433).
- In `confirm_compound`, remove `SUPPLY_FILE` mutations and decrements.
- Update/add regression unit test in `scripts/test_med_confirm_supply.py` verifying that confirmation does not touch `med-supply.json` and returns no `supply_alerts`.

### 2. Runtime State: `~/.hermes/med-supply.json`
- Backup to `~/.hermes/med-supply.json.bak-pre-decommission-20260927`.
- Set `drugs.levetiracetam_b.current = null`.
- Update `drugs.levetiracetam_b.notes` to remove `"Still sufficient (95 pills)."` and replace with factual `"Restocked at IPR — exact count not tracked (untracked mode)."`.
- Update `last_updated` date to `2026-09-27`.

### 3. Skills
- Patch `skills/software-development/anti-fabrication-guardrails/SKILL.md`:
  - Add explicit guardrail on Medication Inventory Invariants: Never guess, estimate, or initialize numeric pill inventory counts. Default is strictly `null` (untracked).
- Patch `skills/med-tracker/SKILL.md`:
  - Clarify that intake confirmation never modifies inventory and alerts must not be generated for untracked stocks.

### 4. Tests & Quality Gates
- Execute `python3 -m unittest discover -s scripts -p "test_*.py"` to ensure 100% test pass.
- Run security scan `bash scripts/guard/secret-scan.sh --tree`.
- Run PII review `python3 scripts/guard/pii-review.py --diff origin/main..HEAD`.
- Validate manifest `bash scripts/guard/manifest-validate.sh docs/reconciliation/v3-source-coverage-manifest.json $(git rev-parse HEAD)`.
