"""Tests for the date-aware Dexa dosage fix in chain_calc.get_pending_required_drugs.

Taper v2.1 (rebased 2026-08-25):
- Phase 7 (until 2026-08-11): TDS 4/4/4 (12mg)
- Phase 8 (2026-08-12 to 2026-08-25): TDS 4/4/3 (11mg)
- Phase 9 (2026-08-26 to 2026-09-08): BD 6mg (Slot B) + 4mg (Slot F @ 14:00) (10mg)
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts.test_runtime_fixtures import write_runtime_fixtures

HERE = Path(__file__).resolve().parent


def _make_home() -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="dexa-dataflow-"))
    hermes_home = tmp / ".hermes"
    write_runtime_fixtures(hermes_home)
    return tmp


class DexaDoseDataflowTest(unittest.TestCase):
    maxDiff = None

    def setUp(self):
        self._home = _make_home()
        with mock.patch.dict(os.environ, {"HOME": str(self._home)}, clear=False):
            for mod in list(sys.modules):
                if mod in ("chain_calc", "dexa_taper_lookup") or mod.startswith(("chain_calc.", "dexa_taper_lookup.")):
                    del sys.modules[mod]
            if str(HERE) not in sys.path:
                sys.path.insert(0, str(HERE))
            import dexa_taper_lookup  # noqa: F401
            import chain_calc

            self.cc = chain_calc
        (self._home / ".hermes" / "med-status.json").write_text(json.dumps({"meds": {}}))

    def tearDown(self):
        for mod in list(sys.modules):
            if mod in ("chain_calc", "dexa_taper_lookup") or mod.startswith(("chain_calc.", "dexa_taper_lookup.")):
                del sys.modules[mod]
        shutil.rmtree(self._home.parent, ignore_errors=True)

    def _pending(self, slot: str, date: str) -> list[dict]:
        with mock.patch.dict(os.environ, {"CHAIN_CALC_NOW_MYT": date + "T12:00:00+08:00"}, clear=False):
            return self.cc.get_pending_required_drugs(slot)

    def _dexa_pending(self, slot: str, date: str) -> dict:
        for d in self._pending(slot, date):
            if d.get("drug_id", "").startswith("dexamethasone_"):
                return d
        self.fail(f"no dexamethasone pending drug in slot {slot}")

    def test_phase7_aug11_c_is_4mg(self):
        self.assertEqual(self._dexa_pending("C", "2026-08-11")["dosage"], "4mg")

    def test_phase8_aug12_b_is_4mg(self):
        self.assertEqual(self._dexa_pending("B", "2026-08-12")["dosage"], "4mg")

    def test_phase8_aug12_c_is_4mg(self):
        self.assertEqual(self._dexa_pending("C", "2026-08-12")["dosage"], "4mg")

    def test_phase8_aug12_d_is_3mg(self):
        self.assertEqual(self._dexa_pending("D", "2026-08-12")["dosage"], "3mg")

    def test_phase8_aug25_d_is_3mg(self):
        self.assertEqual(self._dexa_pending("D", "2026-08-25")["dosage"], "3mg")

    def test_phase9_aug26_b_is_6mg(self):
        self.assertEqual(self._dexa_pending("B", "2026-08-26")["dosage"], "6mg")

    def test_phase9_aug26_f_is_4mg(self):
        self.assertEqual(self._dexa_pending("F", "2026-08-26")["dosage"], "4mg")


if __name__ == "__main__":
    unittest.main()
