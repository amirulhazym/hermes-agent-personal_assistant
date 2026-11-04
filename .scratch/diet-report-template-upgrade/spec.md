# Spec: Diet EOD Report Structured Template Upgrade & Dynamic BMR

## Problem Statement
The current deterministic diet reporting script (`scripts/diet_report.py`) renders a legacy 5-section format with:
1. Static hardcoded BMR of 1,850 kcal (ignoring actual weight drop to 62.8 kg from peak 71 kg).
2. Unsegmented meal items without clinical context or clear macro/micronutrient breakdown.
3. Lack of structured fasting window and active workout telemetry aligned with the clean, non-overwhelming WhatsApp format Amirulhazym approved.

## Solution
1. **Dynamic Weight & BMR Calculation**:
   - Extract `profile.latest_weight_kg` from `diet-log.json` (defaults to 62.8 kg if missing).
   - Compute BMR dynamically: Mifflin-St Jeor formula baseline (~10 * weight + 6.25 * height - 5 * age + 5) rounded to sensible clinical range or ~23.8 kcal/kg (~1,490 kcal for 62.8 kg).
   - Baseline sedentary TDEE = BMR * 1.2 (~1,780 kcal).
   - Total burn (TDEE) = Baseline sedentary + Active workout burn.
   - Enforce Sunday evening cadence for weight confirmation.
2. **Structured 5-Block WhatsApp Layout (Option A)**:
   - ⏱️ **1. TINGKAP PUASA & SENAMAN**: Fasting duration, window, cycling workout telemetry (duration, stop time, est. burn).
   - 📋 **2. PECAHAN HIDANGAN & UBAT**: Meals categorized by window (Window 1 / Window 2) with itemized calories, protein, and brief functional/clinical role (e.g. hydration/potassium, muscle sparing, insulin sensitivity).
   - 🧪 **3. PROFIL NUTRISI (MACROS)**: Total calories in, Protein, Carbs, Fat, and Key Micronutrients (Potassium, Selenium, Iodin, Kalsium).
   - ⚖️ **4. TENAGA KELUAR & STATUS DEFISIT (BURN)**: Dynamic BMR, Active Burn, TDEE, and Net Deficit.
   - 💡 **5. KAJIAN BIOMEDIKAL & NEXT ACTION**: Pros & Cons tailored to steroid taper + immediate evening action items (Slot E Letram, hydration, feeding window close).
3. **Clean WhatsApp Formatting**:
   - Zero markdown tables.
   - High visual contrast with bullet headers and emojis.
   - Concise and ADHD-friendly.

## User Stories
1. *As an AI Engineer / fast-tracker*, I want the nightly diet report to accurately reflect my real physical weight (62.8 kg) and real energy expenditure rather than a generic 1850 kcal BMR, so that my deficit tracking is physiologically true.
2. *As an ADHD user on WhatsApp*, I want the daily nutrition summary to be visually segmented into clean functional blocks with emojis and bold labels, so that I can digest intake, macros, deficit, and medication without eye fatigue.

## Implementation Decisions
- Update `format_eod_report()` in `scripts/diet_report.py`.
- Calculate BMR dynamically using `latest_weight_kg`. If `latest_weight_kg` is present, use `round(10 * weight + 6.25 * 168 - 5 * 28 + 5)` or standard clinical factor ~23.8 * weight -> ~1,495 kcal.
- Maintain backwards compatibility for CLI flags `--date`, `--path`, `--mode eod|compact`, `--json`.
- Provide contract tests in `tests/diet/test_diet_report.py`.

## Testing Decisions
- Unit tests verifying the 5 new structured headers.
- Tests verifying dynamic BMR changes when `latest_weight_kg` varies.
- Tests ensuring zero markdown tables are output.

## Out of Scope
- Direct database schema changes (uses JSON SSOT).
- Altering cron schedule (remains 21:30 MYT).
