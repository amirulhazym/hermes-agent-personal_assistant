# Live Confirmation Pitfalls (CLI + Safety Gate)

Session-derived pitfalls for med_confirm.py / med_resolve.py / med_safety_gate.py flows. Verified live  2026-08-01 (sections 1–4), 2026-08-07 (section 5), 2026-08-11 (sections 7–9).

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

## 7. Session-resume: confirmation may ALREADY be logged by the hook (double-log guard)

When the previous session expired after the user's confirmation message (session DB shows only the user message, no assistant reply), do NOT assume the confirmation was missed. The gateway auto-confirm hook writes med-status.json independently.

Verified 2026-08-11: user msg "Dah makan akurit and pyridoxine jam 648am tadi" at 06:57; med-status.json ALREADY had Slot A 2026-08-11 `akurit_2` + `pyridoxine` @ 06:48 (mtime 06:59:26, hook-logged) with zero assistant writes.

Guard: before re-confirming/re-writing, read med-status.json for that slot/date. If the entry exists with matching drug_ids + time → already logged; acknowledge and read back. Do NOT double-write.

## 8. Transient JSONDecodeError reading med-status.json = concurrent hook write (retry, don't repair)

Reading med-status.json while the auto-confirm hook is mid-write can throw `JSONDecodeError: Expecting property name enclosed in double quotes...` (verified 2026-08-11 during a read that raced the 06:59 hook write; file size changed 54055→54340 between reads and the retry parsed cleanly).

Pattern:
1. On JSONDecodeError, check mtime/size (`ls -la --time-style=full-iso med-status.json`).
2. Re-read after the write completes — usually parses fine on retry.
4. NEVER "repair" or restore from .bak on a transient read failure — that is a mid-write snapshot, not corruption. Same discipline as the atomic-write coverage in test_cc_atomic.py.

## 9. Partial slot confirm (one drug of a multi-drug slot) — read-back remaining drugs

When the user confirms only ONE drug in a multi-drug slot (e.g. "Dah makan dexa jam 1.49pm" for slot C, which also contains calcium + calcitriol [+ conditional b_complex]), `med_confirm.py C dexa --at 13:49 --source-text "Dah makan dexa jam 1.49pm"` writes only `dexamethasone_2` and returns `overall: "partial"`.

Pattern (verified 2026-08-11, slot C):
1. Confirm drug-level (NOT bare slot confirm — bare would auto-mark every drug incl. conditional b_complex, see section 5).
2. After the write, read `med-schedule.json` slot drugs to enumerate what remains REQUIRED.
3. Surface remaining required drugs to the user and ask (e.g. "Slot C masih ada Calcium Carbonate + Calcitriol — dah makan ke belum?"). Do NOT auto-mark the remaining drugs just because the user mentioned dexa.
4. The schedule `window` field (slot C "11:30–12:30") may differ from the time the user actually took the drug (1:49pm). med_resolve.py `--time` routing is the authoritative in-window check — if it accepted the time for the slot, log it without holding; only hold if resolve itself flags out-of-window (per MED GUARD). Note the window-vs-actual gap only if relevant; late-lunch timing is normal for this user.
