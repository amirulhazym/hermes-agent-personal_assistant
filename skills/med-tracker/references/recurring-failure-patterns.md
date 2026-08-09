# Recurring Failure Patterns — Medication Tracking System

> Last updated: 2026-07-15
> Incidents covered: 3 Jul, 9 Jul, 10 Jul, 15 Jul 2026

## Critical Pattern: Agent Verbally Acknowledges But Never Writes State

**This is the #1 recurring failure.** Every incident follows the same shape:

```
User: "Done akurit+pyridoxine jam 6.45am"
→ Agent: "Done, noted ✅"          ← VERBAL ONLY, no state write
→ Hook: misses (regex gap)         ← backup mechanism fails
→ Cron: keeps firing reminders     ← state file still empty/partial
→ User: furious                    ← same problem, nth time
```

The fix is structural, not regex-based: **agent MUST run `med_confirm.py` BEFORE responding.** The hook is a backup, not the primary mechanism.

## COMPLETE_RE Gap — "Done" Missing (Active Bug)

**File:** `~/.hermes/hooks/med-auto-confirm/handler.py` line 51-55

```python
COMPLETE_RE = re.compile(
    r"\b(dah\s*makan|sudah\s*makan|dah\s*ambil|dah\s*telan|dah\s*selesa[ii]kan?"
    r"|selesai|siap|took|ate|confirm|dah\s*confirm|telan|makan)\b",
    re.IGNORECASE,
)
```

**"Done" is NOT in this list.** This is the user's most common confirmation word ("Done akurit+pyridoxine jam 6.45am"). When the user says "Done", `is_med_confirmation()` returns False → hook never fires → no state written.

**Also missing:** "already took", "taken", "aku dah", "lepas" and other natural Manglish variants.

**Fix:** Add `\bdone\b` to COMPLETE_RE.

## TIME_RE Gap — Dot Separator (Active Bug)

**File:** `handler.py` line 80-83

```python
TIME_RE = re.compile(
    r"(?:pukul|jam|at|@|pada)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
)
```

Only `:` is recognized as hour-minute separator. User wrote "jam 6.45am" → parsed as "06:00" instead of "06:45".

**Fix:** Accept `.` as separator: `[.:]` instead of `:`.

## DRUG_MAP Gap — `akurit+pyridoxine` (Fixed 2026-07-11)

Pattern G fix added `\bakurit\b` fallback. Original `\bakurit[- ]?(2|4)\b` required dash/space before the number. `+` was not recognized.

## `_already_logged()` Partial Block (Fixed 2026-07-15 10:05)

Original code blocked all retries for any slot with existing drugs:
```python
if entry.get("overall") in ("completed", "partial"):  # BLOCKS
    return True
if entry.get("drugs"):  # ALSO BLOCKS
    return True
```

Fixed version only blocks "completed", allows "partial" correction.

## `is_confirmed()` — "partial" ≠ confirmed (By Design)

```python
def is_confirmed(slot: str) -> bool:
    return get_drug_level_overall(slot, schedule) == 'completed'
```

Chain monitor fires until overall == "completed". One missed drug = infinite reminders.

## Debugging Methodology

When a med confirmation failure is reported:

1. `python3 ~/.hermes/scripts/med_confirm.py --status` → check today's state
2. `cat ~/.hermes/chain-state.json` → check reminder counts
3. `grep "YYYY-MM-DD" ~/.hermes/logs/med-auto-confirm-audit.log` → hook audit trail
4. `stat ~/.hermes/hooks/med-auto-confirm/handler.py` → when was it last patched?
5. `diff handler.py.bak handler.py` → what changed?
6. Simulate COMPLETE_RE and DRUG_MAP against the user's exact message
7. Check `_already_logged()` — did it block a correction?

## Timeline of Fix Attempts (All Partial)

| Date | What Was Fixed | What Was MISSED |
|------|---------------|-----------------|
| 3 Jul | Drug-level tracking | Agent still verbal-only |
| 9 Jul | med-auto-confirm hook | "Done" not in COMPLETE_RE |
| 11 Jul | Pattern G: `\bakurit\b`, SLOT_RE tighten | "Done" STILL missing |
| 15 Jul 10:05 | `_already_logged()` partial unblock | **"Done" STILL missing** |

Every fix addressed the symptom visible at that moment. No one went back to add "Done" to COMPLETE_RE — the user's most common confirmation word has never been recognized.
