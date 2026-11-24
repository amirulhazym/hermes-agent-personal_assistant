"""Hermetic tests for the 'already broke the fast today' anchor defect.

Owner incident 2026-11-24: diet-log carried
`fasting_window: "23 Nov 19:40 -> 24 Nov 13:40"` and `last_intake_time: "14:15"`,
yet `if_berbuka.py --json` still answered `fast_now_h 20.98 / target 12:40` and the
agent told him "boleh berbuka sekarang" — hours after he had already eaten.

Contract under test: when today's log entry proves the fast ended (window end or a
food intake today), berbuka_plan() must flag it and expose the actual break time
instead of presenting a future target.
"""
from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "if_berbuka.py"
MYT = ZoneInfo("Asia/Kuala_Lumpur")


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location("if_berbuka_under_test", SCRIPT)
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _log(**entries):
    return {"logs": entries}


def test_already_broken_from_fasting_window(mod, monkeypatch):
    monkeypatch.setattr(mod, "_load_log", lambda: _log(**{
        "2026-11-23": {"last_intake_time": "19:40 (boss)"},
        "2026-11-24": {"fasting_window": "23 Nov 19:40 -> 24 Nov 13:40"},
    }))
    plan = mod.berbuka_plan(datetime(2026, 11, 24, 16, 38, tzinfo=MYT))
    assert plan["ok"] is True
    assert plan["already_broken"] is True
    assert plan["broken_at"] == "13:40"


def test_already_broken_from_today_intake(mod, monkeypatch):
    monkeypatch.setattr(mod, "_load_log", lambda: _log(**{
        "2026-11-23": {"last_intake_time": "19:40 (boss)"},
        "2026-11-24": {"last_intake_time": "14:15 (laporan lengkap boss)"},
    }))
    plan = mod.berbuka_plan(datetime(2026, 11, 24, 16, 38, tzinfo=MYT))
    assert plan["already_broken"] is True
    assert plan["broken_at"] == "14:15"


def test_not_broken_when_today_has_no_food(mod, monkeypatch):
    monkeypatch.setattr(mod, "_load_log", lambda: _log(**{
        "2026-11-23": {"last_intake_time": "19:40 (boss)"},
        "2026-11-24": {},
    }))
    plan = mod.berbuka_plan(datetime(2026, 11, 24, 16, 38, tzinfo=MYT))
    assert plan["already_broken"] is False
    assert plan.get("broken_at") is None
    # locked constants must not move
    assert plan["target"] == "12:40"
    assert plan["min_target"] == "11:40"


def test_pending_window_is_not_a_break(mod, monkeypatch):
    monkeypatch.setattr(mod, "_load_log", lambda: _log(**{
        "2026-11-23": {"last_intake_time": "19:40 (boss)"},
        "2026-11-24": {"fasting_window": "PENDING - boss belum nyatakan"},
    }))
    plan = mod.berbuka_plan(datetime(2026, 11, 24, 16, 38, tzinfo=MYT))
    assert plan["already_broken"] is False


def test_reminder_fire_time_unchanged(mod, monkeypatch):
    """berbuka_target_hhmm must keep returning the heads-up clock: reminders are
    owner-locked and this fix must not move them."""
    monkeypatch.setattr(mod, "_load_log", lambda: _log(**{
        "2026-11-23": {"last_intake_time": "19:40 (boss)"},
        "2026-11-24": {},
    }))
    assert mod.berbuka_target_hhmm() == "10:40"
