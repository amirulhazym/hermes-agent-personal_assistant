"""Diet integrity tests — deficit arithmetic, weight provenance, protein floors.

Tickets: .scratch/diet-deficit-integrity-20261128/issues/03..05

The load-bearing rule here is that a report may ADD advisory text but may never
rewrite a computed deficit (owner decision 2026-11-28).
"""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SCRIPT = REPO_ROOT / "scripts" / "diet_report.py"

spec = importlib.util.spec_from_file_location("diet_report_under_test", SCRIPT)
dr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dr)


# ── ticket 05: no clamp, ever ────────────────────────────────────────────────
def test_deficit_is_never_clamped():
    assert dr.reported_deficit(1657.2, 66.0) == 1591.2
    assert dr.reported_deficit(1657.2, 66.0) != 750


def test_deficit_identity_holds_for_synthetic_days():
    for tdee in (1657.2, 1974.22, 2376.4):
        for intake in (0.0, 66.0, 476.0, 900.0, 1731.0):
            assert abs(dr.reported_deficit(tdee, intake) - (tdee - intake)) < 1e-9


# ── ticket 03: weight provenance ─────────────────────────────────────────────
def test_weight_always_carries_measured_date():
    rendered = dr.render_weight(59.0, "2026-11-15")
    assert "59.0 kg" in rendered
    assert "2026-11-15" in rendered


def test_weight_without_date_is_marked_not_current():
    rendered = dr.render_weight(59.0, None)
    assert "tarikh tiada" in rendered


# ── ticket 04: dual protein floor, no false pass ─────────────────────────────
def test_protein_shows_both_floors():
    line = " ".join(dr.protein_floor_lines(28.55, 59.0))
    assert "70.8" in line
    assert "94.4" in line


def test_protein_below_floor_never_says_reached():
    line = " ".join(dr.protein_floor_lines(28.55, 59.0))
    assert "BELUM capai" in line
    assert "mencapai" not in line.lower()


def test_protein_above_floor_reports_reached():
    line = " ".join(dr.protein_floor_lines(71.0, 59.0))
    assert "BELUM" not in line
    assert "capai" in line


# ── ticket 02: profile consistency ───────────────────────────────────────────
def test_profile_inconsistency_is_flagged():
    warned = dr.profile_target_warnings(
        {"daily_deficit_target_kcal": 1400, "est_loss_per_week_kg": 0.45}
    )
    assert warned and "bercanggah" in warned[0]


def test_consistent_profile_is_silent():
    assert dr.profile_target_warnings(
        {"daily_deficit_target_kcal": 1100, "est_loss_per_week_kg": 1.0}
    ) == []


# ── ticket 01: captured live BMR profile (157 cm / 27 y) ─────────────────────
def test_bmr_uses_current_profile_not_legacy_168cm():
    # Mifflin-St Jeor at 59.0 kg, 157 cm, 27 y -> 1441
    assert dr.calculate_dynamic_bmr(59.0) == 1441


SAMPLE_DAY = {
    "fasting_window": "27 Nov 17:20 -> 28 Nov 11:05",
    "meals": ["Window 1 (11:05): air kelapa", "Window 1 (12:15): 4 telur rebus"],
    "estimated_total_calories": 476.0,
    "estimated_protein_g": 28.55,
    "estimated_carbs_g": 44.85,
    "estimated_fat_g": 20.3,
    "last_intake_time": "14:00",
    "protein_floor_check": {"floor_g_1_2": 70.8, "floor_g_1_6": 94.4},
}

SAMPLE_PROFILE = {
    "latest_weight_kg": 59.0,
    "latest_weight_date": "2026-11-15",
    "daily_deficit_target_kcal": 1100,
    "est_loss_per_week_kg": 1.0,
}


def test_eod_report_is_honest_about_weight_date_and_deficit():
    out = dr.format_eod_report("2026-11-28", SAMPLE_DAY, SAMPLE_PROFILE)
    assert "2026-11-15" in out, "weight must show its measurement date"
    # sedentary TDEE 1729.2 - intake 476 = 1253.2, and nothing may clamp it to 750
    deficit_lines = [ln for ln in out.splitlines() if "Defisit" in ln]
    assert deficit_lines, "deficit line missing"
    assert "1,253" in " ".join(deficit_lines)
    assert "750" not in " ".join(deficit_lines)
    assert "BELUM capai" in out


# ── cosmetic: degenerate deficit range ───────────────────────────────────────
def test_degenerate_deficit_range_collapses():
    assert dr.format_deficit_range(1253.2, 1253.2) == "*~1,253 kcal*"
    assert "hingga" in dr.format_deficit_range(1225.0, 1535.0)
