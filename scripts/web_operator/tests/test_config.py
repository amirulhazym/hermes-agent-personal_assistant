import json
import tempfile
import unittest
from pathlib import Path

from scripts.web_operator.config import ConfigError, default_config_dict, load_config


class ConfigTests(unittest.TestCase):
    def test_defaults(self):
        path = Path(tempfile.mkstemp(suffix=".json")[1])
        path.write_text(json.dumps(default_config_dict()), encoding="utf-8")
        cfg = load_config(path)
        self.assertEqual(cfg.max_l3_actions, 30)
        self.assertEqual(cfg.max_l3_active_seconds, 600)
        self.assertEqual(cfg.operation_timeout_seconds, 180)
        self.assertEqual(cfg.approval_ttl_seconds, 900)
        self.assertEqual(cfg.retention_days, 14)
        self.assertTrue(cfg.deny_private_destinations)
        self.assertEqual(cfg.raw_frame_retention_seconds, 0)
        self.assertFalse(cfg.fixture_mode)
        self.assertEqual(cfg.production_l3_concurrency, 1)

    def test_unknown_key_rejected(self):
        path = Path(tempfile.mkstemp(suffix=".json")[1])
        data = default_config_dict()
        data["nope"] = 1
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ConfigError):
            load_config(path)

    def test_fixture_mode_rejected_in_production_load(self):
        path = Path(tempfile.mkstemp(suffix=".json")[1])
        data = default_config_dict()
        data["network"]["fixture_mode"] = True
        path.write_text(json.dumps(data), encoding="utf-8")
        with self.assertRaises(ConfigError):
            load_config(path, allow_fixture=False)


if __name__ == "__main__":
    unittest.main()
