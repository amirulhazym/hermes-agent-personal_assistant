import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "nightly_git_hygiene.py"
SPEC = importlib.util.spec_from_file_location("nightly_git_hygiene", MODULE_PATH)
assert SPEC and SPEC.loader
HYGIENE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = HYGIENE
SPEC.loader.exec_module(HYGIENE)


class NightlyGitHygieneTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test-nightly-hygiene-")
        self.repo_dir = Path(self.temp_dir) / "repo"
        self.repo_dir.mkdir()

        # Init dummy repo
        subprocess.run(["git", "-C", str(self.repo_dir), "init", "-q"], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "config", "user.email", "test@example.invalid"], check=True)

        # Commit initial file
        (self.repo_dir / "README.md").write_text("# Initial Repo\n")
        subprocess.run(["git", "-C", str(self.repo_dir), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "commit", "-q", "-m", "initial commit"], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "branch", "-M", "main"], check=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_clean_repo_status_contract(self):
        audit = HYGIENE.run_audit(repo_root=self.repo_dir, dry_run=True)
        self.assertIn("status", audit)
        self.assertEqual(audit["git_state"]["is_clean"], True)

    def test_dirty_repo_produces_hold_not_pass(self):
        # Create uncommitted file
        (self.repo_dir / "dirty_file.txt").write_text("uncommitted changes\n")
        audit = HYGIENE.run_audit(repo_root=self.repo_dir, dry_run=True)
        self.assertEqual(audit["git_state"]["is_clean"], False)
        self.assertEqual(audit["status"], "HOLD")
        self.assertTrue(any("uncommitted" in h.lower() for h in audit["holds"]))


if __name__ == "__main__":
    unittest.main()
