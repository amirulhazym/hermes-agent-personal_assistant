# Medication Chain Engine (Pilot) — Spec v3

Last updated: 2026-07-08 10:36 MYT
Author: Hermes Native Agent (MJ)
Status: PENDING EXTERNAL AUDIT (Gemini/OpenCode) before execution

## Purpose
Fix repeated LLM chain-confusion bug (E presented as dependent on B→C→D when E is independent).
Root cause: LLM auto-linearizes branched dependency graph. Solution: deterministic rule engine as source of truth, LLM only explains.

## Architecture (final, per tech-lead review 9.95/10)

```
User
  ↓
Intent Classifier (route.py)
  ↓
Constraint Solver (solve.py)
  ↓
Conflict Resolver (resolve_conflict.py)
  ↓
Execution Trace (trace.py)
  ↓
LLM Explanation
  ↓
Semantic Validator (validate_semantic.py)
  ↓
Complexity?
  ├── Low → Send
  └── High → External Review → Send
```

## Layer 1: Constraint Schema (domain-specific + versioned)
File: `~/.hermes/scripts/med_chain/rules.json`
```json
{
  "schema_version": 1,
  "domain": "medication",
  "constraints": [
    {"id": "rule_001", "type": "min_gap", "from": "A", "to": "B", "hours": 1, "priority": 95},
    {"id": "rule_002", "type": "fixed_gap", "from": "B", "to": "C", "hours": 4, "priority": 95},
    {"id": "rule_003", "type": "fixed_gap", "from": "C", "to": "D", "hours": 4, "priority": 95},
    {"id": "rule_004", "type": "fixed_offset", "from": "B", "to": "E", "hours": 12, "priority": 95},
    {"id": "rule_005", "type": "independent", "slot": "E", "priority": 100},
    {"id": "rule_006", "type": "independent", "slot": "A", "priority": 100}
  ]
}
```

## Layer 2: Constraint Solver
File: `~/.hermes/scripts/med_chain/solve.py`
- Topological solve along constraint edges only
- Output: `{slots, untouched, rules_fired, conflicts[]}`
- Example: input "C at 1pm" → D=5pm, E=9:43pm (untouched), A/B untouched

## Layer 2.5: Conflict Resolver (NEW)
File: `~/.hermes/scripts/med_chain/resolve_conflict.py`
```python
PRIORITY = {
  "doctor_prescription": 100,
  "medical_safety": 95,
  "user_request": 60,
  "preference": 20
}
# If user says C=1pm but rule says 4h gap → conflict
# Solver outputs: "Conflict: User(60) vs Rule_002(95). Medical wins. C stays 13:43."
```

## Layer 3: Execution Trace
File: `~/.hermes/scripts/med_chain/trace.py`
- Log: input → rules_fired → slots_affected → slots_untouched → conflicts → validator_result
- Append to `~/.hermes/logs/med_chain_trace.jsonl`

## Layer 4: Unit Tests
File: `~/.hermes/scripts/med_chain/tests/`
- `test_solver.py` — C=1pm → D=5pm, E untouched
- `test_conflicts.py` — user vs rule priority
- `test_offsets.py` — E=B+12h invariant
- `test_regression.py` — Bug #17: "E ikut C" → permanent fail test

## Layer 5: Semantic Validator
File: `~/.hermes/scripts/med_chain/validate_semantic.py`
- Parse LLM output slot times → compare with solver expected
- E≠21:43 → FAIL (fact-based, not text-pattern)

## Layer 6: Intent Router
File: `~/.hermes/scripts/med_chain/route.py`
- Low: query → Solver → Send
- High: multi-change → + Validator + Reviewer

## Layer 7: External Reviewer (optional, high-complexity)
- Rule-based checklist: `RULE 004 PASSED / RULE 005 FAILED`

## Explainability API
File: `~/.hermes/scripts/med_chain/why.py`
```
/why D
→ Rule: fixed_gap C→D
→ Because: C shifted to 13:00
→ Therefore: D = 17:00
```

## Build Order (per tech-lead):
1. `rules.json` (schema v1 + domain)
2. `solve.py` (solver + trace)
3. `resolve_conflict.py` (priority stack)
4. `tests/` (unit + regression #17)
5. `validate_semantic.py`
6. `route.py`
7. `why.py` (explainability)
8. Patch `chain_calc.py` → call solver
9. Hook: auto-inject on med keywords
10. Optional: `chain_review.py`

## Pilot Philosophy:
- Now: Medication only, domain-specific, versioned
- Later (if stable): Extract to generic Constraint Engine → Calendar/Finance/Task
- Don't over-engineer — no universal engine until 2nd domain exists

## Notes for External Auditor:
- This spec is NOT yet implemented. Awaiting your review.
- Check: constraint model correctness, solver edge cases, conflict priority logic
- Verify against `VPS_AUDIT_STATE.md` for existing med-system context
- NO PC→VPS copy. If approved, apply directly on VPS or via Native Auditor.
