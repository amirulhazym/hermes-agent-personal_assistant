import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent


class TestChainAdapterRuntime(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="chain-adapter-"))
        self.hermes = self.tmp / ".hermes"
        scripts = self.hermes / "scripts"
        shutil.copytree(BASE, scripts)
        shutil.copy2(ROOT / "med-schedule.json", self.hermes / "med-schedule.json")
        shutil.copy2(ROOT / "dexa_taper.json", self.hermes / "dexa_taper.json")
        (self.hermes / "chain-state.json").write_text("{}\n")

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def run_chain(self, meds, *, frozen_now=None, chain_state=None):
        if frozen_now:
            today = frozen_now[:10]
        else:
            today = subprocess.check_output(
                ["date", "+%F"], env={**os.environ, "TZ": "Asia/Kuala_Lumpur"}, text=True
            ).strip()
        state = {"meds": {slot: {today: entry} for slot, entry in meds.items()}}
        (self.hermes / "med-status.json").write_text(json.dumps(state))
        if chain_state is not None:
            (self.hermes / "chain-state.json").write_text(json.dumps(chain_state))
        env = {**os.environ, "HOME": str(self.tmp)}
        if frozen_now:
            env["CHAIN_CALC_NOW_MYT"] = frozen_now
        return subprocess.run(
            ["python3", str(self.hermes / "scripts" / "chain_calc.py"), "--next"],
            env=env, capture_output=True, text=True
        )

    @staticmethod
    def partial(drug_id, at):
        return {"overall": "partial", "drugs": {drug_id: {"status": "taken", "time": at}}}

    def test_empty_pre_b_state_resolves_all_active_pending_slots(self):
        result = self.run_chain({})
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertIn(data["next_slot"], {"A", "B", "C", "D", "E"})
        self.assertIn("C ~12:00", data["chain_str"])
        self.assertIn("D ~16:00", data["chain_str"])

    def test_pyridoxine_only_does_not_shift_b(self):
        result = self.run_chain({"A": self.partial("pyridoxine", "07:18")})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("B ~08:00", json.loads(result.stdout)["chain_str"])

    def test_levetiracetam_only_does_not_drive_c_or_d(self):
        result = self.run_chain({"B": self.partial("levetiracetam_b", "09:13")})
        self.assertEqual(result.returncode, 0, result.stderr)
        chain = json.loads(result.stdout)["chain_str"]
        self.assertIn("C ~12:00", chain)
        self.assertIn("D ~16:00", chain)

    def test_calcium_only_does_not_drive_d(self):
        result = self.run_chain({"C": self.partial("calcium", "13:37")})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("D ~16:00", json.loads(result.stdout)["chain_str"])

    def test_pending_reminder_cooldown_matches_polling_cadence(self):
        result = subprocess.run(
            ["python3", "-c", "import chain_calc; print(chain_calc.get_cooldown_interval(1))"],
            env={**os.environ, "HOME": str(self.tmp)},
            cwd=str(self.hermes / "scripts"), capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "15")

    def test_scheduled_window_can_emit_heads_up_before_dynamic_ready_time(self):
        result = subprocess.run(
            ["python3", "-c", (
                "import chain_calc; "
                "print(chain_calc.is_scheduled_heads_up('D', {'meds': {'D': {'time': '16:00'}}}, 16*60, '16:20'))"
            )],
            env={**os.environ, "HOME": str(self.tmp)},
            cwd=str(self.hermes / "scripts"), capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), "True")

    # ── P1 regression: heads-up must never fire far before ready_time ──────
    def test_b_heads_up_silent_54min_before_ready(self):
        # 2026-08-02 incident: A taken 08:10 → B ready 09:10. At 08:16 the old
        # logic fired "belum ambil lagi" 54 minutes early. With the 30-min
        # window this tick must be SILENT.
        result = self.run_chain(
            {"A": self.completed("akurit_2", "08:10")},
            frozen_now="2026-08-02T08:16:00+08:00",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertFalse(data["should_fire"], data)

    def test_b_heads_up_fires_at_ready_minus_30(self):
        result = self.run_chain(
            {"A": self.completed("akurit_2", "08:10")},
            frozen_now="2026-08-02T08:40:00+08:00",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data["should_fire"], data)
        self.assertEqual(data["reason"], "B")

    def test_b_heads_up_fires_once_then_quiet_until_due(self):
        # After the single heads-up (count B=1), ticks inside the window must
        # stay quiet (08:55 < ready 09:10), then the real due reminder fires.
        r_early = self.run_chain(
            {"A": self.completed("akurit_2", "08:10")},
            frozen_now="2026-08-02T08:55:00+08:00",
            chain_state={"reminder_counts": {"B": 1}, "last_reminder_sent": {"B": 1}},
        )
        self.assertEqual(r_early.returncode, 0, r_early.stderr)
        self.assertFalse(json.loads(r_early.stdout)["should_fire"], r_early.stdout)

        r_due = self.run_chain(
            {"A": self.completed("akurit_2", "08:10")},
            frozen_now="2026-08-02T09:10:00+08:00",
            chain_state={"reminder_counts": {"B": 1}, "last_reminder_sent": {"B": 1}},
        )
        self.assertEqual(r_due.returncode, 0, r_due.stderr)
        data = json.loads(r_due.stdout)
        self.assertTrue(data["should_fire"], data)
        self.assertEqual(data["reason"], "B")

    @staticmethod
    def completed(drug_id, at):
        return {"overall": "completed", "drugs": {drug_id: {"status": "taken", "time": at}}}

    def test_d_reminds_at_scheduled_time_when_c_gap_ends_later(self):
        result = self.run_chain(
            {
                "A": self.completed("akurit_2", "06:05"),
                "B": self.completed("dexamethasone_1", "08:10"),
                "C": self.completed("dexamethasone_2", "12:20"),
            },
            frozen_now="2026-07-19T16:00:00+08:00",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data["should_fire"], data)
        self.assertEqual(data["reason"], "D")

    def test_d_retries_on_next_poll_after_unconfirmed_reminder(self):
        result = self.run_chain(
            {
                "A": self.completed("akurit_2", "06:05"),
                "B": self.completed("dexamethasone_1", "08:10"),
                "C": self.completed("dexamethasone_2", "12:20"),
            },
            frozen_now="2026-07-19T16:45:00+08:00",
            chain_state={
                "today": "2026-07-19",
                "reminder_counts": {"D": 1},
                "last_reminder_sent": {"D": 1},
                "last_reminder_times": {"D": "16:30"},
            },
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertTrue(data["should_fire"], data)
        self.assertEqual(data["reason"], "D")


if __name__ == "__main__":
    unittest.main()
