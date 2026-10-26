# Specification: Deterministic ADHD-Friendly Diet Tracker & Reporting Engine

## Problem Statement
The user (Amirulhazym, based in Puchong, managing recovery from TB Meningitis on Dexa taper with strict IF, weight targets, and ADHD) experienced frustration with unstructured, noisy, conversational assistant text regarding daily nutrition and calorie burn. When discussing food and diet on WhatsApp, dense walls of text cause cognitive fatigue and obscure vital numbers (calories, macros, deficit, medication sync). 
Furthermore, diet tracking currently relies on ad-hoc JSON updates in `~/.hermes/diet-log.json` without automated formatting, biomedical pros/cons categorization, or synchronization with the nightly 21:30 MYT cron check-in (`91dd42eacfba`).

## Solution
Implement a deterministic Hybrid Diet Tracker architecture consisting of:
1. **Deterministic Core Script (`scripts/diet_report.py`)**:
   - Parses `~/.hermes/diet-log.json` safely.
   - Calculates total caloric intake, macronutrient estimates, TDEE, net deficit, and fasting duration.
   - Renders a clean 5-category visual output tailored for WhatsApp & ADHD:
     - 📋 1. LOG PEMAKANAN HARIAN (INTAKE)
     - 🧪 2. PROFIL NUTRISI (MACROS)
     - 🔬 3. KAJIAN BIOMEDIKAL: PROS & CONS (Clinical Dexa/Potassium/Protein rules)
     - ⚖️ 4. TENAGA KELUAR & STATUS DEFISIT (BURN)
     - ⚡ 5. NEXT ACTION MALAM INI
   - Supports `--mode eod` (full 5-category report) and `--mode compact` (quick 3-line intake status for daytime logs).
2. **Dedicated Skill (`skills/diet-tracker/SKILL.md`)**:
   - Encodes clinical domain knowledge: Dexa sodium retention vs potassium, inverted triangle lean physique constraints, protein sufficiency, and ADHD visual formatting rules.
   - Injects instructions for live interactive turns so the agent invokes `diet_report.py` instead of hand-generating ad-hoc prose.
3. **Cron Job Alignment (`91dd42eacfba`)**:
   - Updates prompt to invoke the deterministic `diet_report.py` formatting engine for 21:30 evening recaps when logs exist.

## User Stories
1. *As an ADHD user on WhatsApp*, I want diet recaps to be strictly categorized with emojis and visual bullets, so that I can see my calories, macros, deficit, and next action in seconds without reading dense text.
2. *As a user recovering on Dexa*, I want every daily recap to evaluate biomedical pros and cons (especially potassium, sodium, and muscle-sparing protein), so that I know if my food choices counter steroid-induced edema and catabolism.
3. *As an AI operator*, I want daily intake and calorie calculations to be driven by a deterministic Python script, so that the assistant never hallucinates arithmetic or drifts from the required output schema.
4. *As an automated cron recipient*, I want the 21:30 MYT evening check-in to use the exact same 5-category format, so that my daily logs stay unified across interactive and scheduled channels.

## Implementation Decisions
- **Source of Truth**: `~/.hermes/diet-log.json` remains the local JSON store for daily diet logs.
- **Python CLI Interface (`scripts/diet_report.py`)**:
  - `python3 scripts/diet_report.py [--date YYYY-MM-DD] [--mode eod|compact] [--json]`
  - Exit code 0 on success with formatted WhatsApp string on stdout.
- **SSOT Repository**:
  - Developed and tested in `/home/ubuntu/hermes-agent-personal_assistant-work`.
  - Unit tests under `tests/diet/test_diet_report.py`.
- **Formatting Constraints**:
  - WhatsApp compatible (`*bold*`, `_italic_`, bullets, no raw markdown tables).
  - Maximum 1 message bubble (< 2,500 chars).

## Testing Decisions
- Test suite with pytest verifying:
  - Missing file / empty day handling.
  - Correct arithmetic for intake, burn, and deficit.
  - Correct rendering of 5 sections in `--mode eod`.
  - Correct rendering of 3 lines in `--mode compact`.
  - Edge cases (zero exercise, fast still active, multiple meals).

## Out of Scope
- Direct computer-vision food calorie estimation from plate photos (user provides meal descriptions).
- Altering core medical taper schedules in `dexa_taper.json` or `med-status.json` (Slot E / med logging remains governed by `med_confirm.py`).
