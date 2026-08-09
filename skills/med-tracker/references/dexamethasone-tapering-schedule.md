# Dexamethasone Tapering Schedule — Tb Meningitis Regime

## Regime
- **Protocol:** Taper 1mg/2 weeks (Start with 0.3mg/kg)
- **Patient weight basis:** ~60kg → 0.3mg/kg = 18mg starting dose
- **Dosing:** TDS (3x/day) → BD (2x/day) → OD (1x/day)
- **Medication available:** 4mg tablets and 0.5mg tablets
- **Source:** IPR (Institut Perubatan Respiratori) — confirmed by user on 2026-07-05
- **Authoritative data file:** `~/.hermes/dexa_taper.json` — this file is the single source of truth

⚠️ **This reference is a summary. For current dosing, always check `dexa_taper.json` or run `chain_calc.py --taper-display`.**

## Full Tapering Schedule (from dexa_taper.json)

### TDS Phase (3x/day: 8am, 12pm, 4pm)

| Start | End | B (8am) | C (12pm) | D (4pm) | Total | Phase ID |
|-------|-----|---------|----------|---------|-------|----------|
| 2026-05-06 | 2026-05-19 | 6mg | 6mg | 6mg | 18mg | 1 |
| 2026-05-20 | 2026-06-02 | 5mg | 6mg | 5mg | 17mg | 2 |
| 2026-06-03 | 2026-06-16 | 6mg | 6mg | 4mg | 16mg | 3 |
| 2026-06-17 | 2026-06-30 | 5mg | 5mg | 5mg | 15mg | 4 |
| **2026-07-01** | **2026-07-14** | **5mg** | **5mg** | **4mg** | **14mg** | **5 (CURRENT)** |
| 2026-07-15 | 2026-07-28 | 5mg | 4mg | 4mg | 13mg | 6 |
| 2026-07-29 | 2026-08-11 | 4mg | 4mg | 4mg | 12mg | 7 |
| 2026-08-12 | 2026-08-25 | 4mg | 4mg | 3mg | 11mg | 8 |
| 2026-08-26 | 2026-09-08 | 4mg | 3mg | 3mg | 10mg | 9 |

### BD Phase (2x/day: 8am, 2pm) — Slot D deactivated

| Start | End | B (8am) | 2pm | Total | Phase ID |
|-------|-----|---------|-----|-------|----------|
| 2026-09-09 | 2026-09-22 | 6mg | 4mg | 10mg | 10 |
| 2026-09-23 | 2026-10-06 | 5mg | 4mg | 9mg | 11 |
| 2026-10-07 | 2026-10-20 | 4mg | 4mg | 8mg | 12 |
| 2026-10-21 | 2026-11-03 | 4mg | 3mg | 7mg | 13 |
| 2026-11-04 | 2026-11-17 | 3mg | 3mg | 6mg | 14 |
| 2026-11-18 | 2026-12-01 | 3mg | 2mg | 5mg | 15 |
| 2026-12-02 | 2026-12-15 | 2mg | 2mg | 4mg | 16 |

### OD Phase (1x/day: 8am) — Slots C,D deactivated

| Start | End | B (8am) | Total | Phase ID |
|-------|-----|---------|-------|----------|
| 2026-12-16 | 2026-12-29 | 4mg | 4mg | 17 |
| 2026-12-30 | 2027-01-12 | 3mg | 3mg | 18 |
| 2027-01-13 | 2027-01-26 | 2mg | 2mg | 19 |
| 2027-01-27 | 2027-02-09 | 1mg | 1mg | 20 |

### STOP (from 2027-02-10) — Phase ID 21

## Tablet Composition Reference

Available strengths: **4mg tablets** and **0.5mg tablets**

| Dose | Composition | Tablets |
|------|-------------|---------|
| 1mg | 2×0.5mg | 2 |
| 2mg | 4×0.5mg | 4 |
| 3mg | 6×0.5mg | 6 |
| 4mg | 1×4mg | 1 |
| 5mg | 1×4mg + 2×0.5mg | 3 |
| 6mg | 1×4mg + 4×0.5mg | 5 |

## Masa Pemberian Ubat

- **3x sehari (TDS):** 8am, 12pm, 4pm
- **2x sehari (BD):** 8am, 2pm
- **1x sehari (OD):** 8am

## Active Slots by Frequency

| Frequency | Active Slots | Deactivated |
|-----------|--------------|-------------|
| TDS | A, B, C, D, E | None |
| BD | A, B, C, E | D |
| OD | A, B, E | C, D |
| STOP | A, E | B, C, D |

## Important Notes

- **Do NOT assume doses are fixed.** The schedule changes every 2 weeks.
- When user confirms dexa intake, log the ACTUAL dose taken, not a hardcoded assumption.
- The chain calculator uses gap-based timing (4h between slots) which is independent of dose amount — but the dose AMOUNT changes.
- User confirmed dose correction on 2026-07-05: current dose is 5/5/4 (14mg), NOT 5/5/5 (15mg). The 15mg phase ended 30/6/2026.
- **This file was last verified against dexa_taper.json on 2026-07-05.**
