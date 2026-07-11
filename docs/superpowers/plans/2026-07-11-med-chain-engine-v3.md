# Medication Chain Engine v3 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the LLM auto-linearizing chain logic with a deterministic constraint-solver engine that is the source of truth for medication slot timing; the LLM only explains. Fixes the repeated "E presented as dependent on B→C→D" confusion bug.

**Architecture:** A deterministic rule engine (`solve.py`) topologically propagates slot times along explicit constraint edges only. `resolve_conflict.py` applies a priority stack when a user value clashes with a rule. `trace.py` logs every solve. `validate_semantic.py` checks LLM output against solver truth. `route.py` decides low-complexity (send) vs high-complexity (review). `why.py` explains a slot. Integrated into the live pipeline by patching `chain_calc.py` to call the solver (with the existing logic kept as a safe fallback) and a med-keyword hook.

**Tech Stack:** Python 3 (VPS venv at `~/.hermes/hermes-agent/venv`). `pytest` for tests (already used by `test_med_auto_confirm.py`). Pure stdlib for the engine (no new deps). JSON for `rules.json`.

## Global Constraints

- **Deterministic source of truth** — LLM only explains, never computes slot times. (Spec Purpose)
- **Medication-only pilot, domain-specific, versioned** (`schema_version`). No generic engine until a 2nd domain exists. (Spec Pilot Philosophy)
- **NO PC→VPS copy** — implement directly on the VPS (`~/.hermes/scripts/med_chain/`). (Spec Notes)
- **Freeze is real** — must NOT break live med reminders. `chain_calc.py` patch keeps existing behavior as a fallback; engine runs safely behind it. (AGENTS.md)
- **Tests required, TDD** — every module ships with a failing test first, then minimal implementation. (test-driven-development)
- **Apply on VPS, verify on VPS** — run pytest with `~/.hermes/hermes-agent/venv/bin/python -m pytest`.

## Spec inconsistency — RESOLVED (external-audit finding)

The spec example "input C at 1pm → D=5pm, E=9:43pm (untouched), A/B untouched" is **internally contradictory**:
- `rule_005` marks `E` as `independent` (priority 100).
- `rule_004` is `fixed_offset B→E 12h` (priority 95).
- If `B` is unknown, `E` cannot be derived from `B`, so `E` is genuinely untouched (no time). The "9:43pm" value implicitly assumes `B=9:43am`, which is never stated.

**Resolved semantics (used by all tasks/tests):**
1. Solver propagates **forward only** along edges (`from` known → derive `to`). It never back-solves (e.g., `C` known does NOT derive `B`).
2. An `independent` slot is user-controlled and is **never overridden** by a lower-priority derivation.
3. A derivation (`fixed_gap`/`fixed_offset`) applies only when its `from` slot is known AND its `to` slot is not already set by the user / higher priority.
4. **Invariant (regression #17):** `E` must NEVER be derived from `C`. `E` depends only on `B` (via `rule_004`) or is independent.

So for "C at 1pm": `D = C+4h = 17:00`; `E` is untouched (B unknown); `A`,`B` untouched. The engine asserts `E != C + anything`.

## File Structure

```
~/.hermes/scripts/med_chain/
  rules.json                 # Layer 1: constraint schema v1 (seed rules from spec)
  solve.py                   # Layer 2: topological constraint solver
  resolve_conflict.py        # Layer 2.5: priority stack
  trace.py                   # Layer 3: append-only JSONL execution trace
  validate_semantic.py       # Layer 5: LLM-output vs solver truth
  route.py                   # Layer 6: low/high complexity router
  why.py                     # Explainability API
  chain_review.py            # Layer 7 (optional): rule-based reviewer
  tests/
    test_solver.py           # C=13:00 -> D=17:00, E untouched
    test_conflicts.py        # user(60) vs rule(95) -> rule wins
    test_offsets.py          # E = B+12h invariant
    test_regression.py       # Bug #17: "E ikut C" -> permanent fail
```

Integration (separate tasks, freeze-safe):
- `chain_calc.py` (existing) → import solver, call it; fall back to current logic on any error.
- Med-keyword hook → auto-inject engine on med intents.

---

### Task 1: Constraint schema `rules.json`

**Files:**
- Create: `~/.hermes/scripts/med_chain/rules.json`

**Interfaces:** None (seed data consumed by `solve.py` in Task 2).

- [ ] **Step 1: Write `rules.json`**

```json
{
  "schema_version": 1,
  "domain": "medication",
  "constraints": [
    {"id": "rule_001", "type": "min_gap",    "from": "A", "to": "B", "hours": 1,  "priority": 95},
    {"id": "rule_002", "type": "fixed_gap",  "from": "B", "to": "C", "hours": 4,  "priority": 95},
    {"id": "rule_003", "type": "fixed_gap",  "from": "C", "to": "D", "hours": 4,  "priority": 95},
    {"id": "rule_004", "type": "fixed_offset","from": "B", "to": "E", "hours": 12, "priority": 95},
    {"id": "rule_005", "type": "independent", "slot": "E",              "priority": 100},
    {"id": "rule_006", "type": "independent", "slot": "A",              "priority": 100}
  ]
}
```

- [ ] **Step 2: Validate it parses**

Run: `~/.hermes/hermes-agent/venv/bin/python -c "import json; d=json.load(open('/home/ubuntu/.hermes/scripts/med_chain/rules.json')); print('OK', len(d['constraints']))"`
Expected: `OK 6`

- [ ] **Step 3: Commit (local repo only — spec says NO PC→VPS copy; this file lives on VPS, so just confirm on VPS)**

```bash
# on VPS, no git needed for the engine dir; verify presence only
ls -l ~/.hermes/scripts/med_chain/rules.json
```

---

### Task 2: Constraint solver `solve.py` (RED)

**Files:**
- Create: `~/.hermes/scripts/med_chain/tests/test_solver.py`
- Create: `~/.hermes/scripts/med_chain/solve.py`

**Interfaces:**
- Consumes: `rules.json` path.
- Produces: `solve(constraints, fixed_slots: dict[str, datetime.time]) -> dict` with keys `slots`, `untouched`, `rules_fired`, `conflicts`.

- [ ] **Step 1: Write failing test**

```python
# tests/test_solver.py
from datetime import time
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solve import solve, load_rules

def test_c_at_1pm_derives_d_not_e():
    rules = load_rules(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rules.json"))
    result = solve(rules["constraints"], {"C": time(13, 0)})
    assert result["slots"]["D"] == time(17, 0), result["slots"]
    assert "E" not in result["slots"], "E must stay untouched when B unknown"
    assert "A" not in result["slots"] and "B" not in result["slots"]
    assert "rule_003" in result["rules_fired"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `~/.hermes/hermes-agent/venv/bin/python -m pytest ~/.hermes/scripts/med_chain/tests/test_solver.py -v`
Expected: FAIL (`ModuleNotFoundError: solve`) — feature missing.

- [ ] **Step 3: Write minimal implementation**

```python
# solve.py
import json
from datetime import datetime, time, timedelta

def load_rules(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def _add(t: time, hours: int) -> time:
    dt = datetime.combine(datetime(2000, 1, 1), t) + timedelta(hours=hours)
    return dt.time()

def solve(constraints, fixed_slots: dict):
    slots = {k: v for k, v in fixed_slots.items()}
    independent = {c["slot"] for c in constraints if c.get("type") == "independent"}
    untouched = set()
    rules_fired = []
    conflicts = []
    # forward propagation, priority desc so higher priority derivations win
    for c in sorted(constraints, key=lambda x: -x.get("priority", 0)):
        if c["type"] in ("fixed_gap", "fixed_offset"):
            frm, to = c["from"], c["to"]
            if frm in slots and to not in slots and to not in independent:
                slots[to] = _add(slots[frm], c["hours"])
                rules_fired.append(c["id"])
    # untouched = slots present in constraints but never derived and not user-fixed
    derived_or_fixed = set(slots.keys())
    for c in constraints:
        for s in (c.get("to"), c.get("from"), c.get("slot")):
            if s and s not in derived_or_fixed:
                untouched.add(s)
    return {"slots": slots, "untouched": sorted(untouched),
            "rules_fired": rules_fired, "conflicts": conflicts}
```

- [ ] **Step 4: Run test to verify it passes**

Run: same as Step 2. Expected: PASS.

- [ ] **Step 5: Commit (confirm on VPS)**

```bash
ls -l ~/.hermes/scripts/med_chain/solve.py ~/.hermes/scripts/med_chain/tests/test_solver.py
```

---

### Task 3: Offset invariant `test_offsets.py` (RED)

**Files:**
- Create: `~/.hermes/scripts/med_chain/tests/test_offsets.py`

**Interfaces:** Consumes `solve()` from Task 2.

- [ ] **Step 1: Write failing test**

```python
# tests/test_offsets.py
from datetime import time
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solve import solve, load_rules

def test_e_equals_b_plus_12h():
    rules = load_rules(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rules.json"))
    result = solve(rules["constraints"], {"B": time(9, 43)})
    assert result["slots"]["E"] == time(21, 43), result["slots"]
    assert "rule_004" in result["rules_fired"]
```

- [ ] **Step 2: Run test to verify it fails** → then passes after re-run (solver already handles `fixed_offset`; test confirms).

- [ ] **Step 3: Run to verify it passes** (no new code needed — exercises existing solver).

Run: `~/.hermes/hermes-agent/venv/bin/python -m pytest ~/.hermes/scripts/med_chain/tests/test_offsets.py -v`
Expected: PASS.

---

### Task 4: Conflict resolver `resolve_conflict.py` + `test_conflicts.py` (RED)

**Files:**
- Create: `~/.hermes/scripts/med_chain/resolve_conflict.py`
- Create: `~/.hermes/scripts/med_chain/tests/test_conflicts.py`

**Interfaces:**
- Produces: `resolve(user_value, rule_priority, source_priority_map) -> (winner, note)`.

```python
# resolve_conflict.py
PRIORITY = {
    "doctor_prescription": 100,
    "medical_safety": 95,
    "user_request": 60,
    "preference": 20,
}

def resolve(user_value, rule_priority: int, user_source: str = "user_request"):
    """Return ('rule'|'user', explanation)."""
    user_priority = PRIORITY.get(user_source, 60)
    if rule_priority > user_priority:
        return ("rule", f"Medical wins. Keeps computed value, not user {user_value}.")
    return ("user", f"User {user_value} accepted over rule priority {rule_priority}.")
```

- [ ] **Step 1: Write failing test**

```python
# tests/test_conflicts.py
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from resolve_conflict import resolve

def test_rule_beats_user():
    winner, note = resolve("13:43", 95, "user_request")
    assert winner == "rule", note

def test_user_beats_low_priority():
    winner, note = resolve("13:43", 20, "user_request")
    assert winner == "user", note
```

- [ ] **Step 2: Run → FAIL** (module missing). **Step 3:** add `resolve_conflict.py` above. **Step 4:** run → PASS.

---

### Task 5: Regression test #17 — "E ikut C" permanent fail `test_regression.py` (RED)

**Files:**
- Create: `~/.hermes/scripts/med_chain/tests/test_regression.py`

**Interfaces:** Consumes `solve()`.

- [ ] **Step 1: Write the permanent regression test**

```python
# tests/test_regression.py
from datetime import time
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solve import solve, load_rules

def test_e_never_follows_c():
    rules = load_rules(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rules.json"))
    # Bug #17: LLM linearized E as dependent on C. Assert it can NEVER happen.
    result = solve(rules["constraints"], {"C": time(13, 0)})
    assert "E" not in result["slots"], "REGRESSION #17: E must not be derived from C"
    # Also: even if user forces E=C+something, engine must not treat E as C-derived
    result2 = solve(rules["constraints"], {"C": time(13, 0), "E": time(21, 43)})
    assert result2["slots"]["E"] == time(21, 43)
```

- [ ] **Step 2: Run → already passes** (documents the invariant; if future code breaks it, this fails). Expected: PASS.

---

### Task 6: Execution trace `trace.py` (RED)

**Files:**
- Create: `~/.hermes/scripts/med_chain/trace.py`
- Extend: `tests/test_solver.py` (or new `test_trace.py`)

**Interfaces:** Produces `log_trace(run_id, input, result, validator_result)` appending JSONL to `~/.hermes/logs/med_chain_trace.jsonl`.

```python
# trace.py
import json, os, time as _time

TRACE_PATH = os.path.expanduser("~/.hermes/logs/med_chain_trace.jsonl")

def log_trace(run_id, input_slots, result, validator_result=None):
    os.makedirs(os.path.dirname(TRACE_PATH), exist_ok=True)
    row = {
        "ts": _time.time(),
        "run_id": run_id,
        "input": {k: str(v) for k, v in input_slots.items()},
        "slots": {k: str(v) for k, v in result.get("slots", {}).items()},
        "untouched": result.get("untouched"),
        "rules_fired": result.get("rules_fired"),
        "conflicts": result.get("conflicts"),
        "validator_result": validator_result,
    }
    with open(TRACE_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")
    return row
```

- [ ] **Step 1: Write failing test** that calls `log_trace` and asserts a JSONL line is appended with `run_id`. **Step 2:** run → FAIL. **Step 3:** add `trace.py`. **Step 4:** run → PASS.

---

### Task 7: Semantic validator `validate_semantic.py` (RED)

**Files:**
- Create: `~/.hermes/scripts/med_chain/validate_semantic.py`
- Create: `~/.hermes/scripts/med_chain/tests/test_validate.py`

**Interfaces:** Produces `validate(llm_slots: dict, solver_result: dict) -> (bool, list[str])`. Fact-based: compares parsed LLM slot times to solver expected; `E != 21:43`-style mismatches → FAIL.

- [ ] **Step 1: Write failing test** asserting `validate({"D": time(17,0)}, solver_result_with_D_17)` → (True, []) and `validate({"D": time(18,0)}, ...)` → (False, [...]). **Step 2:** FAIL. **Step 3:** implement (compare each LLM slot to solver `slots`; mismatch → fail with message). **Step 4:** PASS.

---

### Task 8: Intent router `route.py` (RED)

**Files:**
- Create: `~/.hermes/scripts/med_chain/route.py`
- Create: `~/.hermes/scripts/med_chain/tests/test_route.py`

**Interfaces:** Produces `route(intent: dict) -> str` returning `"send"` (low complexity) or `"review"` (high: multi-change / conflicts present).

- [ ] **Step 1: Write failing test**: single query → `"send"`; multi-change with conflict → `"review"`. **Step 2:** FAIL. **Step 3:** implement (low = no conflicts and ≤1 slot change; high otherwise). **Step 4:** PASS.

---

### Task 9: Explainability `why.py` (RED)

**Files:**
- Create: `~/.hermes/scripts/med_chain/why.py`

**Interfaces:** Produces `why(slot, solver_result, rules) -> str` like:
`Rule: fixed_gap C→D / Because: C shifted to 13:00 / Therefore: D = 17:00`.

- [ ] **Step 1: Write failing test** asserting `why("D", result, rules)` contains `"D = 17:00"`. **Step 2:** FAIL. **Step 3:** implement (look up the rule that fired for the slot). **Step 4:** PASS.

---

### Task 10: Integration — patch `chain_calc.py` (FREEZE-SAFE)

**Files:**
- Modify: `~/.hermes/scripts/chain_calc.py` (backup first: `cp chain_calc.py chain_calc.py.bak`)

**Interfaces:** `chain_calc.py` gains `from med_chain.solve import solve, load_rules` (add `med_chain` to `sys.path`) and calls the solver when `rules.json` exists; on ANY exception, falls back to the existing (current) computation so live reminders never break.

- [ ] **Step 1: Backup** `chain_calc.py` → `chain_calc.py.bak`.
- [ ] **Step 2: Add a guarded call:**

```python
# at top of chain_calc.py (after existing imports)
import os as _os, sys as _sys
_MED_CHAIN = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "med_chain")
if _MED_CHAIN not in _sys.path:
    _sys.path.insert(0, _MED_CHAIN)

def compute_slots_deterministic(fixed_slots):
    """Best-effort deterministic solve; returns None on any failure."""
    try:
        from solve import solve, load_rules
        rules = load_rules(_os.path.join(_MED_CHAIN, "rules.json"))
        return solve(rules["constraints"], fixed_slots)
    except Exception:
        return None
```

- [ ] **Step 3: Wire existing entry point** to call `compute_slots_deterministic(...)` and use its result when not None, else keep current logic (no behavior change if engine absent/broken).
- [ ] **Step 4: Verify freeze-safety** — run the existing med flow (or a smoke test of `chain_calc.py`) and confirm output is unchanged when engine returns None, and improved (deterministic) when it runs. Confirm `chain_monitor.sh` and the med hook still execute without error.

---

### Task 11: Hook auto-inject on med keywords (FREEZE-SAFE)

**Files:**
- Modify: the existing med hook (the one that currently triggers med logic) to call the engine on med-intent keywords.

**Interfaces:** Reuses `compute_slots_deterministic` from Task 10.

- [ ] **Step 1:** Identify the med-keyword trigger in the existing hook (`med_confirm.py` / chain_monitor path).
- [ ] **Step 2:** Add a guarded call to `compute_slots_deterministic` behind the same try/except fallback.
- [ ] **Step 3:** Verify the hook still loads (`agent:start`) and TG/WA remain connected; run a med-keyword smoke test.

---

### Task 12 (optional): External reviewer `chain_review.py`

**Files:**
- Create: `~/.hermes/scripts/med_chain/chain_review.py`

Emits a rule-based checklist: `RULE 004 PASSED / RULE 005 FAILED` from a solver result. Implement only if Task 1–11 pass and user approves.

---

## Self-Review (against spec)

- [x] Layer 1 rules.json — Task 1
- [x] Layer 2 solve.py — Task 2
- [x] Layer 2.5 resolve_conflict.py — Task 4
- [x] Layer 3 trace.py — Task 6
- [x] Layer 4 tests (solver/conflicts/offsets/regression) — Tasks 2,3,4,5
- [x] Layer 5 validate_semantic.py — Task 7
- [x] Layer 6 route.py — Task 8
- [x] Layer 7 reviewer (optional) — Task 12
- [x] why.py — Task 9
- [x] Patch chain_calc.py — Task 10
- [x] Hook auto-inject — Task 11
- [x] Spec inconsistency flagged & resolved (E untouched when B unknown)
