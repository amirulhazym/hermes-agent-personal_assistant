import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "diet_report.py"

# Fixture mirrors the 2026-11-03 structure plus the evidence fields added on
# 2026-11-06 (explicit burn estimate, intake band, beverages, micronutrients).
SAMPLE_DIET_LOG = {
    "profile": {"latest_weight_kg": 62.8, "latest_weight_date": "2026-11-02"},
    "logs": {
        "2026-11-03": {
            "fasting_window": "Yesterday 8:25pm -> today 3:30pm (19 jam 05 minit solid fast)",
            "workout": "79.25m (1:19:15) cycling statik Zero (stop 2:55pm)",
            "workout_notes": "Stopwatch 1:19:15.",
            "active_burn_kcal_estimate": {
                "low": 250,
                "mid": 350,
                "high": 400,
                "basis": "MET band 3.5-5.0 x 62.8kg x 90.4min",
            },
            "meals": [
                "Window 1 / Buka Puasa (3:30pm): Timun (~60g, ~10 kcal)",
                "Tomato kecil (~75g, ~15 kcal)",
                "Dada ayam air-fryer (~105g, ~165 kcal, ~31g prot)",
                "Air rebus kayu manis (0 kcal)",
                "Slot C (CC: Calcium Carbonate 500mg + Calcitriol) taken 15:30",
                "Window 2 / Sahur Penutup (8:02pm): 2 biji telur rebus Gred B (~100g, ~140 kcal)",
            ],
            "beverages": ["Air rebusan kayu manis + bunga cengkih (~700ml, 0 kcal)"],
            "micronutrients": {"Lutein (gummy 2 biji)": "20mg"},
            "meds": {},
            "estimated_calories_breakdown": {"dada_ayam": 165, "tempe_tauhu": 85, "telur_rebus": 140},
            "estimated_total_calories": 722,
            "estimated_calorie_range_kcal": [640, 800],
            "estimated_protein_g": 88.4,
            "estimated_carbs_g": 18.3,
            "estimated_fat_g": 32.3,
            "last_intake_time": "~20:02",
        }
    },
}

SAMPLE_MED_STATUS = {
    "meds": {
        "A": {"2026-11-03": {"overall": "completed", "drugs": {
            "akurit_2": {"status": "taken", "time": "07:00"},
            "pyridoxine": {"status": "taken", "time": "07:00"},
        }}},
        "C": {"2026-11-03": {"overall": "completed", "drugs": {
            "calcium": {"status": "taken", "time": "15:30"},
            "calcitriol": {"status": "taken", "time": "15:30"},
        }}},
        "E": {"2026-11-03": {"overall": "pending", "drugs": {
            "levetiracetam_e": {"status": "pending", "time": None},
        }}},
    }
}


@pytest.fixture
def diet_log_file(tmp_path):
    log_path = tmp_path / "diet-log.json"
    log_path.write_text(json.dumps(SAMPLE_DIET_LOG, indent=2), encoding="utf-8")
    return str(log_path)


@pytest.fixture
def med_status_file(tmp_path):
    path = tmp_path / "med-status.json"
    path.write_text(json.dumps(SAMPLE_MED_STATUS, indent=2), encoding="utf-8")
    return str(path)


def run_report(diet_log, med_status=None, date="2026-11-03", mode="eod"):
    cmd = ["python3", str(SCRIPT), "--path", diet_log, "--date", date, "--mode", mode]
    if med_status is not None:
        cmd += ["--med-status", med_status]
    res = subprocess.run(cmd, capture_output=True, text=True)
    assert res.returncode == 0, f"Error: {res.stderr}"
    return res.stdout


def test_eod_sections_present(diet_log_file, med_status_file):
    out = run_report(diet_log_file, med_status_file)
    assert "⏱️ *PUASA & WORKOUT*" in out
    assert "🥗 *1. MENU MAKANAN & KALORI" in out
    assert "🧪 *2. PROFIL NUTRISI*" in out
    assert "🌿 *HIDRASI & MINUMAN*" in out
    assert "💊 *STATUS UBAT HARIAN*" in out
    assert "⚖️ *STATUS DEFISIT & KALORI*" in out
    assert "💡 *TINDAKAN MALAM INI*" in out
    assert "722 kcal" in out
    assert "62.8 kg" in out


def test_zero_markdown_tables(diet_log_file, med_status_file):
    out = run_report(diet_log_file, med_status_file)
    assert "|" not in out


# --- Regression: hardcoded 500 kcal burn heuristic (removed 2026-11-06) -----


def test_burn_comes_from_log_not_hardcoded_heuristic(diet_log_file, med_status_file):
    """Workout text contains '79' and '1:19' which used to force 500 kcal."""
    out = run_report(diet_log_file, med_status_file)
    assert "~350 kcal (julat 250–400)" in out
    # The removed heuristic would have printed this exact burn line at 500.
    assert "*Tenaga Terbakar (anggaran log):* ~500 kcal" not in out
    assert "~500 kcal (julat" not in out
    assert "2,150" in out  # 1800 + 350
    # 2050-800 .. 2200-640
    assert "1,250" in out and "1,560" in out


def test_burn_derived_from_duration_and_met_band(tmp_path, med_status_file):
    """When no explicit burn is recorded, derive it from the reported duration."""
    data = json.loads(json.dumps(SAMPLE_DIET_LOG))
    day = data["logs"]["2026-11-03"]
    del day["active_burn_kcal_estimate"]
    day["workout_duration_min"] = 79.25
    day["workout_met_band"] = {"low": 3.5, "high": 5.0, "label": "light"}
    log_path = tmp_path / "diet-log-derived.json"
    log_path.write_text(json.dumps(data), encoding="utf-8")

    out = run_report(str(log_path), med_status_file)
    assert "Tenaga Terbakar (anggaran dikira)" in out
    assert "79.25 min x MET 3.5-5" in out
    assert "62.8kg" in out
    # Existing magic constant must never reappear.
    assert "~500 kcal" not in out


def test_missing_burn_inputs_are_named_not_skipped(tmp_path, med_status_file):
    """A missing duration must be requested explicitly, never silently zeroed."""
    data = json.loads(json.dumps(SAMPLE_DIET_LOG))
    del data["logs"]["2026-11-03"]["active_burn_kcal_estimate"]
    log_path = tmp_path / "diet-log-no-burn.json"
    log_path.write_text(json.dumps(data), encoding="utf-8")

    out = run_report(str(log_path), med_status_file)
    assert "belum boleh dikira" in out
    assert "tempoh workout dalam minit" in out
    assert "Perlu diisi" in out
    assert "~500 kcal" not in out


def test_missing_met_band_is_named(tmp_path, med_status_file):
    data = json.loads(json.dumps(SAMPLE_DIET_LOG))
    day = data["logs"]["2026-11-03"]
    del day["active_burn_kcal_estimate"]
    day["workout_duration_min"] = 79.25
    log_path = tmp_path / "diet-log-no-met.json"
    log_path.write_text(json.dumps(data), encoding="utf-8")

    out = run_report(str(log_path), med_status_file)
    assert "keamatan workout" in out


# --- Regression: invented micronutrients (removed 2026-11-06) ---------------


def test_unconsumed_supplement_is_never_claimed(tmp_path, med_status_file):
    """No lutein recorded today -> the report must not print a lutein figure."""
    data = json.loads(json.dumps(SAMPLE_DIET_LOG))
    data["logs"]["2026-11-03"].pop("micronutrients", None)
    log_path = tmp_path / "diet-log-no-micro.json"
    log_path.write_text(json.dumps(data), encoding="utf-8")

    out = run_report(str(log_path), med_status_file)
    assert "Lutein" not in out
    assert "Selenium" not in out
    # Potassium is still estimated — but only from foods actually logged.
    assert "Kalium (anggaran)" in out
    assert "Asas: USDA FoodData Central" in out


def test_micronutrients_rendered_when_recorded(diet_log_file, med_status_file):
    out = run_report(diet_log_file, med_status_file)
    assert "Mikronutrien direkod" in out
    assert "Lutein" in out
    assert "20mg" in out


def test_no_micronutrient_data_shows_explicit_no_data(tmp_path, med_status_file):
    data = json.loads(json.dumps(SAMPLE_DIET_LOG))
    day = data["logs"]["2026-11-03"]
    day.pop("micronutrients", None)
    day["meals"] = ["Window 1 (3:30pm): air kosong sahaja"]
    day["beverages"] = []
    log_path = tmp_path / "diet-log-empty-micro.json"
    log_path.write_text(json.dumps(data), encoding="utf-8")

    # No CC tablet either, otherwise the calcium line legitimately populates the section.
    meds = json.loads(json.dumps(SAMPLE_MED_STATUS))
    meds["meds"].pop("C")
    med_path = tmp_path / "med-status-no-cc.json"
    med_path.write_text(json.dumps(meds), encoding="utf-8")

    out = run_report(str(log_path), str(med_path))
    assert "Tiada data direkod untuk mikronutrien" in out


# --- Regression: medication status now read from med-status.json ------------


def test_medication_status_read_from_med_status_file(diet_log_file, med_status_file):
    out = run_report(diet_log_file, med_status_file)
    assert "Tiada rekod ubat" not in out
    assert "Slot A: akurit_2 07:00" in out
    assert "Slot C:" in out and "calcium 15:30" in out
    assert "Slot E: levetiracetam_e (pending)" in out


def test_missing_med_status_file_is_reported_not_invented(tmp_path, diet_log_file):
    out = run_report(diet_log_file, str(tmp_path / "nope.json"))
    assert "med-status.json tiada entri" in out
    assert "Slot A" not in out


# --- Misc behaviour --------------------------------------------------------


def test_macro_kcal_drift_is_surfaced_when_large(tmp_path, med_status_file):
    data = json.loads(json.dumps(SAMPLE_DIET_LOG))
    day = data["logs"]["2026-11-03"]
    day["estimated_protein_g"] = 200.0  # 800 kcal protein alone -> obvious drift
    log_path = tmp_path / "diet-log-drift.json"
    log_path.write_text(json.dumps(data), encoding="utf-8")

    out = run_report(str(log_path), med_status_file)
    assert "Macro beri" in out


def test_unverified_beverage_preparation_is_flagged(tmp_path, med_status_file):
    data = json.loads(json.dumps(SAMPLE_DIET_LOG))
    data["logs"]["2026-11-03"]["beverage_preparing"] = "Air kulit kayu manis: sedang dibuat."
    log_path = tmp_path / "diet-log-prep.json"
    log_path.write_text(json.dumps(data), encoding="utf-8")

    out = run_report(str(log_path), med_status_file)
    assert "Belum disahkan diminum" in out


def test_compact_format(diet_log_file):
    out = run_report(diet_log_file, mode="compact")
    lines = [line for line in out.strip().split("\n") if line.strip()]
    assert len(lines) <= 5
    assert "Intake Semasa" in out


def test_missing_date(diet_log_file):
    out = run_report(diet_log_file, date="2026-10-01")
    assert "Tiada rekod diet dijumpai" in out


def test_med_status_default_path_is_hermes_home():
    """Default med-status path resolves under ~/.hermes unless overridden."""
    import importlib.util
    import sys

    spec = importlib.util.spec_from_file_location("diet_report_mod", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["diet_report_mod"] = module
    spec.loader.exec_module(module)
    assert module.DEFAULT_MED_STATUS_PATH.endswith(".hermes/med-status.json")
