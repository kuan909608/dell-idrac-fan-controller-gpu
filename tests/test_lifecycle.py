import unittest

from lifecycle import restore_automatic_control


class RecordingController:
    def __init__(self, failing_hosts=None):
        self.calls = []
        self.failing_hosts = set(failing_hosts or [])

    def set_fan_control(self, mode, host):
        self.calls.append((mode, host["name"]))
        if host["name"] in self.failing_hosts:
            raise RuntimeError("IPMI unavailable")


class RestoreAutomaticControlTests(unittest.TestCase):
    def test_attempts_every_manual_host_even_after_one_failure(self):
        controller = RecordingController(failing_hosts={"node-a"})
        hosts = [
            {"name": "node-a", "fan_control_mode": "manual"},
            {"name": "node-b", "fan_control_mode": "manual"},
            {"name": "node-c", "fan_control_mode": "automatic"},
        ]

        failures = restore_automatic_control(controller, hosts, logger=None)

        self.assertEqual(
            controller.calls,
            [("automatic", "node-a"), ("automatic", "node-b")],
        )
        self.assertEqual(failures, ["node-a"])


if __name__ == "__main__":
    unittest.main()
