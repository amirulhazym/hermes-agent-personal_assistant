import hashlib
import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "deploy_hermes_runtime.py"
SPEC = importlib.util.spec_from_file_location("deploy_hermes_runtime", MODULE_PATH)
assert SPEC and SPEC.loader
DEPLOY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(DEPLOY)


class NormalizedWorktreeParityTest(unittest.TestCase):
    def test_crlf_worktree_is_equivalent_to_raw_git_source_blob(self):
        with tempfile.TemporaryDirectory(prefix="normalized-worktree-") as temp:
            repo = Path(temp) / "repo"
            subprocess.run(["git", "init", "-q", str(repo)], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            subprocess.run(
                ["git", "-C", str(repo), "config", "user.email", "test@example.invalid"],
                check=True,
            )
            raw = b"Write-Output 'line-1'\nWrite-Output 'line-2'\n"
            (repo / "sample.ps1").write_bytes(raw)
            (repo / ".gitattributes").write_text("*.ps1 text eol=crlf\n")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "fixture"], check=True)
            (repo / "sample.ps1").write_bytes(raw.replace(b"\n", b"\r\n"))

            self.assertTrue(
                DEPLOY._destination_matches(
                    repo / "sample.ps1",
                    repo,
                    "sample.ps1",
                    hashlib.sha256(raw).hexdigest(),
                )
            )


if __name__ == "__main__":
    unittest.main()
