import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chain_review import review_slots, review_fixed

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _rules():
    import json
    with open(os.path.join(BASE, "rules.json"), encoding="utf-8") as f:
        return json.load(f)["constraints"]


class TestReview(unittest.TestCase):
    def test_solver_output_all_pass(self):
        lines = review_fixed({"A": "06:00"})
        self.assertTrue(all("PASSED" in ln or "N/A" in ln for ln in lines), lines)
        self.assertFalse(any("FAILED" in ln for ln in lines), lines)

    def test_min_gap_violation_flagged(self):
        lines = review_slots({"A": "07:18", "B": "08:00"}, _rules())
        self.assertTrue(any("rule_001" in ln and "FAILED" in ln for ln in lines), lines)

    def test_night_anchor_passes(self):
        lines = review_slots({"E": "20:00"}, _rules())
        self.assertTrue(any("rule_005" in ln and "PASSED" in ln for ln in lines), lines)

    def test_actual_e_before_target_is_not_failed(self):
        lines = review_fixed({"E": "19:12"})
        self.assertFalse(any("rule_005" in ln and "FAILED" in ln for ln in lines), lines)


if __name__ == "__main__":
    unittest.main()
