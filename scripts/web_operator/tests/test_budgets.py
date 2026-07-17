import unittest

from scripts.web_operator.coordinator import RunBudget


class BudgetTests(unittest.TestCase):
    def test_action_budget(self):
        b = RunBudget(max_actions=2, max_active_seconds=600)
        b.charge_action()
        b.charge_action()
        with self.assertRaises(RuntimeError):
            b.charge_action()

    def test_time_budget(self):
        b = RunBudget(max_actions=30, max_active_seconds=10)
        b.charge_time(9)
        with self.assertRaises(RuntimeError):
            b.charge_time(2)


if __name__ == "__main__":
    unittest.main()
