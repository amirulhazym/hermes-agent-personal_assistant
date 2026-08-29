import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "scripts" / "deploy_custom_runtime.py"
MODULE_SPEC = importlib.util.spec_from_file_location("deploy_custom_runtime", MODULE_PATH)
assert MODULE_SPEC and MODULE_SPEC.loader
DEPLOY = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = DEPLOY
MODULE_SPEC.loader.exec_module(DEPLOY)


class CustomRuntimeDeployTest(unittest.TestCase):
    def make_manifest(self, root: Path, source: str, destination: Path, kind: str = "runtime-deploy"):
        return {
            "schema_version": 1,
            "entries": [
                {
                    "source": source,
                    "source_sha256": sha256((root / source).read_bytes()).hexdigest(),
                    "kind": kind,
                    "destination": str(destination) if kind == "runtime-deploy" else None,
                }
            ],
        }

    def make_fixture(self, specs):
        """Create an isolated source/runtime pair.

        Each spec is ``(relative_path, source_bytes, destination_bytes_or_None,
        source_mode, destination_mode_or_None)``. A None destination means the
        declared runtime destination does not yet exist.
        """
        temp = tempfile.TemporaryDirectory(prefix="custom-deploy-fixture-")
        root = Path(temp.name) / "source"
        runtime = Path(temp.name) / "runtime"
        root.mkdir()
        runtime.mkdir()
        entries = []
        for rel, source_bytes, destination_bytes, source_mode, destination_mode in specs:
            source = root / rel
            destination = runtime / rel
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_bytes(source_bytes)
            os.chmod(source, source_mode)
            if destination_bytes is not None:
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(destination_bytes)
                os.chmod(destination, destination_mode)
            entries.append(
                {
                    "source": rel,
                    "source_sha256": sha256(source_bytes).hexdigest(),
                    "kind": "runtime-deploy",
                    "destination": str(destination),
                }
            )
        return temp, root, runtime, {"schema_version": 1, "entries": entries}

    def apply_in_runtime(self, root, runtime, manifest, release_sha="a" * 40):
        previous_root = getattr(DEPLOY, "RUNTIME_ROOT")
        setattr(DEPLOY, "RUNTIME_ROOT", runtime)
        try:
            return DEPLOY.apply_manifest(root, manifest, release_sha)
        finally:
            setattr(DEPLOY, "RUNTIME_ROOT", previous_root)

    @staticmethod
    def snapshot(paths):
        result = {}
        for path in paths:
            result[path] = {
                "exists": path.exists(),
                "bytes": path.read_bytes() if path.exists() else None,
                "mode": stat.S_IMODE(path.stat().st_mode) if path.exists() else None,
                "inode": path.stat().st_ino if path.exists() else None,
            }
        return result

    def assert_snapshot_equal(self, before, paths):
        after = self.snapshot(paths)
        self.assertEqual(after, before)

    def assert_snapshot_content_mode_equal(self, before, paths):
        after = self.snapshot(paths)
        for path in paths:
            self.assertEqual(after[path]["exists"], before[path]["exists"])
            self.assertEqual(after[path]["bytes"], before[path]["bytes"])
            self.assertEqual(after[path]["mode"], before[path]["mode"])

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
            self.assertEqual(plan.new_destinations, ())
            self.assertEqual(plan.write_sources, ())

    def test_plan_classifies_new_destination_as_planned_write(self):
        with tempfile.TemporaryDirectory(prefix="custom-deploy-new-") as temp:
            root = Path(temp) / "source"
            destination_root = Path(temp) / "runtime"
            root.mkdir()
            destination_root.mkdir()
            source = root / "scripts" / "new_tool.py"
            source.parent.mkdir()
            source.write_bytes(b"print('new')\n")

            plan = DEPLOY.build_plan(
                root,
                self.make_manifest(root, "scripts/new_tool.py", destination_root / "scripts" / "new_tool.py"),
                destination_root,
            )

            self.assertEqual(plan.missing, ())
            self.assertEqual(plan.source_mismatches, ())
            self.assertEqual(plan.new_destinations, ("scripts/new_tool.py",))
            self.assertEqual(plan.content_mismatches, ())
            self.assertEqual(plan.write_sources, ("scripts/new_tool.py",))

    def test_apply_write_set_matches_plan_and_excludes_mode_only_unchanged(self):
        specs = [
            ("scripts/content-1.py", b"new-1\n", b"old-1\n", 0o755, 0o755),
            ("scripts/content-2.py", b"new-2\n", b"old-2\n", 0o755, 0o644),
            ("scripts/content-3.py", b"new-3\n", b"old-3\n", 0o644, 0o600),
            ("scripts/new.py", b"new-file\n", None, 0o755, None),
            ("scripts/mode-only.py", b"same\n", b"same\n", 0o755, 0o600),
            ("scripts/unchanged.py", b"same\n", b"same\n", 0o644, 0o644),
        ]
        temp, root, runtime, manifest = self.make_fixture(specs)
        self.addCleanup(temp.cleanup)
        plan = DEPLOY.build_plan(root, manifest, runtime)
        self.assertEqual(len(plan.write_sources), 4)
        self.assertEqual(
            set(plan.write_sources),
            {
                "scripts/content-1.py",
                "scripts/content-2.py",
                "scripts/content-3.py",
                "scripts/new.py",
            },
        )
        mode_only = runtime / "scripts/mode-only.py"
        unchanged = runtime / "scripts/unchanged.py"
        before_inodes = {p: p.stat().st_ino for p in (mode_only, unchanged)}
        calls = []
        real_replace = DEPLOY.os.replace

        def record_replace(source, destination):
            calls.append(Path(destination).relative_to(runtime).as_posix())
            return real_replace(source, destination)

        with patch.object(DEPLOY.os, "replace", side_effect=record_replace):
            result = self.apply_in_runtime(root, runtime, manifest)

        self.assertEqual(tuple(calls), result.written_sources)
        self.assertEqual(set(calls), set(plan.write_sources))
        self.assertEqual(len(calls), 4)
        self.assertEqual(mode_only.stat().st_ino, before_inodes[mode_only])
        self.assertEqual(unchanged.stat().st_ino, before_inodes[unchanged])
        self.assertEqual(stat.S_IMODE(mode_only.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(unchanged.stat().st_mode), 0o644)
        self.assertEqual((runtime / "scripts/new.py").read_bytes(), b"new-file\n")

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
            self.assertEqual(result.written_sources, ("scripts/tool.py",))

    def test_apply_rejects_unsafe_destination(self):
        with tempfile.TemporaryDirectory(prefix="custom-deploy-safe-") as temp:
            root = Path(temp) / "source"
            root.mkdir()
            source = root / "tool.py"
            source.write_bytes(b"ok\n")
            manifest = self.make_manifest(root, "tool.py", Path(temp) / "outside" / "tool.py")
            with self.assertRaises(RuntimeError):
                DEPLOY.build_plan(root, manifest, Path(temp) / "runtime")

    def test_failure_before_first_replacement_restores_existing_and_leaves_new_absent(self):
        specs = [
            ("scripts/existing.py", b"new\n", b"old\n", 0o755, 0o600),
            ("scripts/new.py", b"new destination\n", None, 0o755, None),
            ("scripts/mode-only.py", b"same\n", b"same\n", 0o755, 0o600),
        ]
        temp, root, runtime, manifest = self.make_fixture(specs)
        self.addCleanup(temp.cleanup)
        sentinel = runtime / "undeclared.keep"
        sentinel.write_bytes(b"do not delete\n")
        declared = [runtime / rel for rel, *_ in specs]
        tracked = declared + [sentinel]
        before = self.snapshot(tracked)
        with patch.object(DEPLOY.os, "replace", side_effect=OSError("before first replacement")):
            with self.assertRaises(OSError):
                self.apply_in_runtime(root, runtime, manifest)
        self.assert_snapshot_content_mode_equal(before, tracked)

    def test_failure_immediately_after_replacing_existing_restores_existing(self):
        specs = [
            ("scripts/existing.py", b"new\n", b"old\n", 0o755, 0o600),
            ("scripts/mode-only.py", b"same\n", b"same\n", 0o755, 0o600),
        ]
        temp, root, runtime, manifest = self.make_fixture(specs)
        self.addCleanup(temp.cleanup)
        tracked = [runtime / "scripts/existing.py", runtime / "scripts/mode-only.py"]
        before = self.snapshot(tracked)
        real_replace = DEPLOY.os.replace

        def replace_then_raise(source, destination):
            real_replace(source, destination)
            raise OSError("after replacing existing file")

        with patch.object(DEPLOY.os, "replace", side_effect=replace_then_raise):
            with self.assertRaises(OSError):
                self.apply_in_runtime(root, runtime, manifest)
        self.assert_snapshot_content_mode_equal(before, tracked)

    def test_post_replace_hash_failure_restores_replaced_file(self):
        specs = [("scripts/existing.py", b"new\n", b"old\n", 0o755, 0o600)]
        temp, root, runtime, manifest = self.make_fixture(specs)
        self.addCleanup(temp.cleanup)
        tracked = [runtime / "scripts/existing.py"]
        before = self.snapshot(tracked)
        plan = DEPLOY.build_plan(root, manifest, runtime)
        with patch.object(DEPLOY, "build_plan", return_value=plan), patch.object(
            DEPLOY, "_sha256_file", return_value="0" * 64
        ):
            with self.assertRaises(RuntimeError):
                self.apply_in_runtime(root, runtime, manifest)
        self.assert_snapshot_content_mode_equal(before, tracked)

    def test_failure_after_multiple_successful_replacements_restores_all(self):
        specs = [
            ("scripts/one.py", b"new-1\n", b"old-1\n", 0o755, 0o600),
            ("scripts/two.py", b"new-2\n", b"old-2\n", 0o755, 0o644),
            ("scripts/three.py", b"new-3\n", b"old-3\n", 0o644, 0o600),
            ("scripts/mode-only.py", b"same\n", b"same\n", 0o755, 0o600),
        ]
        temp, root, runtime, manifest = self.make_fixture(specs)
        self.addCleanup(temp.cleanup)
        tracked = [runtime / rel for rel, *_ in specs]
        before = self.snapshot(tracked)
        real_replace = DEPLOY.os.replace
        calls = 0

        def fail_on_third(source, destination):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise OSError("after multiple successful replacements")
            return real_replace(source, destination)

        with patch.object(DEPLOY.os, "replace", side_effect=fail_on_third):
            with self.assertRaises(OSError):
                self.apply_in_runtime(root, runtime, manifest)
        self.assertEqual(calls, 3)
        self.assert_snapshot_content_mode_equal(before, tracked)

    def test_failure_after_creating_new_destination_restores_and_removes_new_file(self):
        specs = [
            ("scripts/existing.py", b"new\n", b"old\n", 0o755, 0o600),
            ("scripts/new.py", b"new destination\n", None, 0o755, None),
            ("scripts/mode-only.py", b"same\n", b"same\n", 0o755, 0o600),
        ]
        temp, root, runtime, manifest = self.make_fixture(specs)
        self.addCleanup(temp.cleanup)
        sentinel = runtime / "undeclared.keep"
        sentinel.write_bytes(b"do not delete\n")
        existing = runtime / "scripts/existing.py"
        mode_only = runtime / "scripts/mode-only.py"
        new_destination = runtime / "scripts/new.py"
        tracked = [existing, mode_only, sentinel]
        before = self.snapshot(tracked)
        real_replace = DEPLOY.os.replace

        def fail_after_new(source, destination):
            real_replace(source, destination)
            if Path(destination) == new_destination:
                raise OSError("after creating new destination")

        with patch.object(DEPLOY.os, "replace", side_effect=fail_after_new):
            with self.assertRaises(OSError):
                self.apply_in_runtime(root, runtime, manifest)
        self.assert_snapshot_content_mode_equal(before, tracked)
        self.assertFalse(new_destination.exists())


if __name__ == "__main__":
    unittest.main()
