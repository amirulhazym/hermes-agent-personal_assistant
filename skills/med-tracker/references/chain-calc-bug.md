# Chain Calc Bug: Slot Fires at Wall-Clock Default Instead of Chain Time

## Bug ID
med-001 (2026-07-04)

## Symptoms
- C slot reminder fires at 12:00 when chain-calculated ready time is 13:00
- Repeated across days when morning meds shift
- User sees 9+ reminders for a slot that isn't due yet
- Chain state shows correct ready_time (e.g. 13:00) but reminder still fires

## Root Cause
`chain_calc.py` → `calculate_chain()` → partial slot decision logic at approx lines 366-372

```python
if st['overall'] == 'partial':
    if st['ready_time'] and now_min >= time_str_to_minutes(st['ready_time']):
        should_fire = True
        fire_reason = slot
        break
    else:
        # BUG: Falls here even when ready_time IS set but now < ready_time
        default = get_default_time(slot, schedule)
        if default and now_min >= time_str_to_minutes(default):
            should_fire = True
            fire_reason = slot
            break
```

The `else` branch catches TWO cases:
1. `ready_time is None` (genuinely unknown) → should fallback to default ✓
2. `ready_time` IS set, but `now < ready_time` (too early) → should NOT fire ✗

Case 2 is the bug. The `else` unconditionally uses default time for firing.

## Live Trace (2026-07-04 12:17 MYT)
```
now=12:17, ready_time=13:00, now >= ready? FALSE
→ Falls to else branch
→ default=get_default_time('C')='12:00'
→ now >= 12:00? TRUE
→ FIRES ← BUG
Chain was correct: C ~13:00 (B was at 09:00, +4h gap)
```

## Fix
Change line 366:
```python
# OLD:
else:
# NEW:
elif st['ready_time'] is None:
```

This ensures only genuinely unknown ready_times (no prior slot data) fall back to wall-clock defaults. When ready_time IS calculated and says "too early," the system stays silent.

## Secondary Issue: Reminder Template Counts Optional Drugs as Required
The `generate_reminder()` function at the partial-slot branch uses:
- `taken_count = len(get_taken_drugs(slot))` — counts ALL taken, including optional (B-Complex)
- `total_count = len(get_required_drug_ids(slot, schedule))` — only required

Result: C slot shows "Baru 3/3 je" (calcium + calcitriol + b_complex = 3) when actual required progress is 2/3 (dexamethasone_2 still pending).

Fix: Filter taken drugs to required_ids before counting; or change wording to "3 ubat logged" instead of fraction format.

## Lesson
Never trust `else:` branches in state machine logic that mix chain-calculated times with default fallback times. Always distinguish between "ready_time is None" (unknown) and "ready_time is set but too early" (known-future).
