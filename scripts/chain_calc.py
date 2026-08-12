#!/usr/bin/env python3
"""
chain_calc.py — Medication Chain Calculator (v2 with drug-level support).

Reads med-schedule.json (rules) + med-status.json (drug-level intake)
and calculates chain state, ready times, and display strings.

Output formats:
    chain_calc.py                     → Full JSON state
    chain_calc.py --next              → Next slot that needs action (JSON)
    chain_calc.py --display           → Human-readable chain string
    chain_calc.py --template <SLOT>   → Generate reminder text for a slot
"""

import json
import sys
from datetime import datetime, timedelta, time
import os as _os
import sys as _sys
from pathlib import Path
from zoneinfo import ZoneInfo

# ── Paths ──────────────────────────────────────────────────────────────────
HOME = Path.home()
SCHEDULE_FILE = HOME / '.hermes' / 'med-schedule.json'
STATUS_FILE = HOME / '.hermes' / 'med-status.json'
STATE_FILE = HOME / '.hermes' / 'chain-state.json'
TAPER_FILE = HOME / '.hermes' / 'dexa_taper.json'
MYT = ZoneInfo('Asia/Kuala_Lumpur')

# ── Slots in order ─────────────────────────────────────────────────────────
SLOTS = ['A', 'B', 'C', 'D', 'E']

# ── Default planned times (fallback) ──────────────────────────────────────
DEFAULT_TIMES = {'A': '06:00', 'B': '08:00', 'C': '12:00', 'D': '16:00', 'E': '20:00'}

# ── Gap rules in hours ─────────────────────────────────────────────────────
GAPS = {
    'A_to_B': 1.0,
    'B_to_C': 4.0,
    'C_to_D': 4.0,
}

# ── Deterministic med-chain engine ─────────────────────────────────────────
# One resolver is the only timing source. Any resolver error is surfaced to
# the monitor, which suppresses delivery instead of applying legacy gap maths.
_MED_CHAIN = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "med_chain")
if _MED_CHAIN not in _sys.path:
    _sys.path.insert(0, _MED_CHAIN)


class TimingResolutionError(RuntimeError):
    pass


def compute_slots_deterministic(fixed_slots: dict) -> dict:
    """Resolve exact user times plus anchored/minimum-safe pending times."""
    try:
        from solve import solve, load_rules
        rules = load_rules(_os.path.join(_MED_CHAIN, "rules.json"))
        parsed = {}
        for key, value in fixed_slots.items():
            if value:
                hour, minute = str(value).split(":")
                parsed[key] = time(int(hour), int(minute))
        result = solve(rules["constraints"], parsed)
        if result["conflicts"]:
            raise TimingResolutionError("; ".join(result["conflicts"]))
        return {
            key: minutes_to_time_str(value.hour * 60 + value.minute)
            for key, value in result["slots"].items()
        }
    except TimingResolutionError:
        raise
    except Exception as exc:
        raise TimingResolutionError(f"resolver failure: {type(exc).__name__}: {exc}") from exc

# ── Escalation thresholds (in reminders sent) ─────────────────────────────
ESCALATION = {
    'normal': 0,
    'gentle': 1,
    'push': 2,
    'urgent': 4,
    'critical': 7,
}
# ── Cooldown intervals (minutes) between reminders for same slot ────────────
# count=0 (first): fire immediately when ready
# count=1..2 (gentle/push): 60 min between reminders
# count=3..6 (urgent): 30 min between reminders
# count=7+ (critical): 15 min between reminders
COOLDOWN_INTERVAL = {
    0: 0,
    # Monitor polls every 15 minutes. Retry cadence must not exceed polling
    # cadence, otherwise one failed/unseen send creates a blind gap.
    1: 15,
    2: 15,
    'urgent': 30,
    'critical': 15,
}


def get_cooldown_interval(count: int, is_partial: bool = False) -> int:
    """Return minimum minutes to wait before next reminder for this slot.
    
    When is_partial=True (some drugs taken, some pending), use gentler
    cooldown — supplements like CC don't need aggressive chasing.
    """
    if is_partial:
        # Slot partially done — user knows, be patient.
        # 120 min between reminders, no escalation.
        return max(COOLDOWN_INTERVAL.get(count, 120), 120)
    if count >= 7:
        return COOLDOWN_INTERVAL['critical']
    elif count >= 3:
        return COOLDOWN_INTERVAL['urgent']
    return COOLDOWN_INTERVAL.get(count, 60)


def is_within_cooldown(slot: str, reminder_counts: dict, chain_state: dict, now_min: int, is_partial: bool = False) -> bool:
    """
    Check if we're still within the cooldown period for this slot.
    Returns True if we should SKIP firing (too soon), False if we should fire.
    """
    count = reminder_counts.get(slot, 0)
    if count == 0:
        return False  # First reminder, always fire
    
    last_times = chain_state.get('last_reminder_times', {})
    last_time_str = last_times.get(slot)
    if not last_time_str:
        return False  # No recorded time, allow fire
    
    try:
        last_min = time_str_to_minutes(last_time_str)
    except (ValueError, TypeError):
        return False  # Bad data, allow fire
    
    mins_since = now_min - last_min
    if mins_since < 0:
        mins_since += 1440  # Handle day wrap
    
    interval = get_cooldown_interval(count, is_partial)
    return mins_since < interval






# ═══════════════════════════════════════════════════════════════════════════
#  UTILITY
# ═══════════════════════════════════════════════════════════════════════════

def now_myt() -> datetime:
    frozen = _os.environ.get('CHAIN_CALC_NOW_MYT')
    if frozen:
        parsed = datetime.fromisoformat(frozen)
        return parsed.replace(tzinfo=MYT) if parsed.tzinfo is None else parsed.astimezone(MYT)
    return datetime.now(MYT)


def today_myt() -> str:
    return now_myt().strftime('%Y-%m-%d')


def time_str_to_minutes(t: str) -> int:
    h, m = map(int, t.split(':'))
    return h * 60 + m


def minutes_to_time_str(m: int) -> str:
    return f'{m // 60:02d}:{m % 60:02d}'


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, sort_keys=True)


# ═══════════════════════════════════════════════════════════════════════════
#  DEXA TAPER ENGINE
# ═══════════════════════════════════════════════════════════════════════════

def load_taper() -> dict:
    """Load dexa_taper.json, return empty dict on failure."""
    return load_json(TAPER_FILE)


def get_current_phase(taper: dict = None, date_str: str = None) -> dict | None:
    """
    Get the current tapering phase based on today's date (or provided date).
    Returns the phase dict from dexa_taper.json, or None if not found.
    """
    if taper is None:
        taper = load_taper()
    if not taper or 'phases' not in taper:
        return None

    target = date_str or today_myt()
    for phase in taper['phases']:
        start = phase.get('start')
        end = phase.get('end')
        if not start:
            continue
        if end is None:
            # Open-ended final phase (STOP)
            if target >= start:
                return phase
        else:
            if start <= target <= end:
                return phase
    return None


def get_next_phase(taper: dict = None, date_str: str = None) -> dict | None:
    """Get the NEXT tapering phase (the one after current)."""
    if taper is None:
        taper = load_taper()
    if not taper or 'phases' not in taper:
        return None

    target = date_str or today_myt()
    for i, phase in enumerate(taper['phases']):
        start = phase.get('start')
        end = phase.get('end')
        if not start:
            continue
        if end is None:
            if target >= start:
                # Current is last phase, no next
                return None
        else:
            if start <= target <= end:
                # Return next phase if exists
                if i + 1 < len(taper['phases']):
                    return taper['phases'][i + 1]
                return None
    return None


def get_dexa_dose_for_slot(slot: str, phase: dict = None) -> int | None:
    """
    Get the current dexamethasone dose in mg for a specific slot.
    Slot B = dose_morning, C = dose_midday, D = dose_afternoon/evening.
    Delegates to dexa_taper_lookup (single source of truth) so taper logic
    is never implemented in two places that can drift.
    """
    from dexa_taper_lookup import get_dexa_dose
    # phase arg retained for API compat; lookup uses date internally
    return get_dexa_dose(slot)


def get_dexa_total_mg(phase: dict = None) -> int:
    """Get total daily dexamethasone dose in mg for current phase."""
    if phase is None:
        phase = get_current_phase()
    if not phase:
        return 0
    return phase.get('total_mg', 0)


def get_dexa_freq(phase: dict = None) -> str:
    """Get current dosing frequency: TDS, BD, OD, or STOP."""
    if phase is None:
        phase = get_current_phase()
    if not phase:
        return 'TDS'
    return phase.get('freq', 'TDS')


def get_days_until_next_phase(taper: dict = None) -> int | None:
    """Returns number of days until next phase transition, or None."""
    phase = get_current_phase(taper)
    if not phase or not phase.get('end'):
        return None
    end_date = datetime.strptime(phase['end'], '%Y-%m-%d').date()
    today = now_myt().date()
    delta = (end_date - today).days
    return max(0, delta)


def is_slot_active_for_dexa(slot: str, taper: dict = None) -> bool:
    """Check if a slot is active for dexamethasone in the current phase."""
    if taper is None:
        taper = load_taper()
    phase = get_current_phase(taper)
    if not phase:
        return True  # Default: all active
    freq = phase.get('freq', 'TDS')
    active = taper.get('active_slots_by_freq', {}).get(freq, ['A', 'B', 'C', 'D', 'E'])
    return slot in active


# ═══════════════════════════════════════════════════════════════════════════
#  DRUG-LEVEL STATE HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def get_drugs_for_slot(slot: str, schedule: dict) -> list[dict]:
    return schedule.get('meds', {}).get(slot, {}).get('drugs', [])


def get_required_drug_ids(slot: str, schedule: dict) -> list[str]:
    """Get drug_ids for REQUIRED drugs (excludes optional like b_complex)."""
    return [d['drug_id'] for d in get_drugs_for_slot(slot, schedule) if d.get('required', True)]


def get_all_drug_ids(slot: str, schedule: dict) -> list[str]:
    return [d['drug_id'] for d in get_drugs_for_slot(slot, schedule)]


def get_slot_entry(slot: str) -> dict | str | None:
    """Get today's entry for a slot from med-status.json.
    Returns None if no data, or the raw entry (dict/str for legacy)."""
    status = load_json(STATUS_FILE)
    today = today_myt()
    entry = status.get('meds', {}).get(slot, {}).get(today)
    return entry


def get_drug_level_overall(slot: str, schedule: dict) -> str:
    """
    Determine overall status of a slot based on drug-level data.
    Returns: 'completed' | 'partial' | 'pending' | 'legacy'
    
    'legacy' means old format where we can't distinguish — treat as completed.
    """
    entry = get_slot_entry(slot)
    
    # No data at all
    if entry is None:
        return 'pending'
    
    # Legacy string format
    if isinstance(entry, str):
        return 'completed' if entry == 'confirmed' else 'pending'
    
    # Legacy dict format {"status": "confirmed", "time": "..."}
    if isinstance(entry, dict) and 'status' in entry and 'drugs' not in entry:
        return 'completed' if entry.get('status') == 'confirmed' else 'pending'
    
    # New drug-level format
    if isinstance(entry, dict) and 'drugs' in entry:
        return entry.get('overall', 'pending')
    
    return 'pending'


def get_taken_drugs(slot: str) -> dict[str, dict]:
    """Get dict of {drug_id: {status, time}} for drugs that are 'taken'."""
    entry = get_slot_entry(slot)
    if not isinstance(entry, dict) or 'drugs' not in entry:
        return {}
    return {did: info for did, info in entry['drugs'].items() if info.get('status') == 'taken'}


def get_pending_required_drugs(slot: str) -> list[dict]:
    """
    Get list of drug dicts for required drugs that are NOT yet taken.
    Returns from med-schedule so we can show drug names.
    """
    schedule = load_json(SCHEDULE_FILE)
    required = get_required_drug_ids(slot, schedule)
    entry = get_slot_entry(slot)
    drugs_state = entry.get('drugs', {}) if isinstance(entry, dict) else {}
    accounted_ids = {
        did for did in required
        if drugs_state.get(did, {}).get('status') in {'taken', 'skipped'}
    }

    pending_ids = set(required) - accounted_ids
    drugs = get_drugs_for_slot(slot, schedule)
    pending = [d for d in drugs if d.get('drug_id') in pending_ids]

    # Date-aware Dexa dosage: schedule JSON holds a static snapshot (e.g. 5/5/4).
    # The taper engine is the single dosage authority. Override B/C/D Dexa
    # entries with the current phase dose so reminders never render stale
    # static dosages (dataflow gap, 2026-08-12). Non-Dexa drugs untouched.
    if slot in ('B', 'C', 'D') and any(
        d.get('drug_id', '').startswith('dexamethasone_') for d in pending
    ):
        phase = get_current_phase()
        dose_mg = get_dexa_dose_for_slot(slot, phase)
        if dose_mg:
            for d in pending:
                if d.get('drug_id', '').startswith('dexamethasone_'):
                    d['dosage'] = f"{dose_mg}mg"
    return pending


def is_confirmed(slot: str) -> bool:
    """Slot is only truly confirmed if ALL required drugs are taken."""
    schedule = load_json(SCHEDULE_FILE)
    overall = get_drug_level_overall(slot, schedule)
    return overall == 'completed'


def is_partial(slot: str) -> bool:
    """Slot is partial if some but not all required drugs are taken."""
    schedule = load_json(SCHEDULE_FILE)
    overall = get_drug_level_overall(slot, schedule)
    return overall == 'partial'


def is_effectively_done(slot: str) -> bool:
    """True when every required drug has a terminal user decision.

    ``is_confirmed`` remains intake-only: skipped must never be represented as
    taken. This predicate is for reminder resolution and housekeeping only.
    """
    schedule = load_json(SCHEDULE_FILE)
    required = get_required_drug_ids(slot, schedule)
    if not required:
        return False

    entry = get_slot_entry(slot)
    if not isinstance(entry, dict) or 'drugs' not in entry:
        return False

    drugs = entry['drugs']
    return all(
        drugs.get(did, {}).get('status') in {'taken', 'skipped'}
        for did in required
    )


def get_actual_time(slot: str, drug_id: str | None = None) -> str | None:
    """
    Get the actual intake time for a slot.
    
    By default: returns the PRIORITY drug's time for the slot:
      - Dexamethasone slots → returns Dexa time (so gap calc uses Dexa time, not Calcium/other)
      - Other slots → returns latest taken time (current behavior)
    
    When drug_id is specified, returns that specific drug's time.
    For legacy format: return stored time.
    """
    entry = get_slot_entry(slot)
    
    # Legacy dict format
    if isinstance(entry, dict) and 'time' in entry and 'drugs' not in entry:
        return entry['time']
    
    # New drug-level format
    if isinstance(entry, dict) and 'drugs' in entry:
        # If specific drug_id requested
        if drug_id:
            for did, info in entry['drugs'].items():
                if did == drug_id and info.get('status') == 'taken' and info.get('time'):
                    return info['time']
            return None
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


# ═══════════════════════════════════════════════════════════════════════════
#  CHAIN CALCULATION
# ═══════════════════════════════════════════════════════════════════════════

def get_default_time(slot: str, schedule: dict) -> str:
    med = schedule.get('meds', {}).get(slot, {})
    raw = med.get('time', DEFAULT_TIMES.get(slot, '00:00'))
    first_time = raw.split(',')[0].strip().split()[0]
    return first_time if ':' in first_time else DEFAULT_TIMES.get(slot, '00:00')


# Heads-up pre-notices are restricted to this window before the actual ready
# time. A slot pushed late by a gap rule (e.g. B: 08:00 configured -> 09:10
# ready because A was taken at 08:10) must never nag the user to take a drug
# that is not actually due yet.
HEADS_UP_WINDOW_MIN = 30


def is_scheduled_heads_up(slot: str, schedule: dict, now_min: int,
                          ready_time: str | None) -> bool:
    """Configured dose time arrived but dynamic minimum gap is not mature.

    Only pre-notifies within HEADS_UP_WINDOW_MIN of the actual ready time.
    """
    if not ready_time:
        return False
    scheduled_min = time_str_to_minutes(get_default_time(slot, schedule))
    ready_min = time_str_to_minutes(ready_time)
    if not (ready_min > scheduled_min and scheduled_min <= now_min < ready_min):
        return False
    return now_min >= ready_min - HEADS_UP_WINDOW_MIN


def calculate_ready_time(
    slot: str,
    schedule: dict,
    chain_times: dict[str, str],
    resolved_times: dict[str, str],
) -> str | None:
    if is_confirmed(slot):
        actual = get_actual_time(slot)
        return actual or None
    
    if slot == 'A':
        return get_default_time('A', schedule)

    if slot not in resolved_times:
        raise TimingResolutionError(f"resolver omitted active slot {slot}")
    return resolved_times[slot]


def calculate_chain() -> dict:
    now = now_myt()
    now_str = now.strftime('%H:%M')
    now_min = now.hour * 60 + now.minute
    today = today_myt()
    schedule = load_json(SCHEDULE_FILE)
    
    # Step 1: Collect only timing-relevant actual doses. C/D never inherit a
    # calcium/calcitriol time; Dexa gaps are driven only by their Dexa dose.
    chain_times = {}
    timing_drug = {
        'A': 'akurit_2',
        'B': 'dexamethasone_1',
        'C': 'dexamethasone_2',
    }
    for slot, drug_id in timing_drug.items():
        if is_confirmed(slot) or is_partial(slot):
            actual = get_actual_time(slot, drug_id)
            if actual:
                chain_times[slot] = actual
    
    try:
        resolved_times = compute_slots_deterministic(chain_times)
        timing_error = None
    except TimingResolutionError as exc:
        resolved_times = {}
        timing_error = str(exc)

    # Step 1.5: Determine active slots based on taper phase
    taper = load_taper()
    current_phase = get_current_phase(taper)
    freq = current_phase.get('freq', 'TDS') if current_phase else 'TDS'
    active_slots_set = set(taper.get('active_slots_by_freq', {}).get(freq, SLOTS))
    
    # Step 2: Calculate state for each slot
    slot_states = {}
    for slot in SLOTS:
        # Check if slot is active for current taper phase
        slot_active = slot in active_slots_set
        
        overall = get_drug_level_overall(slot, schedule)
        confirmed = overall == 'completed'
        effectively_done = is_effectively_done(slot)
        actual = get_actual_time(slot)
        ready = (
            calculate_ready_time(slot, schedule, chain_times, resolved_times)
            if slot_active and timing_error is None else None
        )
        pending_drugs = get_pending_required_drugs(slot) if not effectively_done and slot_active else []
        
        # Determine status
        if not slot_active:
            status = 'inactive'  # Deactivated by taper phase
        elif confirmed:
            status = 'done'
        elif effectively_done:
            status = 'resolved'
        elif is_partial(slot):
            # Partial — some drugs taken, some still pending
            if ready and now_min >= time_str_to_minutes(ready) - 15:
                status = 'partial_ready'
            else:
                status = 'partial'
        elif ready and now_min >= time_str_to_minutes(ready) - 15:
            status = 'ready'
        elif ready and now_min < time_str_to_minutes(ready):
            status = 'waiting'
        else:
            status = 'pending'
        
        slot_states[slot] = {
            'confirmed': confirmed,
            'effectively_done': effectively_done,
            'overall': overall,
            'actual_time': actual,
            'ready_time': ready,
            'status': status,
            'pending_drugs': pending_drugs,
            'active': slot_active,
        }
    
    # Step 3: Find the next slot that needs action (skip inactive)
    next_slot = None
    for slot in SLOTS:
        if not slot_states[slot].get('active', True):
            continue
        st = slot_states[slot]
        if st['status'] in ('ready', 'partial_ready', 'partial') and not st['effectively_done']:
            next_slot = slot
            break
    if not next_slot:
        for slot in SLOTS:
            if not slot_states[slot].get('active', True):
                continue
            if not slot_states[slot]['effectively_done']:
                next_slot = slot
                break
    
    next_ready = slot_states[next_slot]['ready_time'] if next_slot else None
    
    # Step 4: Build chain display string
    chain_parts = []
    for slot in SLOTS:
        st = slot_states[slot]
        if not st.get('active', True):
            chain_parts.append(f'{slot} —')  # Inactive slot
        elif st['confirmed']:
            t = st['actual_time'] or '✓'
            chain_parts.append(f'{slot} ✅ {t}')
        elif st['effectively_done']:
            t = st['actual_time'] or '⏭'
            chain_parts.append(f'{slot} ⏭ {t}')
        elif st['overall'] == 'partial':
            t = st['actual_time'] or '◐'
            chain_parts.append(f'{slot} ◐ {t}')
        elif st['ready_time']:
            chain_parts.append(f'{slot} ~{st["ready_time"]}')
        else:
            chain_parts.append(f'{slot} ...')
    chain_str = ' → '.join(chain_parts)
    
    # Step 5: Load chain state (reminder counts)
    chain_state = load_json(STATE_FILE)
    reminder_counts = chain_state.get('reminder_counts', {})
    last_sent = chain_state.get('last_reminder_sent', {})
    
    # Step 6: Check for slot overrides (user said "stick with original schedule")
    today_str = datetime.now(MYT).strftime('%Y-%m-%d')
    slot_overrides = chain_state.get('slot_overrides', {}).get(today_str, {})
    
    # Step 7: Determine if a reminder should fire now. A timing error is a
    # delivery suppression condition, never an excuse to use legacy maths.
    should_fire = False
    fire_reason = None
    if timing_error is None:
        for slot in SLOTS:
            st = slot_states[slot]
            if not st.get('active', True):
                continue
            if st['effectively_done']:
                continue

            heads_up = is_scheduled_heads_up(slot, schedule, now_min, st['ready_time'])
            if st['status'] == 'waiting' and not heads_up:
                continue

            if slot in slot_overrides:
                override = slot_overrides[slot]
                suppress_until = override.get('suppress_until')
                if suppress_until and now_min < time_str_to_minutes(suppress_until):
                    continue

            if heads_up:
                # Heads-up fires at most ONCE per slot per day so the 30-min
                # pre-window cannot spam the same text twice. Once it has
                # fired, the slot falls through to the real due branch when
                # now >= ready_time (cooldown applies there as usual).
                if reminder_counts.get(slot, 0) > 0:
                    continue
                if is_within_cooldown(slot, reminder_counts, chain_state, now_min):
                    continue
                should_fire = True
                fire_reason = slot
                break

            if st['overall'] == 'partial':
                if st['ready_time'] and now_min >= time_str_to_minutes(st['ready_time']):
                    if is_within_cooldown(slot, reminder_counts, chain_state, now_min, is_partial=True):
                        continue
                    should_fire = True
                    fire_reason = slot
                    break

            if not st['confirmed'] and st['overall'] != 'partial':
                if st['ready_time'] and now_min >= time_str_to_minutes(st['ready_time']):
                    if now_min >= time_str_to_minutes('22:00'):
                        continue
                    if now_min < time_str_to_minutes('05:00'):
                        continue
                    if is_within_cooldown(slot, reminder_counts, chain_state, now_min):
                        continue
                    should_fire = True
                    fire_reason = slot
                    break
    
    # Step 7: Taper info
    taper = load_taper()
    current_phase = get_current_phase(taper)
    next_phase = get_next_phase(taper)
    days_to_change = get_days_until_next_phase(taper)
    taper_info = None
    if current_phase:
        freq = current_phase.get('freq', 'TDS')
        taper_info = {
            'freq': freq,
            'total_mg': current_phase.get('total_mg', 0),
            'dose_morning': current_phase.get('dose_morning', 0),
            'dose_midday': current_phase.get('dose_2pm') if freq == 'BD' else current_phase.get('dose_midday', 0),
            'dose_afternoon': current_phase.get('dose_afternoon', 0) or current_phase.get('dose_evening', 0),
            'dose_2pm': current_phase.get('dose_2pm', 0),
            'phase_id': current_phase.get('id'),
            'phase_end': current_phase.get('end'),
            'days_until_change': days_to_change,
            'next_phase': {
                'total_mg': next_phase.get('total_mg'),
                'freq': next_phase.get('freq'),
            } if next_phase else None,
        }
    
    return {
        'today': today,
        'now': now_str,
        'slots': slot_states,
        'next_slot': next_slot,
        'next_ready_time': next_ready,
        'chain_str': chain_str,
        'reminder_counts': reminder_counts,
        'last_sent': last_sent,
        'timing_error': timing_error,
        'reminder': {
            'should_fire': should_fire,
            'reason': fire_reason,
        },
        'taper': taper_info,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  REMINDER TEMPLATES — Human-like, contextual, escalating
# ═══════════════════════════════════════════════════════════════════════════

def get_prev_time(slot: str, chain: dict) -> str | None:
    idx = SLOTS.index(slot)
    if idx == 0:
        return None
    prev = SLOTS[idx - 1]
    return chain['slots'][prev].get('actual_time')


def format_pending_drugs(slot: str, chain: dict) -> str:
    """Generate string listing still-pending drugs for a partial slot."""
    pending = chain['slots'][slot].get('pending_drugs', [])
    if not pending:
        return ''
    names = [d.get('drug', '?') for d in pending]
    if len(names) == 1:
        return f"{names[0]} masih belum ambil"
    return f"{', '.join(names[:-1])} dan {names[-1]} masih belum ambil"


def generate_reminder(slot: str, chain: dict) -> str:
    schedule = load_json(SCHEDULE_FILE)
    med_info = schedule.get('meds', {}).get(slot, {})
    count = chain['reminder_counts'].get(slot, 0)
    now = chain['now']
    ready = chain['slots'][slot].get('ready_time', '?')
    prev_time = get_prev_time(slot, chain)
    overall = chain['slots'][slot].get('overall', 'pending')
    pending_str = format_pending_drugs(slot, chain)

    if chain['slots'][slot].get('effectively_done'):
        return ''
    
    med_name = med_info.get('name', f'Medication {slot}')
    drugs = med_info.get('drugs', [])
    drug_list = ' + '.join([f"{d['drug']} {d['dosage']}" for d in drugs]) if drugs else med_name
    condition = med_info.get('condition', '')
    
    # ── Taper-aware dexa dose for this slot ────────────────────────────
    dexa_dose = get_dexa_dose_for_slot(slot)
    dexa_mg_str = f" ({dexa_dose}mg)" if dexa_dose and dexa_dose > 0 else ""
    total_mg = get_dexa_total_mg()
    freq = get_dexa_freq()
    days_left = get_days_until_next_phase()
    
    # ── PARTIAL REMINDER (some drugs taken, some pending) ────────────────
    if overall == 'partial' and pending_str:
        pending = chain['slots'][slot].get('pending_drugs', [])
        # Build list of what's already taken by looking at what's NOT pending
        all_drugs = get_required_drug_ids(slot, schedule)
        taken_ids = set(all_drugs) - set(d.get('drug_id', '') for d in pending)
        schedule_drugs = get_drugs_for_slot(slot, schedule)
        taken_names = [d['drug'] for d in schedule_drugs if d.get('drug_id') in taken_ids]
        done_str = ' + '.join(taken_names) if taken_names else ''
        return (
            f"⚠️ {slot} — {done_str} ✅ tinggal {pending_str}. "
            f"Dah pukul {now}. "
            f"Reply 'dah makan {slot}' terus bila dah ambil."
        )
    
    # ── SLOT A: Akurit-4 + Pyridoxine ──────────────────────────────────────
    if slot == 'A':
        if count == 0:
            return (
                f"🌅 Dah pukul 6 pagi boss! "
                f"Akurit-4 (4biji) + Pyridoxine (3biji) — perut kosong ya. "
                f"Lepas ambil, boleh baca Yasin & Al-Waqiah macam biasa."
            )
        elif count == 1:
            return (
                f"Boss, A belum ambil lagi ke? "
                f"Akurit perlukan sekurang-kurangnya 1 jam sebelum ubat seterusnya. "
                f"B target tetap 8 pagi bila gap tu dah cukup."
            )
        elif count == 2:
            return (
                f"Dah kali ke-3 tanya pasal A. Akurit-4 kena perut kosong — "
                f"kalau dah breakfast, kena tunggu 2 jam baru boleh ambil. "
                f"Kalau tak sempat pagi ni, kita adjust schedule."
            )
        elif count <= 4:
            return (
                f"Dah pukul {now}. A lewat {count}x15 minit dari target. "
                f"Akurit-4 + Pyridoxine belum ambil. "
                f"Saya still tunggu."
            )
        else:
            return (
                f"⚠️ CRITICAL: A belum ambil. Dah {count}x remind. "
                f"Dah pukul {now}. Kalau terlepas pagi ni, "
                f"chain hari ni kena adjust total. Please update boss 🙏"
            )
    
    # ── SLOT B: Levetiracetam + Dexamethasone #1 ───────────────────────────
    if slot == 'B':
        a_info = f"A tadi {prev_time} ✅" if prev_time else "A belum confirm"
        
        if count == 0:
            return (
                f"⏰ B time boss! Levetiracetam + Dexa #1{dexa_mg_str}. "
                f"Total Dexa hari ni: {total_mg}mg ({freq}). "
                f"{a_info}, dah cukup 1 jam gap. Dah boleh ambil sekarang."
            )
        elif count == 1:
            return (
                f"Boss, B belum ke? {a_info}. "
                f"Sepatutnya around pukul {ready} dah boleh ambil "
                f"Levetiracetam + Dexa #1{dexa_mg_str}. Dah pukul {now} dah ni. "
                f"Update bila dah ambil."
            )
        elif count == 2:
            return (
                f"Dah 3x remind B. {a_info}. "
                f"Levetiracetam malam target selepas 8pm. "
                f"Dah pukul {now}."
            )
        elif count <= 4:
            return (
                f"Dah pukul {now}. B masih belum ambil. "
                f"{a_info}. Kali ke-{count+1} remind. "
                f"Saya takkan stop sampai kau reply."
            )
        else:
            return (
                f"⚠️ URGENT: Dah {count}x remind B. {a_info}. "
                f"Levetiracetam + Dexa #1{dexa_mg_str}. Dah pukul {now}. "
                f"Please confirm boss 🙏"
            )
    
    # ── SLOT C: Dexamethasone #2 + Calcium + Calcitriol ─────────────────────
    if slot == 'C':
        b_info = f"B tadi {prev_time} ✅" if prev_time else "B belum confirm"
        
        if count == 0:
            return (
                f"☀️ Lunch time! Dexa #2{dexa_mg_str} + Calcium + Calcitriol. "
                f"{b_info}, dah cukup 4 jam gap. "
                f"Ambil time lunch, ingat layered: nasi > ubat > nasi."
            )
        elif count == 1:
            return (
                f"Boss, dah makan Dexa dose tengah hari ke belum? "
                f"{b_info}. Nak confirmkan je sebab kau belum reply. "
                f"Dah pukul {now}."
            )
        elif count == 2:
            return (
                f"Dah 3x tanya C. {b_info}. "
                f"Calcium mesti ambil dengan lunch, layered. "
                f"Kalau terlepas lunch window, ambil lepas lunch still okay."
            )
        else:
            return (
                f"⚠️ C belum ambil. Kali ke-{count+1}. "
                f"Dah pukul {now}. {b_info}. "
                f"Still boleh ambil, tapi cepat-cepat ya 🙏"
            )
    
    # ── SLOT D: Dexamethasone #3 ────────────────────────────────────────────
    if slot == 'D':
        c_info = f"C tadi {prev_time} ✅" if prev_time else "C belum confirm"
        
        if count == 0:
            return (
                f"⏰ D time — Dexamethasone #3{dexa_mg_str} (dose terakhir hari ni). "
                f"Total Dexa hari ni: {total_mg}mg ({freq}). "
                f"{c_info}, dah cukup 4 jam."
            )
        elif count == 1:
            return (
                f"Boss, Dexa #3{dexa_mg_str} belum ambil? {c_info}. "
                f"Dah pukul {now}. Hari dah petang, jangan lupa."
            )
        else:
            return (
                f"Dah {count+1}x tanya D. {c_info}. "
                f"Dah pukul {now}. Last dose Dexa untuk hari ni."
            )
    
    # ── SLOT E: Levetiracetam (malam) ───────────────────────────────────────
    if slot == 'E':
        b_info = chain['slots']['B'].get('actual_time')
        b_info_str = f"B tadi {b_info} ✅" if b_info else "B pagi takde rekod"
        
        if count == 0:
            return (
                f"🌙 E time — Levetiracetam 500mg dose mlm. "
                f"{b_info_str}. Ambil sebelum tido."
            )
        elif count == 1:
            return (
                f"Boss, Levetiracetam mlm belum ambil? "
                f"Dah pukul {now}."
            )
        elif count == 2:
            return (
                f"Kau dah makan letram ke belum malam ni? "
                f"Aku dah tanya kau 3 kali ni, tapi kau tak update pun "
                f"kau buat apa, kau pergi mana. "
                f"Please update, aku nak save dalam log."
            )
        else:
            return (
                f"⚠️ E belum! Dah {count+1}x tanya. "
                f"Dah pukul {now}. Levetiracetam mlm penting "
                f"untuk coverage anticonvulsant. Confirm please boss 🙏"
            )
    
    # ── Fallback ────────────────────────────────────────────────────────────
    return (
        f"⏰ Reminder: {slot} time boss. "
        f"Dah pukul {now}."
    )


# ═══════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════

def main() -> int:
    chain = calculate_chain()
    
    if len(sys.argv) < 2:
        print(json.dumps(chain, indent=2))
        return 0
    
    arg = sys.argv[1]
    
    if arg == '--next':
        result = {
            'next_slot': chain['next_slot'],
            'next_ready_time': chain['next_ready_time'],
            'should_fire': chain['reminder']['should_fire'],
            'reason': chain['reminder']['reason'],
            'chain_str': chain['chain_str'],
        }
        print(json.dumps(result))
    
    elif arg == '--display':
        print(chain['chain_str'])
    
    elif arg == '--template':
        if len(sys.argv) < 3:
            print('Need slot letter: --template A')
            return 1
        slot = sys.argv[2].upper()
        if slot not in SLOTS:
            print(f'Invalid slot: {slot}')
            return 1
        text = generate_reminder(slot, chain)
        print(text)
    
    elif arg == '--update':
        slot = sys.argv[2].upper() if len(sys.argv) > 2 else None
        state = load_json(STATE_FILE)
        if slot:
            state.setdefault('reminder_counts', {}).pop(slot, None)
            state.setdefault('last_reminder_sent', {}).pop(slot, None)
        else:
            state['reminder_counts'] = {}
            state['last_reminder_sent'] = {}
        save_json(STATE_FILE, state)
        print(json.dumps({'ok': True, 'state_reset': True}))
    
    elif arg == '--taper':
        taper_info = chain.get('taper')
        if taper_info:
            print(json.dumps(taper_info, indent=2))
        else:
            print(json.dumps({'error': 'No taper data found'}))
    
    elif arg == '--taper-display':
        taper_info = chain.get('taper')
        if not taper_info:
            print('No taper data available')
            return 1
        freq = taper_info['freq']
        total = taper_info['total_mg']
        m = taper_info['dose_morning']
        mid = taper_info['dose_midday']
        aft = taper_info['dose_afternoon']
        dose_2pm = taper_info.get('dose_2pm', 0)
        days = taper_info.get('days_until_change')
        next_p = taper_info.get('next_phase')
        
        print(f'Dexa Taper Status ({chain["today"]})')
        print(f'  Phase: {freq} | Total: {total}mg/day')
        if freq == 'TDS':
            print(f'  Doses: {m}mg (8am) + {mid}mg (12pm) + {aft}mg (4pm)')
        elif freq == 'BD':
            print(f'  Doses: {m}mg (8am) + {dose_2pm}mg (2pm)')
        elif freq == 'OD':
            print(f'  Dose: {m}mg (8am)')
        elif freq == 'STOP':
            print(f'  TAPER COMPLETE — Dexamethasone stopped')
        
        if days is not None and days > 0:
            print(f'  Next change: in {days} days')
            if next_p:
                print(f'  → {next_p["total_mg"]}mg ({next_p["freq"]})')
        elif days == 0:
            print(f'  ⚠️ Phase transition TODAY!')
        elif freq == 'STOP':
            print(f'  No further changes')
    
    elif arg == '--summary':
        taper_info = chain.get('taper')
        schedule = load_json(SCHEDULE_FILE)
        
        print(f'💊 MED DOSES TODAY ({chain["today"]})')
        print()
        
        # Slot A: Akurit-4 + Pyridoxine
        print(f'A — Akurit-4 + Pyridoxine')
        print(f'  Akurit-4: 4 tablet (perut kosong)')
        print(f'  Pyridoxine: 3 tablet / substitute')
        print(f'  Masa: ~6:00-7:30am')
        print()
        
        # Slot B: Levetiracetam + Dexa
        dexa_b = taper_info.get('dose_morning', '?') if taper_info else '?'
        print(f'B — Levetiracetam + Dexamethasone #1')
        print(f'  Levetiracetam: 500mg (1 tab)')
        print(f'  Dexamethasone: {dexa_b}mg')
        print(f'  Masa: ~8:00am (min 1h gap dari A)')
        print()
        
        # Slot C: Dexa + Calcium + Calcitriol
        dexa_c = taper_info.get('dose_midday', '?') if taper_info else '?'
        freq = taper_info.get('freq', 'TDS') if taper_info else 'TDS'
        c_active = freq in ('TDS', 'BD')
        if c_active:
            print(f'C — Dexamethasone #2 + Calcium + Calcitriol')
            print(f'  Dexamethasone: {dexa_c}mg')
            print(f'  Calcium Carbonate: 500mg')
            print(f'  Calcitriol: 1 tablet')
            print(f'  Masa: ~12:00pm (4h gap dari B)')
            print(f'  Cara: layered (nasi > ubat > nasi)')
        else:
            print(f'C — Deactivated (OD phase)')
        print()
        
        # Slot D: Dexa #3
        dexa_d = taper_info.get('dose_afternoon', '?') if taper_info else '?'
        d_active = freq == 'TDS'
        if d_active:
            print(f'D — Dexamethasone #3')
            print(f'  Dexamethasone: {dexa_d}mg')
            print(f'  Masa: ~4:00pm (4h gap dari C)')
        else:
            print(f'D — Deactivated ({freq} phase)')
        print()
        
        # Slot E: Levetiracetam
        print(f'E — Levetiracetam (malam)')
        print(f'  Levetiracetam: 500mg (1 tab)')
        print(f'  Masa: target ~8:00pm (bukan derived dari B)')
        print()
        
        # Summary
        if taper_info:
            total = taper_info.get('total_mg', '?')
            print(f'Dexa total hari ni: {total}mg ({freq})')
            days = taper_info.get('days_until_change')
            if days is not None and days > 0:
                print(f'Next dose change: {days} hari lagi')
    
    else:
        print(f'Unknown arg: {arg}')
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
