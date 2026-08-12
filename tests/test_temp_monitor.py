import unittest
from types import SimpleNamespace
from unittest.mock import patch

from temp_monitor import TempMonitor


class TempMonitorTests(unittest.TestCase):
    def test_vm_gpu_reading_returns_ssh_authentication_error(self):
        config = SimpleNamespace(
            general={
                "debug": False,
                "gpu_temperature_command_nvidia": "nvidia-smi",
                "gpu_temperature_command_amd": "rocm-smi",
            }
        )
        host = {
            "name": "host1",
            "vms": [
                {
                    "name": "vm1",
                    "gpu_type": ["nvidia"],
                    "ssh_credentials": {
                        "host": "vm.example",
                        "username": "monitor",
                        "password": "secret",
                    },
                }
            ],
        }

        with patch(
            "temp_monitor.run_command",
            return_value=(None, "Authentication failed."),
        ):
            temperatures, error = TempMonitor(config).get_gpu_temps(host, "vm1")

        self.assertIsNone(temperatures)
        self.assertEqual(error, "Authentication failed.")


if __name__ == "__main__":
    unittest.main()
