# Cooldown System Implementation (2026-07-04)

## Trigger

User experienced 4 D reminders before he could respond (was sleeping). Called the system "barua" — extreme frustration. Root cause: no cooldown between reminders for the same slot.

## Architecture

### Before
```
tick → chain_calc.py → should_fire? → yes → REMIND → wait 15min → tick → REMIND again (repeat until confirmed)
```

### After
```
tick → chain_calc.py → should_fire? → yes → is_within_cooldown? → no → REMIND → store timestamp → wait 15min
                                      → no → silent (exit 0)
                                                                   → is_within_cooldown? → yes → silent → wait 15min
                                                                                          → no  → REMIND again
```

## Files Changed

### `chain_calc.py`
- Added `COOLDOWN_INTERVAL` dict (after `ESCALATION`)
- Added `get_cooldown_interval(count)` — returns minutes to wait based on count
- Added `is_within_cooldown(slot, reminder_counts, chain_state, now_min)` — returns True if too soon to fire
- Added cooldown check in ALL 3 fire paths (partial, regular-pending, default-fallback)

### `chain_monitor.sh`
- Added cleanup of `last_reminder_times` when slot is confirmed (line after `last_reminder_sent` pop)
- Added `import datetime as _dt` and `state.setdefault('last_reminder_times', {})[slot] = _dt.datetime.now().strftime('%H:%M')` after incrementing count

### `chain-state.json`
- Added `last_reminder_times` dict: `{"D": "16:45"}` format (HH:MM, MYT)

## Cooldown Intervals

```python
COOLDOWN_INTERVAL = {
    0: 0,      # First reminder: immediate
    1: 60,     # Second: 1 hour
    2: 60,     # Third: 1 hour
    'urgent': 30,   # Counts 3-6
    'critical': 15,  # Count 7+
}
```

## Edge Cases

| Scenario | Behaviour |
|----------|-----------|
| count=0 (first reminder) | Always fires immediately — no last_reminder_time yet |
| count>0 but no last_reminder_time in state | Allows fire (corrupted state recovery) |
| Day wrap (23:50 → 00:05) | `mins_since += 1440` handles midnight wrap |
| Bad time string in state | Returns False (allow fire — fail open for safety) |

## Verification

Run this to confirm cooldown works:
```bash
cd ~/.hermes
python3 -c "
import sys; sys.path.insert(0, 'scripts')
from chain_calc import is_within_cooldown, get_cooldown_interval

state = {'last_reminder_times': {'D': '16:45'}}
counts = {'D': 1}

# 15 min after → should skip
print(is_within_cooldown('D', counts, state, 17*60+0))  # True

# 60 min after → should fire
print(is_within_cooldown('D', counts, state, 17*60+45))  # False
"
```

## Chain-event flow for real tick

```
1. Cron tick at 16:45 (MYT)
2. chain_monitor.sh → chain_calc.py --next
3. chain_calc.py: D ready at 16:35, now=16:45 → should_fire=True, count=0 → cooldown: no (count=0 means allow)
4. chain_monitor.sh: increment count to 1, store last_reminder_time = "16:45"
5. REMINDER delivered to user
6. Next tick at 17:00
7. chain_calc.py: count=1, last_time="16:45", now=17:00 → mins_since=15 → interval=60 → 15<60 → WITHIN COOLDOWN → should_fire=False
8. Silent (no output)
9. Next tick at 17:45 (60 min after 16:45)
10. chain_calc.py: count=1, last_time="16:45", now=17:45 → mins_since=60 → interval=60 → 60<60? → False → cooldown EXPIRED → should_fire=True
11. 2nd REMINDER delivered
```

## Lesson: Why this matters

The cooldown isn't a "nice to have" — it's the difference between a usable system and an abusive one. Without it, the system harasses the user at maximum rate (4x/hour) until they comply. With reasonable cooldowns, the system becomes:

- **Before:** "REMIND REMIND REMIND REMIND REMIND → RAGE"
- **After:** "Remind → 1h gap → Remind → 30m gap → Remind → 15m gap → Remind"

This respects the user's autonomy while still persisting. The escalating intervals also serve as natural urgency: if I'm getting pinged every 15 min, something must actually be important.

## Testing Pitfall: Manual Runs Pollute Real Cron State (2026-07-04)

When verifying the chain system works, **do not** run `bash scripts/chain_monitor.sh` against the real `~/.hermes/chain-state.json` — it mutates the state, sets `last_reminder_times`, and increments `reminder_counts`. The next real cron tick (15 min later) will then hit the cooldown and go silent, making it look like the cron is broken when it isn't.

**Symptom:** You fix the code, run the script manually to verify (good — reminder fires!), then wait for the next cron tick and it goes silent. You conclude the fix didn't work. Actually it did work — the manual run consumed the cooldown slot.

**Fix — three options:**

1. **Reset state after manual tests.** Always `cat > chain-state.json << EOF {"created":"...", "reminder_counts":{}, "last_reminder_sent":{}, "last_reminder_times":{}} EOF` after a manual run if you want the next cron tick to be able to fire.

2. **Use `--next` only for state-inspection.** `python3 chain_calc.py --next` returns JSON with `should_fire: true/false` and the calculated chain without mutating any state. Use this to verify the timing logic without polluting cooldown.

3. **Sandbox the test.** Copy `chain-state.json` to `/tmp/test-state.json`, run the script with a wrapped bash that points at the temp file, and inspect results. This is the most reliable when iterating on a bug fix and you want to test multiple scenarios in quick succession without resetting state each time.

**Diagnostic to recognize this happened:**
```bash
cat ~/.hermes/chain-state.json
# If reminder_counts has entries from "today" but you didn't get real reminders,
# you probably ran a manual test earlier and forgot to reset.
```

The cooldown design deliberately persists state across restarts (it survives `kill -9`). That means manual tests leave debris that can confuse the next debugging session. Treat `chain-state.json` as production data, not scratch space.
