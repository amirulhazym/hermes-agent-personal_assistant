# Mandatory: Execute med_confirm.py BEFORE Responding

**FAILING TO EXECUTE med_confirm.py IS THE #1 RECURRING BUG.**
This exact failure has happened on at least 5 occasions (July 3, 9, 10, 12, 15, 2026).
Each time the agent says "noted ✅" but NEVER writes to med-status.json. Cron reads
empty state → keeps firing reminders → user gets angry.

**The med-auto-confirm hook is NOT a reliable substitute.** It has known failure modes
(F1-F5 documented in references/med-auto-confirm-hook.md) that cause it to silently
skip messages. The hook is a SECONDARY safety net, NOT the primary mechanism.

## Protocol (EXECUTE IN ORDER, DO NOT SKIP)

1. **RESOLVE** drug/slot from user message
2. **RUN med_confirm.py** immediately:
   ```bash
   python3 ~/.hermes/scripts/med_confirm.py <SLOT> [<drug_id>] --at <HH:MM>
   ```
   - drug_id is optional (if omitted, ALL drugs in slot are confirmed)
   - Use drug_id when user only took some drugs in a multi-drug slot
   - Always prefer explicit `--at HH:MM` from user's stated time
3. **VERIFY** state was written:
   ```bash
   python3 ~/.hermes/scripts/med_confirm.py --check <SLOT>
   ```
   Expected: `overall: completed/partial`, drugs list matches user's report.
4. **DISPLAY** adjusted chain (optional but helpful for user):
   ```bash
   python3 ~/.hermes/scripts/chain_calc.py --display 2>/dev/null
   ```
5. **Only NOW** respond to user with ✅ confirmation + (optionally) chain display.

## What NOT to do (recurring failure patterns)

- ❌ "Done, noted." without running med_confirm.py — PATTERN G (user's term for this)
- ❌ Saying "Slot A ✅" without verifying the state file was written
- ❌ Relying on the hook alone (it silently skips on "Done", "akurit+", "6.45" dot, etc.)
- ❌ Writing med-status.json via ad-hoc Python in terminal — use med_confirm.py only
- ❌ Skipping drug_id for multi-drug slots when user only took some drugs

## Why this protocol exists

The cron bot (`chain_monitor.sh`, every 15 min) reads ONLY from med-status.json
to determine if a slot is confirmed. Chat acknowledgments (verbal "✅") are
invisible to the cron system. Only med-status.json writes matter. Telling the
user "Done, noted ✅" without writing the state is effectively lying — the cron
will keep firing reminders because it sees no state change.

## Verification checklist (for the agent after executing)

```python
import json
from pathlib import Path

status = json.loads(Path.home().joinpath('.hermes/med-status.json').read_text())
today = __import__('datetime').date.today().isoformat()

# Check the specific slot
entry = status.get('meds', {}).get('<SLOT>', {}).get(today, {})
print(f"Slot: overall={entry.get('overall')}")
print(f"Drugs: {list(entry.get('drugs', {}).keys())}")
for drug_id, info in entry.get('drugs', {}).items():
    print(f"  {drug_id}: {info.get('status')} @ {info.get('time')}")
```

If overall is NOT expected (should be 'completed' for full slot, 'partial' for
single-drug confirm), something went wrong. Dry-run and re-confirm.