import unittest

from control_policy import SensorSnapshot, determine_control_temperature


class DetermineControlTemperatureTests(unittest.TestCase):
    def test_max_mode_uses_cpu_when_no_gpu_is_present(self):
        snapshot = SensorSnapshot(cpu_temps=[41.0, 52.5], gpu_temps=[])

        result = determine_control_temperature(snapshot, mode="max")

        self.assertEqual(result.control_temperature, 52.5)
        self.assertFalse(result.fail_safe)

    def test_missing_cpu_data_activates_fail_safe(self):
        snapshot = SensorSnapshot(cpu_temps=None, gpu_temps=[48.0])

        result = determine_control_temperature(snapshot, mode="max")

        self.assertEqual(result.control_temperature, 999.0)
        self.assertTrue(result.fail_safe)

    def test_failed_configured_gpu_source_activates_fail_safe(self):
        snapshot = SensorSnapshot(
            cpu_temps=[45.0], gpu_temps=[], gpu_sources_healthy=False
        )

        result = determine_control_temperature(snapshot, mode="max")

        self.assertEqual(result.control_temperature, 999.0)
        self.assertTrue(result.fail_safe)


if __name__ == "__main__":
    unittest.main()
