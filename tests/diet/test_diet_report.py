import json
import os
import subprocess
import pytest
from pathlib import Path

# Fixture data
SAMPLE_DIET_LOG = {
    "logs": {
        "2026-10-26": {
            "fasting_window": "Yesterday ~8:22pm -> ongoing (currently ~16.5 jam fast)",
            "workout": "60m cycling statik Zero (11:50am - 12:50pm, mixed posture, dynamic resistance, est. 380-450 kcal)",
            "hydration": "Infused water kayu manis + cengkih",
            "meals": [
                "Buka puasa (2:15pm): 1/4 telur mata + 10 utas pegaga (~65 kcal)",
                "Lunch (2:40pm): 5 ketul kecil rendang ayam (~160 kcal)",
                "Dinner (7:30pm): 3 ketul rendang + 2 telur rebus (~260 kcal)"
            ],
            "meds": {
                "A": "taken 06:00",
                "B": "taken 09:15",
                "C_CC": "taken 14:40",
                "E": "taken 20:55"
            },
            "estimated_calories_breakdown": {
                "buka_puasa_215pm": 65,
                "lunch_240pm": 160,
                "dinner_730pm": 260
            },
            "estimated_total_calories": 485,
            "estimated_protein_g": 45,
            "estimated_carbs_g": 35,
            "estimated_fat_g": 18,
            "pros": [
                "Tinggi potassium semulajadi bantu lawan kesan retensi natrium Dexa.",
                "Protein berkualiti tinggi dari telur rebus menyokong pemulihan otot."
            ],
            "cons": [
                "Minyak santan rendang malam melambatkan pengosongan gastrik."
            ],
            "next_actions": [
                "Slot E levetiracetam dah telan cantik.",
                "Minum 1-2 gelas air sebelum tidur."
            ]
        }
    }
}

@pytest.fixture
def diet_log_file(tmp_path):
    log_path = tmp_path / "diet-log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(SAMPLE_DIET_LOG, f, indent=2)
    return str(log_path)

def test_diet_report_eod_format(diet_log_file):
    script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "diet_report.py"
    cmd = ["python3", str(script_path), "--path", diet_log_file, "--date", "2026-10-26", "--mode", "eod"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Error: {res.stderr}"
    out = res.stdout

    # Check 5 major sections and emojis
    assert "📋 1. LOG PEMAKANAN HARIAN (INTAKE)" in out
    assert "🧪 2. PROFIL NUTRISI (MACROS)" in out
    assert "🔬 3. KAJIAN BIOMEDIKAL: PROS & CONS" in out
    assert "⚖️ 4. TENAGA KELUAR & STATUS DEFISIT (BURN)" in out
    assert "⚡ 5. NEXT ACTION MALAM INI" in out

    # Check numbers
    assert "485" in out or "485 kcal" in out
    assert "Protein:" in out

def test_diet_report_compact_format(diet_log_file):
    script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "diet_report.py"
    cmd = ["python3", str(script_path), "--path", diet_log_file, "--date", "2026-10-26", "--mode", "compact"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Error: {res.stderr}"
    out = res.stdout
    lines = [l for l in out.strip().split("\n") if l.strip()]
    assert len(lines) <= 5
    assert "Intake Semasa" in out or "Total Intake" in out

def test_diet_report_missing_date(diet_log_file):
    script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "diet_report.py"
    cmd = ["python3", str(script_path), "--path", diet_log_file, "--date", "2026-10-01", "--mode", "eod"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    assert "Tiada rekod diet dijumpai" in res.stdout or "empty" in res.stdout.lower()
