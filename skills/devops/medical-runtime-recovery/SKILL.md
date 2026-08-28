---
name: medical-runtime-recovery
description: Use when live med scripts are stale or mixed after merges.
---

# Medical Runtime Recovery

Evidence-first recovery of the medication execution layer
(`~/.hermes/scripts/med_*.py`, `chain_*.py`, hooks) when live files are stale,
missing, or a mixed overlay after merges/source-closure work. Complements
med-tracker (confirmation protocol) and hermes-recovery (Hermes source).

## When to use
- `CC` (or another alias) resolves `UNKNOWN` in live but worked historically.
- Reminder shows a dosage that doesn't match `dexa_taper.json` current phase.
- A med script is missing live (`med_state_lock.py` case) or hashes differ
  from clean source.
- Post-merge/post-candidate investigation: "did the merge overwrite newer
  data?"

## Workflow (read-only first, always)

1. **Classify every med path live-vs-source (blob-level).** For each candidate
   file: `sha256sum` live vs `git -C <worktree> hash-object <path>` (or
   runtime repo `git ls-tree HEAD -- <path>`). Classify each as
   `stale-live` / `missing-live` / `current-compatible`.
2. **Recognize split-brain.** Live runtime can mix an old resolver + a
   candidate-equivalent confirmer + a newer hook/chain. Each file gets its own
   verdict; never assume a uniform version. Backups (Gate-1 staging etc.) may
   preserve the STALE hashes — verify, don't assume a backup is a recovery
   source.
3. **Find the coherent set.** The recovery source must be an internally
   coherent set validated together by its own tests (e.g. `test_cc_atomic`
   9/9 + `test_safety_gate` 18/18). Never assemble files from a partial
   hybrid commit/candidate — mixing breaks the transaction set.
4. **Hermetic acceptance probes BEFORE deploy** (temp HOME/HERMES_HOME +
   copied schedule/taper fixtures; live state untouched). See pitfalls for
   the CC probe recipe and the by-design REJECT trap.
5. **Deploy with rollback discipline:** timestamped rollback dir with `cp -p`
   of every replaced file, `install -m <original-mode>` (preserve 711 vs 600),
   post-copy hash verification, med-state hashes must be UNCHANGED,
   `py_compile` each file.
6. **Approval gates:** no commit/push/restart without owner approval. Hooks
   load at gateway STARTUP — file replacement does not hot-reload a running
   gateway; no_agent cron scripts (chain_monitor.sh) DO pick up changes
   per-tick without restart.
7. **Post-deploy:** re-run full regression, verify live resolver output,
   report the complete live hash set so the owner can confirm nothing else
   moved.

## Key pitfalls
- **Partial-state dry-run REJECT is by design.** `med_confirm.py --dry-run
  C --compound cc` against REAL live state rejects with
  `partial/conflicting CC state` when one component is already taken but the
  slot isn't complete — that's the no-overwrite safety, NOT a deployment
  failure. Prove the success path on a fresh empty-state fixture; explain the
  live reject as expected.
- **Static dosage vs taper authority.** `med-schedule.json` dosage fields are
  a static snapshot; the taper engine is the authority. Reminder and
  confirmation consumers must call `dexa_taper_lookup.get_dexa_dose(slot,
  date_str)` for every Dexa-bearing slot, including Slot F. Treat `0` as an
  explicitly inactive slot and `None` as no active phase or an unresolved
  split; never render `None` as `Nonemg` or silently turn it into a dose.
  A `pending_pharmacist_confirm` phase requires a visible HOLD until the
  primary chart/pharmacist source resolves it.
- **`dexa_taper.json` phases have no `phase` key** — selection is by start
  date inside `get_current_phase()`. Don't index fixtures by phase number.
- **Frozen-date tests:** freeze `CHAIN_CALC_NOW_MYT=<date>T12:00:00+08:00`
  and run boundary vectors. Current runtime/source evidence: 08-11 →
  B4/C4/D4/F0, 08-12 → B4/C4/D3/F0, and the 08-26 BD transition →
  B6/C0/D0/F4. For a phase whose split is `null` pending pharmacist
  confirmation, assert a visible HOLD/alert rather than inventing a dosage.
  TDD RED first: the failing stale-value assertion is the bug proof.
- **Fixture probing with bare `HOME=/tmp`** returns phase None (taper file
  missing) → no override; always copy schedule+taper fixtures into the temp
  home.
- **Chart-photo is authoritative, JSON is derived.** When a doctor hands
  a photo of a tapering chart and it disagrees with `dexa_taper.json`,
  the chart wins. The 5-Jul 2026 transcription introduced 2 extra phases
  (4-week out-of-sync) and the system happily ran them for 7 weeks. Rule:
  any taper sequence with a >2-week plateau at constant total_mg is a
  transcription-error red flag. Always check the rule printed in the
  chart's own header ("-1mg / 2 weeks") against the JSON; if a phase
  violates the rule, the JSON is wrong, not the chart.
- **A new med slot is a schema change that touches 14 sites, not 1.**
  Adding Slot F (14:00 BD-only dexa) required edits to: med-schedule.json,
  med-supply.json, dexa_taper_lookup.py (`SLOT_TO_KEY`), chain_calc.py
  (`SLOTS` + `DEFAULT_TIMES` + `dexa_ids` + `timing_drug` + reminder
  branch), med_confirm.py (`ALL_SLOTS`), med_resolve.py (`TIME_RULES` +
  `WORD_TO_SLOT`), med_chain/rules.json (anchor + gap rules),
  med_chain/solve.py (anchor branch), taper_alert.py (freq-change
  message). Missing any one fails silently on the wrong freq day.
  See `references/dexa-chart-rebase-20260825.md` for the full table.
- **Skill reference docs can be the source of the bug.** A reference
  table that encodes the wrong phase table reproduces the bug in every
  future session that loads the skill. After a data rebase, the
  skill's own reference files need a re-pass, not just the runtime
  data. Add a header note pointing to the new authoritative source
  until the table is rewritten.

## References
- `references/cc-compound-recovery-20260812.md` — full split-brain diagnosis,
  the coherent 4-file CC set, acceptance probe recipes, deployment discipline.
- `references/dexa-dose-dataflow-fix-20260812.md` — bug chain, fix code,
  hermetic test recipe, boundary vectors.
- `references/dexa-chart-rebase-20260825.md` — doctor photo vs JSON
  reconciliation, 9-touchpoint slot wiring map, pending-confirm flag pattern,
  end-to-end boundary verification.
- `references/dexa-bd-dynamic-deactivation-20260826.md` — 2026-08-26 BD transition
  root causes: static required list trap, denormalized overall cache, time-over-word
  precedence in med_resolve, and consumer Slot F enumeration synchronization.
- `references/dexa-bd-slot-f-solver-gap-fix-20260827.md` — 2026-08-27 BD Slot F solver
  min_gap bug: static anchor override prevented dynamic push on delayed Slot B intake.
- `references/live-vs-personal-source-drift.md` — differential live-vs-personal
  source hashing and frozen-date probing; distinguishes stale personal tests from
  live runtime defects and requires a visible HOLD for unresolved clinical splits.

## Related
- med-tracker (user-owned): medication confirmation protocol + drug
  resolution. If it needs patching, ask owner to `hermes curator adopt
  med-tracker` first.
- hermes-recovery (user-owned): Hermes source/runtime recovery.
- clean-restart-gateway: the approved gateway restart path.
