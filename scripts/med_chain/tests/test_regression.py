import os
import sys
import unittest
from datetime import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solve import solve, load_rules

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestRegression17(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules(os.path.join(BASE, "rules.json"))["constraints"]

    def test_e_is_always_night_anchor_not_c_derived(self):
        result = solve(self.rules, {"C": time(13, 0)})
        self.assertEqual(result["slots"]["E"], time(20, 0))
        self.assertIn("rule_005", result["rules_fired"])
        result2 = solve(self.rules, {"C": time(13, 0), "E": time(21, 43)})
        self.assertEqual(result2["slots"]["E"], time(21, 43))


if __name__ == "__main__":
    unittest.main()
