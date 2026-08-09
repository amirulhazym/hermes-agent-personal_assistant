# Bug #7: Day-Boundary Reset for Reminder Counts (2026-07-07)

## Symptom

First reminder for slot E @ 20:00 fired with aggressive "dah 4x tanya" template when user had NOT been asked about E even once that day.

## Root Cause

`chain-state.json` had NO day-scoping. Reminder counts persisted forever. The reset logic only cleared counts for slots confirmed today. Since E hadn't been taken yet today, yesterday's count=3 stayed in the state file. At 20:00, the increment fired (3→4), and the template for count=4 said "dah 4x tanya."

```json
// chain-state.json before fix — no "today" field
{
  "reminder_counts": {"E": 3},  // ← from yesterday
  "last_reminder_times": {"E": "21:00"}  // ← from yesterday
}
```

## User Impact

User furious: "Mana datang 4x tanya? Reminder first letram second intake start 8pm... Bila masa lagi 3x tu kau tanya barua????"

Previous session's reminder count was presented as today's aggression level. User blamed system for lying about having asked 4 times.

## Fix Applied

**File:** `~/.hermes/scripts/chain_monitor.sh` (Step 3 Python block)

**Patch (day-boundary check added at top of state processing):**

```python
# Day boundary: reset ALL counts if date changed
today = _dt.date.today().isoformat()
state_today = state.get('today')
if state_today != today:
    state['reminder_counts'] = {}
    state['last_reminder_sent'] = {}
    state['last_reminder_times'] = {}
    state['today'] = today
```

**Location in file:** Immediately after loading state, BEFORE the slot-confirmation cleanup and BEFORE the increment. This ensures:
1. Day check runs every single cron tick
2. Reset fires at most once per day (first tick after midnight)
3. Reset happens before any other state mutation

**chain-state.json after fix:**

```json
{
  "created": "2026-07-04",
  "system": "Domino Chain v2 — cooldown-enabled, day-reset",
  "today": "2026-07-07",
  "reminder_counts": {},
  "last_reminder_sent": {},
  "last_reminder_times": {}
}
```

## Verification Recipe

```bash
# 1. Check current state
cat ~/.hermes/chain-state.json | python3 -c "import sys,json; d=json.load(sys.stdin); print('Today:', d.get('today')); print('Counts:', d.get('reminder_counts'))"

# 2. Simulate day rollover
python3 -c "
import json
# Simulate old state from yesterday
state = {'today': '2026-07-06', 'reminder_counts': {'E': 3}}
today = __import__('datetime').date.today().isoformat()
if state.get('today') != today:
    print('Would reset counts (day changed)')
    state['reminder_counts'] = {}
    state['today'] = today
    print(f'New today: {state[\"today\"]}')
    print(f'Counts: {state[\"reminder_counts\"]}')
else:
    print('Same day — no reset')
"

# 3. Verify live: run chain_calc.py --next to see E's should_fire status
python3 ~/.hermes/scripts/chain_calc.py --next
```

## States at a Glance

| Condition | Before fix | After fix |
|-----------|------------|-----------|
| E count semalam | 3 | 3 |
| E count hari ni (selepas midnight) | 3 → leak | 0 ✅ |
| First reminder tonight template | count=4 "dah 4x tanya" | count=1 normal ✅ |
| E diambil mlm ni → reset | Count cleared (confirmed) | Count cleared (confirmed) |
| Esok pagi | Still 0 (confirmed cleared it) | 0 ✅ (day-boundary cleared it first) |

## Design Rationale

**Why in chain_monitor.sh and not chain_calc.py?** Because `chain_monitor.sh` is the ONLY thing that writes to `chain-state.json`. The increment logic lives in the Step 3 Python block inside chain_monitor.sh. Putting the day-boundary check at the top of that block ensures it runs every time ANY increment happens — no code path can bypass it.

**Why reset before slot-confirmation cleanup?** Because the slot-confirmation cleanup only clears counts for confirmed slots. If we reset AFTER the confirmation check, E's unconsumed yesterday-count would survive if the day rolled over between ticks. The day-boundary reset is the BACKSTOP that catches everything the cleanup miss.

**Why not use a standalone`date` field?** The `today` field is self-maintaining — written once by the first tick of each day, no manual maintenance needed. The `created` field remains as provenance metadata.

## Related

- Bug #4 (no cooldown) — the cooldown system prevents 15-min spam within a day
- Bug #7 (day-boundary) — prevents yesterday's count from escalating today's first reminder
- Together they fix both intra-day and cross-day reminder aggression
