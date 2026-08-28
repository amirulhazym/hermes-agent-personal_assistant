# Dexa Dose Dataflow Fix — static schedule dosage vs taper authority (2026-08-12)

Proven: bug reproduced (RED), fixed, deployed live, verified. Reminder output
now matches the taper engine.

## Bug chain (symptom → root cause)

- Symptom: reminders rendered STALE Dexa dosage — 12 Aug showed C=`5mg`,
  D=`4mg` (the old 5/5/4 static snapshot) while `dexa_taper.json` Phase 8
  (start 2026-08-12) resolves to B=4 / C=4 / D=3 (443). The 11 Aug
  "444 — LAST DAY" and 12 Aug "443 — NEW DOSE" alerts were CORRECT (that is
  the separate `taper_alert.py` daily path).
- Root cause: `chain_calc.get_pending_required_drugs()` returns drug dicts
  straight from `med-schedule.json` (static dosage fields), and
  `chain_llm.render_reminder()` prints `drug["dosage"]`. The date-aware
  `get_current_phase()` / `get_dexa_dose_for_slot()` were already correct —
  the reminder path never consulted them.
- `taper_alert.py` (daily 06:00 cron) is a SEPARATE static consumer of
  dexa_taper.json; it feeds alerts, not reminders. Don't confuse the paths.

## Fix pattern (deployed + verified)

In `chain_calc.get_pending_required_drugs(slot)`, after building the pending
list, override Dexa dosage from the taper engine:

```python
pending = [d for d in drugs if d.get('drug_id') in pending_ids]
if slot in ('B', 'C', 'D') and any(
    d.get('drug_id', '').startswith('dexamethasone_') for d in pending
):
    phase = get_current_phase()
    dose_mg = get_dexa_dose_for_slot(slot, phase)
    if dose_mg:
        for d in pending:
            if d.get('drug_id', '').startswith('dexamethasone_'):
                d['dosage'] = f"{dose_mg}mg"
return pending
```

Rules: taper engine is the single dosage authority; only B/C/D Dexa entries
overridden; non-Dexa drugs untouched; `if dose_mg` guard (0 = slot
deactivated for this freq — skip, don't emit 0mg).

## Hermetic test recipe (TDD RED→GREEN, 7 tests)

File: `scripts/test_dexa_dose_dataflow.py` in the source worktree.

Temp home (never touches live state):

```python
tmp = tempfile.mkdtemp(prefix="dexa-dataflow-")
(tmp / ".hermes").mkdir()
shutil.copy(LIVE / "med-schedule.json", tmp / ".hermes" / "med-schedule.json")
shutil.copy(LIVE / "dexa_taper.json",   tmp / ".hermes" / "dexa_taper.json")
with mock.patch.dict(os.environ, {"HOME": str(tmp)}, clear=False):
    for m in [m for m in sys.modules if m == "chain_calc" or m.startswith("chain_calc.")]:
        del sys.modules[m]   # force fresh import so module-level paths pick up tmp HOME
    sys.path.insert(0, str(HERE))
    import chain_calc
```

- Freeze the date: `mock.patch.dict(os.environ,
  {"CHAIN_CALC_NOW_MYT": date + "T12:00:00+08:00"})`.
- Boundary vectors (live taper): 2026-08-11 → C 4mg; 2026-08-12 → B 4 / C 4 /
  D 3; 2026-08-25 → D 3; 2026-08-26 → C 3 / D 3.
- RED first: on unfixed code these fail with `'5mg' != '3mg'` — the failing
  assertion IS the bug proof.
- E2E after fix: frozen `chain_calc.calculate_chain()` +
  `chain_llm.render_reminder(slot, chain, meta)` prints `Dexamethasone 4mg` /
  `3mg` inside the real reminder text.
- Full regression after fix: 52 tests OK (test_cc_atomic 9/9,
  test_safety_gate 18/18, chain suites + the 7 new).

## Pitfalls

- `dexa_taper.json` phases have NO `phase` key (None) — selection is by start
  date inside `get_current_phase()`. Don't index fixtures by phase number.
- Bare `HOME=/tmp` probing (taper file missing) returns phase None → no
  override; always copy schedule+taper fixtures into the temp home.
- Gateway hook imports med scripts at STARTUP — no hot reload; owner-approved
  restart required for hook-path changes. no_agent cron scripts
  (chain_monitor.sh) execute per-tick and pick up file changes without
  restart.
- med-schedule.json dosage fields are documented in-file as a static snapshot;
  actual dose must come from the taper engine.
