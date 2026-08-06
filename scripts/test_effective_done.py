import json, os, shutil, subprocess, tempfile, unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent


class TestEffectiveDone(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="eff-done-"))
        self.hermes = self.tmp / ".hermes"
        scripts = self.hermes / "scripts"
        shutil.copytree(BASE, scripts)
        shutil.copy2(ROOT / "med-schedule.json", self.hermes / "med-schedule.json")
        shutil.copy2(ROOT / "dexa_taper.json", self.hermes / "dexa_taper.json")
        (self.hermes / "chain-state.json").write_text("{}\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def write_state(self, meds, chain_state=None):
        today = "2026-08-02"
        state = {"meds": {slot: {today: entry} for slot, entry in meds.items()}}
        (self.hermes / "med-status.json").write_text(json.dumps(state))
        if chain_state is not None:
            (self.hermes / "chain-state.json").write_text(json.dumps(chain_state))

    def run_next(self, meds, *, frozen_now=None, chain_state=None):
        self.write_state(meds, chain_state)
        env = {**os.environ, "HOME": str(self.tmp)}
        if frozen_now:
            env["CHAIN_CALC_NOW_MYT"] = frozen_now
        return subprocess.run(
            ["python3", str(self.hermes / "scripts" / "chain_calc.py"), "--next"],
            env=env, capture_output=True, text=True,
        )

    def calc_chain(self, meds, *, frozen_now=None, chain_state=None):
        self.write_state(meds, chain_state)
        env = {**os.environ, "HOME": str(self.tmp)}
        if frozen_now:
            env["CHAIN_CALC_NOW_MYT"] = frozen_now
        code = "import chain_calc, json; print(json.dumps(chain_calc.calculate_chain()))"
        r = subprocess.run(["python3", "-c", code], env=env,
                           cwd=str(self.hermes / "scripts"),
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    @staticmethod
    def slot(drugs):
        return {"drugs": drugs}

    def test_skipped_slot_is_effectively_done_and_does_not_fire(self):
        meds = {
            "A": self.slot({"akurit_2": {"status": "taken", "time": "06:05"},
                            "pyridoxine": {"status": "taken", "time": "06:05"}}),
            "B": self.slot({"levetiracetam_b": {"status": "skipped", "time": "08:00"},
                            "dexamethasone_1": {"status": "skipped", "time": "08:00"}}),
        }
        r = self.run_next(meds, frozen_now="2026-08-02T09:30:00+08:00")
        self.assertEqual(r.returncode, 0, r.stderr)
        data = json.loads(r.stdout)
        self.assertFalse(data["should_fire"], data)
        self.assertIn("C ~", data["chain_str"])

    def test_skipped_drug_does_not_remain_pending_required(self):
        meds = {
            "A": self.slot({"akurit_2": {"status": "taken", "time": "06:05"},
                            "pyridoxine": {"status": "taken", "time": "06:05"}}),
            "B": self.slot({"levetiracetam_b": {"status": "skipped", "time": "08:00"},
                            "dexamethasone_1": {"status": "taken", "time": "08:10"}}),
        }
        c = self.calc_chain(meds, frozen_now="2026-08-02T09:00:00+08:00")
        b = c["slots"]["B"]
        self.assertTrue(b["effectively_done"], c)
        self.assertEqual(b["status"], "resolved")
        self.assertFalse(b["confirmed"], "skipped must not be confirmed")
        self.assertEqual(b["pending_drugs"], [])

    def test_is_effectively_done_predicate_false_for_missing(self):
        env = {**os.environ, "HOME": str(self.tmp)}
        code = "import chain_calc; print(chain_calc.is_effectively_done('B'))"
        r = subprocess.run(["python3", "-c", code], env=env,
                           cwd=str(self.hermes / "scripts"),
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), "False")

    def test_partial_slot_still_pending_when_one_drug_untouched(self):
        meds = {
            "A": self.slot({"akurit_2": {"status": "taken", "time": "06:05"},
                            "pyridoxine": {"status": "taken", "time": "06:05"}}),
            "B": self.slot({"dexamethasone_1": {"status": "taken", "time": "08:10"}}),
        }
        c = self.calc_chain(meds, frozen_now="2026-08-02T09:00:00+08:00")
        b = c["slots"]["B"]
        self.assertFalse(b["effectively_done"], c)
        self.assertIn(b["status"], ("partial", "partial_ready", "ready"), c)
        self.assertTrue(b["pending_drugs"], "untouched drug must remain pending")


if __name__ == "__main__":
    unittest.main()