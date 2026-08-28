# Dexa Chart Fix — Session Evidence (2026-08-25)

Incident backing for SKILL.md section "User-Supplied Primary Source vs Stored Transcription".
Status at capture: plan approved, execution NOT started (owner gates below).

## What happened

- 25/8 ~09:39 owner received cron taper alert: "Phase 8 → Phase 9, Current 11mg TDS (4+4+3), New 10mg TDS (4+3+3) start 26/8". He rejected it: the doctor's chart says BD 6+4 from 26/8.
- First agent response DEFENDED the alert by re-running `taper_alert.py --status` and quoting `dexa_taper.json` — circular defense of a bad transcription. Wrong move; the JSON itself was the problem.

## Evidence trail (all verified live this session)

1. `~/.hermes/dexa_taper.json` mtime **2026-07-05** — untouched since the IPR phone transcription; source field "IPR tapering schedule", rule "Taper 1mg every 2 weeks".
2. JSON phantom phases vs chart photo (`~/.hermes/cache/images/img_597c8e513aa5.jpg`, zoom-verified):
   - Phantom A: phase id 9 "10mg TDS 4/3/3, 2026-08-26→09-08" — chart row 9 is **6/4 BD (2X/Sehari)**.
   - Phantom B: phase id 16 "4mg BD 2+2, 02-12→15-12" — chart switches **OD 4mg at 18/11**.
   - Net: JSON taper ends 10/2/2027; chart ends 12/1/2027 → 4-week lag.
   - Historical minor: JSON phase 2 = 5/6/6 (17mg); chart = 6/5/5. Total identical.
3. Chart self-consistency: 18→1mg unbroken −1mg/2weeks, matches its own header rule → chart authoritative. JSON duplicated 10mg for 4 weeks, violating the rule.
4. Owner's prior memory ("dulu dah successfully record 6+4") confirmed via session_search: 28-Jul session tested and displayed "Esok (2026-09-09): 10mg BD (6+4)" — correct data existed in OUTPUTS while the stored phases were wrong-shaped. Persistence ≠ accuracy.

## Correct target state (chart-authoritative)

| # | Start | End | Dose | Freq |
|---|-------|-----|------|------|
| 8 | 12/8 | 25/8 | 4/4/3 (11) | TDS |
| 9 | 26/8 | 8/9 | 6/4 (10) | BD |
| 10 | 9/9 | 22/9 | 5/4 (9) | BD |
| 11 | 23/9 | 6/10 | 4/4 (8) | BD |
| 12 | 7/10 | 20/10 | 4/3 (7) | BD |
| 13 | 21/10 | 3/11 | 6 mg | BD |
| 14 | 4/11 | 17/11 | 5 mg | BD |
| 15 | 18/11 | 1/12 | 4 mg | OD |
| 16 | 2/12 | 15/12 | 3 mg | OD |
| 17 | 16/12 | 29/12 | 2 mg | OD |
| 18 | 30/12 | 12/1/27 | 1 mg | OD |
| 19 | 13/1/27 | — | STOP | |

BD times: 8am + **2pm** · tablet strengths 4mg & 0.5mg · 6mg=1½×4mg · 3mg=6×0.5mg · 2mg=½×4mg · 1mg=2×0.5mg.

## Owner decisions (25/8)

1. Chart authoritative: **Y**
2. Splits for 6mg (21/10) & 5mg (4/11): **HOLD** — confirm with pharmacist early September (owner will supply exact date). Both splits are pharmacologically plausible (one-time 1½×4mg tab vs split 6×0.5mg), which is exactly why he wants human confirmation.
3. Slot F (14:00, dexa-only, active only during BD phases): **Y**
4. Fix historical phase 2 split to 6/5/5: skip for now (zero operational impact).
5. Timing: execute today, before 26/8 morning reminder.

## Execution checklist (pending)

- [ ] Step 0 backup both JSONs → `~/.hermes/backups/dexa-chart-fix-20260825/`
- [ ] Step 1 rebuild `dexa_taper.json`: delete phantom phases, shift BD/OD dates −14d, renumber ids 1–19, version 2.0, source note "IPR chart photo boss-provided 25/8/2026 supersedes 5-Jul transcription"; arithmetic self-test every phase sum==total_mg
- [ ] Step 2 Slot F: `med-schedule.json` new slot 14:00 dexa-only + wire `chain_calc.py` (SLOTS list line ~32, active gating via active_slots_by_freq), `med_confirm.py` (ALL_SLOTS line ~54, confirm path), `dexa_taper_lookup.py` (add "F"→dose_2pm mapping + BD-only gating); auto-deactivate at OD
- [ ] Step 3 resync med-schedule snapshot notes/version + skill refs `dexamethasone-tapering-schedule.md`, `dexa-resolver-and-timing.md`
- [ ] Step 4 verify: `test_dexa_dose_dataflow.py` (check hardcoded fixtures first), dry-run taper_alert/chain_calc renders for 25/8, 26/8, 27/8, 9/9, 18/11, 13/1/27; show raw outputs to owner
- [ ] Step 5 git commit via source clone (separate approval)
- [ ] Later: pharmacist answer → set splits for rows 13–14

## Key code facts (verified)

- Consumers are already dynamic (read JSON live): `dexa_taper_lookup.get_dexa_dose(slot, date_str)`, `chain_calc` delegates, `taper_alert` formats. No consumer code change needed for the phase rebuild itself — only for Slot F.
- BD 2pm gap is REAL: slots A–E only; `chain_calc.py:729` maps dose_2pm into slot C's key but no 14:00 slot exists in med-schedule.json; grep shows no slot_f anywhere.
- Cron "Dexa Taper Alert" fires 06:00 daily (`taper_alert.py`, no_agent) — deadline driver.
- `dexa_taper_lookup` honours CHAIN_CALC_NOW_MYT freeze env — use it for deterministic date-matrix verification.
