import unittest
from unittest.mock import MagicMock, patch

from scripts.web_operator.live_wiring import load_browser_callables, load_research_callables, wire_status


class LiveWiringTests(unittest.TestCase):
    def test_wire_status_without_hermes(self):
        with patch("scripts.web_operator.live_wiring.discover_hermes_root", return_value=None):
            status = wire_status()
        self.assertFalse(status["browser_wired"])
        self.assertFalse(status["search_wired"])

    def test_load_browser_with_fake_module(self):
        fake = MagicMock()
        fake.browser_navigate = lambda url, task_id=None: f"ok:{url}"
        fake.browser_snapshot = lambda full=False, task_id=None, user_task=None: "snap"
        fake.browser_click = lambda ref, task_id=None: "click"
        fake.browser_type = lambda ref, text, task_id=None: "type"
        fake.cleanup_browser = lambda task_id=None: None
        with patch("scripts.web_operator.live_wiring.discover_hermes_root") as disc, patch(
            "scripts.web_operator.live_wiring.importlib.import_module", return_value=fake
        ):
            from pathlib import Path

            disc.return_value = Path("/tmp/fake-hermes")
            callables, status = load_browser_callables()
        self.assertTrue(status.browser)
        self.assertIn("navigate", callables)
        self.assertEqual(callables["navigate"]("https://example.com"), "ok:https://example.com")

    def test_load_research_with_fake_module(self):
        fake = MagicMock()
        fake.web_search_tool = lambda query, limit=5: f"search:{query}:{limit}"
        fake.web_extract_tool = lambda urls, **kwargs: f"extract:{urls}"
        with patch("scripts.web_operator.live_wiring.discover_hermes_root") as disc, patch(
            "scripts.web_operator.live_wiring.importlib.import_module", return_value=fake
        ):
            from pathlib import Path

            disc.return_value = Path("/tmp/fake-hermes")
            callables, status = load_research_callables()
        self.assertTrue(status.search)
        self.assertTrue(status.extract)
        self.assertEqual(callables["search_fn"]("q", 3), "search:q:3")
        self.assertEqual(callables["extract_fn"](["https://a"]), "extract:['https://a']")


if __name__ == "__main__":
    unittest.main()
