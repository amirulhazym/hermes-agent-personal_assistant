# Fix draft: med_confirm.py `--at` validation gap (phantom "20:00")

**Date:** 2026-07-10. **Status:** DRAFT — not applied (overhaul freeze; analyst role). Proven in isolated `/tmp` HOME with 7 tests; live `~/.hermes` untouched.

## Root cause
`med_confirm.py` line: `now = time_val or get_now_hm()`. With `--at`, `time_val` is written verbatim — no validation. `get_now_hm()` is MYT-correct (Asia/Kuala_Lumpur), so the bug is NOT a timezone issue; it is a missing sanity check on the caller-supplied time. A misparse ("8" → 20:00) or a wrong value silently poisons `chain_calc` (A@20:00 → B ready ~21:00 → B never fires → missed reminders).

## Fix #1 — validate `--at` time
Add after `validate_time()`:

```python
# ── Audit log (fix #3) ───────────────────────────────────────────────────────
AUDIT_LOG = Path(os.environ.get("MED_AUDIT_LOG",
                                str(Path.home() / ".hermes" / "med_confirm_audit.log")))

def _audit_write(slot, drug_id, time_val, source_text, caller, ok, detail):
    """One JSON line per med_confirm action. Fail-open."""
    try:
        rec = {
            "ts": datetime.now(ZoneInfo("Asia/Kuala_Lumpur")).strftime("%Y-%m-%d %H:%M:%S"),
            "slot": slot, "drug": drug_id, "time": time_val,
            "source": (source_text or "")[:150], "caller": caller or "manual",
            "argv": " ".join(sys.argv[1:])[:300], "ok": ok, "detail": detail,
        }
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass

def _get_slot_scheduled_hour(slot):
    try:
        sched = load_schedule()
        node = sched.get('meds', {}).get(slot, {})
        t = node.get('time') or node.get('scheduled') or ''
        mm = re.search(r'(\d{1,2}):(\d{2})', str(t))
        if mm: return int(mm.group(1))
    except Exception:
        pass
    return {'A':6,'B':8,'C':12,'D':16,'E':20}.get(slot)

def _validate_at_time(time_val, slot):
    """Returns (True, None) or (False, reason)."""
    if not time_val: return True, None
    h, m = (int(x) for x in time_val.split(':'))
    now = datetime.now(ZoneInfo("Asia/Kuala_Lumpur"))
    t_today = now.replace(hour=h, minute=m, second=0, microsecond=0)
    if t_today > now:
        return False, (f"time '{time_val}' is in the FUTURE (now {now:%H:%M}); "
                       f"refusing - a med cannot be logged before it is taken")
    sched_h = _get_slot_scheduled_hour(slot)
    if sched_h is not None:
        logged_pm, sched_pm = h >= 12, sched_h >= 12
        if logged_pm != sched_pm:
            part = "PM (evening/night)" if logged_pm else "AM (morning)"
            exp = "AM" if not sched_pm else "PM"
            return False, (f"time '{time_val}' is {part} but Slot {slot} is a {exp} slot "
                           f"(scheduled ~{sched_h:02d}:00); refusing cross-half-day misparse")
    return True, None
```

Wire into `confirm_slot` and `confirm_drug` (after `now = time_val or get_now_hm()`):
```python
    if time_val is not None:
        if source_text is None:
            _audit_write(slot, None, time_val, None, CALLER, False,
                         "REJECTED: --at used without --source-text")
            return {"ok": False, "error": "REJECTED: --at requires --source-text"}
        ok, err = _validate_at_time(time_val, slot)
        if not ok:
            _audit_write(slot, None, time_val, source_text, CALLER, False, err)
            return {"ok": False, "error": f"REJECTED: {err}"}
```
Add `from zoneinfo import ZoneInfo` to imports; add global `CALLER = os.environ.get("MED_CONFIRM_CALLER", "manual")` after `DRY_RUN = False`.

## Fix #2 — `--at` requires `--source-text`
In `main()`, both the `--at` branch and the default-confirm branch: if `time_val` is set and `source_text is None` → print rejection and `return 1`. Also add `--caller` parse (top of main, after `--dry-run`) and skip `--caller` in the default-branch arg loop (`elif sys.argv[i] == "--caller" and i+1 < len(sys.argv): i += 2`) — else its value is misread as a drug fragment (caught in testing).

Add `source_text` param to `confirm_drug(slot, drug_id, time_val=None, source_text=None)` and pass `source_text=source_text` from main.

## Fix #3 — per-write audit log
Call `_audit_write(..., ok=True, detail=...)` right after `save_json(...)` in both `confirm_slot` and `confirm_drug`. Log location `~/.hermes/med_confirm_audit.log` (override with `MED_AUDIT_LOG` env).

## Companion change — hook (required by Fix #2)
`hooks/med-auto-confirm/handler.py` currently calls `med_confirm.py <slot> --at <time>` with NO `--source-text` → Fix #2 would reject it. Update:
```python
    cmd = [sys.executable, str(CONFIRM_SCRIPT), slot]
    if drug_id: cmd.append(drug_id)
    if time_str:
        cmd += ["--at", time_str, "--source-text", message, "--caller", "hook"]
    else:
        cmd += ["--source-text", message, "--caller", "hook"]
```

## Test results (isolated HOME, all pass)
| Test | Command | Result |
|------|---------|--------|
| T1 | `A --at 20:00 --source-text test` | REJECT (future) |
| T2 | `A --at 06:30 --source-text "dah makan A 6.30am" --caller agent` | SUCCESS (06:30) |
| T3 | `A --source-text "dah makan A" --caller agent` | SUCCESS (current time) |
| T4 | `A --at 06:30` (no source-text) | REJECT (requires --source-text) |
| T5 | `E --at 08:00 --source-text "dah makan E 8am" --caller agent` | REJECT (cross-half-day) |
| T6 | `C --at 12:00 --source-text "dah makan dexa 12pm" --caller agent` | SUCCESS (12:00) |
| T7 | `A --at 20:00 --source-text x --dry-run` | DRY-RUN + REJECT, file unchanged |

Audit log captured every action with `caller` + `argv`. See `references/isolated-patch-test.md` (verification-before-completion skill) for the isolated-HOME test harness.

## Caveats
- Future-time rejection means pre-logging a future dose is unsupported (log at actual intake instead). Add `--allow-future` if ever needed.
- Cross-half-day (not tight ±N-min) is deliberate, to respect flexibly-late real intake.
- Audit log is fail-open.
