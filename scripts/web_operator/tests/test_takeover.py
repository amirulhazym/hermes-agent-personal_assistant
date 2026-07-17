import asyncio
import unittest

from scripts.web_operator.takeover import ObservationGate, TakeoverController, TakeoverError


class TakeoverTests(unittest.TestCase):
    def test_suspend_blocks_emit(self):
        gate = ObservationGate()
        ctrl = TakeoverController(gate, ttl_seconds=900)

        async def run():
            await ctrl.grant("t1")
            gate.assert_suspended("t1")
            with self.assertRaises(TakeoverError):
                gate.emit("t1", "screenshot", "secret")
            await ctrl.return_control("t1")
            gate.emit("t1", "screenshot", "ok")

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
