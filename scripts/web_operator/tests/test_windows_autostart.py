import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
LAUNCHER = ROOT / "windows" / "web-operator-worker-autostart.ps1"


class WindowsAutostartContractTests(unittest.TestCase):
    def test_launcher_registers_worker_loop_at_logon(self):
        content = LAUNCHER.read_text(encoding="utf-8")

        self.assertIn("Register-ScheduledTask", content)
        self.assertIn("AtLogOn", content)
        self.assertIn("web-operator-worker.ps1", content)
        self.assertIn("-Action Run", content)
        self.assertIn("-Seconds 0", content)
        self.assertIn("New-ScheduledTaskPrincipal", content)
        self.assertRegex(content, r"-LogonType\s+Interactive(?:Token)?")
        self.assertIn("RunLevel Limited", content)

    def test_worker_treats_zero_seconds_as_forever(self):
        content = (ROOT / "windows" / "web-operator-worker.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn("$deadline = if ($Seconds -gt 0)", content)
        self.assertIn("$null -eq $deadline", content)

    def test_launcher_is_outbound_only_and_contains_no_secret_material(self):
        content = LAUNCHER.read_text(encoding="utf-8").lower()

        self.assertNotIn("start-listener", content)
        self.assertNotIn("http:\\", content)
        self.assertNotIn("listenport", content)
        self.assertNotIn("api_key", content)
        self.assertNotIn("bot_token", content)
        self.assertNotIn("password", content)


if __name__ == "__main__":
    unittest.main()
