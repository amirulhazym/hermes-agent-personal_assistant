import importlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
SCRIPTS = BASE / "scripts"
LIVE = Path("/home/ubuntu/.hermes")

# Operational-artifact gate: tests copy LIVE runtime fixtures; CI runners
# have no /home/ubuntu/.hermes so they skip, the VPS host runs them.
_LIVE_SCHEDULE = LIVE / "med-schedule.json"


class _FrozenNow(datetime):
    """datetime subclass whose now() returns a fixed midday reference.

    Handler tests must not depend on the real wall clock: past midnight,
    messages like "jam 6.08am" parse as *future* times and are rejected by
    G-2 before any assertion runs (timing flake, 2026-08-13).
    """

    FROZEN = datetime(2026, 8, 12, 18, 0)

    @classmethod
    def now(cls, tz=None):
        return cls.FROZEN


def freeze_handler_now(handler):
    from unittest import mock

    return mock.patch.object(handler, "datetime", _FrozenNow)


def load_gate(home: Path):
    os.environ["HERMES_HOME"] = str(home)
    sys.path.insert(0, str(SCRIPTS))
    for name in ("med_resolve", "med_safety_gate"):
        sys.modules.pop(name, None)
    return importlib.import_module("med_safety_gate")


def load_handler(home: Path):
    os.environ["HERMES_HOME"] = str(home)
    for name in ("med_resolve", "med_safety_gate", "med_auto_confirm_isolated"):
        sys.modules.pop(name, None)
    spec = importlib.util.spec_from_file_location(
        "med_auto_confirm_isolated", BASE / "hooks" / "med-auto-confirm" / "handler.py"
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot load isolated med-auto-confirm handler")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(_LIVE_SCHEDULE.exists(), "live runtime fixtures not present (CI skips)")
class TestSafetyGate(unittest.TestCase):
    """Hermetic Phase 1 contract tests. No production state is read or written."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / ".hermes"
        self.home.mkdir(parents=True)
        # Fixtures intentionally copied once into isolated HOME; runtime paths stay untouched.
        shutil.copy2(LIVE / "med-schedule.json", self.home / "med-schedule.json")
        shutil.copy2(LIVE / "dexa_taper.json", self.home / "dexa_taper.json")
        self.gate = load_gate(self.home)
        self.now = datetime(2026, 7, 24, 6, 8)

    def tearDown(self):
        self.tmp.cleanup()

    def decision(self, message: str, time_hm: str, now=None):
        return self.gate.evaluate(message, time_hm, now or self.now)

    def test_expected_a_pair_allows(self):
        result = self.decision("dah makan akurit-2 dan pyridoxine jam 6.08am", "06:08")
        self.assertEqual(result["decision"], "ALLOW", result)

    def test_original_cross_slot_typo_holds_full_parse(self):
        result = self.decision("dah makan dexa pagi dan pyridoxine jam 6.08am", "06:08")
        self.assertEqual(result["decision"], "HOLD", result)
        self.assertEqual({m["drug_id"] for m in result["mentions"]}, {"dexamethasone_1", "pyridoxine"})
        self.assertIn("CROSS_SLOT_COMBINATION", {f["rule_id"] for f in result["findings"]})

    def test_early_dexa_holds_against_schedule_window(self):
        result = self.decision("dah makan dexa pagi jam 6.08am", "06:08")
        self.assertEqual(result["decision"], "HOLD", result)
        self.assertIn("SCHEDULE_TIME_WINDOW", {f["rule_id"] for f in result["findings"]})

    def test_expected_b_pair_allows(self):
        result = self.decision("dah makan dexa pagi dan letram pagi jam 8.02am", "08:02", datetime(2026, 7, 24, 8, 2))
        self.assertEqual(result["decision"], "ALLOW", result)

    def test_clinician_or_hospital_change_never_becomes_intake_allow(self):
        result = self.decision("hospital suruh tukar dexa pagi jadi 4mg mulai hari ini", "08:02", datetime(2026, 7, 24, 8, 2))
        self.assertEqual(result["decision"], "HOLD", result)
        self.assertIn("REGIMEN_CHANGE_REPORTED", {f["rule_id"] for f in result["findings"]})

    def test_missing_active_schedule_holds_not_fails_open(self):
        (self.home / "med-schedule.json").unlink()
        result = self.decision("dah makan dexa pagi jam 8.02am", "08:02", datetime(2026, 7, 24, 8, 2))
        self.assertEqual(result["decision"], "HOLD", result)
        self.assertIn("CONFIG_ACTIVE_SCHEDULE", {f["rule_id"] for f in result["findings"]})

    def test_hold_persists_structured_record_and_does_not_create_med_state(self):
        decision = self.decision("dah makan dexa pagi dan pyridoxine jam 6.08am", "06:08")
        hold = self.gate.persist_hold(decision)
        saved = json.loads((self.home / "med-holds.json").read_text())
        self.assertEqual(saved["holds"][-1]["hold_id"], hold["hold_id"])
        self.assertEqual(saved["holds"][-1]["status"], "OPEN")
        self.assertEqual(saved["holds"][-1]["decision"]["decision"], "HOLD")
        self.assertFalse((self.home / "med-status.json").exists())
        self.assertFalse((self.home / "med-supply.json").exists())
        audit = (self.home / "logs" / "med-safety-audit.jsonl").read_text()
        self.assertIn('"MED_SAFETY_HOLD"', audit)
        self.assertEqual((self.home / "triggered_skills.txt").read_text(), "med-tracker\n")

        # Closing a HOLD records a decision but cannot mutate medication state.
        script = SCRIPTS / "med_hold.py"
        import subprocess
        result = subprocess.run(
            [sys.executable, str(script), "--resolve", hold["hold_id"], "--outcome", "CORRECTED", "--note", "user corrected typo"],
            env={**os.environ, "HERMES_HOME": str(self.home), "HOME": str(self.home.parent)},
            capture_output=True, text=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        closed = json.loads((self.home / "med-holds.json").read_text())["holds"][-1]
        self.assertEqual(closed["status"], "RESOLVED")
        self.assertEqual(closed["resolution"]["outcome"], "CORRECTED")
        self.assertFalse((self.home / "med-status.json").exists())
        self.assertFalse((self.home / "med-supply.json").exists())

    def test_handler_hold_has_no_medication_state_or_subprocess_side_effect(self):
        handler = load_handler(self.home)
        from unittest.mock import patch
        calls = []
        message = "dah makan dexa pagi dan pyridoxine jam 6.08am"
        with freeze_handler_now(handler), \
             patch.object(handler.subprocess, "run", side_effect=lambda *a, **kw: calls.append((a, kw))):
            handler.handle("agent:start", {"message": message})
        self.assertEqual(calls, [])
        self.assertFalse((self.home / "med-status.json").exists())
        self.assertFalse((self.home / "med-supply.json").exists())
        self.assertFalse((self.home / "chain-state.json").exists())
        holds = json.loads((self.home / "med-holds.json").read_text())["holds"]
        self.assertEqual(holds[-1]["status"], "OPEN")
        self.assertIn("CROSS_SLOT_COMBINATION", {f["rule_id"] for f in holds[-1]["decision"]["findings"]})

    def test_missing_active_taper_holds_not_fails_open(self):
        (self.home / "dexa_taper.json").unlink()
        result = self.decision("dah makan dexa pagi jam 8.02am", "08:02", datetime(2026, 7, 24, 8, 2))
        self.assertEqual(result["decision"], "HOLD", result)
        self.assertEqual(result["findings"][0]["observed"], "ACTIVE_TAPER_UNAVAILABLE")

    def test_taper_stop_phase_does_not_crash_and_holds_inactive_dexa(self):
        result = self.decision("dah makan dexa pagi jam 8.02am", "08:02", datetime(2027, 2, 11, 8, 2))
        self.assertEqual(result["decision"], "HOLD", result)
        self.assertIn("TAPER_INACTIVE_SLOT", {f["rule_id"] for f in result["findings"]})

    def test_handler_literal_cc_reaches_one_real_compound_command(self):
        handler = load_handler(self.home)
        from unittest.mock import patch
        calls = []
        message = "dah makan CC jam 1.35pm tadi"
        decision = {
            "decision": "ALLOW",
            "mentions": [
                {"drug_id": "calcium", "slot": "C", "compound_id": "cc"},
                {"drug_id": "calcitriol", "slot": "C", "compound_id": "cc"},
            ],
        }
        class Result:
            returncode = 0
            stdout = '{"ok": true, "compound": "cc"}'
            stderr = ''
        with freeze_handler_now(handler), \
             patch.object(handler, "evaluate_safety", return_value=decision), \
             patch.object(handler, "_already_logged", return_value=False), \
             patch.object(handler, "_check_chain_consistency"), \
             patch.object(handler, "CONFIRM_SCRIPT", BASE / "scripts" / "med_confirm.py"), \
             patch.object(handler.subprocess, "run", side_effect=lambda command, **kwargs: calls.append(command) or Result()), \
             patch.object(handler, "_audit"):
            handler.handle("agent:start", {"message": message})
        self.assertEqual(len(calls), 1, "literal CC must enter compound path")
        self.assertIn("--compound", calls[0])

    def test_handler_cc_uses_one_compound_transaction_command(self):
        handler = load_handler(self.home)
        from unittest.mock import patch
        calls = []
        message = "dah makan CC jam 1.35pm tadi"
        decision = {
            "decision": "ALLOW",
            "mentions": [
                {"drug_id": "calcium", "slot": "C", "compound_id": "cc"},
                {"drug_id": "calcitriol", "slot": "C", "compound_id": "cc"},
            ],
        }
        class Result:
            returncode = 0
            stdout = '{"ok": true, "compound": "cc"}'
            stderr = ''
        with freeze_handler_now(handler), \
             patch.object(handler, "evaluate_safety", return_value=decision), \
             patch.object(handler, "_already_logged", return_value=False), \
             patch.object(handler, "_check_chain_consistency"), \
             patch.object(handler, "CONFIRM_SCRIPT", BASE / "scripts" / "med_confirm.py"), \
             patch.object(handler.subprocess, "run", side_effect=lambda command, **kwargs: calls.append(command) or Result()), \
             patch.object(handler, "_audit"):
            handler.handle("agent:start", {"message": message})
        self.assertEqual(len(calls), 1)
        self.assertIn("--compound", calls[0])
        self.assertIn("cc", calls[0])
        self.assertNotIn("calcium", calls[0])
        self.assertNotIn("calcitriol", calls[0])

    def test_handler_change_report_holds_without_completion_word(self):
        handler = load_handler(self.home)
        message = "Hospital suruh tukar dexa pagi jadi 4mg mulai hari ini"
        with freeze_handler_now(handler):
            handler.handle("agent:start", {"message": message})
        holds = json.loads((self.home / "med-holds.json").read_text())["holds"]
        hold = holds[-1]
        self.assertIn("REGIMEN_CHANGE_REPORTED", {f["rule_id"] for f in hold["decision"]["findings"]})
        self.assertEqual({m["drug_id"] for m in hold["decision"]["mentions"]}, {"dexamethasone_1"})

    def test_cc_compound_resolves_both_components(self):
        import med_resolve
        result = med_resolve.resolve("CC", time_24h="13:35")
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["compound"])
        self.assertEqual(result["compound_id"], "cc")
        self.assertEqual(result["all_drug_ids"], ["calcium", "calcitriol"])
        self.assertEqual(result["slot"], "C")

    def test_late_lunch_cc_allows_without_static_c_window_hold(self):
        result = self.decision("dah makan CC jam 1.35pm tadi", "13:35", datetime(2026, 7, 24, 13, 35))
        self.assertEqual(result["decision"], "ALLOW", result)
        self.assertEqual({m["drug_id"] for m in result["mentions"]}, {"calcium", "calcitriol"})
        self.assertEqual({m["compound_id"] for m in result["mentions"]}, {"cc"})

    def test_explicit_calcium_plus_calcitriol_is_same_cc_bundle(self):
        result = self.decision("dah makan both calcium carbonate dan calcitriol jam 1.35pm tadi", "13:35", datetime(2026, 7, 24, 13, 35))
        self.assertEqual(result["decision"], "ALLOW", result)
        self.assertEqual({m["drug_id"] for m in result["mentions"]}, {"calcium", "calcitriol"})
        self.assertEqual({m["compound_id"] for m in result["mentions"]}, {"cc"})

    def test_explicit_cc_components_are_not_whole_slot_c(self):
        result = self.decision("dah makan CC jam 1.35pm tadi", "13:35", datetime(2026, 7, 24, 13, 35))
        self.assertNotIn("dexamethasone_2", {m["drug_id"] for m in result["mentions"]})
        self.assertNotIn("b_complex", {m["drug_id"] for m in result["mentions"]})

    def test_prn_unslotted_medication_holds_for_agent_handling(self):
        result = self.decision("dah makan pantoprazole jam 8.02am", "08:02", datetime(2026, 7, 24, 8, 2))
        self.assertEqual(result["decision"], "HOLD", result)
        self.assertEqual(result["mentions"][0]["drug_id"], "pantoprazole")
        self.assertIn("UNSLOTTED_MEDICATION", {f["rule_id"] for f in result["findings"]})


if __name__ == "__main__":
    unittest.main()
