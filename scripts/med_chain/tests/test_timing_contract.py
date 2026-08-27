import os
import sys
import unittest
from datetime import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solve import solve, load_rules

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestTimingContract(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules(os.path.join(BASE, "rules.json"))["constraints"]

    def test_early_akurit_does_not_move_dexa_morning_anchor(self):
        for a in (time(5, 40), time(6, 0), time(6, 32), time(6, 41)):
            with self.subTest(a=a):
                result = solve(self.rules, {"A": a})
                self.assertEqual(result["slots"]["B"], time(8, 0), result)
                self.assertEqual(result["slots"]["E"], time(20, 0), result)
                self.assertEqual(result["slots"]["C"], time(12, 0), result)
                self.assertEqual(result["slots"]["D"], time(16, 0), result)

    def test_late_akurit_only_delays_b_until_safe(self):
        result = solve(self.rules, {"A": time(7, 18)})
        self.assertEqual(result["slots"]["B"], time(8, 18), result)
        self.assertEqual(result["slots"]["E"], time(20, 0), result)
        self.assertEqual(result["slots"]["C"], time(12, 0), result)
        self.assertEqual(result["slots"]["D"], time(16, 0), result)

    def test_actual_b_drives_only_c_with_exact_time(self):
        result = solve(self.rules, {"B": time(7, 38)})
        self.assertEqual(result["slots"]["C"], time(11, 38), result)
        self.assertEqual(result["slots"]["D"], time(15, 38), result)
        self.assertEqual(result["slots"]["E"], time(20, 0), result)

    def test_actual_c_drives_only_d_with_exact_time(self):
        result = solve(self.rules, {"C": time(11, 38)})
        self.assertEqual(result["slots"]["D"], time(15, 38), result)
        self.assertEqual(result["slots"]["E"], time(20, 0), result)

    def test_late_calcium_is_not_a_dexa_input(self):
        result = solve(self.rules, {"B": time(8, 0), "C": time(12, 0), "E": time(20, 30)})
        self.assertEqual(result["slots"]["D"], time(16, 0), result)
        self.assertEqual(result["slots"]["E"], time(20, 30), result)

    def test_unsafe_actual_b_is_reported_as_conflict(self):
        result = solve(self.rules, {"A": time(7, 18), "B": time(8, 0)})
        self.assertTrue(result["conflicts"], result)
        self.assertIn("A→B", result["conflicts"][0], result)

    def test_pyridoxine_alone_is_not_an_a_timing_input(self):
        # The resolver receives no A until actual Akurit time exists.
        result = solve(self.rules, {})
        self.assertEqual(result["slots"]["B"], time(8, 0), result)

    def test_late_b_pushes_f_min_gap_safe(self):
        # B taken at 10:35 -> F (anchor 14:00) must push to at least 16:35 (6h gap)
        result = solve(self.rules, {"B": time(10, 35)})
        self.assertEqual(result["slots"]["F"], time(16, 35), result)
        self.assertIn("rule_009", result["rules_fired"])

    def test_early_b_keeps_f_at_anchor(self):
        # B taken at 08:00 -> F remains at 14:00 anchor (6h gap satisfied)
        result = solve(self.rules, {"B": time(8, 0)})
        self.assertEqual(result["slots"]["F"], time(14, 0), result)
        self.assertIn("rule_008", result["rules_fired"])


if __name__ == "__main__":
    unittest.main()
