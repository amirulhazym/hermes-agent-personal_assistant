import unittest

from scripts.web_operator.pc_protocol import ProtocolMessage, WorkerSession, WorkerState


class ProtocolTests(unittest.TestCase):
    def test_happy_path(self):
        s = WorkerSession()
        s.on_message(ProtocolMessage("hello", {"device_id": "pc1"}), 1.0)
        s.on_message(ProtocolMessage("authenticate", {"proof": "x"}), 2.0)
        s.on_message(ProtocolMessage("availability", {"online": True}), 3.0)
        self.assertEqual(s.state, WorkerState.AVAILABLE)
        s.on_message(ProtocolMessage("grant-accepted", {}), 4.0)
        self.assertEqual(s.state, WorkerState.BUSY)
        s.on_message(ProtocolMessage("result", {"ok": True}), 5.0)
        self.assertEqual(s.state, WorkerState.AVAILABLE)

    def test_unknown_message(self):
        with self.assertRaises(ValueError):
            ProtocolMessage("nope", {}).validate()


if __name__ == "__main__":
    unittest.main()
