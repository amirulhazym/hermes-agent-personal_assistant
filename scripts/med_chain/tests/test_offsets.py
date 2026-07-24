import os
import sys
import unittest
from datetime import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solve import solve, load_rules

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestOffsets(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules(os.path.join(BASE, "rules.json"))["constraints"]

    def test_e_stays_night_anchor_despite_late_morning_b(self):
        result = solve(self.rules, {"B": time(9, 43)})
        self.assertEqual(result["slots"]["E"], time(20, 0), result["slots"])
        self.assertIn("rule_005", result["rules_fired"])


if __name__ == "__main__":
    unittest.main()
