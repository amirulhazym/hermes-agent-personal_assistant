"""Hermetic tests for plugins/hybrid-web/provider.py Playwright driver leak fix.

No browser, no network: the /proc scan and the reaper are exercised against a
fake proc root / monkeypatched helpers.

Regression context (2026-11-10): crawl4ai's failure path left one
`playwright/driver/package/cli.js run-driver` node process (~135 MB RSS) as a
direct child of the gateway on every launch failure. 17 of them accumulated
before being manually reaped on 2026-11-07.
"""
from __future__ import annotations

import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROVIDER_PATH = REPO_ROOT / "plugins" / "hybrid-web" / "provider.py"


def _load_provider():
    """Load the plugin module with the runtime-only base class stubbed."""
    if "agent" not in sys.modules:
        pkg = types.ModuleType("agent")
        pkg.__path__ = []  # type: ignore[attr-defined]
        sys.modules["agent"] = pkg
    if "agent.web_search_provider" not in sys.modules:
        base = types.ModuleType("agent.web_search_provider")

        class WebSearchProvider:  # noqa: D401 - stub
            name = ""

        base.WebSearchProvider = WebSearchProvider  # type: ignore[attr-defined]
        sys.modules["agent.web_search_provider"] = base

    spec = importlib.util.spec_from_file_location("hybrid_web_provider_ssot", PROVIDER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def hw():
    return _load_provider()


def _fake_proc(root: Path, entries) -> Path:
    """entries: list of (pid, ppid, cmdline bytes)."""
    root.mkdir(parents=True, exist_ok=True)
    for pid, ppid, cmdline in entries:
        d = root / str(pid)
        d.mkdir()
        (d / "stat").write_text(f"{pid} (node) S {ppid} 0 0 0 0 0 0 0 0 0 0 0\n")
        (d / "cmdline").write_bytes(cmdline)
    return root


ME = os.getpid()
DRIVER_CMD = b"/usr/bin/node /x/playwright/driver/package/cli.js\x00run-driver\x00"


def test_detects_child_driver(hw, tmp_path):
    root = _fake_proc(
        tmp_path / "proc",
        [
            (101, ME, DRIVER_CMD),
            (102, 1, DRIVER_CMD),  # reparented to init: not our child
            (103, ME, b"/usr/bin/node\x00something-else\x00"),
        ],
    )
    assert hw._child_playwright_drivers(str(root)) == [101]


def test_pids_with_children(hw, tmp_path):
    root = _fake_proc(
        tmp_path / "proc",
        [(201, 42, b"x"), (202, 42, b"y"), (203, 1, b"z")],
    )
    parents = hw._pids_with_children(str(root))
    assert 42 in parents
    assert 203 not in parents


def test_reap_skips_driver_that_owns_a_browser(hw, monkeypatch):
    """A driver with a live chromium child belongs to a running extraction."""
    monkeypatch.setattr(hw, "_child_playwright_drivers", lambda *a, **k: [301])
    monkeypatch.setattr(hw, "_pids_with_children", lambda *a, **k: {301})
    killed = []
    monkeypatch.setattr(hw.os, "kill", lambda pid, sig: killed.append(pid))

    assert hw._reap_new_drivers(set(), grace_s=0.0) == []
    assert killed == []


def test_reap_terminates_childless_new_driver(hw, monkeypatch):
    monkeypatch.setattr(hw, "_child_playwright_drivers", lambda *a, **k: [401])
    monkeypatch.setattr(hw, "_pids_with_children", lambda *a, **k: set())

    seen = []

    def fake_reap(pids):
        seen.extend(sorted(pids))
        return sorted(pids)

    monkeypatch.setattr(hw, "_reap_drivers", fake_reap)

    reaped = hw._reap_new_drivers(set(), grace_s=0.0)
    assert reaped == [401]
    assert seen == [401]


def test_reap_ignores_pre_existing_driver(hw, monkeypatch):
    """Snapshot-before semantics: drivers that already existed are untouched."""
    monkeypatch.setattr(hw, "_child_playwright_drivers", lambda *a, **k: [501])
    monkeypatch.setattr(hw, "_pids_with_children", lambda *a, **k: set())
    monkeypatch.setattr(hw.os, "kill", lambda *a: pytest.fail("must not kill pre-existing"))

    assert hw._reap_new_drivers({501}, grace_s=0.0) == []


def test_prefers_system_chrome_before_bundled(hw):
    assert hw.CHROME_CHANNEL_CANDIDATES[0] == "chrome"
    assert None in hw.CHROME_CHANNEL_CANDIDATES


def test_reexport_driver_marker_matches_playwright_layout(hw):
    assert hw._PLAYWRIGHT_DRIVER_MARKER == "playwright/driver/package/cli.js"
