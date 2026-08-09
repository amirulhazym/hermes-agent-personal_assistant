# Cooldown & Reminder Bugs — 2026-07-17 Fix

**Root cause of reminder spam:** User got 5 reminders for CC (Calcium Carbonate + Calcitriol) in ~3h (13:15→14:15→14:45→15:15) after taking Dexa at 12:20. 2 bugs + 1 design flaw.

## Bug 1: Boundary bug — `mins_since < interval` fires one tick early

**File:** `~/.hermes/scripts/chain_calc.py`, line 131
**Function:** `is_within_cooldown()`
**Old:** `return mins_since < interval`
**New:** `return mins_since <= interval`

**Why it matters:** With a 30-min cooldown and cron firing at :00/:15/:30/:45, a reminder
at 14:15 sets last_time=14:15. The 14:45 tick computes `14:45 - 14:15 = 30 min`.
`30 < 30 = False` means "not in cooldown" → fires one tick early at every boundary.

**Impact:** With count=2 and 60-min cooldown, same issue fires at :15 boundary.
With count=3+ and 30-min cooldown, fires 4 extra ticks per hour.

**Test:**
```
count=2, last=13:15, now=14:15 (exactly 60 min)
Old: 60 < 60 = False → FIRES (wrong)
New: 60 <= 60 = True → SKIP (correct)
```

## Bug 2: Partial-slot cooldown treats supplements like critical meds

**Files:** `~/.hermes/scripts/chain_calc.py`, functions `get_cooldown_interval()` + `is_within_cooldown()`

**Problem:** When slot C is partial (Dexa ✅, CC pending), remaining drugs are CC
(calcium supplement, taken with lunch — not time-critical). But the system escalates
reminders: after 3 reminders, cooldown drops from 60→30 min.

For a supplement the user is deliberately delaying (waiting for food), more aggressive
reminders are counterproductive.

**Fix:** Added `is_partial` flag to both functions. When `is_partial=True`:
- Flat 120-min cooldown regardless of reminder count
- No escalation — user knows the remaining drugs exist
- `get_cooldown_interval(count, is_partial=True)` returns `max(120, normal_interval)`

**Callers updated:** Both `is_within_cooldown()` calls inside the `if st['overall'] == 'partial':` block
in `--next` now pass `is_partial=True`.

**Test:**
```
Partial slot, count=3: old=30min, new=120min
At exactly 120 min boundary: within_cooldown=True (SKIP, was False before Fix 1)
At 121 min: within_cooldown=False (fire)
```

## Bug 3: Accusatory reminder tone for partial slots

**File:** `~/.hermes/scripts/chain_calc.py`, `generate_reminder()` function, partial block (~line 760)

**Old:**
```
⚠️ C belum complete! Calcium Carbonate dan Calcitriol masih belum ambil.
Baru 1/3 je — Dah pukul 13:15.
Reply 'dah makan C calcium carbonate' atau 'dah makan C' terus.
```

**Problem:** "Baru 1/3 je" ignores Dexa ✅ already taken. Tone is accusatory
for a non-critical supplement.

**New:**
```
⚠️ C — Dexamethasone ✅ tinggal Calcium Carbonate dan Calcitriol masih belum ambil.
Dah pukul 13:15. Reply 'dah makan C' terus bila dah ambil.
```

**How it works:** Computes taken drug names by subtracting pending drug_ids from
required drug_ids, then looks up names from med-schedule.json. Builds `{done_str} ✅`.
No more partial/total fraction display.

## What the pattern looks like after all 3 fixes

Before (actual 2026-07-17):
```
12:20  Dexa ✅ (user logs)
13:15  ⚠️ C belum complete! Baru 1/3 je  (55 min later — too fast)
14:15  ⚠️ C belum complete! Baru 1/3 je
14:45  ⚠️ C belum complete! Baru 1/3 je  (boundary bug — shouldn't fire)
15:15  ⚠️ C belum complete! Baru 1/3 je
```
Total: 4 reminders in 3h (worst case: 5 with the LLM one at 12:15)

After (simulated):
```
12:20  Dexa ✅ (user logs)
14:20  ⚠️ C — Dexamethasone ✅ tinggal CC  (120 min grace — respect lunch)
16:20  ⚠️ C — Dexamethasone ✅ tinggal CC  (120 min later)
```
Total: 2 reminders max. Each acknowledges progress. No boundary fires.
