import json
import os
import subprocess
import pytest
from pathlib import Path

# Fixture data with new structure
SAMPLE_DIET_LOG = {
    "profile": {
        "latest_weight_kg": 62.8,
        "latest_weight_date": "2026-11-02"
    },
    "logs": {
        "2026-11-03": {
            "fasting_window": "Yesterday 8:25pm -> today 3:30pm (19 jam 05 minit solid fast)",
            "workout": "79.25m (1:19:15) cycling statik Zero (stop 2:55pm, est. 480-520 kcal)",
            "meals": [
                "Window 1 / Buka Puasa (3:30pm): Timun (~60g, ~10 kcal)",
                "Tomato kecil (~75g, ~15 kcal)",
                "Dada ayam air-fryer (~105g, ~165 kcal, ~31g prot)",
                "1 jemput telur dadar (~15g, ~40 kcal, ~2.5g prot)",
                "Lutein 20mg gummy (~12 kcal, ~3g carbs)",
                "Air-fried tempe (~30g) & tauhu (~40g) [~85 kcal, ~8.7g prot]",
                "Air rebusan kayu manis + bunga cengkih (0 kcal)",
                "Slot C (CC: Calcium Carbonate 500mg + Calcitriol) taken 15:30",
                "Window 2 / Sahur Penutup (8:02pm): Timun (~60g, ~10 kcal)",
                "2 keping daging sup (~40g, ~95 kcal, ~11.0g prot)",
                "1 jemput telur dadar lebihan (~15g, ~40 kcal, ~2.5g prot)",
                "Tomato saiz kecil (~75g, ~15 kcal)",
                "Seketul kecil sederhana ayam air-fryer bahagian isi (~60g, ~95 kcal, ~18.0g prot)",
                "2 biji telur rebus Gred B (~100g, ~140 kcal, ~12.5g prot)"
            ],
            "meds": {
                "A": "taken 07:00 (Akurit-2 + Pyridoxine)",
                "B": "taken 09:15 (Dexa 6mg + Letram 500mg)",
                "C": "taken 15:30 (Calcium Carbonate 500mg + Calcitriol)",
                "E": "taken 20:55 (Letram 500mg)"
            },
            "estimated_calories_breakdown": {
                "dada_ayam": 165,
                "tempe_tauhu": 85,
                "telur_rebus": 140
            },
            "estimated_total_calories": 722,
            "estimated_protein_g": 88.4,
            "estimated_carbs_g": 18.3,
            "estimated_fat_g": 32.3
        }
    }
}

@pytest.fixture
def diet_log_file(tmp_path):
    log_path = tmp_path / "diet-log.json"
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(SAMPLE_DIET_LOG, f, indent=2)
    return str(log_path)

def test_diet_report_eod_new_structured_format(diet_log_file):
    script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "diet_report.py"
    cmd = ["python3", str(script_path), "--path", diet_log_file, "--date", "2026-11-03", "--mode", "eod"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Error: {res.stderr}"
    out = res.stdout

    # Must contain the new approved sections
    assert "⏱️ *PUASA & WORKOUT*" in out
    assert "🥗 *1. MENU MAKANAN & KALORI" in out
    assert "🧪 *2. PROFIL NUTRISI LENGKAP" in out
    assert "🌿 *HIDRASI & MINUMAN*" in out
    assert "💊 *STATUS UBAT HARIAN" in out or "💊 *UBAT-UBATAN HARIAN*" in out
    assert "⚖️ *STATUS DEFISIT & KALORI*" in out
    assert "💡 *TINDAKAN MALAM INI*" in out

    # Dynamic BMR check for 62.8kg
    assert "62.8 kg" in out
    assert "~1,500 kcal" in out or "1500 kcal" in out or "1,49" in out or "1,54" in out
    # Net deficit check
    assert "-1,5" in out or "Defisit Bersih" in out

    # Check that meals are itemized with kcal
    assert "Dada ayam" in out
    assert "722 kcal" in out

    # Check full nutrition entries
    assert "Protein:" in out
    assert "Karbohidrat:" in out
    assert "Lemak:" in out
    assert "Kalium (Potassium):" in out
    assert "Natrium (Sodium):" in out
    assert "Kalsium:" in out

    # ZERO markdown tables allowed on WhatsApp
    assert "|" not in out

def test_diet_report_dynamic_bmr_calculation(diet_log_file):
    script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "diet_report.py"
    cmd = ["python3", str(script_path), "--path", diet_log_file, "--date", "2026-11-03", "--mode", "eod"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0
    # Must NOT use the old static 1850 kcal as BMR
    assert "BMR & Asas Harian:* ~1850 kcal" not in res.stdout

def test_diet_report_compact_format(diet_log_file):
    script_path = Path(__file__).resolve().parent.parent.parent / "scripts" / "diet_report.py"
    cmd = ["python3", str(script_path), "--path", diet_log_file, "--date", "2026-11-03", "--mode", "compact"]
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
