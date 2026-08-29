import importlib.util
import hashlib
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "nightly_git_hygiene.py"
SPEC = importlib.util.spec_from_file_location("nightly_git_hygiene", MODULE_PATH)
assert SPEC and SPEC.loader
HYGIENE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = HYGIENE
SPEC.loader.exec_module(HYGIENE)


def test_execution_identity_records_executable_hash_separately_from_repo_head():
    audited_head = "a" * 40
    identity = HYGIENE.execution_identity(REPO_ROOT, audited_head)
    script_path = MODULE_PATH.resolve()
    expected_hash = hashlib.sha256(script_path.read_bytes()).hexdigest()

    assert identity["script_path"] == str(script_path)
    assert identity["script_sha256"] == expected_hash
    assert identity["script_size"] == script_path.stat().st_size
    assert identity["audited_repo"] == str(REPO_ROOT)
    assert identity["audited_repo_head"] == audited_head
    assert identity["script_sha256"] != identity["audited_repo_head"]
