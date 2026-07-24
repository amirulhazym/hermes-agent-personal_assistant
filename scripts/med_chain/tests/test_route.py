import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from route import route


class TestRoute(unittest.TestCase):
    def test_single_query_sends(self):
        decision = route({"slot_changes": 1, "conflicts": []})
        self.assertEqual(decision, "send")

    def test_multi_change_with_conflict_reviews(self):
        decision = route({"slot_changes": 3, "conflicts": ["rule_004 vs user"]})
        self.assertEqual(decision, "review")

    def test_no_changes_sends(self):
        decision = route({"slot_changes": 0, "conflicts": []})
        self.assertEqual(decision, "send")


if __name__ == "__main__":
    unittest.main()
