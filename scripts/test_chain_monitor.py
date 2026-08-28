import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent


class TestMonitorDeliveryAccounting(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="monitor-test-"))
        hermes = self.tmp / ".hermes"
        scripts = hermes / "scripts"
        scripts.mkdir(parents=True)
        shutil.copy2(BASE / "chain_monitor.sh", scripts / "chain_monitor.sh")
        (hermes / "chain-state.json").write_text(json.dumps({"today": "2026-07-18", "reminder_counts": {}}))
        (scripts / "chain_calc.py").write_text(
            "import json,sys\n"
            "if '--next' in sys.argv: print(json.dumps({'should_fire': True, 'reason': 'C', 'next_slot': 'C'}))\n"
            "elif '--display' in sys.argv: print('test')\n"
        )
        # Housekeeping imports chain_calc.is_confirmed().
        with (scripts / "chain_calc.py").open("a") as file:
            file.write("\ndef is_confirmed(slot): return False\n")
        (scripts / "chain_llm.py").write_text("raise SystemExit(1)\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def test_failed_generation_does_not_increment_delivery_state(self):
        result = subprocess.run(
            ["bash", str(self.tmp / ".hermes" / "scripts" / "chain_monitor.sh")],
            env={**os.environ, "HOME": str(self.tmp)},
            capture_output=True,
            text=True,
        )
        state = json.loads((self.tmp / ".hermes" / "chain-state.json").read_text())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual(state.get("reminder_counts"), {}, state)
        self.assertEqual(state.get("last_reminder_sent", {}), {}, state)
        self.assertEqual(state.get("last_reminder_times", {}), {}, state)

    def test_successful_generation_increments_once_and_emits_text(self):
        llm = self.tmp / ".hermes" / "scripts" / "chain_llm.py"
        llm.write_text("print('real reminder text')\n")
        result = subprocess.run(
            ["bash", str(self.tmp / ".hermes" / "scripts" / "chain_monitor.sh")],
            env={**os.environ, "HOME": str(self.tmp)},
            capture_output=True,
            text=True,
        )
        state = json.loads((self.tmp / ".hermes" / "chain-state.json").read_text())
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "real reminder text")
        self.assertEqual(state["reminder_counts"], {"C": 1})
        self.assertEqual(state["last_reminder_sent"], {"C": 1})
        self.assertIn("C", state["last_reminder_times"])

    def test_real_renderer_emits_contract_and_only_partial_pending_drugs(self):
        shutil.copy2(BASE / "chain_llm.py", self.tmp / ".hermes" / "scripts" / "chain_llm.py")
        (self.tmp / ".hermes" / "scripts" / "chain_calc.py").write_text(
            "import json,sys\n"
            "def is_confirmed(slot): return False\n"
            "def calculate_chain():\n"
            "    return {'reminder': {'should_fire': True, 'reason': 'C'}, 'now': '13:22', "
            "'reminder_counts': {}, 'slots': {'C': {'pending_drugs': ["
            "{'drug': 'Calcium Carbonate', 'dosage': '500mg'}, "
            "{'drug': 'Calcitriol', 'dosage': '1 tablet'}]}}}\n"
            "if '--next' in sys.argv: print(json.dumps({'should_fire': True, 'reason': 'C', 'next_slot': 'C'}))\n"
        )
        result = subprocess.run(
            ["bash", str(self.tmp / ".hermes" / "scripts" / "chain_monitor.sh")],
            env={**os.environ, "HOME": str(self.tmp)},
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("‼️ Waktu Ubat (Tengah Hari) ‼️", result.stdout)
        self.assertIn("Calcium Carbonate 500mg", result.stdout)
        self.assertIn("Calcitriol 1 tablet", result.stdout)
        self.assertNotIn("Dexamethasone", result.stdout)
        self.assertIn("[C:1-", result.stdout)


if __name__ == "__main__":
    unittest.main()
