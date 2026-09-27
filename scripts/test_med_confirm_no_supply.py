#!/usr/bin/env python3
"""Tests proving that dosage confirmation does NOT decrement supply and emits no supply alerts."""

import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
sys.path.insert(0, str(BASE))
from test_runtime_fixtures import write_runtime_fixtures


def load_confirm(hermes_home: Path):
    sys.modules.pop('med_resolve', None)
    sys.modules.pop('med_confirm', None)
    sys.modules.pop('med_confirm_test', None)
    spec = importlib.util.spec_from_file_location('med_confirm_test', BASE / 'med_confirm.py')
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    orig_hermes = os.environ.get('HERMES_HOME')
    orig_home = os.environ.get('HOME')
    try:
        os.environ['HOME'] = str(hermes_home.parent)
        os.environ['HERMES_HOME'] = str(hermes_home)
        spec.loader.exec_module(mod)
        return mod
    finally:
        if orig_hermes is None:
            os.environ.pop('HERMES_HOME', None)
        else:
            os.environ['HERMES_HOME'] = orig_hermes
        if orig_home is None:
            os.environ.pop('HOME', None)
        else:
            os.environ['HOME'] = orig_home


class TestMedConfirmNoSupplyDecrement(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / '.hermes'
        self.home.mkdir()
        write_runtime_fixtures(self.home, include_supply=True)
        # Seed supply with specific values and one 0 to ensure no alerts or decrements trigger
        supply = json.loads((self.home / 'med-supply.json').read_text())
        supply['drugs']['levetiracetam_b'] = {
            'name': 'Levetiracetam (pagi)',
            'current': 0,
            'warning_threshold': 7,
            'slot': 'B'
        }
        supply['drugs']['calcium'] = {
            'name': 'Calcium Carbonate',
            'current': 10,
            'warning_threshold': 7,
            'slot': 'C'
        }
        (self.home / 'med-supply.json').write_text(json.dumps(supply))
        self.mod = load_confirm(self.home)

    def tearDown(self):
        self.tmp.cleanup()

    def test_confirm_slot_does_not_mutate_supply_or_emit_supply_alerts(self):
        supply_before = (self.home / 'med-supply.json').read_bytes()
        res = self.mod.confirm_slot('A', '06:12', source_text='Dah makan akurit dan pyridoxine jam 6.12am')
        self.assertTrue(res['ok'], res)
        # Supply alerts must NOT be present
        self.assertNotIn('supply_alerts', res, "Confirmation output must not leak passive supply alerts")
        self.assertNotIn('supply_alert', res)
        supply_after = (self.home / 'med-supply.json').read_bytes()
        self.assertEqual(supply_after, supply_before, "med-supply.json must be untouched after slot confirm")

    def test_confirm_drug_does_not_decrement_supply(self):
        supply_before = (self.home / 'med-supply.json').read_bytes()
        res = self.mod.confirm_drug('B', 'levetiracetam_b', '10:20', source_text='Dah makan letram jam 10.20am')
        self.assertTrue(res['ok'], res)
        self.assertNotIn('supply_alerts', res)
        self.assertNotIn('supply_alert', res)
        supply_after = (self.home / 'med-supply.json').read_bytes()
        self.assertEqual(supply_after, supply_before, "med-supply.json must be untouched after drug confirm")


if __name__ == '__main__':
    unittest.main()
