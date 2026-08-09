# Chain Calc Bug Traces (Verified 2026-07-04)

Live bug traces for `chain_calc.py`. Each trace shows actual CLI output proving the bug existed, the fix, and the verified post-fix state.

## Bug #1: Partial slot fires using wall-clock default instead of chain time

**Live trace — broken state, 12:17 MYT:**

```
now: 12:17
slots:
  A: confirmed, actual=07:33, ready=07:33, status=done
  B: confirmed, actual=09:00, ready=09:00, status=done
  C: partial (calcium/calcitriol at 09:00, Dexa #2 pending)
     ready=13:00, status=partial
  D: pending, ready=13:00 (WRONG, should be 16:35)
     status=waiting
  E: pending, ready=21:00, status=waiting

next_slot: C
should_fire: TRUE  ← BUG: 12:17 < 13:00 (ready), but C fires anyway
reason: C
```

**Why it fired at 12:17 (43 min too early):**

The partial-slot branch in `calculate_chain()`:
```python
if st['ready_time'] and now_min >= time_str_to_minutes(st['ready_time']):
    should_fire = True
    fire_reason = slot
    break
else:                                # ← this branch taken
    # No ready time yet but partial — still fire if past default time
    default = get_default_time(slot, schedule)   # = "12:00"
    if default and now_min >= time_str_to_minutes(default):
        should_fire = True
        fire_reason = slot
        break
```

`now=12:17` is NOT >= `ready_time=13:00`, so falls to `else`. Then `12:17 >= 12:00` (wall-clock default) → fires. The chain knew the right time; the code ignored it.

**Fix:**
```python
elif st['ready_time'] is None:    # only fall back when truly unknown
```

**Post-fix verification — 13:15 MYT:**

```
now: 13:15
slots:
  A: confirmed, actual=07:33, status=done
  B: confirmed, actual=09:00, status=done
  C: confirmed, actual=12:35, status=done
  D: pending, ready=16:35, status=waiting
  E: pending, ready=21:00, status=waiting

next_slot: D
should_fire: FALSE  ← correct, D not until 16:35
chain_str: A ✅ 07:33 → B ✅ 09:00 → C ✅ 12:35 → D ~16:35 → E ~21:00
```

## Bug #3: `get_actual_time()` returns earliest drug time, breaks domino gap

**Live trace — broken state, 12:17 MYT:**

```
D ready_time: 13:00  ← WRONG
```

**Why:** C slot had drugs at different times:
- calcium, calcitriol: 09:00 (taken during breakfast shift)
- dexamethasone_2: not yet taken (now 12:17)

`get_actual_time()` returned `sorted(times)[0]` = `"09:00"` (calcium). D's gap calc: `09:00 + 4h = 13:00`. But D's 4h gap should be from Dexa #2 (the actual steroid dose), not from calcium. After Dexa #2 is taken at 12:35, D should be ready at 16:35, not 13:00.

**Fix:** `sorted(times)[-1]` (latest, not earliest)

**Post-fix verification — 13:15 MYT:**

```
D ready_time: 16:35  ← correct (Dexa #2 at 12:35 + 4h)
E ready_time: 21:00  ← correct (B at 09:00 + 12h)
```

## Why the Two Bugs Compound

When Bug #1 fires C prematurely (at 12:00 instead of 13:00), the user rushes to take Dexa #2. Then Bug #3 miscalculates D's ready time based on calcium's time (09:00), making D ready at 13:00 (which is way too early because Dexa #2 is the actual reference point for the 4h gap).

**Combined effect:** Reminder fires for C at 12:00 → user takes Dexa #2 around 12:35 → reminder fires for D at 13:00 because of Bug #3. D reminder says "C tadi 09:00" (calcium), making it look like a 4h gap is satisfied. User is now being told to take D 1.5h after Dexa #2. The 4h steroid spacing is broken.

## How to Verify the Fixes Are Holding

Run this any time after edits to `chain_calc.py`:

```bash
cd /home/ubuntu && python3 -c "
import json, sys
sys.path.insert(0, '.hermes/scripts')
exec(open('.hermes/scripts/chain_calc.py').read())
c = calculate_chain()
print(f'now={c[\"now\"]}, should_fire={c[\"reminder\"][\"should_fire\"]}')
for s in ['A','B','C','D','E']:
    st = c['slots'][s]
    print(f'{s}: ready={st[\"ready_time\"]}, actual={st[\"actual_time\"]}, status={st[\"status\"]}')
print(c['chain_str'])
"
```

Expected: `should_fire=False` if no slot is currently due, `chain_str` times match the user's actual intake pattern with 4h/12h gaps correctly applied from the latest drug times.

## Bug #6: `get_actual_time()` Uses Latest Drug Time Instead of Dexa Priority Drug Time (2026-07-07)

**Live trace — broken state, 13:00 MYT post-Dexa #2 + Calcium/Calcitriol:**

```
User took: Dexa #2 at 12:15, Calcium + Calcitriol at 13:00

BEFORE FIX (get_actual_time returns latest drug time = 13:00):
A ✅ 06:15 → B ✅ 08:00 → C ✅ 13:00 → D ~17:00 → E ~20:00

AFTER FIX (get_actual_time returns Dexa #2 time = 12:15):
A ✅ 06:15 → B ✅ 08:00 → C ✅ 12:15 → D ~16:15 → E ~20:00
```

**Why it was wrong:** `get_actual_time()` returned the LATEST taken time among ALL drugs in the slot (13:00 from Calcium), ignoring that the gap B→C→D is specifically for **Dexamethasone** spacing. Chain said "C done at 13:00" → D ready at 17:00 (13:00 + 4h). But the 4h gap is from Dexa, not Calcium.

**User's reaction:** "ANJING BETUL KAU NI" — extreme frustration. User explicitly stated: "Our main priority is Dexa, Akurit-4, and Letram. Any gaps or timeframe must prioritize this, bukan CC."

**Code path before fix:**
```python
# get_actual_time() for drug-level format:
if isinstance(entry, dict) and 'drugs' in entry:
    times = [info.get('time') for did, info in entry['drugs'].items()
             if info.get('status') == 'taken' and info.get('time')]
    if times:
        return sorted(times)[-1]  # ← LATEST drug time, not Dexa time
```

**Fix — Dexa-priority in get_actual_time():**
```python
def get_actual_time(slot: str, drug_id: str | None = None) -> str | None:
    # ... legacy handling ...
    if isinstance(entry, dict) and 'drugs' in entry:
        # If specific drug_id requested
        if drug_id:
            for did, info in entry['drugs'].items():
                if did == drug_id and info.get('status') == 'taken' and info.get('time'):
                    return info['time']
        # Priority: Dexa time for slots that have Dexamethasone
        dexa_ids = ['dexamethasone_1', 'dexamethasone_2', 'dexamethasone_3']
        dexa_times = [
            info['time'] for did, info in entry['drugs'].items()
            if did in dexa_ids and info.get('status') == 'taken' and info.get('time')
        ]
        if dexa_times:
            return sorted(dexa_times)[-1]
        # Fallback: latest taken time among all drugs
        times = [
            info['time'] for did, info in entry['drugs'].items()
            if info.get('status') == 'taken' and info.get('time')
        ]
        if times:
            return sorted(times)[-1]
    return None
```

**Relationship to Bug #3:** Bug #3 fixed `sorted(times)[0]` → `sorted(times)[-1]` (earliest to latest). Bug #6 goes further: even `[-1]` is wrong when non-Dexa drugs are taken after Dexa. The chain must use Dexa-specific time, not "latest of everything".

**Design principle:** The chain calculation system has two distinct use cases for "actual time":
- **Display purposes** (chain_str): Show the overall slot completion time (could be Dexa time or latest — user wants Dexa-priority here too per their rage)
- **Gap calculation** (D ready_time): MUST use Dexa-specific time for B→C and C→D gaps

**Verification recipe:**
```bash
cd /home/ubuntu
python3 .hermes/scripts/chain_calc.py --display
# Expected: A ✅ 06:15 → B ✅ 08:00 → C ✅ 12:15 → D ~16:15 → E ~20:00
# NOT: C ✅ 13:00 → D ~17:00
```

**Edge case — Slot B Dexa vs Levetiracetam:** Slot B has both Dexa #1 and Levetiracetam (taken together). With Dexa-priority, B's time = Dexa #1 time which ≈ Levetiracetam time. This is correct for both C's gap (B→C = 4h from Dexa) and E's gap (B→E = 12h from Letram) since the times are identical in practice.
