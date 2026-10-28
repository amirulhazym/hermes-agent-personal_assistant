import unittest
from unittest import mock


class MemoryWatchHysteresisModel:
    """Mathematical and stateful model of memory alert hysteresis.

    Designed for memory health checks to avoid alerting when MemAvailable oscillates
    near a single static threshold.
    """

    def __init__(
        self,
        *,
        critical_mb: float = 300.0,
        warning_mb: float = 450.0,
        recovery_mb: float = 550.0,
        consecutive_required: int = 2,
    ):
        self.critical_mb = critical_mb
        self.warning_mb = warning_mb
        self.recovery_mb = recovery_mb
        self.consecutive_required = consecutive_required
        self.state = "HEALTHY"
        self.warning_count = 0
        self.recovery_count = 0

    def evaluate_sample(self, avail_mb: float) -> tuple[str, bool]:
        """Evaluate a MemAvailable sample (MB).

        Returns: (current_state, should_notify_transition)
        """
        if avail_mb <= self.critical_mb:
            self.recovery_count = 0
            if self.state != "CRITICAL":
                self.state = "CRITICAL"
                return self.state, True
            return self.state, False

        if avail_mb <= self.warning_mb:
            self.recovery_count = 0
            self.warning_count += 1
            if self.state == "HEALTHY" and self.warning_count >= self.consecutive_required:
                self.state = "WARNING"
                return self.state, True
            return self.state, False

        # Above warning threshold
        self.warning_count = 0
        if self.state in {"WARNING", "CRITICAL"}:
            if avail_mb >= self.recovery_mb:
                self.recovery_count += 1
                if self.recovery_count >= self.consecutive_required:
                    self.state = "HEALTHY"
                    return self.state, True
            else:
                self.recovery_count = 0
        return self.state, False


class MemoryHysteresisCandidateTests(unittest.TestCase):
    def test_single_dip_does_not_trigger_warning(self):
        model = MemoryWatchHysteresisModel(warning_mb=450.0, recovery_mb=550.0, consecutive_required=2)
        state, notified = model.evaluate_sample(440.0)  # Dip
        self.assertEqual(state, "HEALTHY")
        self.assertFalse(notified)

        state, notified = model.evaluate_sample(520.0)  # Back up, but not full recovery
        self.assertEqual(state, "HEALTHY")
        self.assertFalse(notified)

    def test_sustained_low_triggers_warning_after_required_consecutive_ticks(self):
        model = MemoryWatchHysteresisModel(warning_mb=450.0, recovery_mb=550.0, consecutive_required=2)
        model.evaluate_sample(440.0)
        state, notified = model.evaluate_sample(430.0)
        self.assertEqual(state, "WARNING")
        self.assertTrue(notified)

        # Still low: no duplicate transition notification
        state, notified = model.evaluate_sample(435.0)
        self.assertEqual(state, "WARNING")
        self.assertFalse(notified)

    def test_flapping_near_boundary_does_not_oscillate_state(self):
        # Oscillate between 440 and 460
        model = MemoryWatchHysteresisModel(warning_mb=450.0, recovery_mb=550.0, consecutive_required=2)
        notifications = []
        for val in [440.0, 460.0, 440.0, 460.0, 440.0, 460.0]:
            _, notified = model.evaluate_sample(val)
            if notified:
                notifications.append(val)
        self.assertEqual(notifications, [], "Oscillations around threshold must not fire notifications")

    def test_recovery_requires_reaching_recovery_band_consecutively(self):
        model = MemoryWatchHysteresisModel(warning_mb=450.0, recovery_mb=550.0, consecutive_required=2)
        model.evaluate_sample(440.0)
        model.evaluate_sample(430.0)  # In WARNING
        self.assertEqual(model.state, "WARNING")

        # Rises to 510MB (above warning 450, but below recovery 550) -> stays WARNING
        state, notified = model.evaluate_sample(510.0)
        self.assertEqual(state, "WARNING")
        self.assertFalse(notified)

        # Rises to 560MB (1st recovery tick) -> stays WARNING
        state, notified = model.evaluate_sample(560.0)
        self.assertEqual(state, "WARNING")
        self.assertFalse(notified)

        # Rises to 570MB (2nd recovery tick) -> transitions to HEALTHY
        state, notified = model.evaluate_sample(570.0)
        self.assertEqual(state, "HEALTHY")
        self.assertTrue(notified)

    def test_critical_memory_triggers_immediately_without_waiting(self):
        model = MemoryWatchHysteresisModel(critical_mb=300.0, warning_mb=450.0, consecutive_required=2)
        state, notified = model.evaluate_sample(250.0)
        self.assertEqual(state, "CRITICAL")
        self.assertTrue(notified)


if __name__ == "__main__":
    unittest.main()
