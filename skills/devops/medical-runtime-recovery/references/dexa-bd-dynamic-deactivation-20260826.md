# BD Transition & Dynamic Slot Deactivation Incident (2026-08-26)

## Problem & Symptoms
On 2026-08-26 (first day of Dexa BD 10mg phase: 6mg@8am Slot B + 4mg@2pm Slot F; Midday Slot C and Afternoon Slot D Dexa = 0mg):
1. User confirmed CC intake at 14:51 (`Dah mkn cc jam 251pm`).
2. Slot C was marked `partial` instead of `completed` in runtime state.
3. At 16:30, `chain_monitor.sh` fired reminder `[C:7-260826]` ("‼️ Waktu Ubat (Tengah Hari) ‼️ Hai boss!! Dexamethasone 4mg masih belum ambil walaupun dah pukul 16:30").
4. User subsequently confirmed Dexa intake at 14:55 (`Dah makan dexa petang 255pm`), but `med_resolve.py` failed with `Time rules eliminated all matches for 'dexa petang' at 14:55` because "petang" forced Slot D (>=16:00) while 14:55 is Slot F (14:00-16:00).

## Root Causes
1. **Static Schedule Required List:** `get_required_drug_ids()` in `med_confirm.py` and `chain_calc.py` read `med-schedule.json` statically. Even though Dexa for Slot C was 0mg (deactivated by `dexa_taper.json`), `dexamethasone_2` was still treated as a required drug, holding Slot C in `partial`.
2. **Denormalized Overall Cache:** `chain_calc.py` trusted the `overall` field in `med-status.json` rather than re-evaluating required drugs dynamically against active date-aware taper rules.
3. **Colloquial Token vs Explicit Time Precedence:** `med_resolve.py` applied word-based slot hints (`WORD_TO_SLOT['petang'] = 'D'`) unconditionally even when an explicit clock time (`--time 14:55`) was supplied.
4. **Slot F Omissions in Consumers:**
   - `chain_monitor.sh` housekeeping loop only iterated over `['A', 'B', 'C', 'D', 'E']`, failing to clear reminder counters for Slot F upon completion.
   - `chain_llm.py` lacked `"F": "Petang"` in `TIME_LABELS`, crashing on Slot F reminder generation.
   - `med_report.py` had `SLOTS = ["A", "B", "C", "D", "E"]`, dropping Slot F from daily and weekly compliance statistics.

## Fix Architecture
1. **Dynamic Required Filtering:**
   ```python
   def get_required_drug_ids(slot: str, schedule: dict) -> list[str]:
       from dexa_taper_lookup import get_dexa_dose, is_dexa_drug
       req = []
       for d in get_drugs_for_slot(slot, schedule):
           if not d.get('required', True):
               continue
           did = d.get('drug_id', '')
           if is_dexa_drug(did):
               dose = get_dexa_dose(slot)
               if dose is None or dose <= 0:
                   continue
           req.append(did)
       return req
   ```
2. **Dynamic Live Overall:**
   `chain_calc.get_drug_level_overall()` recalculates taken count against `get_required_drug_ids()` for the active date.
3. **Time-First Disambiguation:**
   In `med_resolve.py`, only apply `slot_hint = WORD_TO_SLOT[w]` when `time_24h` is NOT provided, allowing numeric time rules to disambiguate slot boundaries properly.
4. **Full Slot Enumeration Synchronization:**
   Ensure `SLOTS` and loop iterations in `chain_calc.py`, `chain_llm.py`, `chain_monitor.sh`, and `med_report.py` include all active slots (`A` through `F`).
