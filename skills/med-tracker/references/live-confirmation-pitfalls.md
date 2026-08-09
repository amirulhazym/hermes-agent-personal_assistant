# Live Confirmation Pitfalls (CLI + Safety Gate)

Session-derived pitfalls for med_confirm.py / med_resolve.py / med_safety_gate.py flows. Verified live  2026-08-01 (sections 1–4), 2026-08-07 (section 5).

## 1. Drug-level confirmation REJECTED without --source-text

`med_confirm.py <SLOT> <drug_id> --at HH:MM` (no source text) returns:

```
{"ok": false, "error": "REJECTED: source-backed CONFIRM_INTAKE required"}
```

Correct invocation (source text must mention the drug — the tool checks mentions):

```
python3 med_confirm.py D dexamethasone_3 --at 17:10 --source-text "Dexa petang dah makan 510pm"
```

Always dry-run first (`--dry-run`), then real write. Auto-backups to .bak1/.bak2/.bak3 on write.

## 2. med_resolve.py does NOT know "cc"

```
python3 med_resolve.py cc  →  UNKNOWN (suggestions list calcium / calcitriol separately)
```

CC is compound user shorthand = Calcium Carbonate + Calcitriol together. First inspect the LIVE `med_confirm.py`; do not assume this documented path is deployed.

When `--compound` is implemented live, preferred path:
```bash
python3 med_confirm.py C --compound cc --at HH:MM --source-text "user's exact words"
```
Source text must contain completion wording and `cc` (or both component names). Dry-run first, then read back status, chain, and transaction journal.

If the live script lacks `--compound`, do not use slot-level confirmation and do not fabricate source text. Isolate-test a candidate implementation before using it against live state; compare live-state hashes after dry-run. See `references/compound-runtime-drift-20260804.md`. Never interpret CC as B-Complex.

Note: passing bare fragment `C cc` (not `--compound`) is not a valid compound invocation.

## 3. "Dexa" is ambiguous — 3 matches

```
dexamethasone_1 → Slot B (pagi, 5mg)
dexamethasone_2 → Slot C (tengah hari, 5mg)
dexamethasone_3 → Slot D (petang, 4mg)
```

Disambiguate by time context in the user's message ("petang" → Slot D / dexamethasone_3). Cross-check the expected dose against the current taper phase in dexa_taper.json (e.g. phase 7 = morning 4 / midday 4 / afternoon 4 mg).

## 4. Stale OPEN holds in med-holds.json

The safety gate persists a HOLD when it cannot resolve a drug name (e.g. "deca" → rule MEDICATION_PARSE_INCOMPLETE). A hold can remain `status: OPEN, resolution: null` even AFTER the underlying confirmation was written to med-status.json — med_confirm.py and the gate are independent write paths.

Before proposing hold cleanup: check med-status.json for that slot/date. If the confirmation exists, the hold is stale/duplicate and can be closed (only with user approval — never auto-close).

## 5. Slot-level confirm auto-marks ALL drugs — including conditional (b_complex)

`python3 med_confirm.py C` (bare slot confirm) marks **every** drug in the slot as taken — `confirm_slot()` iterates all drug_ids and does NOT honor the schedule's `condition` field. On a non-Wed/Sat day this wrongly records `b_complex` as taken. Verified live 2026-08-07 (Friday): user confirmed slot C (dexa #2 + both CC) ~13:14; bare `med_confirm.py C` wrote all 4 drugs incl. b_complex at 13:27.

Correction sequence (verified working):
```bash
python3 med_confirm.py --reset C b_complex   # removes wrongly-marked conditional drug
python3 med_confirm.py --update C 13:14      # rewrites ALL taken drugs' times in slot
python3 med_confirm.py --check C             # verify final state
```

Rules:
- **Before any bare slot confirm, check weekday against conditional drugs** in med-schedule.json (`b_complex` = "Rabu & Sabtu SAHAJA"). Friday/Sun/Mon/Tue/Thu → reset b_complex after, or use drug-level confirm with --source-text instead.
- `--update <slot> HH:MM` applies the time to all taken drugs in that slot — use it whenever the logged time differs from the user's stated time (bare confirm defaults to now(), not the user's reported intake time).
- `--reset <slot> <drug_id>` removes a single drug from today's entry and recomputes `overall`.
- Supply: confirm_slot also decrements every drug in the slot. b_complex had `current: null` so decrement was a no-op here, but a tracked conditional drug could be wrongly decremented — check med-supply.json after reset.
- `--source-text` gate does NOT prevent this: it only checks the user's words mention ≥1 slot drug, it does not check day-of-week conditions. Always verify final state with `--check`.

## 6. Timing-deviation questions ("Okay ke?" — e.g. CC with dinner)

Evidence pattern before answering:

1. `med-interactions.json` → drug `safe_with` list + `timing_notes` (calcium: "Take WITH lunch..."; calcitriol: "Take WITH calcium at lunch").
2. Pharmacokinetic reasoning: calcium carbonate needs gastric acid (better WITH food); calcitriol is fat-soluble (better with food). Taking CC with dinner is fine — arguably better than empty stomach.
3. No `unsafe_with` entries → zero interaction risk, including vs Slot E levetiracetam malam.
4. Distinguish one-off delay (acceptable; note routine inconsistency) from recurring change (requires regimen update approval per med safety policy — collect changes one question at a time, show system impact).
