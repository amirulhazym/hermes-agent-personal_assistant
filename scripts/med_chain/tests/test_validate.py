import os
import sys
import unittest
from datetime import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from solve import solve, load_rules
from validate_semantic import validate

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestValidate(unittest.TestCase):
    def setUp(self):
        self.rules = load_rules(os.path.join(BASE, "rules.json"))["constraints"]
        self.solver_d17 = solve(self.rules, {"C": time(13, 0)})

    def test_matching_llm_passes(self):
        ok, msgs = validate({"D": time(17, 0)}, self.solver_d17)
        self.assertTrue(ok, msgs)
        self.assertEqual(msgs, [])

    def test_mismatched_llm_fails(self):
        ok, msgs = validate({"D": time(18, 0)}, self.solver_d17)
        self.assertFalse(ok)
        self.assertTrue(msgs)


if __name__ == "__main__":
    unittest.main()
