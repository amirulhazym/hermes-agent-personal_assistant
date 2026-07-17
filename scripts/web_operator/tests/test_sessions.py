import tempfile
import unittest
from pathlib import Path

from scripts.web_operator.contracts import SessionIdentity
from scripts.web_operator.crypto import CryptoError, HostKeyStore
from scripts.web_operator.sessions import SessionError, SessionStore
from scripts.web_operator.storage import StateStore


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.store = StateStore(self.root / "s.db")
        try:
            self.keys = HostKeyStore(self.root / "keys")
            self.keys.load_or_create_identity()
            self.keys.load_or_create_data_key()
            self.crypto_ok = True
        except CryptoError:
            self.crypto_ok = False

    def test_enroll_acquire_revoke(self):
        if not self.crypto_ok:
            self.skipTest("cryptography not installed")
        sessions = SessionStore(self.store, self.keys, self.root / "profiles")
        identity = SessionIdentity(
            site="example.com", account="a1", profile="default", execution_device="vps"
        )
        sessions.enroll(identity, mode="persistent", profile_bytes=b"cookies")
        lease = sessions.acquire(identity)
        self.assertTrue(lease.locked)
        with self.assertRaises(SessionError):
            sessions.acquire(identity)
        sessions.release(lease)
        proof = sessions.revoke(identity)
        self.assertEqual(proof["profile_deleted"], "true")

    def test_financial_forbidden(self):
        if not self.crypto_ok:
            self.skipTest("cryptography not installed")
        sessions = SessionStore(self.store, self.keys, self.root / "profiles")
        identity = SessionIdentity(site="bank.example", account="x", execution_device="vps")
        with self.assertRaises(SessionError):
            sessions.enroll(identity, financial=True)


if __name__ == "__main__":
    unittest.main()
