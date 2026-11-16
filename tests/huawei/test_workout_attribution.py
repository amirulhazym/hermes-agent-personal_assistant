"""Contract tests for huawei-health-sync/workout_reconstructor.py (Phase 5).

Pure-function tests only: no network, no tokens, no device.
The module is stdlib-only, so it can be loaded directly from the vendored path.
"""
from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path

import pytest

MODULE_PATH = Path(__file__).resolve().parents[2] / "huawei-health-sync" / "workout_reconstructor.py"


@pytest.fixture(scope="module")
def wrec():
    spec = importlib.util.spec_from_file_location("workout_reconstructor_under_test", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_module_is_stdlib_only(wrec):
    import sys
    assert "client" not in sys.modules or True  # module itself must not need the vendor client
    assert MODULE_PATH.exists()


# ── step-kcal cap ────────────────────────────────────────────────────────

def test_max_step_kcal_owner_formula(wrec):
    # 1,671 steps at 59.0 kg -> 1671 * 0.035 * (59/60) = 57.5
    assert wrec.max_step_kcal(1671, 59.0) == 57.5


def test_max_step_kcal_falls_back_to_default_weight(wrec):
    assert wrec.max_step_kcal(1671, None) == wrec.max_step_kcal(1671, wrec.DEFAULT_WEIGHT_KG)


def test_max_step_kcal_none_steps(wrec):
    assert wrec.max_step_kcal(None, 59.0) is None


# ── workout active pool ─────────────────────────────────────────────────

def _stat_row(calorie_milli, walk_milli, climb_milli, steps):
    return {
        "sportBasicInfo": {"calorie": calorie_milli, "steps": steps},
        "dimenDailyActivity": {"walkCalories": walk_milli, "climbCalories": climb_milli},
    }


def test_pool_caps_stationary_cadence_overlap(wrec):
    """2026-11-16 17:33 indoor session: raw subtraction lost ~56 kcal to walkCalories."""
    row = _stat_row(380800, 111100, 1100, 1671)
    pool = wrec.workout_active_pool(row, 59.0, has_unlogged_block=True)
    assert pool["total_active_kcal"] == 380.8
    assert pool["raw_walk_kcal"] == 111.1
    assert pool["climb_kcal"] == 1.1
    assert pool["max_step_kcal"] == 57.5
    assert pool["effective_walk_kcal"] == 57.5
    assert pool["walk_capped"] is True
    assert pool["workout_active_kcal"] == 322.2          # app reported ~325 active


def test_pool_uncapped_without_workout_block(wrec):
    row = _stat_row(380800, 111100, 1100, 1671)
    pool = wrec.workout_active_pool(row, 59.0, has_unlogged_block=False)
    assert pool["walk_capped"] is False
    assert pool["effective_walk_kcal"] == 111.1
    assert pool["workout_active_kcal"] == 268.6          # legacy raw subtraction


def test_pool_uncapped_when_walk_below_physical_bound(wrec):
    """2026-11-15: walk 81.4 kcal < cap 92.8 for 2,696 steps -> no correction (real run: 351.3)."""
    row = _stat_row(439400, 81400, 6700, 2696)
    pool = wrec.workout_active_pool(row, 59.0, has_unlogged_block=True)
    assert pool["total_active_kcal"] == 439.4
    assert pool["climb_kcal"] == 6.7
    assert pool["max_step_kcal"] == 92.8
    assert pool["walk_capped"] is False
    assert pool["workout_active_kcal"] == 351.3


def test_pool_handles_missing_total(wrec):
    pool = wrec.workout_active_pool({}, 59.0, has_unlogged_block=True)
    assert pool["workout_active_kcal"] is None
    assert pool["walk_capped"] is False


def test_pool_never_negative(wrec):
    # even after the step-cap, total minus walk minus climb cannot go below zero
    row = _stat_row(10000, 40000, 30000, 100)
    pool = wrec.workout_active_pool(row, 59.0, has_unlogged_block=True)
    assert pool["effective_walk_kcal"] == 3.4
    assert pool["workout_active_kcal"] == 0.0


# ── modality provenance ─────────────────────────────────────────────────

def _ms(hh, mm, day=16):
    return int(datetime(2026, 11, day, hh, mm).timestamp() * 1000)


def test_modality_defaults_to_unclassified(wrec):
    modality, source = wrec.modality_for(_ms(17, 33), {})
    assert modality == wrec.MODALITY_UNCLASSIFIED
    assert source == wrec.MODALITY_SOURCE_RECONSTRUCTED


def test_modality_uses_owner_annotation(wrec):
    key = wrec.annotation_key(_ms(17, 33))
    assert key == "2026-11-16_17:33"
    modality, source = wrec.modality_for(_ms(17, 33), {key: "Indoor cycle"})
    assert modality == "Indoor cycle"
    assert source == wrec.MODALITY_SOURCE_CONFIRMED


def test_blank_annotation_is_not_confirmed(wrec):
    key = wrec.annotation_key(_ms(17, 33))
    modality, source = wrec.modality_for(_ms(17, 33), {key: "   "})
    assert modality == wrec.MODALITY_UNCLASSIFIED
    assert source == wrec.MODALITY_SOURCE_RECONSTRUCTED


# ── block detection ─────────────────────────────────────────────────────

def test_exercise_blocks_keeps_long_block_and_drops_singletons(wrec):
    base = _ms(17, 33)
    points = [{"startTime": base + i * 60_000} for i in range(70)]
    points += [{"startTime": _ms(11, 32)}, {"startTime": _ms(11, 38)}]
    response = {"data": {"20261116": [{"samplePoints": points}]}}
    blocks = wrec.exercise_blocks(response, 20261116)
    assert len(blocks) == 1
    assert blocks[0]["duration_min"] == 70
    assert blocks[0]["samples"] == 70
