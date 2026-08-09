# Skipped-Drug Reminder Pitfall (chain_calc.py)

## Symptom (2026-07-30, 21:57 MYT)

User marked CC as skipped for the day. Data was logged CORRECTLY —
`med-status.json` has `status: 'skipped'` for the CC slot drugs. Yet the
Domino Chain reminder engine kept firing: **7 reminders for Slot C that day,
last at 22:15** (e.g. "Calcium Carbonate 500mg dan Calcitriol 1 tablet belum
ambil lagi. Dah pukul 22:15").

## Root cause — two compounding bugs in `~/.hermes/scripts/chain_calc.py`

1. **`get_pending_required_drugs()` doesn't exclude skipped drugs.**
   It computes `pending = required - taken_only`. A drug with
   `status='skipped'` is neither taken nor excluded, so it shows up as
   "pending" — the engine believes calcium + calcitriol are still waiting.
2. **No `is_effectively_done()` concept.** The reminder loop sees
   `overall == 'partial'` (some drugs taken, some not) and fires a nudge.
   There is no rule saying "all remaining required drugs are intentionally
   skipped → this slot is effectively complete."

## Fix plan (designed 2026-07-30, NOT yet implemented — user approval pending)

1. `get_pending_required_drugs()` — exclude drugs with `status='skipped'`
   from the pending set.
2. In `calculate_chain()` — after computing `overall`, if `partial` but all
   remaining drugs are skipped, treat as done (confirmed + completed).
3. `chain_monitor.sh` housekeeping — also reset reminder counts for
   effectively-done slots.

## Verification state

- Live `chain_calc.py` (Jul 19 17:14) has NO `skipped` handling — grep for
  "skipped" returns nothing.
- Rechecked 2026-07-31 11:25 MYT: current `med-status.json` still records Slot C
  with calcium + calcitriol `status: 'skipped'`, dexamethasone taken, and
  `overall: 'partial'`. Current `is_confirmed()` still returns true only for
  `overall == 'completed'`; this is direct evidence the semantic gap remains.
- The live tree still has no `med_safety_gate.py`; that candidate exists only in
  the separate `feat/med-safety-gate-phase1` worktree. Do not treat candidate
  safety code as deployed or as a fix for skipped-slot reminder semantics.
- Fix was proposed to the user ("Saya boleh implement sekarang. Approve?")
  and the session ended before approval. Do NOT assume it's applied.
