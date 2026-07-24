import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from resolve_conflict import resolve


class TestConflicts(unittest.TestCase):
    def test_rule_beats_user(self):
        winner, note = resolve("13:43", 95, "user_request")
        self.assertEqual(winner, "rule", note)

    def test_user_beats_low_priority(self):
        winner, note = resolve("13:43", 20, "user_request")
        self.assertEqual(winner, "user", note)


if __name__ == "__main__":
    unittest.main()
