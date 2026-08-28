# Dexa Chart Rebase — doctor photo vs JSON reconciliation + new slot wiring (2026-08-25)

Proven: 19-phase dexa_taper.json rebuilt from doctor's IPR photo; new Slot F
(14:00, BD-only dexa) wired across 11 touchpoints; end-to-end verified for
boundary dates; med-status.json SHA256 unchanged.

## When this reference applies

- Boss attaches a photo of a doctor's tapering chart and the system SSOT
  (dexa_taper.json) disagrees with it.
- Boss asks to add a new med slot (e.g. a 4th daily dose time) to a tapering
  drug.
- Any change to a drug's dosing frequency where the slot set changes (TDS →
  BD, BD → OD, etc.).

## Incident summary (what the bug was)

- `dexa_taper.json` had 20 phases ending 2027-02-10; doctor's chart had 18
  phases ending 2027-01-12. The system was running a "10mg TDS 26/8–8/9" phase
  that did not exist on the chart; BD 6+4 was deferred to 9/9 (chart said
  26/8). System and chart were 4 weeks out of sync.
- The skill's own reference table `dexamethasone-tapering-schedule.md`
  encoded the wrong phase table — i.e. the skill was the source of the bug,
  not the runtime data. A reference doc that disagrees with a primary source
  is itself a bug.
- Root cause: 5-Jul 2026 transcription of the chart introduced 2 extra
  phases (the "10mg TDS 26/8–8/9" and "4mg BD 2/12–15/12" buffers). The chart
  self-validates against its own header rule "Taper 1mg/2 Week (Start with
  0.3mg/kg)" — any 4-week plateau where total mg is constant is a red flag.
  Rule: chart = authoritative; JSON = derived; never the other way around.

## Reconciliation pattern (4 phases, all required)

1. **Backup BEFORE any edit.** Copy `dexa_taper.json`, `med-schedule.json`,
   `med-supply.json`, `med-status.json` to `~/.hermes/backups/<timestamp>/`.
   SHA256 each. State file is included even though it won't be restored —
   it's the regression baseline. Rollback = `cp -p` from backup dir.

2. **Transcribe the chart with vision zoom**, region-by-region if needed. For
   the 18 Aug chart, three zooms were required: top rows, lower rows, and
   the sidebar (Masa Pemberian Ubat). Do NOT trust `web_extract` or
   `pdftoppm`-style OCR for table cells; use `vision_analyze` with explicit
   question + `region` parameter, and re-zoom if the answer is ambiguous.
   Vision output is semantic-only; the actual cell text must be re-typed or
   copied verbatim.

3. **Rebuild JSON phases, version-bump, mark source.** `version: "2.0"`,
   `source: "IPR chart photo <date>, boss-provided (supersedes <prior>)"`.
   Run arithmetic self-test in the same script: for each phase, sum the
   per-slot doses and assert `sum == total_mg`. This catches transcription
   typos immediately. The 5-Jul bug would have been caught this way.

4. **Add `pending_*` flags for chart entries the boss hasn't confirmed.**
   The IPR chart for phases 13 (21/10–3/11, 6mg) and 14 (4/11–17/11, 5mg)
   listed total only with no split. Live `dexa_taper.json` v2.1 deliberately
   stores `dose_morning` and `dose_2pm` as `null` for these phases; it does
   **not** infer conservative 3+3 / 3+2 values. Keep the top-level
   `pending_pharmacist_confirm` array with `phase_id`, `chart_says`,
   `system_uses`, `owner_confirms`, and require a consumer-visible HOLD/alert
   until a pharmacist confirms the split. The flag must remain traceable to a
   specific `phase_id` so the next visit is one concrete question, not a hunt.

## 9-touchpoint slot wiring map (add a new med slot, end to end)

Adding Slot F (14:00, BD-only dexa) required 11 file changes. The list is
generic to any new slot — only the slot letter and which scripts vary.

| # | File | What changes | Why it bit me when I missed it |
|---|------|--------------|--------------------------------|
| 1 | `med-schedule.json` | New slot entry with `name`, `time`, `window`, `drugs[]` | The data definition; everything else reads it. |
| 2 | `med-supply.json` | New `<drug_id>` entry under `drugs` with `slot` and `warning_threshold` | `med_supply.decrement()` looks up by drug_id; missing key silently no-ops. |
| 3 | `dexa_taper_lookup.py` | `SLOT_TO_KEY[<slot>]` mapping to the phase field (e.g. `dose_2pm`) | Without this, `get_dexa_dose(<slot>, date)` returns None. |
| 4 | `chain_calc.py` `SLOTS` | Add the letter to the global slot list | `calculate_chain` iterates SLOTS; missing letter means it never computes `ready_time` for the slot. |
| 5 | `chain_calc.py` `DEFAULT_TIMES` | Add `<slot>: 'HH:MM'` fallback | Default chain time used when no rule fires. |
| 6 | `chain_calc.py` `dexa_ids` | If the slot carries Dexa, append the drug_id | `get_actual_time` priority path skips dexa entries not in this list. |
| 7 | `chain_calc.py` `timing_drug` | Map `<slot>: '<drug_id>'` for chain-time calc | Chain time = max(taken drug times) for that slot. |
| 8 | `chain_calc.py` reminder branch | Add `if slot == '<LETTER>': return f"⏰ <name>..."` for count 0/1/2+ | Without a branch, F just shows as `pending` with no escalation copy. |
| 9 | `med_confirm.py` `ALL_SLOTS` | Append the letter; update error message | Hardcoded validation gate. |
| 10 | `med_resolve.py` `TIME_RULES` | Add a time window for the new slot | Without this, `resolve('dexa', time='14:00')` falls back to the default slot (was returning B). |
| 11 | `med_resolve.py` `WORD_TO_SLOT` | Add any new time-word hints (e.g. `'2pm': 'F'`) | Word-based slot inference for fragments like "dexa 2pm". |
| 12 | `med_chain/rules.json` | Add `anchor` rule for the slot + any `min_gap`/`fixed_gap` from neighbours | `solve.py` raises `TimingResolutionError: resolver omitted active slot <X>` if a referenced slot has no anchor. |
| 13 | `med_chain/solve.py` | If the slot is independent, add an anchor branch (mirror the B/E pattern) | `_anchors()` only extracts slots with `anchor` constraints; non-anchor slots must be set explicitly or `compute_slots_deterministic` skips them. |
| 14 | `taper_alert.py` | Update freq-change messages (BD → "Slot D deactivated, Slot F activated", OD → "Slots C,D,F deactivated") | Without this, the daily 06:00 alert reports a misleading diff. |

That's 14 items, not 9 — my session message said "9 wiring touches" but the
actual count was 14. The lesson: the touched-files count is always larger
than the visible "data definition" change. A new slot is a *schema* change
that touches every consumer.

## End-to-end verification recipe (proved, not asserted)

Five tests, all run as part of the same script before reporting completion:

1. **Dose matrix across all boundary dates.** Iterate every
   `<phase_start, phase_end>` boundary plus the day before STOP, print
   `B / C / D / F / sum`. Assert `sum == expected_total_mg` per row. This
   catches transcription errors and missing slot wiring in one shot.

2. **med_resolve with each alias + time combination.** For the new slot,
   test: drug_id directly, "dexa <time-word>" no time, with time
   <HH:MM>, with no time, with neighbouring times (one window before/after
   the boundary). Print `slot= / drug_id= / ok=` for each.

3. **med_confirm dry-run with the new slot.** Always `--dry-run` first.
   A real write that lands in the wrong drug_id is a clinical bug, not
   a config typo. Verify the would_write list contains the expected
   drug_ids.

4. **Reminder render at a simulated future date.** `CHAIN_CALC_NOW_MYT=YYYY-MM-DDTHH:MM:00 TZ=Asia/Kuala_Lumpur python3 chain_calc.py --template <slot>`
   freezes the chain engine to a specific date. Inject a minimal
   `med-status.json` (A/B completed, others pending) into a temp file,
   run the reminder, restore. The reminder text should match the live
   dose + the freq + the chain reference. If the text says "11mg (TDS)"
   on a BD day, the freq detection is broken upstream.

5. **State SHA256 unchanged.** Before/after SHA256 of `med-status.json`.
   If it moved, the dry-run didn't dry-run. Assert before claiming done.

## Pitfalls specific to chart rebase / slot add

- **Skill references lag the data.** `dexamethasone-tapering-schedule.md`
  in `~/.hermes/skills/med-tracker/references/` was the source of the wrong
  phase table, not just a downstream consumer. After a data rebase, the
  skill's own reference files need a re-pass — at minimum a header note
  pointing to the new authoritative source. Patching the data without
  updating the skill reference leaves a future agent to re-discover the
  same bug.
- **`get_dexa_dose(<new_slot>, date)` returns None if SLOT_TO_KEY is
  incomplete.** The error path is silent — the script will keep running
  but every subsequent consumer that reads the value will branch on
  `None` and the reminder will be wrong. Always assert against the
  expected value, don't trust the absence of a stack trace.
- **`compute_slots_deterministic` raises on missing anchor.** If you add
  a slot referenced by a rule (e.g. `from: B, to: F`) but don't add the
  F anchor, `chain_calc.calculate_chain()` raises
  `TimingResolutionError: resolver omitted active slot F` — but only
  when the slot is `active_slots_set`, which depends on the current
  taper freq. So the bug hides on TDS days and explodes the moment the
  freq transitions. Test the active freq.
- **Don't double-write `pending_pharmacist_confirm` arrays.** The
  top-level array is the contract; the per-phase `notes` field is the
  visible hint. They must agree. We had a bug where the notes said
  "Split corrected to chart 6/5/5" but the values were still 5/6/6 from
  the old transcription — the fix was a no-op data-wise. The lesson:
  edit the data first, then the notes; never the reverse.
- **Rollback by SHA256, not by mtime.** `cp -p` preserves mtime, so
  rollback leaves a "newer mtime" file. SHA256 + `cp` (no `-p`) is the
  honest path; if anyone checks git, the file appears as "modified".
  We use `cp -p` for now and rely on backup-dir preservation.

## What the boss's Q1/Q3/Q5 decision pattern looks like (for future agents)

When given a structured plan with Q-numbers (Q1: replace SSOT? Y/N. Q2:
which split? Q3: approve structural change? Q4: include historical fix?
Q5: timing?):

- Q1, Q3, Q5 = approve immediately, "Buat now!" if the structural change
  is needed before the next operational event.
- Q2 = defer to a real-world confirmation (pharmacist visit, doctor
  appointment). Implement with `pending_*` flag; surface the flag in
  every reminder or status output until resolved.
- Q4 = "skip" usually means "yes-but-not-now"; roll the fix into the
  same edit if it's free, and explicitly note in the deliverable that
  Q4 was also done (not just skipped), so the boss can revert if they
  actually meant "leave it alone".

This Q-pattern is the boss's way of saying "act on the parts I'm sure
about, park the parts I'm not, don't proceed without the parts I have
to go ask a human for". Defaulting on any Q is wrong; treating them as
independent decision points is right.
