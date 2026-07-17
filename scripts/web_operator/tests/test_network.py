import unittest

from scripts.web_operator.network import DestinationError, DestinationGuard


def fake_resolve(host, port, type=None):
    mapping = {
        "example.com": [("af", "sock", "proto", "canon", ("93.184.216.34", port))],
        "localhost": [("af", "sock", "proto", "canon", ("127.0.0.1", port))],
        "metadata.google.internal": [("af", "sock", "proto", "canon", ("169.254.169.254", port))],
    }
    if host not in mapping:
        raise OSError("nxdomain")
    return mapping[host]


class NetworkTests(unittest.TestCase):
    def setUp(self):
        self.guard = DestinationGuard(resolve=fake_resolve)

    def test_public_ok(self):
        t = self.guard.validate_url("https://example.com/path")
        self.assertEqual(t.host, "example.com")

    def test_loopback_blocked(self):
        with self.assertRaises(DestinationError):
            self.guard.validate_url("http://localhost/admin")

    def test_file_scheme_blocked(self):
        with self.assertRaises(DestinationError):
            self.guard.validate_url("file:///etc/passwd")

    def test_userinfo_blocked(self):
        with self.assertRaises(DestinationError):
            self.guard.validate_url("https://user:pass@example.com/")

    def test_redirect_to_private_blocked(self):
        prev = self.guard.validate_url("https://example.com/")
        with self.assertRaises(DestinationError):
            self.guard.validate_redirect(prev, "http://127.0.0.1/")

    def test_normalize_strips_query(self):
        n = self.guard.normalize_for_artifact("https://example.com/a?token=secret#x")
        self.assertNotIn("token", n)
        self.assertNotIn("#", n)


if __name__ == "__main__":
    unittest.main()
