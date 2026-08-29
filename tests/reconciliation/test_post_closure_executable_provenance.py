import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "verify_post_closure.py"
SPEC = importlib.util.spec_from_file_location("verify_post_closure", MODULE_PATH)
assert SPEC and SPEC.loader
VERIFIER = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = VERIFIER
SPEC.loader.exec_module(VERIFIER)


class PostClosureExecutableProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="post-closure-provenance-")
        self.root = Path(self.temp_dir.name)
        self.repo = self.root / "repo"
        self.runtime_scripts = self.root / "runtime" / "scripts"
        self.runtime_scripts.mkdir(parents=True)
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.name", "Test User"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "config", "user.email", "test@example.invalid"], check=True)

    def tearDown(self):
        self.temp_dir.cleanup()

    @staticmethod
    def digest(data: bytes) -> str:
        return sha256(data).hexdigest()

    def commit_candidate(self, wrapper_bytes: bytes, target_bytes: bytes, include_wrapper=True):
        source_dir = self.repo / "scripts"
        source_dir.mkdir(exist_ok=True)
        target_source = source_dir / "nightly_git_hygiene.py"
        wrapper_source = source_dir / "nightly_git_hygiene_wrapper.sh"
        target_source.write_bytes(target_bytes)
        os.chmod(target_source, 0o755)
        if include_wrapper:
            wrapper_source.write_bytes(wrapper_bytes)
            os.chmod(wrapper_source, 0o755)
        subprocess.run(["git", "-C", str(self.repo), "add", "scripts"], check=True)
        subprocess.run(["git", "-C", str(self.repo), "commit", "-q", "-m", "candidate"], check=True)
        candidate_sha = subprocess.check_output(
            ["git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True
        ).strip()
        return candidate_sha, target_source, wrapper_source

    def write_inputs(self, candidate_sha, target_bytes, wrapper_bytes, *, manifest_wrapper=True, receipt=None):
        target_live = self.runtime_scripts / "nightly_git_hygiene.py"
        wrapper_live = self.runtime_scripts / "nightly_git_hygiene_wrapper.sh"
        target_live.write_bytes(target_bytes)
        wrapper_live.write_bytes(wrapper_bytes)
        os.chmod(target_live, 0o755)
        os.chmod(wrapper_live, 0o755)

        entries = [
            {
                "source": "scripts/nightly_git_hygiene.py",
                "source_sha256": self.digest(target_bytes),
                "kind": "runtime-deploy",
                "destination": str(target_live),
            }
        ]
        if manifest_wrapper:
            entries.append(
                {
                    "source": "scripts/nightly_git_hygiene_wrapper.sh",
                    "source_sha256": self.digest(wrapper_bytes),
                    "kind": "runtime-deploy",
                    "destination": str(wrapper_live),
                }
            )
        manifest = self.root / "manifest.json"
        manifest.write_text(json.dumps({"schema_version": 1, "entries": entries}))
        jobs = self.root / "jobs.json"
        jobs.write_text(
            json.dumps(
                {
                    "jobs": [
                        {
                            "id": "9517378892e3",
                            "name": "nightly-git-hygiene",
                            "enabled": True,
                            "no_agent": True,
                            "script": "nightly_git_hygiene_wrapper.sh",
                            "workdir": str(self.repo),
                        }
                    ]
                }
            )
        )
        receipt_path = self.root / "cron-output.md"
        receipt_path.write_text(json.dumps(receipt or {}))
        return target_live, wrapper_live, manifest, jobs, receipt_path

    def verify(self, candidate_sha, manifest, jobs, receipt):
        return VERIFIER.verify(
            repo_root=self.repo,
            candidate_sha=candidate_sha,
            jobs_path=jobs,
            manifest_path=manifest,
            receipt_path=receipt,
            scripts_root=self.runtime_scripts,
            job_id="9517378892e3",
            target_source="scripts/nightly_git_hygiene.py",
        )

    def test_catches_old_main_target_and_unmanaged_wrapper(self):
        candidate_target = b"candidate corrected implementation\n"
        candidate_wrapper = (
            f"#!/usr/bin/env bash\nexec {self.runtime_scripts / 'nightly_git_hygiene.py'}\n"
        ).encode()
        candidate_sha, _, _ = self.commit_candidate(candidate_wrapper, candidate_target, include_wrapper=True)

        old_target = b"personal main implementation\n"
        old_wrapper = (
            f"#!/usr/bin/env bash\nexec {self.repo / 'scripts' / 'nightly_git_hygiene.py'}\n"
        ).encode()
        receipt = {"git_state": {"head": "2" * 40}}
        _, _, manifest, jobs, receipt_path = self.write_inputs(
            candidate_sha,
            old_target,
            old_wrapper,
            manifest_wrapper=False,
            receipt=receipt,
        )

        result = self.verify(candidate_sha, manifest, jobs, receipt_path)

        self.assertNotEqual(result["status"], "PROVEN")
        self.assertEqual(result["verdicts"]["wrapper_manifest"], "FALSE")
        self.assertEqual(result["verdicts"]["current_target_matches_candidate"], "FALSE")
        self.assertEqual(result["receipt"]["audited_repo_head"], "2" * 40)
        self.assertEqual(result["verdicts"]["historical_execution_identity"], "PARTIAL")

    def test_proves_chain_when_runtime_and_receipt_match_candidate(self):
        candidate_target = b"candidate corrected implementation\n"
        candidate_wrapper = (
            f"#!/usr/bin/env bash\nexec {self.runtime_scripts / 'nightly_git_hygiene.py'}\n"
        ).encode()
        candidate_sha, _, _ = self.commit_candidate(candidate_wrapper, candidate_target, include_wrapper=True)
        target_live = self.runtime_scripts / "nightly_git_hygiene.py"
        _, _, manifest, jobs, receipt_path = self.write_inputs(
            candidate_sha,
            candidate_target,
            candidate_wrapper,
            receipt={
                "git_state": {"head": candidate_sha},
                "execution": {
                    "script_path": str(target_live),
                    "script_sha256": self.digest(candidate_target),
                    "script_size": len(candidate_target),
                    "audited_repo_head": candidate_sha,
                },
            },
        )

        result = self.verify(candidate_sha, manifest, jobs, receipt_path)

        self.assertEqual(result["status"], "PROVEN")
        self.assertEqual(result["verdicts"]["current_target_matches_candidate"], "PROVEN")
        self.assertEqual(result["verdicts"]["current_wrapper_matches_candidate"], "PROVEN")
        self.assertEqual(result["verdicts"]["historical_execution_identity"], "PROVEN")

    def test_audited_head_alone_does_not_prove_executed_bytes(self):
        candidate_target = b"candidate corrected implementation\n"
        candidate_wrapper = (
            f"#!/usr/bin/env bash\nexec {self.runtime_scripts / 'nightly_git_hygiene.py'}\n"
        ).encode()
        candidate_sha, _, _ = self.commit_candidate(candidate_wrapper, candidate_target, include_wrapper=True)
        old_target = b"old implementation\n"
        target_live = self.runtime_scripts / "nightly_git_hygiene.py"
        _, _, manifest, jobs, receipt_path = self.write_inputs(
            candidate_sha,
            old_target,
            candidate_wrapper,
            receipt={"git_state": {"head": candidate_sha}},
        )

        result = self.verify(candidate_sha, manifest, jobs, receipt_path)

        self.assertNotEqual(result["status"], "PROVEN")
        self.assertEqual(result["receipt"]["audited_repo_head"], candidate_sha)
        self.assertEqual(result["receipt"]["execution_script_sha256"], None)
        self.assertEqual(result["verdicts"]["historical_execution_identity"], "PARTIAL")
        self.assertEqual(result["verdicts"]["current_target_matches_candidate"], "FALSE")

    def test_rejects_wrapper_target_outside_allowed_script_root(self):
        candidate_target = b"candidate corrected implementation\n"
        candidate_wrapper = (
            f"#!/usr/bin/env bash\nexec {self.runtime_scripts / 'nightly_git_hygiene.py'}\n"
        ).encode()
        candidate_sha, _, _ = self.commit_candidate(candidate_wrapper, candidate_target, include_wrapper=True)
        outside_wrapper = f"#!/usr/bin/env bash\nexec {self.repo / 'scripts' / 'nightly_git_hygiene.py'}\n".encode()
        _, _, manifest, jobs, receipt_path = self.write_inputs(
            candidate_sha,
            candidate_target,
            outside_wrapper,
            receipt={},
        )

        result = self.verify(candidate_sha, manifest, jobs, receipt_path)

        self.assertNotEqual(result["status"], "PROVEN")
        self.assertEqual(result["verdicts"]["wrapper_target_path"], "FALSE")


if __name__ == "__main__":
    unittest.main()
