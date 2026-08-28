# BD Slot F Dynamic Gap Solver Fix (2026-08-27)

## Incident Summary
On 2026-08-27 (Phase 9 BD mode), morning Slot B (Levetiracetam + Dexamethasone 6mg) was delayed and confirmed at 10:35am.
At 14:00 (2:00pm), the reminder engine fired a premature reminder for Slot F (Dexamethasone 4mg), despite the clinical safety requirement of a 6-hour gap between morning and afternoon steroid doses.

## Root Cause
1. `med_chain/rules.json` defined `rule_009`: `{"id": "rule_009", "type": "min_gap", "from": "B", "to": "F", "hours": 6, "priority": 95}`.
2. In `med_chain/solve.py`, Slot F handling was implemented as a purely static anchor:
   ```python
   # Defective implementation:
   if "F" not in slots and "F" in anchors:
       slots["F"] = anchors["F"]
       rules_fired.append("rule_008")
   ```
   `solve.py` did not inspect `fixed_slots['B']` or evaluate `rule_009` against `fixed_slots['B']`.
3. When Slot B shifted from 08:00 to 10:35, `solve.py` left Slot F at `14:00` instead of pushing it to `16:35` (`10:35 + 6h`).
4. As a result, `chain_calc.py` computed `ready_time: "14:00"` and triggered a prompt tick at 14:00.

## Solution
1. In `med_chain/solve.py`, implement dynamic lower bound evaluation for Slot F:
   ```python
   b_to_f = next((c for c in constraints if c.get("id") == "rule_009"), None)
   f_anchor = anchors.get("F")
   if "F" in slots:
       if "B" in slots and b_to_f:
           earliest_f = _add(slots["B"], b_to_f["hours"])
           if slots["F"] < earliest_f:
               conflicts.append(
                   f"B→F unsafe: F {slots['F'].strftime('%H:%M')} is before "
                   f"minimum {earliest_f.strftime('%H:%M')}"
               )
   elif f_anchor:
       if "B" in fixed_slots and b_to_f:
           earliest_f = _add(fixed_slots["B"], b_to_f["hours"])
           slots["F"] = max(f_anchor, earliest_f)
           rules_fired.append("rule_008")
           rules_fired.append("rule_009")
       else:
           slots["F"] = f_anchor
           rules_fired.append("rule_008")
   ```
2. Reset erroneous reminder delivery state in `chain-state.json` (`reminder_counts['F']=0`, `last_reminder_sent['F']=0`).
3. Add unit test coverage in `test_timing_contract.py` (`test_late_b_pushes_f_min_gap_safe`, `test_early_b_keeps_f_at_anchor`).
