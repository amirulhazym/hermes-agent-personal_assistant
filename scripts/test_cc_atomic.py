import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BASE = Path(__file__).resolve().parent
LIVE = Path('/home/ubuntu/.hermes')

# Operational-artifact gate: these tests copy LIVE runtime fixtures. CI
# runners have no /home/ubuntu/.hermes, so they skip; the VPS host runs them.
_LIVE_SCHEDULE = LIVE / 'med-schedule.json'


def load_confirm(home: Path):
    # Set env ONLY for the import; restore after so no global HOME leak
    # breaks other test modules (lazy imports read HOME at call time).
    orig_home = os.environ.get('HOME')
    orig_hermes = os.environ.get('HERMES_HOME')
    os.environ['HOME'] = str(home.parent)
    os.environ['HERMES_HOME'] = str(home)
    try:
        sys.modules.pop('med_resolve', None)
        sys.modules.pop('med_confirm_isolated', None)
        sys.path.insert(0, str(BASE))
        spec = importlib.util.spec_from_file_location('med_confirm_isolated', BASE / 'med_confirm.py')
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    finally:
        if orig_home is None:
            os.environ.pop('HOME', None)
        else:
            os.environ['HOME'] = orig_home
        if orig_hermes is None:
            os.environ.pop('HERMES_HOME', None)
        else:
            os.environ['HERMES_HOME'] = orig_hermes


@unittest.skipUnless(_LIVE_SCHEDULE.exists(), "live runtime fixtures not present (CI skips)")
class TestCCAtomicConfirmation(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name) / '.hermes'
        self.home.mkdir()
        for name in ('med-schedule.json', 'med-supply.json'):
            shutil.copy2(LIVE / name, self.home / name)
        supply = json.loads((self.home / 'med-supply.json').read_text())
        supply['drugs']['calcium']['current'] = 10
        supply['drugs']['calcitriol']['current'] = 20
        (self.home / 'med-supply.json').write_text(json.dumps(supply))
        self.mod = load_confirm(self.home)

    def tearDown(self):
        self.tmp.cleanup()

    def snapshot(self):
        return {
            name: (self.home / name).read_bytes() if (self.home / name).exists() else None
            for name in ('med-status.json', 'med-supply.json')
        }

    def test_compound_validation_failure_writes_neither_component(self):
        before = self.snapshot()
        result = self.mod.confirm_compound('C', 'cc', '13:35', 'dah makan calcium sahaja jam 1.35pm')
        self.assertFalse(result['ok'], result)
        self.assertEqual(self.snapshot(), before)

    def test_compound_second_file_failure_rolls_back_all_files(self):
        before = self.snapshot()
        real_write = self.mod._atomic_json_write
        calls = []

        def fail_supply(path, data):
            calls.append(path.name)
            if path.name == 'med-supply.json':
                raise OSError('injected supply failure')
            return real_write(path, data)

        with patch.object(self.mod, '_atomic_json_write', side_effect=fail_supply):
            result = self.mod.confirm_compound('C', 'cc', '13:35', 'dah makan CC jam 1.35pm tadi')
        self.assertFalse(result['ok'], result)
        self.assertEqual(self.snapshot(), before)
        self.assertEqual(calls, ['.med-confirm-transaction.json', 'med-status.json', 'med-supply.json'])

    def test_prepared_journal_recovers_exact_before_images(self):
        before = self.snapshot()
        self.mod._write_transaction({
            self.mod.STATE_FILE: before['med-status.json'],
            self.mod.SUPPLY_FILE: before['med-supply.json'],
        })
        # Simulate power loss after status replacement but before supply replacement.
        self.mod._atomic_json_write(self.mod.STATE_FILE, {'corrupted': 'partial commit'})
        self.assertNotEqual(self.snapshot()['med-status.json'], before['med-status.json'])
        self.assertTrue(self.mod._recover_prepared_transaction())
        self.assertEqual(self.snapshot(), before)
        self.assertFalse((self.home / '.med-confirm-transaction.json').exists())

    def test_hermes_home_overrides_home_for_all_transaction_files(self):
        alternate = Path(self.tmp.name) / 'configured-hermes'
        alternate.mkdir()
        for name in ('med-schedule.json', 'med-supply.json'):
            shutil.copy2(self.home / name, alternate / name)
        original_home = os.environ.get('HOME')
        original_hermes = os.environ.get('HERMES_HOME')
        try:
            os.environ['HOME'] = str(Path(self.tmp.name) / 'wrong-home')
            os.environ['HERMES_HOME'] = str(alternate)
            configured = load_confirm(alternate)
            result = configured.confirm_compound('C', 'cc', '13:35', 'dah makan CC jam 1.35pm tadi')
            self.assertTrue(result['ok'], result)
            self.assertTrue((alternate / 'med-status.json').exists())
            self.assertFalse((Path(os.environ['HOME']) / '.hermes' / 'med-status.json').exists())
        finally:
            if original_home is None: os.environ.pop('HOME', None)
            else: os.environ['HOME'] = original_home
            if original_hermes is None: os.environ.pop('HERMES_HOME', None)
            else: os.environ['HERMES_HOME'] = original_hermes

    def test_bare_cc_without_completion_word_rejects_without_write(self):
        before = self.snapshot()
        result = self.mod.confirm_compound('C', 'cc', '13:35', 'cc')
        self.assertFalse(result['ok'], result)
        self.assertEqual(self.snapshot(), before)

    def test_invalid_compound_time_rejects_without_write(self):
        before = self.snapshot()
        import subprocess
        result = subprocess.run(
            [sys.executable, str(BASE / 'med_confirm.py'), 'C', '--compound', 'cc', '--at', 'bogus', '--source-text', 'dah makan CC'],
            env={**os.environ, 'HOME': str(self.home.parent), 'HERMES_HOME': str(self.home)},
            text=True, capture_output=True, check=False,
        )
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.snapshot(), before)

    def test_compound_repeat_same_time_is_idempotent_no_second_supply_decrement(self):
        first = self.mod.confirm_compound('C', 'cc', '13:35', 'dah makan CC jam 1.35pm tadi')
        self.assertTrue(first['ok'], first)
        before_repeat = self.snapshot()
        second = self.mod.confirm_compound('C', 'cc', '13:35', 'dah makan CC jam 1.35pm tadi')
        self.assertTrue(second['ok'], second)
        self.assertTrue(second['idempotent'], second)
        self.assertEqual(self.snapshot(), before_repeat)

    def test_cli_compound_command_uses_single_transaction(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, str(BASE / 'med_confirm.py'), 'C', '--compound', 'cc', '--at', '13:35', '--source-text', 'dah makan CC jam 1.35pm tadi'],
            env={**os.environ, 'HOME': str(self.home.parent), 'HERMES_HOME': str(self.home)},
            text=True, capture_output=True, check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertTrue(payload['ok'], payload)
        self.assertEqual(payload['compound'], 'cc')

    def test_compound_success_writes_both_same_time_and_decrements_both_once(self):
        result = self.mod.confirm_compound('C', 'cc', '13:35', 'dah makan CC jam 1.35pm tadi')
        self.assertTrue(result['ok'], result)
        state = json.loads((self.home / 'med-status.json').read_text())
        today = self.mod.get_today()
        drugs = state['meds']['C'][today]['drugs']
        self.assertEqual(drugs['calcium'], {'status': 'taken', 'time': '13:35'})
        self.assertEqual(drugs['calcitriol'], {'status': 'taken', 'time': '13:35'})
        supply = json.loads((self.home / 'med-supply.json').read_text())['drugs']
        self.assertEqual(supply['calcium']['current'], 9)
        self.assertEqual(supply['calcitriol']['current'], 19)


if __name__ == '__main__':
    unittest.main()
