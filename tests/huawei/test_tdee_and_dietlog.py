"""Contract tests for the dynamic-BMR + diet-log bridge in huawei-health-sync/sync_huawei.py (Phase 6).

Hermetic: no network, no tokens, no writes to the real `~/.hermes/diet-log.json`
(the module's DIET_LOG constant is redirected at a tmp copy).
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SYNC_PATH = REPO / "huawei-health-sync" / "sync_huawei.py"

BASE_DIET_LOG = {
    "version": "1.0.0",
    "profile": {
        "latest_weight_kg": 59.8,
        "latest_weight_date": "2026-11-14",
        "weight_history": [{"date": "2026-11-14", "weight_kg": 59.8}],
    },
    "logs": {
        "2026-11-16": {
            "meals": ["telur rebus 2"],
            "estimated_total_calories": 450.2,
            "burn": {"bmr_kcal": 1449, "tdee_kcal": 1829.8, "device_active_kcal": 380.8},
            "deficit_uniform": {"kcal": 1379.6, "tdee_kcal": 1829.8, "intake_kcal": 450.2},
        }
    },
}

PAYLOAD = {
    "date_myt": "2026-11-16",
    "fetched_at": "2026-11-16T22:48:22+08:00",
    "sync_settling": False,
    "body_weight_kg": 59.0,
    "body_weight_measured_date": "20261115",
    "metrics": {"active_kcal": {"value": 380.8}},
    "tdee_calibration": {
        "bmr_kcal": 1441,
        "bmr_basis": {"weight_kg": 59.0, "height_cm": 157.0, "age_years": 27},
        "pal_floor_kcal": 216.15,
        "device_active_kcal": 380.8,
        "candidate_tdee_kcal": 1821.8,
    },
}


@pytest.fixture(scope="module")
def sync_mod():
    # The module inserts its own BASE/VENDOR paths at import; add the repo copy first so the
    # test still works on a host without the live runtime directory.
    for p in (str(REPO / "huawei-health-sync" / "vendor"), str(REPO / "huawei-health-sync")):
        if p not in sys.path:
            sys.path.insert(0, p)
    spec = importlib.util.spec_from_file_location("sync_huawei_under_test", SYNC_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def diet_file(sync_mod, tmp_path):
    path = tmp_path / "diet-log.json"
    path.write_text(json.dumps(BASE_DIET_LOG, indent=1), encoding="utf-8")
    os.chmod(path, 0o600)
    original = sync_mod.DIET_LOG
    sync_mod.DIET_LOG = str(path)
    yield path
    sync_mod.DIET_LOG = original


def _read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


# ── Mifflin-St Jeor ──────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "weight,bmr",
    [(59.0, 1441), (59.8, 1449), (62.8, 1479), (53.0, 1381)],
)
def test_mifflin_bmr_matches_owner_profile(sync_mod, weight, bmr):
    assert sync_mod.mifflin_bmr(weight) == bmr


def test_no_hardcoded_bmr_constant_left(sync_mod):
    assert not hasattr(sync_mod, "BMR_KCAL"), "BMR must be dynamic; the old constant is gone"


def test_mifflin_matches_diet_report_formula():
    # same formula the tracker uses: 10*w + 6.25*157 - 5*27 + 5
    for w in (53.0, 59.0, 59.8, 62.8):
        assert round(10 * w + 6.25 * 157 - 5 * 27 + 5) == round(10 * w + 851.25)


# ── date normalisation ───────────────────────────────────────────────────

def test_iso_date_normalises_both_formats(sync_mod):
    assert sync_mod._iso_date("20261115") == "2026-11-15"
    assert sync_mod._iso_date("2026-11-14") == "2026-11-14"
    assert sync_mod._iso_date(None) is None
    assert sync_mod._iso_date("not-a-date") is None


# ── sync_diet_log guards ─────────────────────────────────────────────────

def test_settling_payload_never_writes(sync_mod, diet_file):
    before = diet_file.read_text(encoding="utf-8")
    payload = dict(PAYLOAD, sync_settling=True)
    res = sync_mod.sync_diet_log(payload)
    assert res["written"] is False
    assert "sync_settling" in res["reason"]
    assert diet_file.read_text(encoding="utf-8") == before


def test_settled_payload_updates_burn_and_deficit(sync_mod, diet_file):
    res = sync_mod.sync_diet_log(PAYLOAD)
    assert res["written"] is True
    day = _read(diet_file)["logs"]["2026-11-16"]
    assert day["burn"]["bmr_kcal"] == 1441
    assert day["burn"]["tdee_kcal"] == 1821.8
    assert day["burn"]["source"].endswith("data/latest.json")
    assert day["deficit_uniform"]["kcal"] == 1371.6          # 1821.8 - 450.2
    assert day["deficit_uniform"]["intake_kcal"] == 450.2
    # owner-authored content untouched
    assert day["meals"] == ["telur rebus 2"]


def test_newer_cloud_weight_updates_profile(sync_mod, diet_file):
    sync_mod.sync_diet_log(PAYLOAD)
    profile = _read(diet_file)["profile"]
    assert profile["latest_weight_kg"] == 59.0
    assert profile["latest_weight_date"] == "2026-11-15"
    assert profile["weight_history"] == BASE_DIET_LOG["profile"]["weight_history"], (
        "auto-sync must not invent weight_history entries"
    )


def test_older_cloud_weight_never_overwrites(sync_mod, diet_file):
    payload = dict(PAYLOAD, body_weight_kg=61.0, body_weight_measured_date="20261101")
    sync_mod.sync_diet_log(payload)
    profile = _read(diet_file)["profile"]
    assert profile["latest_weight_kg"] == 59.8
    assert profile["latest_weight_date"] == "2026-11-14"


def test_missing_day_entry_is_not_created(sync_mod, diet_file):
    payload = dict(PAYLOAD, date_myt="2026-12-31")
    res = sync_mod.sync_diet_log(payload)
    # the profile weight may still mirror forward (it is day-independent), but no day entry appears
    assert res["fields"] == ["profile.latest_weight_kg"]
    assert "2026-12-31" not in _read(diet_file)["logs"]
    assert any("no diet-log entry" in s for s in res["skipped"])


def test_no_intake_leaves_deficit_untouched(sync_mod, diet_file):
    data = _read(diet_file)
    del data["logs"]["2026-11-16"]["estimated_total_calories"]
    diet_file.write_text(json.dumps(data, indent=1), encoding="utf-8")
    res = sync_mod.sync_diet_log(PAYLOAD)
    assert res["written"] is True
    day = _read(diet_file)["logs"]["2026-11-16"]
    assert day["burn"]["tdee_kcal"] == 1821.8
    assert day["deficit_uniform"]["kcal"] == 1379.6, "deficit must not be recomputed without intake"


def test_file_mode_preserved(sync_mod, diet_file):
    sync_mod.sync_diet_log(PAYLOAD)
    assert oct(Path(diet_file).stat().st_mode & 0o777) == "0o600"


def test_missing_diet_log_is_reported_not_created(sync_mod, tmp_path):
    original = sync_mod.DIET_LOG
    missing = tmp_path / "nope.json"
    sync_mod.DIET_LOG = str(missing)
    try:
        res = sync_mod.sync_diet_log(PAYLOAD)
    finally:
        sync_mod.DIET_LOG = original
    assert res["written"] is False
    assert "cannot read" in res["reason"]
    assert not missing.exists()


# ── CLI surface ──────────────────────────────────────────────────────────

def test_cli_exposes_sync_diet_log_flag(sync_mod):
    args = sync_mod.parse_args(["--sync-diet-log"])
    assert args.sync_diet_log is True
    assert sync_mod.parse_args([]).sync_diet_log is False
