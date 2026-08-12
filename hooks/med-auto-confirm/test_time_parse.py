"""Hermetic tests for tolerant med-intake time parsing in the auto-confirm hook.

Owner directive (2026-08-12/13): in a med confirmation context (reminder
reply containing a completion word + drug), ANY plausible time shape must be
understood — "4.32pm tadi", "432pm", "4.32", "20:00", "jam 1.49pm".
12h ambiguity is resolved from context words (pagi/petang/malam/siang) or
nearest-to-now. Only truly absent/unparseable times fall through to CLARIFY
(agent asks). Bare digits without separator/suffix ("4", "20") are NOT times
— they are tablet counts.
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

    def _parse(self, msg: str, now=None):
        dt = self.handler._parse_time(msg, now or self.now)
        return f"{dt.hour:02d}:{dt.minute:02d}" if dt else None

    # --- New tolerant formats (2026-08-12/13) ---
    def test_pm_dot_without_leading_word(self):
        self.assertEqual(self._parse("Dah makan dexa petang, 4.32pm tadi"), "16:32")

    def test_pm_colon_without_leading_word(self):
        self.assertEqual(self._parse("Dah makan dexa petang, 4:32pm tadi"), "16:32")

    def test_compact_typo_432pm(self):
        self.assertEqual(self._parse("Dah makan dexa petang, 432pm tadi"), "16:32")

    def test_compact_typo_815pm(self):
        self.assertEqual(self._parse("dah makan letram malam 815pm"), "20:15")

    def test_am_compact(self):
        self.assertEqual(self._parse("dah makan akurit 645am tadi"), "06:45")

    def test_pm_without_minutes(self):
        self.assertEqual(self._parse("dah makan dexa 4pm tadi"), "16:00")

    # --- No am/pm: context-word resolution ---
    def test_dot_with_petang_hint_resolves_pm(self):
        self.assertEqual(self._parse("Dah makan dexa petang, 4.32 tadi"), "16:32")

    def test_dot_with_pagi_hint_resolves_am(self):
        self.assertEqual(self._parse("dah makan akurit 6.45 pagi"), "06:45")

    def test_dot_with_malam_hint_resolves_pm(self):
        self.assertEqual(self._parse("dah makan letram malam 8.12"), "20:12")

    def test_dot_with_siang_hint_resolves_pm(self):
        self.assertEqual(self._parse("dah makan dexa siang 12.15"), "12:15")

    # --- No am/pm: nearest-to-now resolution ---
    def test_dot_no_hint_nearest_now_evening(self):
        # now 23:00 -> 4.32 nearest is 16:32
        self.assertEqual(self._parse("dah makan dexa 4.32"), "16:32")

    def test_dot_no_hint_nearest_now_morning(self):
        # now 07:00 -> 6.45 nearest is 06:45
        morning = datetime(2026, 8, 12, 7, 0)
        self.assertEqual(self._parse("dah makan akurit 6.45", morning), "06:45")

    def test_dot_no_hint_24h_direct(self):
        self.assertEqual(self._parse("dah makan dexa 16.32"), "16:32")

    # --- Bare 24h times ARE accepted in confirmation context (G-2 relaxed) ---
    def test_bare_24h_accepted_in_completion_context(self):
        self.assertEqual(self._parse("dah makan ubat 20:00"), "20:00")

    def test_bare_24h_accepted_with_makan(self):
        self.assertEqual(self._parse("makan lepas 20:00"), "20:00")

    # --- Bare digits are NOT times (tablet counts) ---
    def test_bare_digit_rejected(self):
        self.assertIsNone(self._parse("dah makan dexa 4"))

    def test_bare_digits_rejected(self):
        self.assertIsNone(self._parse("dah makan dexa 20"))

    # --- Regression: leading-word formats keep working ---
    def test_leading_jam_am_pm(self):
        self.assertEqual(self._parse("Dah makan dexa jam 1.49pm"), "13:49")

    def test_leading_jam_dot(self):
        self.assertEqual(self._parse("Dah makan letram malam jam 8.12pm"), "20:12")

    def test_leading_pukul(self):
        self.assertEqual(self._parse("dah makan dexa pukul 12.15pm"), "12:15")

    def test_leading_jam_no_suffix(self):
        self.assertEqual(self._parse("dah makan dexa jam 16:32"), "16:32")

    def test_leading_jam_bare_hour(self):
        # "jam 4" -> 04:00 when now is morning (leading word makes a bare
        # hour a time; past-preference resolves 4 -> 04:00 at 07:00)
        morning = datetime(2026, 8, 12, 7, 0)
        self.assertEqual(self._parse("dah makan dexa jam 4", morning), "04:00")

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
