"""Tests for the date-aware Dexa dosage fix in chain_calc.get_pending_required_drugs.

Bug: get_pending_required_drugs() returned static schedule dosage (5/5/4) instead
of the date-aware taper dose (e.g. 4/4/3 for phase 8), so reminders rendered
stale dosages. This suite freezes CHAIN_CALC_NOW_MYT and asserts the exact
dosage string emitted for B/C/D across phase boundaries.

Fixture HOME points to a temporary HERMES_HOME with only schedule/taper copies;
no live medical state is touched.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
LIVE = Path("/home/ubuntu/.hermes")  # explicit — Path.home() is dynamic and breaks if another test mutates HOME

# Operational-artifact gate: tests copy LIVE runtime fixtures; CI runners
# have no /home/ubuntu/.hermes so they skip, the VPS host runs them.
_LIVE_SCHEDULE = LIVE / "med-schedule.json"


def _make_home() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="dexa-dataflow-"))
    (tmp / ".hermes").mkdir()
    for name in ("med-schedule.json", "dexa_taper.json"):
        shutil.copy(LIVE / name, tmp / ".hermes" / name)
    return tmp


@unittest.skipUnless(_LIVE_SCHEDULE.exists(), "live runtime fixtures not present (CI skips)")
class DexaDoseDataflowTest(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self._home = _make_home()
        with mock.patch.dict(os.environ, {"HOME": str(self._home)}, clear=False):
            for mod in list(sys.modules):
                if mod == "chain_calc" or mod.startswith("chain_calc."):
                    del sys.modules[mod]
            if str(HERE) not in sys.path:
                sys.path.insert(0, str(HERE))
            # Import dexa_taper_lookup NOW under the correct HOME: chain_calc's
            # delegation imports it lazily at call time, when this HOME context
            # is gone — a cached module with the right TAPER_FILE is required.
            import dexa_taper_lookup  # noqa: F401
            import chain_calc

            self.cc = chain_calc
        (self._home / ".hermes" / "med-status.json").write_text(json.dumps({"meds": {}}))

    def tearDown(self):
        for mod in list(sys.modules):
            if mod == "chain_calc" or mod.startswith("chain_calc."):
                del sys.modules[mod]

    def _pending(self, slot: str, date: str) -> list[dict]:
        with mock.patch.dict(os.environ, {"CHAIN_CALC_NOW_MYT": date + "T12:00:00+08:00"}, clear=False):
            return self.cc.get_pending_required_drugs(slot)

    def _dexa_pending(self, slot: str, date: str) -> dict:
        for d in self._pending(slot, date):
            if d.get("drug_id", "").startswith("dexamethasone_"):
                return d
        self.fail(f"no dexamethasone pending drug in slot {slot}")

    def test_phase8_aug12_c_is_4mg(self):
        self.assertEqual(self._dexa_pending("C", "2026-08-12")["dosage"], "4mg")

    def test_phase7_aug11_c_is_4mg(self):
        self.assertEqual(self._dexa_pending("C", "2026-08-11")["dosage"], "4mg")

    def test_phase8_aug12_d_is_3mg(self):
        self.assertEqual(self._dexa_pending("D", "2026-08-12")["dosage"], "3mg")

    def test_phase8_aug25_d_is_3mg(self):
        self.assertEqual(self._dexa_pending("D", "2026-08-25")["dosage"], "3mg")

    def test_phase9_aug26_c_is_3mg(self):
        self.assertEqual(self._dexa_pending("C", "2026-08-26")["dosage"], "3mg")

    def test_phase9_aug26_d_is_3mg(self):
        self.assertEqual(self._dexa_pending("D", "2026-08-26")["dosage"], "3mg")

    def test_phase8_aug12_b_is_4mg(self):
        self.assertEqual(self._dexa_pending("B", "2026-08-12")["dosage"], "4mg")


if __name__ == "__main__":
    unittest.main()
