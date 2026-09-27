# 01 — Decouple Supply Decrement & Alerts from med_confirm.py

**What to build:** Remove automatic inventory decrement and passive supply alert generation from `scripts/med_confirm.py`, ensuring dosage confirmation is strictly decoupled from inventory mutation.

**Blocked by:** None — can start immediately

**Status:** ready-for-agent

- [ ] Remove `med_supply.decrement` invocations in `confirm_slot` and `confirm_drug` in `scripts/med_confirm.py`
- [ ] Remove `check_low()` / `supply_alerts` population in `confirm_slot` and compound handling
- [ ] Ensure `med_confirm.py` return dict contains only intake status, slot details, and timing
- [ ] Verify test suite runs clean in isolated sandbox
