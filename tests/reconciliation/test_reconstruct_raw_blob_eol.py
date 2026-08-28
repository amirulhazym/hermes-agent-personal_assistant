import importlib.util
import os
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "reconstruct_hermes_runtime.py"
SPEC = importlib.util.spec_from_file_location("reconstruct_hermes_runtime", MODULE_PATH)
assert SPEC and SPEC.loader
reconstruct = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reconstruct)


class RawBlobExtractionTest(unittest.TestCase):
    def test_extraction_preserves_git_blob_bytes_when_eol_attribute_exists(self):
        with tempfile.TemporaryDirectory(prefix="raw-blob-eol-") as temp:
            repo = Path(temp) / "repo"
            output = Path(temp) / "output"
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
            subprocess.run(
                ["git", "-C", str(repo), "commit", "-q", "-m", "fixture"],
                check=True,
            )
            commit = subprocess.check_output(
                ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
            ).strip()

            reconstruct._extract_archive(repo, commit, output)

            self.assertEqual((output / "sample.ps1").read_bytes(), raw)
            self.assertEqual(
                (output / "sample.ps1").stat().st_mode & 0o777,
                0o644,
            )


if __name__ == "__main__":
    unittest.main()
