#!/usr/bin/env python3
"""
mri_reminder.py — Deterministic reminder generator for Amirulhazym's HKL MRI appointment.

Usage:
    python3 mri_reminder.py --stage [catchup|day3_evening|day2_morning|day2_evening|day1_morning|day1_evening]
"""

import argparse
import sys

STAGES = {
    "catchup": (
        "🔔 [CATCH-UP] PERINGATAN TEMUJANJI MRI HKL\n\n"
        "Tarikh: Isnin, 19 Oktober 2026 (lagi 3 hari)\n"
        "Masa: Awal pagi (anggaran 8:00 AM – 10:00 AM)\n"
        "Lokasi: Hospital Kuala Lumpur (HKL)\n"
        "Tujuan: MRI Scan (Otak / Neuro)\n"
        "Perjalanan: Rancang gerak awal dari rumah ke LRT IOI Puchong Jaya menghala ke HKL.\n"
        "Nota: Mesej ini dihantar sebagai pengganti reminder slot 9:00 AM pagi ini yang tertangguh. Sila semak sebarang arahan persediaan khusus daripada pihak HKL."
    ),
    "day3_evening": (
        "🌙 Peringatan Malam: Temujanji MRI HKL (Lagi 3 Hari)\n\n"
        "Tarikh: Isnin, 19 Oktober 2026\n"
        "Masa: Awal pagi (anggaran 8:00 AM – 10:00 AM)\n"
        "Lokasi: Hospital Kuala Lumpur (HKL)\n"
        "Tujuan: MRI Scan (Otak / Neuro)\n"
        "Perjalanan: Laluan LRT IOI Puchong Jaya ke HKL waktu puncak pagi.\n"
        "Peringatan: Pastikan rehat secukupnya dan semak dokumen/surat rujukan HKL."
    ),
    "day2_morning": (
        "📅 Peringatan Pagi: Temujanji MRI HKL (Lagi 2 Hari)\n\n"
        "Tarikh: Isnin, 19 Oktober 2026\n"
        "Masa: Awal pagi (anggaran 8:00 AM – 10:00 AM)\n"
        "Lokasi: Hospital Kuala Lumpur (HKL)\n"
        "Tujuan: MRI Scan (Otak / Neuro)\n"
        "Perjalanan: Rancang jadual transit LRT IOI Puchong Jaya lebih awal."
    ),
    "day2_evening": (
        "🌙 Peringatan Malam: Temujanji MRI HKL (Lagi 2 Hari)\n\n"
        "Tarikh: Isnin, 19 Oktober 2026\n"
        "Masa: Awal pagi (anggaran 8:00 AM – 10:00 AM)\n"
        "Lokasi: Hospital Kuala Lumpur (HKL)\n"
        "Tujuan: MRI Scan (Otak / Neuro)\n"
        "Nota: Pastikan tiada barang logam/aksesori terlarang semasa scan."
    ),
    "day1_morning": (
        "⚠️ PERINGATAN: TEMUJANJI MRI HKL ESOK!\n\n"
        "Tarikh: Esok, Isnin 19 Oktober 2026\n"
        "Masa: Awal pagi (anggaran 8:00 AM – 10:00 AM)\n"
        "Lokasi: Hospital Kuala Lumpur (HKL)\n"
        "Tujuan: MRI Scan (Otak / Neuro)\n"
        "Perjalanan: Perlu gerak awal pagi dari LRT IOI Puchong Jaya untuk elak kesesakan."
    ),
    "day1_evening": (
        "🚨 PERINGATAN MALAM: TEMUJANJI MRI HKL ESOK PAGI!\n\n"
        "Tarikh: Esok Pagi, Isnin 19 Oktober 2026\n"
        "Masa: Awal pagi (anggaran 8:00 AM – 10:00 AM)\n"
        "Lokasi: Hospital Kuala Lumpur (HKL)\n"
        "Tujuan: MRI Scan (Otak / Neuro)\n"
        "Checklist Malam Ini:\n"
        "1. Kunci jam penggera awal pagi.\n"
        "2. Sediakan kad pengenalan, surat temujanji, dan rekod perubatan.\n"
        "3. Rancang pergerakan awal ke stesen LRT IOI Puchong Jaya."
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
