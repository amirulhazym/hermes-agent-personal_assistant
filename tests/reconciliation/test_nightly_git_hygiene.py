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


class NightlyGitHygieneScenarioTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="test-hygiene-scenarios-")
        self.origin_dir = Path(self.temp_dir) / "origin.git"
        self.upstream_dir = Path(self.temp_dir) / "upstream.git"
        self.repo_dir = Path(self.temp_dir) / "repo"

        # 1. Bare remotes with main as default branch
        subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(self.origin_dir)], check=True)
        subprocess.run(["git", "init", "--bare", "-q", "-b", "main", str(self.upstream_dir)], check=True)

        # 2. Local clone
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo_dir)], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "config", "user.email", "test@example.invalid"], check=True)

        # Initial commit
        (self.repo_dir / "README.md").write_text("# Initial Repo\n")
        subprocess.run(["git", "-C", str(self.repo_dir), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "commit", "-q", "-m", "initial commit"], check=True)

        # Setup remotes
        subprocess.run(["git", "-C", str(self.repo_dir), "remote", "add", "origin", str(self.origin_dir)], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "remote", "add", "upstream", str(self.upstream_dir)], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "push", "-q", "-u", "origin", "main"], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "push", "-q", "-u", "upstream", "main"], check=True)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    # Scenario 1: Clean tree + all gates pass -> PASS
    def test_scenario_1_clean_tree_passes(self):
        audit = HYGIENE.run_audit(repo_root=self.repo_dir, dry_run=True)
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["git_state"]["is_clean"], True)
        self.assertEqual(audit["release_pending"], False)

    # Scenario 2: Dirty tracked tree -> HOLD
    def test_scenario_2_dirty_tracked_tree_hold(self):
        (self.repo_dir / "README.md").write_text("# Modified\n")
        audit = HYGIENE.run_audit(repo_root=self.repo_dir, dry_run=True)
        self.assertEqual(audit["status"], "HOLD")
        self.assertEqual(audit["git_state"]["is_clean"], False)

    # Scenario 3: Untracked source-like file -> HOLD
    def test_scenario_3_untracked_file_hold(self):
        (self.repo_dir / "new_script.py").write_text("print('hello')\n")
        audit = HYGIENE.run_audit(repo_root=self.repo_dir, dry_run=True)
        self.assertEqual(audit["status"], "HOLD")
        self.assertEqual(audit["git_state"]["is_clean"], False)

    # Scenario 4: Contract test command failure -> FAIL
    def test_scenario_4_test_failure_fails(self):
        (self.repo_dir / "scripts").mkdir(parents=True, exist_ok=True)
        (self.repo_dir / "scripts" / "run_contract_tests.sh").write_text("#!/bin/bash\nexit 1\n")
        os.chmod(self.repo_dir / "scripts" / "run_contract_tests.sh", 0o755)

        audit = HYGIENE.run_audit(repo_root=self.repo_dir, dry_run=True)
        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("Contract tests failed", audit["errors"])

    # Scenario 5: Secret scan failure -> FAIL
    def test_scenario_5_secret_scan_failure_fails(self):
        (self.repo_dir / "scripts" / "guard").mkdir(parents=True, exist_ok=True)
        (self.repo_dir / "scripts" / "guard" / "secret-scan.sh").write_text("#!/bin/bash\nexit 1\n")
        os.chmod(self.repo_dir / "scripts" / "guard" / "secret-scan.sh", 0o755)

        audit = HYGIENE.run_audit(repo_root=self.repo_dir, dry_run=True)
        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("Secret scan failed on staged files", audit["errors"])

    # Scenario 6: PII scan failure -> FAIL
    def test_scenario_6_pii_scan_failure_fails(self):
        (self.repo_dir / "scripts" / "guard").mkdir(parents=True, exist_ok=True)
        (self.repo_dir / "scripts" / "guard" / "pii-review.py").write_text("#!/bin/bash\nexit 1\n")
        os.chmod(self.repo_dir / "scripts" / "guard" / "pii-review.py", 0o755)

        audit = HYGIENE.run_audit(repo_root=self.repo_dir, dry_run=True)
        self.assertEqual(audit["status"], "FAIL")
        self.assertIn("PII review flagged unredacted patterns in diff", audit["errors"])

    # Scenario 7: Local & remote divergence -> HOLD
    def test_scenario_7_divergence_hold(self):
        temp_clone = Path(self.temp_dir) / "clone"
        subprocess.run(["git", "clone", "-q", "-b", "main", str(self.origin_dir), str(temp_clone)], check=True)
        subprocess.run(["git", "-C", str(temp_clone), "config", "user.name", "Remote User"], check=True)
        subprocess.run(["git", "-C", str(temp_clone), "config", "user.email", "remote@example.invalid"], check=True)
        (temp_clone / "remote_change.txt").write_text("remote\n")
        subprocess.run(["git", "-C", str(temp_clone), "add", "remote_change.txt"], check=True)
        subprocess.run(["git", "-C", str(temp_clone), "commit", "-q", "-m", "remote commit"], check=True)
        subprocess.run(["git", "-C", str(temp_clone), "push", "-q", "origin", "main"], check=True)

        (self.repo_dir / "local_change.txt").write_text("local\n")
        subprocess.run(["git", "-C", str(self.repo_dir), "add", "local_change.txt"], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "commit", "-q", "-m", "local commit"], check=True)

        audit = HYGIENE.run_audit(repo_root=self.repo_dir, dry_run=True)
        self.assertEqual(audit["status"], "HOLD")
        self.assertTrue(any("diverged" in h.lower() for h in audit["holds"]))

    # Scenario 8: Local ahead of remote without divergence -> PASS with release_pending=True
    def test_scenario_8_local_ahead_passes_with_release_pending(self):
        (self.repo_dir / "feature.txt").write_text("new feature\n")
        subprocess.run(["git", "-C", str(self.repo_dir), "add", "feature.txt"], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "commit", "-q", "-m", "feat: local commit"], check=True)

        audit = HYGIENE.run_audit(repo_root=self.repo_dir, dry_run=True)
        self.assertEqual(audit["status"], "PASS")
        self.assertEqual(audit["release_pending"], True)
        self.assertEqual(audit["push_allowed"], False)

    # Scenario 9: Merged local branch -> cleaned up in non-dry-run
    def test_scenario_9_merged_branch_cleanup(self):
        subprocess.run(["git", "-C", str(self.repo_dir), "checkout", "-q", "-b", "feat/merged-branch"], check=True)
        (self.repo_dir / "branch_file.txt").write_text("branch file\n")
        subprocess.run(["git", "-C", str(self.repo_dir), "add", "branch_file.txt"], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "commit", "-q", "-m", "branch commit"], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "checkout", "-q", "main"], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "merge", "-q", "--ff-only", "feat/merged-branch"], check=True)

        audit = HYGIENE.run_audit(repo_root=self.repo_dir, dry_run=False)
        self.assertIn("feat/merged-branch", audit["branches"]["merged"])

        branches = subprocess.check_output(["git", "-C", str(self.repo_dir), "branch"], text=True)
        self.assertNotIn("feat/merged-branch", branches)

    # Scenario 10: Unmerged stale branch (>7d) -> retained and reported in holds
    def test_scenario_10_unmerged_stale_branch_retained(self):
        subprocess.run(["git", "-C", str(self.repo_dir), "checkout", "-q", "-b", "feat/stale-unmerged"], check=True)
        (self.repo_dir / "stale_file.txt").write_text("stale unmerged\n")
        subprocess.run(["git", "-C", str(self.repo_dir), "add", "stale_file.txt"], check=True)

        past_date = "2026-08-10T12:00:00+08:00"
        env = {**os.environ, "GIT_COMMITTER_DATE": past_date, "GIT_AUTHOR_DATE": past_date}
        subprocess.run(["git", "-C", str(self.repo_dir), "commit", "-q", "-m", "old unmerged commit"], env=env, check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "checkout", "-q", "main"], check=True)

        audit = HYGIENE.run_audit(repo_root=self.repo_dir, dry_run=True)
        self.assertEqual(audit["status"], "HOLD")
        self.assertTrue(any(b["name"] == "feat/stale-unmerged" for b in audit["branches"]["stale"]))

        branches = subprocess.check_output(["git", "-C", str(self.repo_dir), "branch"], text=True)
        self.assertIn("feat/stale-unmerged", branches)

    # Scenario 11: Upstream ahead -> reported in sync_state
    def test_scenario_11_upstream_ahead_reported(self):
        temp_up = Path(self.temp_dir) / "upstream_clone"
        subprocess.run(["git", "clone", "-q", "-b", "main", str(self.upstream_dir), str(temp_up)], check=True)
        subprocess.run(["git", "-C", str(temp_up), "config", "user.name", "Upstream Dev"], check=True)
        subprocess.run(["git", "-C", str(temp_up), "config", "user.email", "dev@example.invalid"], check=True)
        (temp_up / "upstream_patch.txt").write_text("patch\n")
        subprocess.run(["git", "-C", str(temp_up), "add", "upstream_patch.txt"], check=True)
        subprocess.run(["git", "-C", str(temp_up), "commit", "-q", "-m", "upstream release"], check=True)
        subprocess.run(["git", "-C", str(temp_up), "push", "-q", "origin", "main"], check=True)

        audit = HYGIENE.run_audit(repo_root=self.repo_dir, dry_run=True)
        self.assertEqual(audit["sync_state"]["upstream"]["behind"], 1)

    # Scenario 12: Malformed git path -> handled gracefully
    def test_scenario_12_malformed_path_handling(self):
        bad_path = Path(self.temp_dir) / "nonexistent"
        audit = HYGIENE.run_audit(repo_root=bad_path, dry_run=True)
        self.assertEqual(audit["status"], "HOLD")

    # Scenario 13: Proposal generation / recurring issue logging
    def test_scenario_13_proposal_generation(self):
        proposals_dir = self.repo_dir / "docs" / "proposals"
        proposals_dir.mkdir(parents=True, exist_ok=True)
        today_str = "2026-08-28"
        proposal_file = proposals_dir / f"nightly-{today_str}.md"
        proposal_file.write_text("# Proposal Draft\n")

        audit = HYGIENE.run_audit(repo_root=self.repo_dir, dry_run=True)
        self.assertEqual(audit["proposal_path"], str(proposal_file))

    # Scenario 14: Dry run mode performs no branch deletions
    def test_scenario_14_dry_run_preserves_merged_branches(self):
        subprocess.run(["git", "-C", str(self.repo_dir), "checkout", "-q", "-b", "feat/dry-run-branch"], check=True)
        (self.repo_dir / "f.txt").write_text("f\n")
        subprocess.run(["git", "-C", str(self.repo_dir), "add", "f.txt"], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "commit", "-q", "-m", "f"], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "checkout", "-q", "main"], check=True)
        subprocess.run(["git", "-C", str(self.repo_dir), "merge", "-q", "--ff-only", "feat/dry-run-branch"], check=True)

        audit = HYGIENE.run_audit(repo_root=self.repo_dir, dry_run=True)
        self.assertIn("feat/dry-run-branch", audit["branches"]["merged"])
        self.assertEqual(audit["actions_taken"], [])

        branches = subprocess.check_output(["git", "-C", str(self.repo_dir), "branch"], text=True)
        self.assertIn("feat/dry-run-branch", branches)


if __name__ == "__main__":
    unittest.main()
