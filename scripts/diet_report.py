#!/usr/bin/env python3
"""
scripts/diet_report.py
Deterministic diet, nutrition, and caloric deficit reporting engine for Amirulhazym.
Designed for ADHD readers on WhatsApp: structured 5-category layout, visual bullets, emojis, zero walls of text.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_DIET_LOG_PATH = os.path.expanduser("~/.hermes/diet-log.json")
BASELINE_BMR_SEDENTARY = 1850

def load_diet_log(path: str) -> dict:
    if not os.path.exists(path):
        return {"logs": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        sys.stderr.write(f"Error reading {path}: {e}\n")
        return {"logs": {}}

def format_compact_report(date_str: str, log_data: dict) -> str:
    total_kcal = log_data.get("estimated_total_calories", 0)
    protein_g = log_data.get("estimated_protein_g", 0)
    workout = log_data.get("workout", "Tiada senaman direkod")
    meals_count = len(log_data.get("meals", []))

    lines = [
        f"📊 *Status Diet ({date_str})*",
        f"• *Intake Semasa:* ~{total_kcal} kcal ({meals_count} entri, protein ~{protein_g}g)",
        f"• *Workout:* {workout}",
        f"• *Status:* On track. Teruskan minum air kosong!"
    ]
    return "\n".join(lines)

def format_eod_report(date_str: str, log_data: dict) -> str:
    meals = log_data.get("meals", [])
    total_kcal = log_data.get("estimated_total_calories", 0)
    protein_g = log_data.get("estimated_protein_g", 0)
    carbs_g = log_data.get("estimated_carbs_g")
    fat_g = log_data.get("estimated_fat_g")
    workout = log_data.get("workout", "Tiada senaman direkod")
    pros = log_data.get("pros", [])
    cons = log_data.get("cons", [])
    next_actions = log_data.get("next_actions", [])

    # Workout burn heuristic
    active_burn = 400 if "cycling" in workout.lower() or "basikal" in workout.lower() else 0
    tdee_low = BASELINE_BMR_SEDENTARY + active_burn
    tdee_high = BASELINE_BMR_SEDENTARY + active_burn + 50
    deficit_low = tdee_low - total_kcal
    deficit_high = tdee_high - total_kcal

    # Format Date Header
    report = [f"📊 *REKOD DIET & DEFISIT HARIAN ({date_str})*", "---"]

    # 1. Intake
    report.append("📋 1. LOG PEMAKANAN HARIAN (INTAKE)")
    if meals:
        for m in meals:
            report.append(f"• {m}")
    else:
        report.append("• Tiada makanan direkodkan lagi.")
    report.append(f"➡️ *Total Kalori Masuk:* *~{total_kcal} kcal*\n---")

    # 2. Macros
    report.append("🧪 2. PROFIL NUTRISI (MACROS)")
    report.append(f"• 🥩 *Protein:* *~{protein_g}g* (Sasaran pemulihan otot)")
    if carbs_g is not None:
        report.append(f"• 🍚 *Karbohidrat:* *~{carbs_g}g*")
    if fat_g is not None:
        report.append(f"• 🥑 *Lemak:* *~{fat_g}g*")
    report.append("• 🌿 *Mikronutrien:* Potassium semulajadi, Vitamin D, Kalsium & Antioksidan\n---")

    # 3. Pros & Cons (Clinical Dexa Context)
    report.append("🔬 3. KAJIAN BIOMEDIKAL: PROS & CONS")
    report.append("🟢 *PROS & KELEBIHAN:*")
    if pros:
        for p in pros:
            report.append(f"• {p}")
    else:
        report.append("• Pilihan makanan rendah indeks glisemik dan menyokong defisit bersih.")
        report.append("• Mengelakkan makanan proses dan sodium tinggi.")

    report.append("🔴 *CONS & PERHATIAN:*")
    if cons:
        for c in cons:
            report.append(f"• {c}")
    else:
        report.append("• Pantau hidrasi air kosong secukupnya untuk singkirkan lebihan garam.")
    report.append("---")

    # 4. Burn & Deficit
    report.append("⚖️ 4. TENAGA KELUAR & STATUS DEFISIT (BURN)")
    report.append(f"• 🔥 *Aktiviti Aktif:* {workout}")
    report.append(f"• 🔋 *BMR & Asas Harian:* ~{BASELINE_BMR_SEDENTARY} kcal")
    report.append(f"• 📊 *Total Burn (TDEE):* *~{tdee_low} – {tdee_high} kcal*")
    report.append(f"• 🎯 *Net Defisit Bersih:* *~{deficit_low} – {deficit_high} kcal* (Disiplin cemerlang!)\n---")

    # 5. Next Action
    report.append("⚡ 5. NEXT ACTION MALAM INI")
    if next_actions:
        for a in next_actions:
            report.append(f"• {a}")
    else:
        report.append("• 💊 Pastikan ubat Slot E (Levetiracetam) diambil on time.")
        report.append("• 💧 Minum 1-2 gelas air kosong sebelum tidur.")
        report.append("• 🛑 Tutup feeding window dan rehat secukupnya.")

    return "\n".join(report)

def main():
    parser = argparse.ArgumentParser(description="Deterministic Diet Reporter")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Target date YYYY-MM-DD")
    parser.add_argument("--path", default=DEFAULT_DIET_LOG_PATH, help="Path to diet-log.json")
    parser.add_argument("--mode", choices=["eod", "compact"], default="eod", help="Report mode")
    parser.add_argument("--json", action="store_true", help="Output raw JSON data for the date")

    args = parser.parse_args()

    data = load_diet_log(args.path)
    day_log = data.get("logs", {}).get(args.date)

    if not day_log:
        if args.json:
            print(json.dumps({"ok": False, "error": f"Tiada rekod diet dijumpai untuk tarikh {args.date}."}))
        else:
            print(f"Tiada rekod diet dijumpai untuk tarikh {args.date} dalam {args.path}.")
        return 0

    if args.json:
        print(json.dumps({"ok": True, "date": args.date, "data": day_log}, indent=2))
        return 0

    if args.mode == "compact":
        output = format_compact_report(args.date, day_log)
    else:
        output = format_eod_report(args.date, day_log)

    print(output)
    return 0

if __name__ == "__main__":
    sys.exit(main())
