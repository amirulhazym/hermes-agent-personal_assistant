#!/usr/bin/env python3
"""
scripts/diet_report.py
Deterministic diet, nutrition, and caloric deficit reporting engine for Amirulhazym.
Designed for ADHD readers on WhatsApp: structured sections, visual bullets, emojis, zero tables, zero dense walls.

Evidence rules (2026-11-06 revision):
  * Every number rendered MUST come from the day's log or an explicitly supplied
    reference file. This module never invents a burn value, micronutrient figure,
    or medication status that is not present in data.
  * Workout burn is read from ``active_burn_kcal_estimate`` (dict or int). The old
    substring heuristic (500 kcal whenever the workout text contained "90") was
    removed because it silently overrode the logged estimate.
  * Micronutrients are rendered only from an explicit ``micronutrients`` block.
  * Medication status is read from med-status.json, not guessed from the diet log.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

DEFAULT_DIET_LOG_PATH = os.path.expanduser("~/.hermes/diet-log.json")
DEFAULT_MED_STATUS_PATH = os.path.expanduser("~/.hermes/med-status.json")

NO_DATA = "Tiada data direkod"


def load_json_file(path: str, default: dict | None = None) -> dict:
    """Load JSON, returning ``default`` when the file is missing or unreadable."""
    if not path or not os.path.exists(path):
        return default if default is not None else {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else (default if default is not None else {})
    except Exception as e:
        sys.stderr.write(f"Error reading {path}: {e}\n")
        return default if default is not None else {}


def load_diet_log(path: str) -> dict:
    return load_json_file(path, {"logs": {}, "profile": {}})


def calculate_dynamic_bmr(weight_kg: float) -> int:
    """
    Mifflin-St Jeor formula baseline for Amirulhazym:
    BMR = 10 * weight (kg) + 6.25 * height (168 cm) - 5 * age (28) + 5
        = 10 * weight + 1050 - 140 + 5
        = 10 * weight + 915
    For 62.8 kg -> ~1543 kcal (calibrated baseline ~1,500 kcal).
    """
    bmr = round(10 * weight_kg + 6.25 * 168 - 5 * 28 + 5)
    if 62.0 <= weight_kg <= 63.5:
        return 1500
    return bmr


# ---------------------------------------------------------------------------
# Evidence resolvers — return None / NO_DATA rather than a guessed number
# ---------------------------------------------------------------------------


def resolve_active_burn(day_log: dict) -> dict | None:
    """Read the workout burn estimate recorded in the log.

    Accepts ``active_burn_kcal_estimate`` as either a dict with
    ``low``/``mid``/``high`` (+ optional ``basis``) or a bare number.
    Returns ``None`` when the log carries no estimate — the caller then reports
    the absence instead of substituting a default.
    """
    est = day_log.get("active_burn_kcal_estimate")
    if isinstance(est, (int, float)) and est >= 0:
        return {"low": float(est), "mid": float(est), "high": float(est), "basis": ""}
    if isinstance(est, dict):
        mid = est.get("mid")
        if isinstance(mid, (int, float)):
            low = est.get("low", mid)
            high = est.get("high", mid)
            if not isinstance(low, (int, float)):
                low = mid
            if not isinstance(high, (int, float)):
                high = mid
            low, high = sorted((float(low), float(high)))
            return {
                "low": low,
                "mid": float(mid),
                "high": high,
                "basis": str(est.get("basis") or ""),
            }
    return None


def resolve_intake_range(day_log: dict) -> tuple[float, float]:
    """Return (low, high) intake band from the log; collapses to total if absent."""
    total = day_log.get("estimated_total_calories", 0) or 0
    rng = day_log.get("estimated_calorie_range_kcal")
    if isinstance(rng, (list, tuple)) and len(rng) == 2:
        vals = [v for v in rng if isinstance(v, (int, float))]
        if len(vals) == 2:
            low, high = sorted(float(v) for v in vals)
            return low, high
    return float(total), float(total)


def load_med_status_today(path: str, date_str: str) -> dict:
    """Return {slot: {'overall': str, 'drugs': {drug_id: (status, time)}}} for date."""
    data = load_json_file(path, {})
    meds = data.get("meds", {})
    out: dict = {}
    if not isinstance(meds, dict):
        return out
    for slot, by_date in meds.items():
        if not isinstance(by_date, dict):
            continue
        entry = by_date.get(date_str)
        if not isinstance(entry, dict):
            continue
        drugs = {}
        for drug_id, detail in (entry.get("drugs") or {}).items():
            if isinstance(detail, dict):
                drugs[drug_id] = (detail.get("status"), detail.get("time"))
        out[slot] = {"overall": entry.get("overall"), "drugs": drugs}
    return out


def format_macronutrients(day_log: dict) -> list[str]:
    lines = []
    protein = day_log.get("estimated_protein_g")
    carbs = day_log.get("estimated_carbs_g")
    fat = day_log.get("estimated_fat_g")
    if protein is None and carbs is None and fat is None:
        lines.append(f"• {NO_DATA} untuk makronutrien.")
        return lines
    lines.append("• *Makronutrien (anggaran):*")
    if protein is not None:
        lines.append(f"  - Protein: *~{protein}g*")
    if carbs is not None:
        lines.append(f"  - Karbohidrat: *~{carbs}g*")
    if fat is not None:
        lines.append(f"  - Lemak: *~{fat}g*")

    # Flag macro-vs-kcal drift instead of hiding it.
    total_kcal = day_log.get("estimated_total_calories")
    if total_kcal and protein is not None and carbs is not None and fat is not None:
        macro_kcal = protein * 4 + carbs * 4 + fat * 9
        drift = abs(macro_kcal - total_kcal)
        if drift >= max(25, 0.03 * total_kcal):
            lines.append(
                f"  - ⚠️ Macro beri ~{macro_kcal:,.0f} kcal vs jumlah log "
                f"{total_kcal:,} kcal (beza ~{drift:,.0f}) — dua-dua anggaran berasingan."
            )
    return lines


def format_micronutrients(day_log: dict) -> list[str]:
    """Render only explicitly recorded micronutrients. Never a canned list."""
    micros = day_log.get("micronutrients")
    if not isinstance(micros, dict) or not micros:
        return [f"• {NO_DATA} untuk mikronutrien hari ini."]
    lines = ["• *Mikronutrien (direkod):*"]
    for name, value in micros.items():
        label = str(name).replace("_", " ")
        lines.append(f"  - {label}: *{value}*")
    return lines


def format_hydration(day_log: dict) -> list[str]:
    """Show only hydration data recorded explicitly.

    Meals are already itemised in section 1, so re-scanning them for drink
    keywords would duplicate whole meal lines here. Only an explicit
    ``beverages`` list (or free-text ``hydration`` note) is rendered.
    """
    lines = []
    beverages = day_log.get("beverages")
    if isinstance(beverages, (list, tuple)):
        for b in beverages:
            if isinstance(b, str) and b.strip():
                lines.append(f"• {b}")
    elif isinstance(beverages, str) and beverages.strip():
        lines.append(f"• {beverages}")
    hydration = day_log.get("hydration")
    if isinstance(hydration, str) and hydration.strip():
        lines.append(f"• {hydration}")
    preparing = day_log.get("beverage_preparing")
    if isinstance(preparing, str) and preparing.strip():
        lines.append(f"• ⚠️ Belum disahkan diminum: {preparing}")
    if not lines:
        lines.append(f"• {NO_DATA} untuk hidrasi.")
    return lines


def format_meds(med_today: dict) -> list[str]:
    if not med_today:
        return [f"• {NO_DATA} untuk ubat (med-status.json tiada entri tarikh ini)."]
    lines = []
    for slot in sorted(med_today):
        entry = med_today[slot]
        drugs = entry.get("drugs") or {}
        parts = []
        for drug_id, (status, time_value) in sorted(drugs.items()):
            label = str(drug_id)
            if status == "taken":
                parts.append(f"{label} {time_value}" if time_value else label)
            else:
                parts.append(f"{label} ({status or 'tiada status'})")
        detail = ", ".join(parts) if parts else "tiada butiran"
        mark = "✅" if entry.get("overall") == "completed" else "—"
        lines.append(f"• Slot {slot}: {detail} {mark}")
    return lines


def format_compact_report(date_str: str, log_data: dict) -> str:
    total_kcal = log_data.get("estimated_total_calories", 0)
    protein_g = log_data.get("estimated_protein_g", 0)
    workout = log_data.get("workout", "Tiada senaman direkod")
    meals_count = len(log_data.get("meals", []))

    return "\n".join([
        f"📊 *Status Diet ({date_str})*",
        f"• *Intake Semasa:* ~{total_kcal} kcal ({meals_count} entri, protein ~{protein_g}g)",
        f"• *Workout:* {workout}",
        "• *Status:* Teruskan minum air kosong.",
    ])


def format_eod_report(
    date_str: str,
    log_data: dict,
    profile_data: dict | None = None,
    med_status: dict | None = None,
) -> str:
    profile = profile_data or {}
    weight_kg = profile.get("latest_weight_kg", 62.8)

    fasting_window = log_data.get("fasting_window", "Tiada data puasa")
    workout = log_data.get("workout", "Tiada senaman direkod")
    meals = log_data.get("meals", [])

    total_kcal = log_data.get("estimated_total_calories", 0)

    burn = resolve_active_burn(log_data)
    intake_low, intake_high = resolve_intake_range(log_data)

    bmr = calculate_dynamic_bmr(weight_kg)
    sedentary_tdee = round(bmr * 1.2)

    report: list[str] = []
    report.append(f"📊 *REKOD DIET & DEFISIT HARIAN ({date_str})*")
    report.append("")

    # ⏱️ PUASA & WORKOUT
    report.append("⏱️ *PUASA & WORKOUT*")
    report.append(f"• *Fasting Window:* {fasting_window}")
    report.append(f"• *Workout:* {workout}")
    if burn:
        if burn["low"] == burn["high"]:
            report.append(f"• *Tenaga Terbakar (anggaran log):* ~{burn['mid']:,.0f} kcal")
        else:
            report.append(
                f"• *Tenaga Terbakar (anggaran log):* ~{burn['mid']:,.0f} kcal "
                f"(julat {burn['low']:,.0f}–{burn['high']:,.0f})"
            )
        if burn.get("basis"):
            report.append(f"  - Asas: {burn['basis']}")
    else:
        report.append(f"• *Tenaga Terbakar:* {NO_DATA} — tiada anggaran burn dalam log.")
    report.append("")
    report.append("---")
    report.append("")

    # 🥗 1. MENU MAKANAN & KALORI
    report.append("🥗 *1. MENU MAKANAN & KALORI HARIAN*")
    food_meals = []
    for m in meals:
        if not isinstance(m, str):
            continue
        lower = m.lower()
        if "slot " in lower and ("taken" in lower or "cc" in lower):
            continue
        food_meals.append(m)
    if food_meals:
        for m in food_meals:
            report.append(f"• {m}")
    else:
        report.append("• Tiada rekod makanan hari ini.")
    if intake_low != intake_high:
        report.append(
            f"➡️ *TOTAL KALORI MASUK (24 JAM):* *~{total_kcal:,} kcal* "
            f"(julat ~{intake_low:,.0f}–{intake_high:,.0f})"
        )
    else:
        report.append(f"➡️ *TOTAL KALORI MASUK (24 JAM):* *~{total_kcal:,} kcal*")
    report.append("")
    report.append("---")
    report.append("")

    # 🧪 2. PROFIL NUTRISI
    report.append("🧪 *2. PROFIL NUTRISI*")
    report.append("")
    report.extend(format_macronutrients(log_data))
    report.append("")
    report.extend(format_micronutrients(log_data))
    report.append("")
    report.append("---")
    report.append("")

    # 🌿 HIDRASI
    report.append("🌿 *HIDRASI & MINUMAN*")
    report.extend(format_hydration(log_data))
    report.append("")
    report.append("---")
    report.append("")

    # 💊 UBAT
    report.append("💊 *STATUS UBAT HARIAN*")
    report.extend(format_meds(med_status or {}))
    report.append("")
    report.append("---")
    report.append("")

    # ⚖️ DEFISIT
    report.append("⚖️ *STATUS DEFISIT & KALORI*")
    report.append(f"• ⚖️ *Berat Terkini:* *{weight_kg} kg*")
    report.append(f"• 🔋 *BMR Asas:* *~{bmr:,} kcal*")
    report.append(f"• 🚶 *TDEE Sedentary:* *~{sedentary_tdee:,} kcal*")
    if burn:
        tdee_low = sedentary_tdee + burn["low"]
        tdee_high = sedentary_tdee + burn["high"]
        report.append(
            f"• 📊 *Total TDEE:* *~{sedentary_tdee + burn['mid']:,.0f} kcal* "
            f"(julat {tdee_low:,.0f}–{tdee_high:,.0f})"
        )
        deficit_low = tdee_low - intake_high
        deficit_high = tdee_high - intake_low
        report.append(
            f"• 🎯 *Anggaran Defisit:* *~{deficit_low:,.0f} hingga {deficit_high:,.0f} kcal* "
            "(julat, bukan bacaan tepat)"
        )
    else:
        deficit_low = sedentary_tdee - intake_high
        deficit_high = sedentary_tdee - intake_low
        report.append(
            "• 📊 *Total TDEE:* sedentary sahaja (tiada anggaran burn workout)"
        )
        report.append(
            f"• 🎯 *Anggaran Defisit (tanpa burn workout):* "
            f"*~{deficit_low:,.0f} hingga {deficit_high:,.0f} kcal*"
        )
    report.append("")
    report.append("---")
    report.append("")

    # 💡 NEXT
    report.append("💡 *TINDAKAN MALAM INI*")
    last_intake = log_data.get("last_intake_time")
    if isinstance(last_intake, str) and last_intake.strip():
        report.append(f"• Feeding window ditutup pada *{last_intake}*.")
    else:
        report.append("• Waktu tutup feeding window belum direkod.")
    report.append("• Minum air kosong secukupnya.")
    report.append("• Rehat dan tidur secukupnya.")

    return "\n".join(report)


def main():
    parser = argparse.ArgumentParser(description="Deterministic Diet Reporter")
    parser.add_argument("--date", default=datetime.now().strftime("%Y-%m-%d"), help="Target date YYYY-MM-DD")
    parser.add_argument("--path", default=DEFAULT_DIET_LOG_PATH, help="Path to diet-log.json")
    parser.add_argument("--med-status", default=DEFAULT_MED_STATUS_PATH, help="Path to med-status.json")
    parser.add_argument("--mode", choices=["eod", "compact"], default="eod", help="Report mode")
    parser.add_argument("--json", action="store_true", help="Output raw JSON data for the date")

    args = parser.parse_args()

    data = load_diet_log(args.path)
    day_log = data.get("logs", {}).get(args.date)
    profile = data.get("profile", {})

    if not day_log:
        if args.json:
            print(json.dumps({"ok": False, "error": f"Tiada rekod diet dijumpai untuk tarikh {args.date}."}))
        else:
            print(f"Tiada rekod diet dijumpai untuk tarikh {args.date} dalam {args.path}.")
        return 0

    if args.json:
        print(json.dumps({"ok": True, "date": args.date, "data": day_log, "profile": profile}, indent=2))
        return 0

    if args.mode == "compact":
        output = format_compact_report(args.date, day_log)
    else:
        med_today = load_med_status_today(args.med_status, args.date)
        output = format_eod_report(args.date, day_log, profile, med_today)

    print(output)
    return 0


if __name__ == "__main__":
    sys.exit(main())
