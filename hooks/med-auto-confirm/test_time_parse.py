"""Hermetic tests for tolerant med-intake time parsing in the auto-confirm hook.

Covers the 2026-08-12 regression: user messages like
"Dah makan dexa petang, 4.32pm tadi" and typos like "432pm" were rejected
as `missing-intake-time` because TIME_RE required a leading word
(pukul/jam/at/@/pada). Requirement (owner, 2026-08-12): parse common
variants intelligently; keep the G-2 hardening (bare "20:00" in
discussion without am/pm must NOT become a med time); when no time can be
resolved, the hook must record CLARIFY, never silently REJECT.
"""
import importlib.util
import os
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
LIVE = Path("/home/ubuntu/.hermes")


def load_handler(home: Path):
    os.environ["HERMES_HOME"] = str(home)
    for name in ("med_resolve", "med_safety_gate", "med_auto_confirm_time_test"):
        sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(
        "med_auto_confirm_time_test", BASE / "hooks" / "med-auto-confirm" / "handler.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load isolated med-auto-confirm handler")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class TestTimeParse(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / ".hermes"
        self.home.mkdir(parents=True)
        self.handler = load_handler(self.home)
        # Fixed reference time: 2026-08-12 23:00 MYT
        self.now = datetime(2026, 8, 12, 23, 0)

    def tearDown(self):
        self.tmp.cleanup()

    def _parse(self, msg: str):
        dt = self.handler._parse_time(msg, self.now)
        return f"{dt.hour:02d}:{dt.minute:02d}" if dt else None

    # --- New tolerant formats (2026-08-12) ---
    def test_pm_dot_without_leading_word(self):
        # "Dah makan dexa petang, 4.32pm tadi" -> 16:32
        self.assertEqual(self._parse("Dah makan dexa petang, 4.32pm tadi"), "16:32")

    def test_pm_colon_without_leading_word(self):
        self.assertEqual(self._parse("Dah makan dexa petang, 4:32pm tadi"), "16:32")

    def test_compact_typo_432pm(self):
        # Typo "432pm" = 4:32pm
        self.assertEqual(self._parse("Dah makan dexa petang, 432pm tadi"), "16:32")

    def test_compact_typo_815pm(self):
        self.assertEqual(self._parse("dah makan letram malam 815pm"), "20:15")

    def test_am_compact(self):
        self.assertEqual(self._parse("dah makan akurit 645am tadi"), "06:45")

    def test_pm_without_minutes(self):
        # "4pm" with no minutes -> 16:00
        self.assertEqual(self._parse("dah makan dexa 4pm tadi"), "16:00")

    def test_bare_dot_12h_no_suffix_in_completion(self):
        # "4.32" alone (no am/pm) is NOT accepted without leading word (G-2)
        self.assertIsNone(self._parse("dah makan dexa petang, 4.32 tadi"))

    # --- Regression: leading-word formats keep working ---
    def test_leading_jam_am_pm(self):
        self.assertEqual(self._parse("Dah makan dexa jam 1.49pm"), "13:49")

    def test_leading_jam_dot(self):
        self.assertEqual(self._parse("Dah makan letram malam jam 8.12pm"), "20:12")

    def test_leading_pukul(self):
        self.assertEqual(self._parse("dah makan dexa pukul 12.15pm"), "12:15")

    def test_leading_jam_no_suffix(self):
        # 24h with leading word remains accepted
        self.assertEqual(self._parse("dah makan dexa jam 16:32"), "16:32")

    # --- G-2 hardening: bare times in discussion must NOT match ---
    def test_bare_24h_no_leading_word_not_accepted(self):
        self.assertIsNone(self._parse("makan lepas 20:00"))

    def test_bare_24h_no_suffix_not_accepted(self):
        self.assertIsNone(self._parse("dah makan ubat 20:00"))

    # --- No time at all -> None (hook records CLARIFY, agent asks) ---
    def test_no_time_returns_none(self):
        self.assertIsNone(self._parse("Dah makan dexa petang"))

    def test_cc_leading_word_regression(self):
        self.assertEqual(self._parse("Dah makan CC jam 1.35pm tadi"), "13:35")

    # --- Invalid values rejected ---
    def test_invalid_hour_rejected(self):
        self.assertIsNone(self._parse("dah makan dexa jam 25:00"))

    def test_invalid_minute_rejected(self):
        self.assertIsNone(self._parse("dah makan dexa jam 12:99"))


class TestClarifyLabel(unittest.TestCase):
    """Missing intake time must be logged as CLARIFY (agent asks), not REJECT."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / ".hermes"
        self.home.mkdir(parents=True)
        (self.home / "logs").mkdir()
        self.handler = load_handler(self.home)

    def tearDown(self):
        self.tmp.cleanup()

    def test_audit_label_is_clarify_when_time_missing(self):
        # Isolate audit: point AUDIT_LOG at the temp home and call handle()
        # with a completion message that has no time.
        from unittest import mock

        with mock.patch.object(self.handler, "_audit") as audit:
            self.handler.handle(
                "agent:start",
                {"message": "Dah makan dexa petang"},
            )
        labels = [str(c.args[0]) for c in audit.call_args_list]
        self.assertTrue(
            any(l.startswith("CLARIFY") for l in labels),
            f"expected a CLARIFY audit entry, got: {labels}",
        )
        self.assertFalse(
            any(l.startswith("REJECT") for l in labels),
            f"missing-time must not be REJECT, got: {labels}",
        )


if __name__ == "__main__":
    unittest.main()
