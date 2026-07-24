import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from chain_consistency import consistency_warnings


class TestConsistency(unittest.TestCase):
    def test_contradiction_flagged(self):
        warnings = consistency_warnings("B", "21:00", {"A": "06:00"})
        self.assertTrue(any("contradicts" in w for w in warnings), warnings)

    def test_anchor_consistent_no_warning(self):
        warnings = consistency_warnings("B", "08:00", {"A": "06:00"})
        self.assertEqual(warnings, [])

    def test_actual_e_before_target_is_not_a_conflict(self):
        self.assertEqual(consistency_warnings("E", "19:12", {}), [])

    def test_downstream_conflict_flagged(self):
        warnings = consistency_warnings("B", "08:00", {"A": "06:00", "C": "13:00"})
        self.assertTrue(any("chain conflict" in w for w in warnings), warnings)

    def test_no_time_no_warning(self):
        self.assertEqual(consistency_warnings("B", None, {"A": "06:00"}), [])


if __name__ == "__main__":
    unittest.main()
