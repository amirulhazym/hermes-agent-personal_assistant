# med-auto-confirm Hook — Structural Enforcement (VERIFIED 2026-07-09)

## Problem
The "run med_confirm.py FIRST" rule in SKILL.md is instruction-level. Under
distracted/excited model state it gets skipped. Result (2026-07-09): user said
"A dah ambil 6am", agent acknowledged ✅ verbally but NEVER ran med_confirm.py.
med-status.json[2026-07-09][A] stayed empty → cron read A=pending → fired 2
reminders. Recurring daily rage-loop.

## Hook Infra Reality (from gateway/hooks.py)
- Events: `gateway:startup`, `session:start`, `session:end`, `session:reset`,
  `agent:start`, `agent:step`, `agent:end`, `command:*`
- `HookRegistry.emit()` DISCARDS return values (line 191-198). `emit_collect`
  exists but is NEVER called in run.py → no event can block/modify a response.
- Doc string: "Errors in hooks are caught and logged but never block the main
  pipeline." Fail-open by design.
- `agent:end` carries `response` but fires AFTER delivery — too late to gate.
- `agent:start` fires BEFORE the agent processes the inbound message, with
  `context['message']` (truncated 500 chars).

## Conclusion
A "pre-delivery gate that blocks response" is IMPOSSIBLE with current hooks.
The achievable structural guarantee is a SIDE-EFFECT on `agent:start`:
parse the inbound message, and if it's a med-confirmation not yet in
med-status.json, run `med_confirm.py` as a side-effect. By the time the agent
reads the message, state is already correct → cron won't fire, agent has context.

## Implementation
Hook dir: `~/.hermes/hooks/med-auto-confirm/`
- `HOOK.yaml`: `name: med-auto-confirm`, `events: [agent:start]`
- `handler.py`: `handle(event_type, context)`:
  1. if event_type != "agent:start": return
  2. msg = context.get("message", "")
  3. parse slot/drug + time via same regex/resolve logic as med_confirm.py
  4. if matched AND med-status.json[today][slot] missing →
     `subprocess.run(["python3", MED_CONFIRM, slot, "--at", time])`
  5. wrap in try/except — on ANY error, log + return (fail-open)

### Safety
- `med_confirm.py` is idempotent (overwrites same-day entry with same data).
  Double-run (hook + agent both call it) is harmless.
- NEVER run `chain_monitor.sh` from the hook — it writes live reminder state.
- Test against a COPY of med-status.json first (--dry-run principle).
  The hook writes to the real file by design, so validate parse logic on a copy
  before deploying.

## Regression Test (proves bug gone)
```python
# Simulate: user msg "A dah ambil 6am" -> after pipeline, state must exist
import json, datetime
d = json.load(open('/home/ubuntu/.hermes/med-status.json'))
today = datetime.date.today().isoformat()
assert today in d['meds']['A'], "BUG LIVE: A not logged after confirm"
```
Red now (before hook), green after hook deployed + agent acknowledges.

## Deploy note
Hook loads on `gateway:startup` via `discover_and_load()`. After writing the
hook dir, RESTART the gateway for it to load. Verify with:
`search_files ~/.hermes/hooks` → med-auto-confirm dir present, then check
gateway startup log for "[hooks] Loaded hook 'med-auto-confirm'".

NOTE: Despite `hooks: {}` in config.yaml (meaning no ADDITIONAL config
overrides), Hermes auto-discovers all Python handlers in the hooks/
directory by convention. The hook IS active even when hooks config is empty.

---

## KNOWN FAILURE MODES (Updated 2026-07-15)

The hook is NOT a silver bullet. These gaps have caused missed confirmations
REPEATEDLY (July 9, 10, 12, 15, 2026). The agent MUST ALWAYS run med_confirm.py
manually as the PRIMARY mechanism — the hook is only a SECONDARY safety net.

### F1: "Done" missing from COMPLETE_RE (Discovered 2026-07-15)

```python
COMPLETE_RE = re.compile(
    r"\b(dah\s*makan|sudah\s*makan|dah\s*ambil|dah\s*telan|"
    r"dah\s*selesa[ii]kan?|selesai|siap|took|ate|confirm|"
    r"dah\s*confirm|telan|makan)\b",
)
```

**"Done" is NOT in this pattern.** User messages like "Done akurit+pyridoxine jam
6.45am" are silently skipped. `is_med_confirmation()` returns False, the hook
does nothing, and the agent later gets blamed.

**Fix:** Add `\bdone\b` to COMPLETE_RE.

### F2: akurit regex fails on "+" concatenation (Discovered 2026-07-15)

```python
(r"\bakurit[- ]?(2|4)\b", "A", "akurit_2"),
```

This pattern requires a dash (`-`), space (` `), or nothing between "akurit" and
"2"/"4". User often writes "akurit+pyridoxine" (plus-separated stack). The `+`
is not `[- ]` and not `2|4`, so **the entire pattern fails**.

Only `pyridoxine` (second drug in the stack) matches via its own pattern, giving
a PARTIAL confirmation (1/2 drugs) → cron keeps firing reminders.

| User input | Hook matches? |
|------------|---------------|
| `akurit-2` | ✅ `akurit_2` |
| `akurit 4` | ✅ `akurit_2` (legacy mapped) |
| `akurit2` | ✅ `akurit_2` |
| `akurit+pyridoxine` | ❌ No match — `+` breaks the pattern |

**Fix:** `\bakurit\b` bare match should also work, with optional `[- ]?(2|4)?`.
Or add a separate pattern for concatenated forms.

### F3: TIME_RE doesn't handle dot "." separator (Discovered 2026-07-15)

```python
TIME_RE = re.compile(
    r"(?:pukul|jam|at|@|pada)\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?",
    re.IGNORECASE,
)
```

The pattern requires `:` as separator (e.g., "6:45"). But users often write
"6.45am" with a DOT. The result: "jam 6.45am" → parsed as "jam 6" at midnight
→ time is **06:00, not 06:45**.

**Fix:** Extend group 2 to accept both `:` and `.`: `(?:[.:](\d{2}))?`

### F4: `_already_logged()` treats "partial" as blocked (Discovered 2026-07-15)

```python
if entry.get("overall") in ("completed", "partial"):
    return True  # PARTIAL BLOCKS RETRY
```

When the hook writes a PARTIAL entry (only 1 of 2 drugs for A), subsequent
opportunities to write the missing drug are blocked because `_already_logged()`
returns True for `overall == "partial"`. The partial entry becomes PERMANENTLY
stuck — nothing will complete it until the user manually runs med_confirm.py.

**Fix:** The hook should return False for "partial" so a later message can
complete the missing drug(s). Only "completed" should block retry.

### F5: Hook runs on secondary messages, not always the trigger (Observed 2026-07-15)

The hook fires on `agent:start`. It processes EVERY inbound message through
the regexes. But it SILENTLY skips messages where:
- `is_med_confirmation()` returns False (F1)
- No slot/drug resolves (F2)
- TIME_RE misparses (F3)

There is NO feedback to the agent when the hook takes action or skips. The
agent must check med-status.json after every user confirmation to verify the
hook (or its own manual call) actually wrote the data.

### Agent-Side Mitigation (until hooks are patched)

**The agent MUST NOT rely on the hook alone.** After every user med confirmation:

1. **EXECUTE** `med_confirm.py <slot> <drug_id> --at <HH:MM>` IMMEDIATELY
2. **VERIFY** the state was written:
   ```bash
   python3 ~/.hermes/scripts/chain_calc.py --check <slot>
   # or: python3 ~/.hermes/scripts/med_confirm.py --check <slot>
   ```
3. **MATCH** the result — if overall != "completed" for a full-slot confirm,
   or if the drug list is incomplete, dry-run and re-confirm
4. **RESET REMINDER** count: the confirm script should do this automatically,
   but verify chain-state.json was updated:
   ```bash
   python3 -c "import json; d=json.load(open('~/.hermes/chain-state.json'));
   print(d.get('reminder_counts',{}).get('<SLOT>','cleared'))"
   ```

### Recurring Bug Pattern (cited from user)

This exact sequence has happened on **at least 5 occasions**:
1. User confirms med ✅ in chat
2. Agent says "noted ✅" without running med_confirm.py
3. Hook either misses (F1-F4) or was never the PRIMARY mechanism
4. Cron fires reminders for hours
5. User gets angry, asks "why does this keep happening"

The fix is structural: the agent must ALWAYS run med_confirm.py as step 1,
use the hook as step 2 (safety net), and verify state as step 3 (audit).
