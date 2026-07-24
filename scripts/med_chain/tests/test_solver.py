import os
import sys
import unittest
from datetime import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solve import solve, load_rules

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestSolver(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules(os.path.join(BASE, "rules.json"))["constraints"]

    def test_c_at_1pm_derives_d_and_keeps_night_anchor(self):
        result = solve(self.rules, {"C": time(13, 0)})
        self.assertEqual(result["slots"]["D"], time(17, 0), result["slots"])
        self.assertEqual(result["slots"]["E"], time(20, 0))
        self.assertNotIn("A", result["slots"])
        self.assertEqual(result["slots"]["B"], time(8, 0))
        self.assertIn("rule_003", result["rules_fired"])


if __name__ == "__main__":
    unittest.main()
