"""Hermetic tests for scripts/dashboard_idle_guard.py.

Owner policy under test: dashboard off after 4h idle; RDC never touched.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "dashboard_idle_guard.py"


@pytest.fixture(scope="module")
def g():
    spec = importlib.util.spec_from_file_location("dashboard_idle_guard", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_connection_counts_as_active(g):
    now = 1_000_000.0
    assert g.decide(now, now - 10 * 3600, 4 * 3600, 1) == "active"


def test_idle_under_threshold_keeps_running(g):
    now = 1_000_000.0
    assert g.decide(now, now - 3 * 3600, 4 * 3600, 0) == "idle-keep"


def test_idle_over_threshold_stops(g):
    now = 1_000_000.0
    assert g.decide(now, now - 4 * 3600 - 1, 4 * 3600, 0) == "idle-stop"


def test_exactly_at_threshold_stops(g):
    now = 1_000_000.0
    assert g.decide(now, now - 4 * 3600, 4 * 3600, 0) == "idle-stop"


def test_state_roundtrip(g, tmp_path):
    p = tmp_path / "sub" / "state"
    g.write_last_activity(12345.9, str(p))
    assert g.read_last_activity(str(p)) == 12345.0


def test_missing_state_returns_none(g, tmp_path):
    assert g.read_last_activity(str(tmp_path / "nope")) is None


def test_inactive_service_never_stops_and_refreshes_clock(g, monkeypatch, tmp_path):
    state = tmp_path / "state"
    calls = []
    monkeypatch.setattr(g, "service_active", lambda *a, **k: False)
    monkeypatch.setattr(g, "_run", lambda cmd: (calls.append(cmd) or (0, "")))

    rc = g.main(["--state-file", str(state)])
    assert rc == 0
    assert g.read_last_activity(str(state)) is not None
    assert not any("stop" in c for c in calls)


def test_dry_run_does_not_stop(g, monkeypatch, tmp_path):
    state = tmp_path / "state"
    g.write_last_activity(1.0, str(state))
    calls = []
    monkeypatch.setattr(g, "service_active", lambda *a, **k: True)
    monkeypatch.setattr(g, "count_active_connections", lambda *a, **k: 0)
    monkeypatch.setattr(g, "_run", lambda cmd: (calls.append(cmd) or (0, "")))

    rc = g.main(["--state-file", str(state), "--dry-run"])
    assert rc == 0
    assert not any("stop" in c for c in calls)


def test_stop_targets_only_the_dashboard_unit(g, monkeypatch, tmp_path):
    """Hard policy: idle-stop may only ever stop the dashboard unit (never RDC)."""
    state = tmp_path / "state"
    g.write_last_activity(1.0, str(state))
    calls = []
    monkeypatch.setattr(g, "service_active", lambda *a, **k: True)
    monkeypatch.setattr(g, "count_active_connections", lambda *a, **k: 0)
    monkeypatch.setattr(g, "_run", lambda cmd: (calls.append(cmd) or (0, "")))

    rc = g.main(["--state-file", str(state)])
    assert rc == 0
    assert calls == [["systemctl", "stop", "hermes-dashboard.service"]]
    assert g.SERVICE == "hermes-dashboard.service"
