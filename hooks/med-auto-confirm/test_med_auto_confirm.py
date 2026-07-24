import importlib.util
import json
import os
import stat
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parents[2]
os.environ["HERMES_HOME"] = str(BASE)
spec = importlib.util.spec_from_file_location("med_auto_confirm_handler", BASE / "hooks" / "med-auto-confirm" / "handler.py")
handler = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = handler
spec.loader.exec_module(handler)


class TestExactUserConfirmations(unittest.TestCase):
    def test_done_akurit_and_pyridoxine_with_dot_time(self):
        text = "Done akurit+pyridoxine jam 6.45am"
        now = datetime(2026, 7, 18, 8, 0)
        self.assertTrue(handler.is_med_confirmation(text))
        parsed = handler._parse_time(text, now)
        self.assertEqual(parsed, datetime(2026, 7, 18, 6, 45))
        self.assertEqual(handler._resolve_slot_drug(text, now), ("A", "akurit_2", "06:45"))

    def test_colon_time_keeps_working(self):
        text = "Dah makan akurit jam 6:45am"
        parsed = handler._parse_time(text, datetime(2026, 7, 18, 8, 0))
        self.assertEqual(parsed, datetime(2026, 7, 18, 6, 45))

    def test_question_about_taking_dexa_is_not_confirmation(self):
        text = "Boleh ke aku nak makan dexa siang jam sekarang?"
        self.assertFalse(handler.is_med_confirmation(text))

    def test_status_question_is_not_confirmation(self):
        text = "Btw dah log ke aku makan dexa siang jam berapa?"
        self.assertFalse(handler.is_med_confirmation(text))

    def test_quoted_whatsapp_transcript_is_not_confirmation(self):
        text = (
            "[Fri 2026-07-24 06:51:38 +08] "
            "[24/07, 6:00 am] MJ Hermes Maxis: Waktu Ubat Pagi\n"
            "Akurit-2 dan Pyridoxine belum ambil. Dah pukul 06:00.\n"
            "[24/07, 6:16 am] amirulhazym: "
            "Dah makan dexa pagi dan pyridoxine jam 6.08am tadi"
        )
        self.assertFalse(handler.is_med_confirmation(text))

    def test_stated_time_controls_dexa_slot(self):
        text = "Dah makan dexa siang jam 12:20pm tadi"
        now = datetime(2026, 7, 19, 15, 0)
        self.assertEqual(handler._resolve_slot_drug(text, now), ("C", "dexamethasone_2", "12:20"))

        calls = []

        class Result:
            returncode = 0
            stderr = ""

        def fake_run(command, **kwargs):
            calls.append(command)
            return Result()

        text = "Dah makan dexa siang tadi"
        with patch.object(handler, "_already_logged", return_value=False), \
             patch.object(handler, "_check_chain_consistency"), \
             patch.object(handler, "_validate_timestamp", return_value=True), \
             patch.object(handler, "evaluate_safety", return_value={"decision": "ALLOW", "mentions": [{"slot": "A", "drug_id": "akurit_2"}, {"slot": "A", "drug_id": "pyridoxine"}]}), \
             patch.object(handler, "CONFIRM_SCRIPT", Path("/tmp/fake-med-confirm.py")), \
             patch.object(Path, "exists", return_value=True), \
             patch.object(handler.subprocess, "run", side_effect=fake_run), \
             patch.object(handler, "_audit"):
            handler.handle("agent:start", {"message": text})

        self.assertEqual(calls, [])

    def test_combined_a_statement_confirms_both_drugs(self):
        calls = []

        class Result:
            returncode = 0
            stderr = ""
            stdout = '{"ok": true, "overall": "completed"}'

        def fake_run(command, **kwargs):
            calls.append(command)
            return Result()

        text = "Done akurit+pyridoxine jam 6.45am"
        with patch.object(handler, "_already_logged", return_value=False), \
             patch.object(handler, "_check_chain_consistency"), \
             patch.object(handler, "_validate_timestamp", return_value=True), \
             patch.object(handler, "evaluate_safety", return_value={"decision": "ALLOW", "mentions": [{"slot": "A", "drug_id": "akurit_2"}, {"slot": "A", "drug_id": "pyridoxine"}]}), \
             patch.object(handler, "CONFIRM_SCRIPT", Path("/tmp/fake-med-confirm.py")), \
             patch.object(Path, "exists", return_value=True), \
             patch.object(handler.subprocess, "run", side_effect=fake_run), \
             patch.object(handler, "_audit"):
            handler.handle("agent:start", {"message": text})

        drug_args = [command[3] for command in calls]
        self.assertEqual(drug_args, ["akurit_2", "pyridoxine"], calls)
        for command in calls:
            self.assertEqual(command[1:3], ["/tmp/fake-med-confirm.py", "A"])
            self.assertEqual(command[-4:-2], ["--at", "06:45"])
            self.assertEqual(command[-2], "--source-text")
            self.assertEqual(command[-1], text)

    def test_safety_hold_never_invokes_med_confirm(self):
        calls = []
        held = []

        def fake_run(*args, **kwargs):
            calls.append((args, kwargs))
            raise AssertionError("med_confirm must not run for HOLD")

        decision = {
            "decision": "HOLD",
            "findings": [{"rule_id": "CROSS_SLOT_COMBINATION"}],
            "mentions": [{"drug_id": "dexamethasone_1", "slot": "B"}, {"drug_id": "pyridoxine", "slot": "A"}],
        }
        text = "Dah makan dexa pagi dan pyridoxine jam 6.08am tadi"
        with patch.object(handler, "evaluate_safety", return_value=decision), \
             patch.object(handler, "persist_hold", side_effect=lambda value: held.append(value) or {"hold_id": "hold-test"}), \
             patch.object(handler.subprocess, "run", side_effect=fake_run), \
             patch.object(handler, "_audit"):
            handler.handle("agent:start", {"message": text})

        self.assertEqual(calls, [])
        self.assertEqual(held, [decision])


if __name__ == "__main__":
    unittest.main()
