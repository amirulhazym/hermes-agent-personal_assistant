#!/usr/bin/env python3
"""
mri_reminder.py — Deterministic reminder generator for Amirulhazym's HKL MRI appointment.
Style: Action-Oriented (Option 2).
"""

import argparse
import sys

STAGES = {
    "catchup": (
        "🏥 *MRI HKL — Isnin 19 Okt (Lagi 3 Hari)*\n"
        "⏱ *Slot:* 8:00 AM – 10:00 AM (Awal Pagi)\n\n"
        "📍 *Lokasi:* Hospital Kuala Lumpur (Scan Otak/Neuro)\n"
        "🚇 *Logistik:* LRT IOI Puchong Jaya ➔ HKL (Gerak awal, waktu puncak)\n"
        "⚠️ *Checklist:* IC & surat temujanji sedia malam sebelum."
    ),
    "day3_evening": (
        "🌙 *MRI HKL — Isnin 19 Okt (Lagi 3 Hari)*\n"
        "⏱ *Slot:* 8:00 AM – 10:00 AM (Awal Pagi)\n\n"
        "📍 *Lokasi:* Hospital Kuala Lumpur (Scan Otak/Neuro)\n"
        "🚇 *Logistik:* LRT IOI Puchong Jaya ➔ HKL (Gerak awal, waktu puncak pagi)\n"
        "💡 *Nota:* Pastikan rehat secukupnya & semak dokumen/surat rujukan HKL."
    ),
    "day2_morning": (
        "☀️ *MRI HKL — Isnin 19 Okt (Lagi 2 Hari)*\n"
        "⏱ *Slot:* 8:00 AM – 10:00 AM (Awal Pagi)\n\n"
        "📍 *Lokasi:* Hospital Kuala Lumpur (Scan Otak/Neuro)\n"
        "🚇 *Logistik:* LRT IOI Puchong Jaya ➔ HKL (Rancang jadual transit waktu puncak)"
    ),
    "day2_evening": (
        "🌙 *MRI HKL — Isnin 19 Okt (Lagi 2 Hari)*\n"
        "⏱ *Slot:* 8:00 AM – 10:00 AM (Awal Pagi)\n\n"
        "📍 *Lokasi:* Hospital Kuala Lumpur (Scan Otak/Neuro)\n"
        "⚠️ *Peringatan:* Elak pakaian/aksesori berlogam untuk scan Isnin nanti."
    ),
    "day1_morning": (
        "⚠️ *MRI HKL — ESOK PAGI (Isnin 19 Okt)*\n"
        "⏱ *Slot:* 8:00 AM – 10:00 AM\n\n"
        "📍 *Lokasi:* Hospital Kuala Lumpur (Scan Otak/Neuro)\n"
        "🚇 *Logistik:* LRT IOI Puchong Jaya ➔ HKL (Wajib gerak awal pagi)\n"
        "📋 *Tindakan:* Sedia kad pengenalan & surat temujanji hari ini."
    ),
    "day1_evening": (
        "🚨 *MRI HKL — ESOK PAGI! (Isnin 19 Okt)*\n"
        "⏱ *Slot:* 8:00 AM – 10:00 AM (Hospital Kuala Lumpur)\n\n"
        "Checklist Malam Ini:\n"
        "1. ⏰ Kunci jam penggera awal pagi (waktu puncak LRT).\n"
        "2. 🪪 Masukkan IC & surat temujanji dalam beg sekarang.\n"
        "3. 👕 Sediakan pakaian selesa tanpa zip/butang logam.\n"
        "🚇 Laluan: LRT IOI Puchong Jaya ➔ HKL"
    ),
}

def main():
    parser = argparse.ArgumentParser(description="Emit deterministic MRI reminder text")
    parser.add_argument(
        "--stage",
        required=True,
        choices=list(STAGES.keys()),
        help="Stage of reminder to emit"
    )
    args = parser.parse_args()
    print(STAGES[args.stage])
    return 0

if __name__ == "__main__":
    sys.exit(main())
