# Ticket 02: Deterministic ADHD-Friendly WhatsApp Formatter

## Description
Implement the rendering layer in `scripts/diet_report.py` for both `--mode eod` and `--mode compact`.
`--mode eod` must render:
- 📋 1. LOG PEMAKANAN HARIAN (INTAKE)
- 🧪 2. PROFIL NUTRISI (MACROS)
- 🔬 3. KAJIAN BIOMEDIKAL: PROS & CONS
- ⚖️ 4. TENAGA KELUAR & STATUS DEFISIT (BURN)
- ⚡ 5. NEXT ACTION MALAM INI

`--mode compact` must render a clean 3-line status card for midday checks.

## Acceptance Criteria
- [ ] No raw markdown tables (use bullets and emojis).
- [ ] Under 2,500 characters total.
- [ ] Visual separation between categories with `---`.
- [ ] Formats verified on WhatsApp syntax.

## Blocked by: 01-diet-calculator-core
