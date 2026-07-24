import os
import sys
import unittest
from datetime import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solve import solve, load_rules
from why import why

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestWhy(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules(os.path.join(BASE, "rules.json"))["constraints"]
        self.result = solve(self.rules, {"C": time(13, 0)})

    def test_why_explains_d(self):
        explanation = why("D", self.result, self.rules)
        self.assertIn("D = 17:00", explanation, explanation)


if __name__ == "__main__":
    unittest.main()
