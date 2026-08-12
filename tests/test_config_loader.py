import tempfile
import unittest
import math
from pathlib import Path

import yaml

from config_loader import Config, ConfigError


def load_config(document):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "fan_control_config.yaml"
        path.write_text(yaml.safe_dump(document), encoding="utf-8")
        return Config(str(path))


def base_host():
    return {
        "name": "node-a",
        "fan_control_mode": "manual",
        "temperatures": [40, 80],
        "speeds": [20, 100],
        "hysteresis": 5,
    }


class ConfigLoaderTests(unittest.TestCase):
    def test_web_settings_are_loaded_without_exposing_the_service_by_default(self):
        config = load_config(
            {
                "general": {"web_enabled": False, "web_host": "127.0.0.2", "web_port": 9090},
                "hosts": [base_host()],
            }
        )

        self.assertFalse(config.general["web_enabled"])
        self.assertEqual(config.general["web_host"], "127.0.0.2")
        self.assertEqual(config.general["web_port"], 9090)

    def test_rejects_fan_speeds_outside_ipmi_percentage_range(self):
        host = base_host()
        host["speeds"] = [20, 150]

        with self.assertRaises(ConfigError):
            load_config({"hosts": [host]})

    def test_rejects_non_finite_thresholds(self):
        host = base_host()
        host["temperatures"] = [40, math.nan]

        with self.assertRaises(ConfigError):
            load_config({"hosts": [host]})

    def test_rejects_empty_sensor_command(self):
        with self.assertRaises(ConfigError):
            load_config(
                {
                    "general": {"cpu_temperature_command": "  "},
                    "hosts": [base_host()],
                }
            )

    def test_ssh_private_key_does_not_require_a_password(self):
        host = base_host()
        host["ssh_credentials"] = {
            "host": "192.0.2.10",
            "username": "operator",
            "key_path": "/run/secrets/id_rsa",
        }

        config = load_config({"hosts": [host]})

        self.assertEqual(config.hosts[0]["ssh_credentials"]["key_path"], "/run/secrets/id_rsa")


if __name__ == "__main__":
    unittest.main()
