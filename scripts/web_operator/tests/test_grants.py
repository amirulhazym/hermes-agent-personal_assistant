import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from scripts.web_operator.crypto import CryptoError, HostKeyStore
from scripts.web_operator.grants import GrantError, GrantIssuer, GrantRequest
from scripts.web_operator.storage import StateStore


class GrantTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.store = StateStore(self.root / "s.db")
        try:
            self.identity = HostKeyStore(self.root / "keys").load_or_create_identity()
            self.crypto_ok = True
        except CryptoError:
            self.crypto_ok = False

    def test_issue_and_verify(self):
        if not self.crypto_ok:
            self.skipTest("cryptography not installed")
        issuer = GrantIssuer(self.store, self.identity)
        now = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)
        signed = issuer.issue(
            GrantRequest(
                task_id="t1",
                action_id="a1",
                owner_id="o1",
                device_id="pc1",
                app="Brave",
                window="main",
                action_class="cua_run",
                parameter_digest="p1",
            ),
            now=now,
        )
        grant = issuer.verify(
            signed,
            public_key_bytes=self.identity.public_key_bytes,
            now=now + timedelta(seconds=1),
            expected_device_id="pc1",
        )
        self.assertEqual(grant.app, "Brave")
        with self.assertRaises(GrantError):
            issuer.verify(
                signed,
                public_key_bytes=self.identity.public_key_bytes,
                now=now + timedelta(seconds=10000),
            )


if __name__ == "__main__":
    unittest.main()
