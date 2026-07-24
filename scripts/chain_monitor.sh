#!/bin/bash
# chain_monitor.sh — Single no_agent cron for Domino Chain reminders.
#
# Every 15 minutes:
# 1. Check current chain state via chain_calc.py
# 2. (G-5) Housekeeping: advance chain-state.json 'today' + reset confirmed-slot
#    counts on EVERY tick (not only when a reminder fires) so the chain can
#    never freeze on a stale date.
# 3. If a reminder should fire: increment count, generate + deliver reminder.
# 4. If nothing should fire -> silent (empty stdout)
#
# Cron schedule: */15 5-22 * * *
# Cron mode: no_agent = true
# Cron deliver: origin (back to this chat)

set -euo pipefail

SCRIPT_DIR="$HOME/.hermes/scripts"
STATE_FILE="$HOME/.hermes/chain-state.json"
CALC_PY="$SCRIPT_DIR/chain_calc.py"
LLM_PY="$SCRIPT_DIR/chain_llm.py"

# ── Step 1: Check if reminder should fire ──────────────────────────────────
NEXT_OUTPUT=$(python3 "$CALC_PY" --next 2>/dev/null) || {
    echo "[chain_monitor] ERROR: chain_calc.py --next failed" >&2
    exit 0  # Silent fail — don't flood user with errors
}

SHOULD_FIRE=$(echo "$NEXT_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('should_fire', False))")
FIRE_REASON=$(echo "$NEXT_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('reason', '') or '')")
NEXT_SLOT=$(echo "$NEXT_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('next_slot', '') or '')")

# ── Step 2: Housekeeping — runs EVERY tick (Pattern G-5 fix) ────────────────
# Advances 'today' and clears stale counts even when nothing should fire, so a
# corrupt/empty state can never freeze the chain on a past date.
python3 -c "
import json, sys, datetime as _dt
from pathlib import Path
state_file = Path('$STATE_FILE')
try:
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
except (json.JSONDecodeError, IOError):
    state = {}

# Day boundary: reset ALL counts if date changed.
today = _dt.date.today().isoformat()
state_today = state.get('today')
if state_today != today:
    state['reminder_counts'] = {}
    state['last_reminder_sent'] = {}
    state['last_reminder_times'] = {}
    state['today'] = today
    state.pop('slot_overrides', None)

# Reset counts for slots that are fully confirmed today.
import sys as _sys
_sys.path.insert(0, '$SCRIPT_DIR')
import chain_calc
for slot_letter in ['A', 'B', 'C', 'D', 'E']:
    if chain_calc.is_confirmed(slot_letter):
        state.setdefault('reminder_counts', {}).pop(slot_letter, None)
        state.setdefault('last_reminder_sent', {}).pop(slot_letter, None)
        state.setdefault('last_reminder_times', {}).pop(slot_letter, None)

state_file.write_text(json.dumps(state, indent=2))
" 2>/dev/null || true

# ── Step 3: If nothing to fire -> silent exit (after housekeeping) ──────────
if [ "$SHOULD_FIRE" != "True" ]; then
    exit 0
fi

# The slot to remind about
SLOT="$FIRE_REASON"
if [ -z "$SLOT" ]; then
    SLOT="$NEXT_SLOT"
fi
if [ -z "$SLOT" ]; then
    exit 0
fi

# ── Step 4: Generate approved reminder text ───────────────────────────────
# Resolver or LLM failure produces no stdout. no_agent cron treats empty
# stdout as silent, preventing unsafe fallback delivery.
REMINDER_TEXT=$(python3 "$LLM_PY" "$SLOT" 2>/dev/null) || REMINDER_TEXT=""
if [ -z "$REMINDER_TEXT" ]; then
    echo "[chain_monitor] reminder generation failed; delivery suppressed" >&2
    exit 0
fi

# ── Step 5: Record generated reminder, not handset delivery ─────────────────
# no_agent scripts have no destination receipt callback. This state records that
# reminder text was generated; it must never be interpreted as user-visible.
python3 -c "
import json, datetime as _dt
from pathlib import Path
state_file = Path('$STATE_FILE')
try:
    state = json.loads(state_file.read_text()) if state_file.exists() else {}
except (json.JSONDecodeError, IOError):
    state = {}
counts = state.setdefault('reminder_counts', {})
counts['$SLOT'] = counts.get('$SLOT', 0) + 1
state.setdefault('last_reminder_sent', {})['$SLOT'] = counts['$SLOT']
state.setdefault('last_reminder_times', {})['$SLOT'] = _dt.datetime.now().strftime('%H:%M')
state.setdefault('last_reminder_delivery', {})['$SLOT'] = 'unverified'
state_file.write_text(json.dumps(state, indent=2))
" 2>/dev/null || true

echo "$REMINDER_TEXT"
