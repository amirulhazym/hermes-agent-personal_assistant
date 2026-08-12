#!/usr/bin/env python3
"""
med_confirm.py - Drug-level medication confirmation with Domino Chain support.

Usage (slot-level - marks ALL drugs in slot as taken):
    python3 med_confirm.py <LETTER>
    python3 med_confirm.py <LETTER> --at HH:MM

Usage (drug-level - marks specific drug only):
    python3 med_confirm.py <LETTER> <drug_id|drug_name_fragment>
    python3 med_confirm.py <LETTER> <drug_id> --at HH:MM

Query:
    python3 med_confirm.py --check <LETTER>          # Slot-level check
    python3 med_confirm.py --check <LETTER> <drug_id> # Drug-level check
    python3 med_confirm.py --status                   # All slots today
    python3 med_confirm.py --reset <LETTER>           # Reset slot
    python3 med_confirm.py --reset <LETTER> <drug_id> # Reset single drug
    python3 med_confirm.py --update <LETTER> HH:MM    # Update time

Safety:
    python3 med_confirm.py --dry-run <LETTER>         # Dry-run: show without writing
    --dry-run prevents ANY write - use for testing/live-verification
    ALL write ops auto-backup state to .json.bak1/.bak2/.bak3

State file: ~/.hermes/med-status.json
"""

import base64
import json
import os
import sys
import re
import tempfile
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from med_resolve import resolve as resolve_drug
from med_state_lock import exclusive_state_lock, locked_mutation

HERMES_HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
STATE_FILE = HERMES_HOME / "med-status.json"
SCHEDULE_FILE = HERMES_HOME / "med-schedule.json"
SUPPLY_FILE = HERMES_HOME / "med-supply.json"
LOCK_FILE = HERMES_HOME / ".med-confirm.lock"
TXN_FILE = HERMES_HOME / ".med-confirm-transaction.json"
COMPOUNDS = {"cc": {"slot": "C", "drug_ids": ["calcium", "calcitriol"]}}
COMPLETION_RE = re.compile(r"\b(dah\s*makan|sudah\s*makan|dah\s*ambil|dah\s*telan|done|took|ate|confirm)\b", re.IGNORECASE)

ALL_SLOTS = ['A', 'B', 'C', 'D', 'E']

# ── Safety: DRY_RUN prevents all writes ────────────────────────────────────
DRY_RUN = False


def get_today() -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).strftime("%Y-%m-%d")
    except ImportError:
        return datetime.now().strftime("%Y-%m-%d")


def get_now_hm() -> str:
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).strftime("%H:%M")
    except ImportError:
        return datetime.now().strftime("%H:%M")


def load_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_json(path: Path, data: dict) -> None:
    """Save with auto-backup rotation. Respects global DRY_RUN."""
    global DRY_RUN
    if DRY_RUN:
        print(f"[DRY-RUN] Would save to {path}")
        return

    path.parent.mkdir(parents=True, exist_ok=True)

    # Rotating backup: keep 3 copies
    if path.exists():
        import shutil
        for i in [3, 2, 1]:
            old = path if i == 1 else path.with_suffix(f'.json.bak{i-1}')
            new = path.with_suffix(f'.json.bak{i}')
            if old.exists():
                shutil.copy2(old, new)

    with open(path, 'w') as f:
        json.dump(data, f, indent=2, sort_keys=True)


def validate_time(t: str) -> str | None:
    m = re.match(r'^(\d{1,2}):(\d{2})$', t.strip())
    if not m:
        return None
    h, m = int(m.group(1)), int(m.group(2))
    if 0 <= h <= 23 and 0 <= m <= 59:
        return f"{h:02d}:{m:02d}"
    return None


def load_schedule() -> dict:
    return load_json(SCHEDULE_FILE)


def get_drugs_for_slot(slot: str, schedule: dict) -> list[dict]:
    return schedule.get('meds', {}).get(slot, {}).get('drugs', [])


def get_required_drug_ids(slot: str, schedule: dict) -> list[str]:
    return [d['drug_id'] for d in get_drugs_for_slot(slot, schedule) if d.get('required', True)]


def get_all_drug_ids(slot: str, schedule: dict) -> list[str]:
    return [d['drug_id'] for d in get_drugs_for_slot(slot, schedule)]


def find_drug_by_fragment(slot: str, fragment: str, schedule: dict) -> str | None:
    result = resolve_drug(fragment, slot=slot)
    if result.get("ok"):
        return result["drug_id"]
    return None


def _fsync_dir(path: Path) -> None:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _atomic_json_write(path: Path, data: dict) -> None:
    """Write one JSON file atomically without backup rotation.

    Used only inside a multi-file transaction which retains exact before-images
    for rollback. Do not call this for ordinary single-file operations.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, sort_keys=True)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        _fsync_dir(path.parent)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


@contextmanager
def _compound_lock():
    """Serialize compound confirmation against other med-confirm writers."""
    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, "a+", encoding="utf-8") as lock:
        try:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        except ImportError:
            pass
        try:
            yield
        finally:
            try:
                import fcntl
                fcntl.flock(lock.fileno(), fcntl.LOCK_UN)
            except ImportError:
                pass


def _write_transaction(before: dict[Path, bytes | None]) -> None:
    payload = {
        "version": 1,
        "status": "PREPARED",
        "files": {
            str(path): None if raw is None else base64.b64encode(raw).decode("ascii")
            for path, raw in before.items()
        },
    }
    _atomic_json_write(TXN_FILE, payload)


def _recover_prepared_transaction() -> bool:
    """Restore exact before-images left by an interrupted compound transaction."""
    if not TXN_FILE.exists():
        return False
    try:
        payload = json.loads(TXN_FILE.read_text(encoding="utf-8"))
        if payload.get("status") != "PREPARED":
            raise ValueError("unrecognised transaction status")
        for raw_path, encoded in payload.get("files", {}).items():
            path = Path(raw_path)
            raw = None if encoded is None else base64.b64decode(encoded.encode("ascii"))
            _restore_exact(path, raw)
        TXN_FILE.unlink(missing_ok=True)
        _fsync_dir(TXN_FILE.parent)
        return True
    except Exception as exc:
        raise RuntimeError(f"MED_TRANSACTION_RECOVERY_FAILED: {exc}") from exc


def _atomic_bytes_write(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
        _fsync_dir(path.parent)
    except Exception:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass
        raise


def _restore_exact(path: Path, before: bytes | None) -> None:
    if before is None:
        path.unlink(missing_ok=True)
        _fsync_dir(path.parent)
        return
    _atomic_bytes_write(path, before)


# ── State operations ────────────────────────────────────────────────────────

def get_slot_entry(state: dict, slot: str) -> dict:
    today = get_today()
    slot_data = state.setdefault('meds', {}).setdefault(slot, {})
    entry = slot_data.get(today, {})

    if isinstance(entry, str):
        schedule = load_schedule()
        drug_ids = get_all_drug_ids(slot, schedule)
        entry = {
            "overall": "completed",
            "drugs": {did: {"status": "taken", "time": None} for did in drug_ids}
        }
        slot_data[today] = entry
    elif isinstance(entry, dict) and 'status' in entry and 'drugs' not in entry:
        schedule = load_schedule()
        drug_ids = get_all_drug_ids(slot, schedule)
        old_time = entry.get('time')
        entry = {
            "overall": "completed",
            "drugs": {did: {"status": "taken", "time": old_time} for did in drug_ids}
        }
        slot_data[today] = entry
    elif isinstance(entry, dict) and 'drugs' not in entry:
        entry = {"overall": "pending", "drugs": {}}
        slot_data[today] = entry
    elif 'drugs' not in entry:
        entry = {"overall": "pending", "drugs": {}}
        slot_data[today] = entry

    return entry


def recalc_overall(slot: str, entry: dict, schedule: dict) -> str:
    required_ids = get_required_drug_ids(slot, schedule)
    if not required_ids:
        return "completed"

    drugs = entry.get('drugs', {})
    taken_count = sum(1 for did in required_ids if drugs.get(did, {}).get('status') == 'taken')

    if taken_count == 0:
        return "pending"
    elif taken_count < len(required_ids):
        return "partial"
    else:
        return "completed"


def save_and_recalc(slot: str, entry: dict) -> dict:
    state = load_json(STATE_FILE)
    today = get_today()
    schedule = load_schedule()

    entry['overall'] = recalc_overall(slot, entry, schedule)
    state.setdefault('meds', {}).setdefault(slot, {})[today] = entry
    save_json(STATE_FILE, state)

    return {
        "ok": True,
        "med": slot,
        "date": today,
        "overall": entry['overall'],
        "drugs": entry.get('drugs', {}),
        "file": str(STATE_FILE),
    }


# ── Operations ──────────────────────────────────────────────────────────────

@locked_mutation
def confirm_slot(slot: str, time_val: str | None = None, source_text: str | None = None) -> dict:
    """Mark ALL drugs in a slot as taken (slot-level confirmation).

    Args:
        slot: Letter A-E
        time_val: Optional time override
        source_text: REQUIRED. The agent must pass the user's actual statement.
            The tool verifies the statement mentions this slot's drugs before
            confirming. Prevents agent fabrication of medication confirmation.
    """
    global DRY_RUN
    state = load_json(STATE_FILE)
    schedule = load_schedule()
    today = get_today()
    now = time_val or get_now_hm()

    # ── Source text verification gate ────────────────────────────────────
    # The agent MUST pass the user's exact words. We verify those words
    # mention at least one drug from this slot. If not → REJECT.
    # Uses med_resolve aliases so "dexa" → Dexamethasone works.
    if source_text is not None:
        from med_resolve import resolve as resolve_drug
        drug_ids = get_all_drug_ids(slot, schedule)
        mentioned = []
        # Method 1: Direct match against drug_id (e.g. "dexamethasone_1")
        for did in drug_ids:
            if did.lower().replace("_", " ") in source_text.lower():
                mentioned.append(did)
        if not mentioned:
            # Method 2: Try to resolve each word/alias via med_resolve
            words = source_text.lower().split()
            for word in words:
                try:
                    r = resolve_drug(word, slot=slot)
                    if r.get("ok") and r.get("drug_id") in drug_ids:
                        mentioned.append(r["drug_id"])
                except Exception:
                    pass
        if not mentioned:
            return {
                "ok": False,
                "error": f"REJECTED: User's statement doesn't mention any Slot {slot} drugs. "
                         f"Statement: '{source_text[:100]}'. "
                         f"Expected mentions: {', '.join(drug_ids)}. "
                         f"If this is a genuine med confirmation, include the drug name."
            }

    entry = get_slot_entry(state, slot)
    drug_ids = get_all_drug_ids(slot, schedule)

    if DRY_RUN:
        print(f"[DRY-RUN] Would mark these drugs as taken at {now}: {drug_ids}")
        existing = {did: entry.get('drugs', {}).get(did, {}).get('status', 'pending')
                    for did in drug_ids}
        for did, st in existing.items():
            if st == 'taken':
                print(f"  {did}: already taken (would overwrite time)")
            else:
                print(f"  {did}: pending -> taken at {now}")
        return {"ok": True, "med": slot, "dry_run": True,
                "would_set": {did: now for did in drug_ids}}

    for did in drug_ids:
        entry.setdefault('drugs', {})[did] = {"status": "taken", "time": now}
        try:
            from med_supply import decrement
            decrement(did)
        except Exception:
            pass

    entry['overall'] = recalc_overall(slot, entry, schedule)
    state.setdefault('meds', {}).setdefault(slot, {})[today] = entry
    save_json(STATE_FILE, state)

    result = {
        "ok": True,
        "med": slot,
        "date": today,
        "overall": entry['overall'],
        "drugs": entry['drugs'],
        "file": str(STATE_FILE),
    }

    # Supply alerts: only show for drugs NOT in this slot (other slots' issues).
    # No point alerting "STOCK OUT" on a drug the user just took — they know.
    supply_alerts = []
    try:
        from med_supply import check_low as _check
        low_drugs = _check()
        drug_ids_lower = set(did.lower() for did in drug_ids)
        for d in low_drugs:
            if d.get('drug_id', '').lower() not in drug_ids_lower:
                if d['status'] == 'out_of_stock':
                    supply_alerts.append(f"STOCK OUT: {d['name']}")
                elif d['status'] == 'low':
                    supply_alerts.append(f"LOW: {d['name']} left {d['current']}")
    except Exception:
        pass

    if supply_alerts:
        result['supply_alerts'] = supply_alerts

    return result


def _source_mentions_drug(slot: str, drug_id: str, source_text: str | None) -> bool:
    if not source_text:
        return False
    lowered = source_text.lower()
    if drug_id.lower().replace("_", " ") in lowered or drug_id.lower() in lowered:
        return True
    for token in re.findall(r"[a-z0-9_-]+", lowered):
        try:
            resolved = resolve_drug(token, slot=slot)
        except Exception:
            continue
        if resolved.get("ok") and resolved.get("drug_id") == drug_id:
            return True
    return False


def confirm_compound(slot: str, compound_id: str, time_val: str | None = None,
                     source_text: str | None = None) -> dict:
    """Confirm all components of one approved compound in one recoverable transaction.

    Status and supply are prepared fully before either is written. If second-file
    commit fails, exact before-images are restored. This function never falls
    back to sequential component confirmation.
    """
    compound = COMPOUNDS.get(compound_id.lower())
    if compound is None or compound["slot"] != slot:
        return {"ok": False, "error": f"Unknown compound '{compound_id}' for slot {slot}"}
    drug_ids = compound["drug_ids"]
    now = time_val or get_now_hm()
    if not validate_time(now):
        return {"ok": False, "error": f"Invalid time: {now}"}
    lowered = (source_text or "").lower()
    if not COMPLETION_RE.search(lowered):
        return {"ok": False, "error": "REJECTED: source-backed intake completion wording required"}
    if "cc" not in re.findall(r"[a-z0-9_-]+", lowered):
        # Explicit component pair is also valid compound evidence.
        if not ("calcium" in lowered and "calcitriol" in lowered):
            return {"ok": False, "error": "REJECTED: source-backed CC or both component names required"}

    with _compound_lock():
        try:
            _recover_prepared_transaction()
        except RuntimeError as exc:
            return {"ok": False, "error": str(exc)}
        before = {path: path.read_bytes() if path.exists() else None for path in (STATE_FILE, SUPPLY_FILE)}
        state, schedule, supply = load_json(STATE_FILE), load_schedule(), load_json(SUPPLY_FILE)
        scheduled = set(get_all_drug_ids(slot, schedule))
        if not set(drug_ids).issubset(scheduled):
            return {"ok": False, "error": "REJECTED: CC components unavailable in active Slot C schedule"}
        supply_drugs = supply.get("drugs", {})
        missing_supply = [did for did in drug_ids if did not in supply_drugs]
        if missing_supply:
            return {"ok": False, "error": f"REJECTED: supply tracking missing {missing_supply}"}

        entry = get_slot_entry(state, slot)
        drugs = entry.setdefault("drugs", {})
        already_taken = [did for did in drug_ids if drugs.get(did, {}).get("status") == "taken"]
        if already_taken:
            # Compound duplicate is idempotent only when whole same-time event already exists.
            all_same = all(drugs.get(did, {}).get("status") == "taken" and drugs.get(did, {}).get("time") == now for did in drug_ids)
            if all_same:
                return {"ok": True, "idempotent": True, "compound": compound_id, "med": slot, "date": get_today(), "drugs": {did: drugs[did] for did in drug_ids}}
            return {"ok": False, "error": f"REJECTED: partial/conflicting CC state for {already_taken}; create HOLD, do not overwrite"}

        for did in drug_ids:
            drugs[did] = {"status": "taken", "time": now}
        entry["overall"] = recalc_overall(slot, entry, schedule)
        state.setdefault("meds", {}).setdefault(slot, {})[get_today()] = entry

        supply_result = {}
        for did in drug_ids:
            item = supply_drugs[did]
            current = item.get("current")
            if current is not None:
                item["current"] = max(0, current - 1)
            supply_result[did] = item.get("current")
        supply["last_updated"] = get_today()

        if DRY_RUN:
            return {"ok": True, "dry_run": True, "compound": compound_id, "med": slot, "would_set": {did: now for did in drug_ids}, "would_supply": supply_result}
        try:
            _write_transaction(before)
            _atomic_json_write(STATE_FILE, state)
            _atomic_json_write(SUPPLY_FILE, supply)
            TXN_FILE.unlink(missing_ok=True)
            _fsync_dir(TXN_FILE.parent)
        except Exception as exc:
            rollback_errors = []
            for path in (STATE_FILE, SUPPLY_FILE):
                try:
                    _restore_exact(path, before[path])
                except Exception as rollback_exc:
                    rollback_errors.append(f"{path.name}: {rollback_exc}")
            if not rollback_errors:
                try:
                    TXN_FILE.unlink(missing_ok=True)
                    _fsync_dir(TXN_FILE.parent)
                except Exception as rollback_exc:
                    rollback_errors.append(f"transaction journal: {rollback_exc}")
            if rollback_errors:
                return {"ok": False, "error": f"COMPOUND_COMMIT_AND_ROLLBACK_FAILED: {exc}; {'; '.join(rollback_errors)}"}
            return {"ok": False, "error": f"COMPOUND_COMMIT_FAILED_ROLLED_BACK: {exc}"}

    return {"ok": True, "compound": compound_id, "med": slot, "date": get_today(), "overall": entry["overall"], "drugs": {did: drugs[did] for did in drug_ids}, "supply": supply_result}


@locked_mutation
def confirm_drug(slot: str, drug_id: str, time_val: str | None = None,
                 source_text: str | None = None,
                 intent: str = "CONFIRM_INTAKE") -> dict:
    """Mark a single drug as taken only with source-backed intent."""
    global DRY_RUN
    state = load_json(STATE_FILE)
    schedule = load_schedule()
    today = get_today()
    now = time_val or get_now_hm()

    if intent != "CONFIRM_INTAKE" or not _source_mentions_drug(slot, drug_id, source_text):
        return {"ok": False, "error": "REJECTED: source-backed CONFIRM_INTAKE required"}

    entry = get_slot_entry(state, slot)

    if DRY_RUN:
        existing = entry.get('drugs', {}).get(drug_id, {}).get('status', 'pending')
        print(f"[DRY-RUN] Would mark {drug_id} in slot {slot}: {existing} -> taken at {now}")
        return {"ok": True, "med": slot, "drug": drug_id, "dry_run": True,
                "would_set": {"time": now}}

    entry.setdefault('drugs', {})[drug_id] = {"status": "taken", "time": now}
    entry['overall'] = recalc_overall(slot, entry, schedule)

    state.setdefault('meds', {}).setdefault(slot, {})[today] = entry
    save_json(STATE_FILE, state)

    supply_info = None
    try:
        from med_supply import decrement
        supply_info = decrement(drug_id)
    except Exception:
        pass

    result = {
        "ok": True,
        "med": slot,
        "drug": drug_id,
        "date": today,
        "overall": entry['overall'],
        "drugs": entry['drugs'],
        "file": str(STATE_FILE),
    }
    if supply_info and supply_info.get('alert'):
        result['supply_alert'] = supply_info['alert']
    return result


def check(slot: str, drug_id: str | None = None) -> dict:
    state = load_json(STATE_FILE)
    today = get_today()
    entry = state.get('meds', {}).get(slot, {}).get(today, {})

    if isinstance(entry, str):
        return {"med": slot, "date": today, "confirmed": entry == "confirmed", "overall": "completed" if entry == "confirmed" else "pending"}
    if isinstance(entry, dict) and 'status' in entry and 'drugs' not in entry:
        return {"med": slot, "date": today, "confirmed": entry.get('status') == 'confirmed', "overall": "completed"}

    if drug_id:
        drug_entry = entry.get('drugs', {}).get(drug_id, {})
        return {"med": slot, "drug": drug_id, "date": today, "status": drug_entry.get('status', 'pending'), "time": drug_entry.get('time')}

    return {"med": slot, "date": today, "overall": entry.get('overall', 'pending'), "confirmed": entry.get('overall') == 'completed', "drugs": entry.get('drugs', {})}


def status() -> dict:
    state = load_json(STATE_FILE)
    today = get_today()
    out = {"date": today, "meds": {}}
    for slot in ALL_SLOTS:
        entry = state.get('meds', {}).get(slot, {}).get(today, {})
        if isinstance(entry, str):
            out["meds"][slot] = {"overall": "completed" if entry == "confirmed" else "pending", "drugs": {}}
            continue
        if isinstance(entry, dict) and 'status' in entry and 'drugs' not in entry:
            out["meds"][slot] = {"overall": "completed", "drugs": {}}
            continue
        out["meds"][slot] = {"overall": entry.get('overall', 'pending'), "drugs": entry.get('drugs', {})}
    return out


@locked_mutation
def reset_slot(slot: str, drug_id: str | None = None) -> dict:
    global DRY_RUN
    state = load_json(STATE_FILE)
    today = get_today()

    if slot not in state.get('meds', {}):
        return {"ok": False, "error": f"No data for {slot}"}

    if drug_id:
        entry = state.setdefault('meds', {}).get(slot, {}).get(today, {})
        if not isinstance(entry, dict):
            return {"ok": False, "error": f"No drug-level data for {slot} today"}
        if drug_id not in entry.get('drugs', {}):
            return {"ok": False, "error": f"Drug {drug_id} not found in slot {slot}"}
        if DRY_RUN:
            print(f"[DRY-RUN] Would reset {drug_id} in slot {slot}")
            return {"ok": True, "med": slot, "drug": drug_id, "dry_run": True}
        entry['drugs'].pop(drug_id, None)
        entry['overall'] = recalc_overall(slot, entry, load_schedule())
        save_json(STATE_FILE, state)
        return {"ok": True, "med": slot, "drug": drug_id, "reset": True}

    if DRY_RUN:
        print(f"[DRY-RUN] Would reset ALL of slot {slot}")
        return {"ok": True, "med": slot, "dry_run": True}
    state['meds'][slot].pop(today, None)
    save_json(STATE_FILE, state)
    return {"ok": True, "med": slot, "reset": True}


@locked_mutation
def update_time(slot: str, new_time: str) -> dict:
    global DRY_RUN
    state = load_json(STATE_FILE)
    schedule = load_schedule()
    today = get_today()

    time_val = validate_time(new_time)
    if not time_val:
        return {"ok": False, "error": f"Invalid time: {new_time}. Use HH:MM format."}

    entry = state.get('meds', {}).get(slot, {}).get(today, {})
    if not entry:
        return {"ok": False, "error": f"{slot} not recorded today"}

    if DRY_RUN:
        print(f"[DRY-RUN] Would update {slot} times to {time_val}")
        return {"ok": True, "med": slot, "date": today, "time": time_val, "dry_run": True}

    if isinstance(entry, str) or (isinstance(entry, dict) and 'status' in entry and 'drugs' not in entry):
        if isinstance(entry, str):
            drug_ids = get_all_drug_ids(slot, schedule)
            entry = {"overall": "completed", "drugs": {did: {"status": "taken", "time": time_val} for did in drug_ids}}
        elif isinstance(entry, dict) and 'status' in entry:
            drug_ids = get_all_drug_ids(slot, schedule)
            entry = {"overall": "completed", "drugs": {did: {"status": "taken", "time": time_val} for did in drug_ids}}
        state['meds'][slot][today] = entry
        save_json(STATE_FILE, state)
        return {"ok": True, "med": slot, "date": today, "time": time_val, "migrated": True}

    if 'drugs' in entry:
        for did, drug_entry in entry['drugs'].items():
            if drug_entry.get('status') == 'taken':
                drug_entry['time'] = time_val
        save_json(STATE_FILE, state)

    return {"ok": True, "med": slot, "date": today, "time": time_val}


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    global DRY_RUN

    # Parse --dry-run first (before any operation)
    if '--dry-run' in sys.argv:
        DRY_RUN = True
        sys.argv.remove('--dry-run')
        print("[DRY-RUN MODE] No data will be written\n")

    if len(sys.argv) < 2:
        print("Usage: med_confirm.py <LETTER|--check|--status|--reset|--update> [drug_id] [--at HH:MM]")
        return 1

    arg = sys.argv[1]

    # ── --check ──
    if arg == "--check":
        if len(sys.argv) < 3:
            print("Need med letter")
            return 1
        slot = sys.argv[2].upper()
        drug_id = sys.argv[3].lower() if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else None
        result = check(slot, drug_id)

    # ── --status ──
    elif arg == "--status":
        result = status()

    # ── --reset ──
    elif arg == "--reset":
        if len(sys.argv) < 3:
            print("Need med letter")
            return 1
        slot = sys.argv[2].upper()
        drug_id = sys.argv[3].lower() if len(sys.argv) > 3 and not sys.argv[3].startswith('--') else None
        result = reset_slot(slot, drug_id)

    # ── --update ──
    elif arg == "--update":
        if len(sys.argv) < 4:
            print("Need med letter and time: --update A 08:15")
            return 1
        result = update_time(sys.argv[2].upper(), sys.argv[3])

    # ── --at ──
    elif arg == "--at":
        if len(sys.argv) < 4:
            print("Need med letter and time: --at A 08:15")
            return 1
        time_val = validate_time(sys.argv[3])
        if not time_val:
            print(f"Invalid time: {sys.argv[3]}. Use HH:MM format.")
            return 1
        slot = sys.argv[2].upper()
        # Check for --source-text after the --at args
        source_text = None
        if len(sys.argv) > 4 and sys.argv[4] == "--source-text" and len(sys.argv) > 5:
            source_text = sys.argv[5]
        result = confirm_slot(slot, time_val, source_text=source_text)

    elif arg.startswith("--"):
        print(f"Unknown option: {arg}")
        return 1

    # ── Compound confirmation ──
    elif arg == "--compound":
        if len(sys.argv) < 4:
            print("Need slot and compound: C --compound cc")
            return 1
        slot = sys.argv[2].upper()
        compound_id = sys.argv[3].lower()
        time_val = None
        source_text = None
        i = 4
        while i < len(sys.argv):
            if sys.argv[i] == "--at" and i + 1 < len(sys.argv):
                time_val = validate_time(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--source-text" and i + 1 < len(sys.argv):
                source_text = sys.argv[i + 1]
                i += 2
            else:
                i += 1
        if time_val is None and any(arg == "--at" for arg in sys.argv[4:]):
            print("Invalid --at time. Use HH:MM format.")
            return 1
        result = confirm_compound(slot, compound_id, time_val, source_text=source_text)

    # ── Default: confirm mode ──
    else:
        slot = arg.upper()
        if slot not in ALL_SLOTS:
            print(f"Invalid slot: {slot}. Use A/B/C/D/E")
            return 1

        drug_id = None
        compound_id = None
        time_val = None
        time_supplied = False
        source_text = None

        i = 2
        while i < len(sys.argv):
            if sys.argv[i] == "--compound" and i + 1 < len(sys.argv):
                compound_id = sys.argv[i + 1].lower()
                i += 2
            elif sys.argv[i] == "--at" and i + 1 < len(sys.argv):
                time_supplied = True
                time_val = validate_time(sys.argv[i + 1])
                i += 2
            elif sys.argv[i] == "--source-text" and i + 1 < len(sys.argv):
                source_text = sys.argv[i + 1]
                i += 2
            elif not sys.argv[i].startswith('--'):
                fragment = sys.argv[i].lower()
                schedule = load_schedule()
                matched = find_drug_by_fragment(slot, fragment, schedule)
                if matched:
                    drug_id = matched
                else:
                    schedule = load_schedule()
                    valid = get_all_drug_ids(slot, schedule)
                    print(f"ERROR: '{fragment}' not found in slot {slot}.")
                    print(f"  Valid drug IDs for slot {slot}: {', '.join(valid)}")
                    print(f"  Run: python3 med_resolve.py '{fragment}' --slot {slot}")
                    return 1
                i += 1
            else:
                i += 1

        if compound_id:
            if time_supplied and time_val is None:
                result = {"ok": False, "error": "Invalid --at time. Use HH:MM format."}
            else:
                result = confirm_compound(slot, compound_id, time_val, source_text=source_text)
        elif drug_id:
            result = confirm_drug(slot, drug_id, time_val, source_text=source_text)
        else:
            result = confirm_slot(slot, time_val, source_text=source_text)

    print(json.dumps(result, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
