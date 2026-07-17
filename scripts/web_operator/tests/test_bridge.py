import base64
import json
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from scripts.web_operator.bridge import BridgeControlPlane, GrantConsumer, encode_signed_grant
from scripts.web_operator.crypto import CryptoError, HostKeyStore
from scripts.web_operator.grants import GrantError, GrantRequest
from scripts.web_operator.pc_worker_runtime import PcWorkerRuntime


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        try:
            HostKeyStore(self.root / "probe").load_or_create_identity()
            self.crypto_ok = True
        except CryptoError:
            self.crypto_ok = False

    def test_enroll_offline_postpone(self):
        if not self.crypto_ok:
            self.skipTest("cryptography not installed")
        plane = BridgeControlPlane(self.root)
        # no heartbeat → offline
        posted = plane.post_grant(
            task_id="t1",
            owner_id="owner",
            device_id="pc-missing",
            app="Notepad",
        )
        self.assertFalse(posted["ok"])
        self.assertTrue(posted.get("postpone"))

    def test_grant_verify_replay_and_named_app(self):
        if not self.crypto_ok:
            self.skipTest("cryptography not installed")
        plane = BridgeControlPlane(self.root)
        pc_keys = HostKeyStore(self.root / "pc-keys")
        pc_id = pc_keys.load_or_create_identity()
        device_id = "pc-test-1"
        plane.enroll_device(device_id, pc_id.public_key_bytes, label="test")

        # heartbeat online
        status = {
            "device_id": device_id,
            "online": True,
            "heartbeat_at": __import__("datetime")
            .datetime.now(__import__("datetime").timezone.utc)
            .isoformat()
            .replace("+00:00", "Z"),
        }
        (plane.paths.status / f"{device_id}.json").write_text(
            json.dumps(status), encoding="utf-8"
        )

        runtime = PcWorkerRuntime(plane.paths.root, device_id=device_id)
        runtime.cua = MagicMock()
        runtime.cua.available.return_value = True
        runtime.cua.status_text.return_value = "running"
        runtime.cua.call.side_effect = lambda tool, args=None: {
            "ok": True,
            "tool": tool,
            "args": args or {},
            "pid": 42,
            "apps": [{"name": "Notepad"}],
            "_legacy_windows": [{"title": "Untitled - Notepad"}],
        }

        # worker processes grant in background after post
        def worker():
            time.sleep(0.2)
            runtime.heartbeat(online=True)
            runtime.process_inbox_once()

        th = threading.Thread(target=worker, daemon=True)
        th.start()
        result = plane.run_named_app_task(
            task_id="t2",
            owner_id="owner",
            device_id=device_id,
            app="Notepad",
            timeout_seconds=10,
        )
        th.join(timeout=5)
        self.assertTrue(result.get("ok"), result)

        # replay rejected
        consumer = GrantConsumer(plane.paths.consumed, device_id)
        # craft envelope from inbox done/archive or re-issue and consume twice
        signed = plane.issuer.issue(
            GrantRequest(
                task_id="t3",
                action_id="a3",
                owner_id="owner",
                device_id=device_id,
                app="Notepad",
                window="",
                action_class="cua_run",
                parameter_digest="p",
            )
        )
        env = encode_signed_grant(signed, plane.identity)
        consumer.verify_and_consume(env)
        with self.assertRaises(GrantError):
            consumer.verify_and_consume(env)

        # wrong app denied by runtime allow-list
        signed2 = plane.issuer.issue(
            GrantRequest(
                task_id="t4",
                action_id="a4",
                owner_id="owner",
                device_id=device_id,
                app="EvilAdminTool",
                window="",
                action_class="cua_run",
                parameter_digest="p",
            )
        )
        env2 = encode_signed_grant(signed2, plane.identity)
        denied = runtime.execute_grant(env2)
        self.assertFalse(denied.get("ok"))
        self.assertTrue(denied.get("fail_closed"))


if __name__ == "__main__":
    unittest.main()
