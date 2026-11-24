# Slot C → berbuka reminder (2026-11-20) — FINAL owner-locked spec

Context: slot C reminder had been firing at `B + 4h` as a "lunch" / Dexa-#2 message, even though
Dexa midday is deactivated in the OD phase and C holds only Calcium Carbonate + Calcitriol. CC needs food,
so the correct fire time is the IF break.

## Correction rounds (chronological — each one is a spec decision, not a preference)

1. **Invented hour rejected.** I proposed `suppress_until 19:00` for slot C — no data behind it.
   Owner: "Apalancau supress_until 19:00 pulak barua??? … Bila masa aku berbuka jam 19:00?"
   → convert the CC reminder into a berbuka alert based on real fasting data.
2. **First implementation was still wrong.** Trigger at median (14:16) + generic renderer text; the
   14:00 cron tick delivered "belum due lagi — boleh ambil lepas 14:16… 🌙 Dah 18.4j puasa" while he
   was already past 18h. Owner: "Apabenda reminder kau macam ni??" → alert must say: already fasted
   ~17h since last makan <time> semalam, ready berbuka, ready CC, key in/log Window 1 food.
   → trigger moved to the **17h floor**; pre-floor silence gate added.
3. **Header rejected.** "TITLE TU KENA TUKAR JUGAK!! SHOULD BE: WAKTU BERBUKA IF & UBAT CC".
4. **Header shortened.** "instead of 'ubat cc' just tulis as 'CC'" → final header
   `‼️ Waktu Berbuka IF & CC ‼️`. Owner confirmed: reminder repeats while CC untaken; only
   template/text changed, purpose (log CC) identical.

Also found: `chain-state.json` carries `"suppressed_slots": {"C": true}` and **no script reads it** —
`grep -rn suppressed_slots ~/.hermes/scripts/` → 0 hits. Dead field; never cite it as a suppression
mechanism.

## Real data (source: ~/.hermes/diet-log.json, field `fasting_hours`)

```text
n = 26   min 17.03h   median 18.60h   mean 18.56h   max 20.05h   stdev 0.91
anchor 2026-11-19 19:40  ->  17h floor 12:41 (TRIGGER)   median 14:16 (context only)
actual buka 13-19 Nov: 14:00, 14:20, 14:55, 15:00, 15:10, 15:13
```

## Files as they now stand

1. **`~/.hermes/scripts/if_berbuka.py` (stdlib only)**
   - `fasting_stats()` — min/median/mean/max from `fasting_hours`, 10 ≤ x ≤ 30 sanity filter,
     labelled FALLBACK if absent.
   - `latest_basis()` — newest `last_intake_time` strictly before today; regex `(\d{1,2}):(\d{2})`
     on the prose field; keeps the raw string.
   - `berbuka_plan()` — `target` = anchor + **min** (17h floor); `median_target` separate;
     `fast_now_h`; `basis_stale` when anchor date ≠ yesterday.
   - `berbuka_target_hhmm()` — `None` when `basis_stale` (chain falls back to B+4h instead of
     nagging from an old meal).
   - CLI: `--json` (plan, no side effects), `--check` (prints only after target).
   - Bug hit while writing it: `datetime.now(MYT)` with `MYT = timedelta(hours=8)` → TypeError.
     Use `timezone(timedelta(hours=8))`.

2. **`chain_calc.py` — `calculate_ready_time()`**: slot C with `get_dexa_dose('C') == 0` →
   `berbuka_target_hhmm()`; try/except → fall through to `resolved_times[slot]`.
   (`chain_calc.generate_reminder()` also has a berbuka branch, but the delivery path is
   `chain_llm.render_reminder()`.)

3. **`chain_llm.py`**
   - `render_reminder()`: `berbuka_mode` when C dose is 0 → header
     `‼️ Waktu Berbuka IF & CC ‼️` (exact), body = "Hai boss, dah ~X.Xj puasa since last makan
     semalam HH:MM. Ready berbuka IF dan ready untuk <CC drugs> lepas makan. Lepas tu key in/log
     apa yang kau makan untuk Window 1." Tiers: count ≤1 first wording; count 2 adds "Dah pukul
     HH:MM — key in/log Window 1 sekali ya"; count 3+ "Reminder ke-N … Kalau dah berbuka, key in/log
     Window 1." Stale basis → "waktu berbuka IF — ready untuk" without fake hour counts.
   - `validate_reminder_text()` extended: accepts the exact berbuka header line OR the standard
     `‼️ Waktu Ubat (…) ‼️`; still 3 non-empty lines, body must start with the salutation.
   - `_berbuka_ready_gate(slot, slot_meta, chain)` in `main()`: for C-with-zero-Dexa, silent
     (exit 0) until `now >= ready_time` — the chain's −15min fire window must not produce a
     pre-17h alert. Other slots unaffected.

## Verified final output (live, 14:32)

```text
‼️ Waktu Berbuka IF & CC ‼️

Hai boss, dah ~18.9j puasa since last makan semalam 19:40. Ready berbuka IF dan ready untuk Calcium Carbonate 500mg dan Calcitriol 1 tablet lepas makan. Reminder ke-3, dah pukul 14:32. Kalau dah berbuka, key in/log Window 1.

[C:3-261120]
```

Chain display: `A ✅ 09:30 → B ✅ 10:28 → C ~12:41 → F — → D — → E ~20:00`.
Validator True on all tiers; slot E still `‼️ Waktu Ubat (Malam) ‼️` (scoped change).

## Safe test recipes

```bash
python3 if_berbuka.py --json                     # stats + today's plan (target = 17h floor)
python3 chain_calc.py --display                  # chain string only
python3 -c "import chain_calc as cc, chain_llm as l; ch=cc.calculate_chain(); \
  ch['now']='12:41'; ch['reminder_counts']={'C':0}; \
  t=l.render_reminder('C', ch, ch['slots']['C'], date_code='201126'); \
  print(l.validate_reminder_text(t,'C',ch['slots']['C']['pending_drugs'])); print(t)"
```

Never `bash chain_monitor.sh` — it writes reminder counts into live state. `python3 chain_llm.py C`
is safe (render only) but bypasses `should_fire`.

## 2026-11-23 correction (owner-approved): constants + single merged alert

**Incident:** 13:45 alert said "dah ~15.8j puasa … Ready berbuka IF dan ready untuk CC" —
below the owner's own 16h minimum. Owner: "Wtf, how this can be approved?"

**Root cause (verified, not inferred):** `berbuka_plan()` used `stats["min_h"]` =
`min(fasting_hours)` → one sub-floor day (2026-11-22, 15.67h, its own log note says
"BAWAH floor 17j (rekod terpendek dalam 28 hari)") became the floor for every later day:
target 13:40 = 22:00 + 15.67h. Nothing human-approved it; the floor is data-derived.

**Fixed design (owner lock):**
- `MIN_FLOOR_H = 16.0` (hard floor, breach line — never a trigger), `TARGET_H = 17.0`
  (optimum berbuka), `HEADS_UP_LEAD_H = 2.0`. No threshold derived from data any more.
- ONE merged alert, not two. Fire time = `berbuka_target_hhmm()` = anchor + 15h
  (2h before 17h optimum). Anchor 22:00 → fire 13:00, berbuka 15:00.
- Wording is split by clock, not be two reminders: before `target` → heads-up only
  ("Berbuka optimum 17j pukul HH:MM — lagi X.Xj", CC-after-food, log Window 1);
  at/after `target` → existing ready text. Never "ready" before 17h.
- `_berbuka_ready_gate` now gates on the heads-up hour (12:30–12:59 ticks stay silent,
  no count increment since monitor only counts non-empty stdout).
- Sub-floor days stay in the log untouched (data integrity); they just no longer set policy.

**Verified live (2026-11-23 14:22, anchor 22:00):** display `C ~13:00`, validator True on
heads-up and ready renders, gate False at 12:30/12:59, True at 13:00.

## Open follow-ups

- `suppressed_slots` in `chain-state.json` is unreferenced; decide with the owner whether to delete it.
- If the fasting distribution drifts, the floor moves with the data — quote n and min when explaining
  a change.
