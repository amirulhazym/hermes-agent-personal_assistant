# Ticket 02: Structured 5-Block WhatsApp Layout

**Blocked by:** 01-dynamic-bmr.md

## Description
Revamp `format_eod_report()` in `scripts/diet_report.py` to match the exact approved WhatsApp structure:
- Block 1: ⏱️ 1. TINGKAP PUASA & SENAMAN
- Block 2: 📋 2. PECAHAN HIDANGAN & UBAT
- Block 3: 🧪 3. PROFIL NUTRISI HARIAN (MACROS)
- Block 4: ⚖️ 4. TENAGA KELUAR & STATUS DEFISIT (BURN)
- Block 5: 💡 5. KAJIAN BIOMEDIKAL & NEXT ACTION

## Acceptance Criteria
- Zero markdown tables (`|`).
- Clean emoji headers, distinct sections, bold labels.
- Output visually comfortable, ADHD-friendly, without dense walls of text.
- Tested and verified against sample fixtures and live 2026-11-03 data.
