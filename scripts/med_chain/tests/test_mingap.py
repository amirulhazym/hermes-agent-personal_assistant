import os
import sys
import unittest
from datetime import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solve import solve, load_rules

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestMinGap(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules(os.path.join(BASE, "rules.json"))["constraints"]

    def test_a_early_keeps_b_at_doctor_anchor(self):
        result = solve(self.rules, {"A": time(6, 0)})
        self.assertEqual(result["slots"]["B"], time(8, 0), result["slots"])
        self.assertIn("rule_001", result["rules_fired"])

    def test_a_does_not_create_dexa_cascade(self):
        result = solve(self.rules, {"A": time(6, 0)})
        self.assertEqual(result["slots"]["B"], time(8, 0))
        self.assertEqual(result["slots"]["E"], time(20, 0))
        self.assertEqual(result["slots"]["C"], time(12, 0))
        self.assertEqual(result["slots"]["D"], time(16, 0))


if __name__ == "__main__":
    unittest.main()
