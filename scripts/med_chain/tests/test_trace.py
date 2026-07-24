import os
import sys
import unittest
from datetime import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solve import solve, load_rules
from chain_trace import log_trace, TRACE_PATH

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestTrace(unittest.TestCase):
    def test_log_trace_appends_jsonl(self):
        rules = load_rules(os.path.join(BASE, "rules.json"))["constraints"]
        result = solve(rules, {"C": time(13, 0)})
        row = log_trace("unit-test-1", {"C": time(13, 0)}, result)
        self.assertEqual(row["run_id"], "unit-test-1")
        with open(TRACE_PATH, encoding="utf-8") as f:
            lines = f.read().splitlines()
        self.assertTrue(any("unit-test-1" in ln for ln in lines))


if __name__ == "__main__":
    unittest.main()
