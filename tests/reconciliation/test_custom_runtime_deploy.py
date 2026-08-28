import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parents[2] / "scripts" / "deploy_custom_runtime.py"
_MODULE_SPEC = importlib.util.spec_from_file_location("deploy_custom_runtime", _MODULE_PATH)
assert _MODULE_SPEC and _MODULE_SPEC.loader
DEPLOY = importlib.util.module_from_spec(_MODULE_SPEC)
sys.modules[_MODULE_SPEC.name] = DEPLOY
_MODULE_SPEC.loader.exec_module(DEPLOY)


class CustomRuntimeDeployTest(unittest.TestCase):
    def make_manifest(self, root: Path, source: str, destination: Path, kind: str = "runtime-deploy"):
        return {
            "schema_version": 1,
            "entries": [
                {
                    "source": source,
                    "source_sha256": __import__("hashlib").sha256(
                        (root / source).read_bytes()
                    ).hexdigest(),
                    "kind": kind,
                    "destination": str(destination) if kind == "runtime-deploy" else None,
                }
            ],
        }

    def test_plan_preserves_mode_differences_as_metadata(self):
        with tempfile.TemporaryDirectory(prefix="custom-deploy-plan-") as temp:
            root = Path(temp) / "source"
            destination_root = Path(temp) / "runtime"
            root.mkdir()
            destination_root.mkdir()
            source = root / "scripts" / "tool.py"
            destination = destination_root / "scripts" / "tool.py"
            source.parent.mkdir()
            destination.parent.mkdir()
            source.write_bytes(b"print('ok')\n")
            destination.write_bytes(source.read_bytes())
            os.chmod(source, 0o664)
            os.chmod(destination, 0o600)

            plan = DEPLOY.build_plan(
                root,
                self.make_manifest(root, "scripts/tool.py", destination),
                destination_root,
            )

            self.assertEqual(plan.content_mismatches, ())
            self.assertEqual(plan.mode_only, ("scripts/tool.py",))
            self.assertEqual(plan.missing, ())

    def test_apply_preserves_existing_mode_and_creates_rollback(self):
        with tempfile.TemporaryDirectory(prefix="custom-deploy-apply-") as temp:
            root = Path(temp) / "source"
            destination_root = Path(temp) / "runtime"
            root.mkdir()
            destination_root.mkdir()
            source = root / "scripts" / "tool.py"
            destination = destination_root / "scripts" / "tool.py"
            source.parent.mkdir()
            destination.parent.mkdir()
            source.write_bytes(b"new\n")
            destination.write_bytes(b"old\n")
            os.chmod(source, 0o755)
            os.chmod(destination, 0o600)
            manifest = self.make_manifest(root, "scripts/tool.py", destination)

            previous_root = DEPLOY.RUNTIME_ROOT
            DEPLOY.RUNTIME_ROOT = destination_root
            try:
                result = DEPLOY.apply_manifest(root, manifest, "a" * 40)
            finally:
                DEPLOY.RUNTIME_ROOT = previous_root

            self.assertEqual(destination.read_bytes(), b"new\n")
            self.assertEqual(stat.S_IMODE(destination.stat().st_mode), 0o600)
            self.assertTrue(result.rollback_root.is_dir())
            self.assertEqual(
                (result.rollback_root / "scripts" / "tool.py").read_bytes(),
                b"old\n",
            )

    def test_apply_rejects_unsafe_destination(self):
        with tempfile.TemporaryDirectory(prefix="custom-deploy-safe-") as temp:
            root = Path(temp) / "source"
            root.mkdir()
            source = root / "tool.py"
            source.write_bytes(b"ok\n")
            manifest = self.make_manifest(root, "tool.py", Path(temp) / "outside" / "tool.py")
            with self.assertRaises(RuntimeError):
                DEPLOY.build_plan(root, manifest, Path(temp) / "runtime")


if __name__ == "__main__":
    unittest.main()
