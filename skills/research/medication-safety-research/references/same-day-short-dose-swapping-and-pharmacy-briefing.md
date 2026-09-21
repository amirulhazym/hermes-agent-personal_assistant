# Clinical Pattern: Same-Day Short-Dose Swapping & Emergency Pharmacy Top-Up

## Problem Pattern
During prolonged corticosteroid tapering (e.g. Dexamethasone), patients frequently encounter a supply shortfall on appointment day:
1. **Pill inventory mismatch:** Only a partial strength remains (e.g., patient has a 4mg tablet remaining at home, but the prescribed morning dose is 6mg).
2. **Same-day dose swap:** Patient takes the smaller available tablet (4mg, intended for 2pm) in the morning to avoid missing intake entirely.
3. **Pending remainder:** The larger remainder (6mg) is delayed until the clinic/pharmacy dispense happens later that afternoon.
4. **Transition day inventory gap:** Additional deficit covers the transition days before a new tapering phase begins.

## Clinical Rationale & Pharmacological Boundary
- **Total Daily Dose Equivalence:** For glucocorticoids, maintaining the exact total daily exposure (e.g., 10mg total) is paramount to preventing acute adrenal insufficiency or rebound neuro-inflammation.
- **Inverted Sequence Tolerance:** Taking 4mg morning + 6mg afternoon (instead of 6mg morning + 4mg afternoon) is well tolerated as an emergency one-day stopgap. While morning dosing better mimics endogenous diurnal cortisol rhythm, ensuring total daily mg coverage far outweighs the pharmacokinetic shift.
- **Sleep Impact Safeguard:** Ensure the delayed remainder is administered before late evening (ideally by 4:00 PM–5:00 PM) to minimize steroid-induced insomnia.

## Concise Clinic/Pharmacy Explanation Formula
Patients waiting at hospital pharmacy counters are often fatigued, overwhelmed, or experiencing cognitive load. When preparing a briefing for the patient to present to the pharmacist, follow this strict 2-part structure:

```text
1. Short Dose Hari Ini (Tanggal):
   - Dos pagi dah ambil [Dose taken, e.g. 4mg] sebab baki ubat habis.
   - Baki [Remaining dose, e.g. 6mg] belum ambil — plan nak telan petang ni sebaik dapat ubat supaya cukup total harian [Total daily dose, e.g. 10mg].

2. Baki Hari Sebelum Fasa Baru:
   - Nyatakan baki dos yang langsung tiada ubat (e.g., esok 10mg: 6mg pagi + 4mg petang).
   - Minta dispenser pastikan pek ubat cover dos petang ini + dos hari esok sebelum masuk fasa baru.
```

## Logging & Reconciling in State
1. **Preserve User Stated Time:** When the user confirms intake of the swapped remainder and accompanying meds (e.g., \"Done makan dexa + cc jam 4.30pm\"), record the exact time.
2. **Compound Disambiguation:**
   - In drug-level trackers, compound shorthand like \"CC\" must resolve cleanly to both component drugs (`calcium` + `calcitriol`).
   - If CLI tool lacks direct `--compound` flag, invoke each component with `--source-text` containing the exact confirmation string.
3. **Slot Allocation Integrity:**
   - Map the morning 4mg intake to the morning dexa record (`dexamethasone_1` / Slot B).
   - Map the afternoon 6mg intake to the afternoon dexa record (`dexamethasone_f` / Slot F).
   - Verify that daily total is marked completed without corrupting previous slot timestamps.
