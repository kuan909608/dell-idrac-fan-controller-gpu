import os
import tempfile
import unittest
from pathlib import Path

import yaml

from config_loader import Config, ConfigError, ConfigWatcher
from main import apply_config_reload
from state import state


def document(host_name="node-a", mode="manual", interval=60):
    return {
        "general": {"debug": True, "interval": interval, "web_enabled": False},
        "hosts": [
            {
                "name": host_name,
                "fan_control_mode": mode,
                "temperatures": [40, 80],
                "speeds": [20, 80],
                "hysteresis": 5,
            }
        ],
    }


class RecordingController:
    def __init__(self, config, fail_restore=False):
        self.config = config
        self.fail_restore = fail_restore
        self.calls = []

    def set_fan_control(self, mode, host):
        self.calls.append((mode, host["name"]))
        if self.fail_restore and mode == "automatic" and host["name"] == "node-a":
            return False
        return True


class RecordingMonitor:
    def __init__(self, config):
        self.config = config


class ConfigReloadTests(unittest.TestCase):
    def write(self, path, value):
        path.write_text(yaml.safe_dump(value), encoding="utf-8")
        stat = path.stat()
        os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000))

    def test_watcher_returns_a_validated_candidate_after_change(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fan_control_config.yaml"
            self.write(path, document(interval=60))
            watcher = ConfigWatcher(str(path))

            self.assertIsNone(watcher.load_if_changed())
            self.write(path, document(interval=5))

            candidate = watcher.load_if_changed()
            self.assertEqual(candidate.general["interval"], 5)
            self.assertIsNone(watcher.load_if_changed())

    def test_invalid_change_is_rejected_without_mutating_active_config(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fan_control_config.yaml"
            self.write(path, document(interval=60))
            active = Config(str(path))
            watcher = ConfigWatcher(str(path))
            self.write(path, {"general": {"interval": -1}, "hosts": []})

            with self.assertRaises(ConfigError):
                watcher.load_if_changed()

            self.assertEqual(active.general["interval"], 60)
            self.assertEqual(active.hosts[0]["name"], "node-a")
            self.assertIsNone(watcher.load_if_changed())

    def test_reload_restores_old_manual_host_before_applying_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fan_control_config.yaml"
            self.write(path, document())
            active = Config(str(path))
            self.write(path, document(host_name="node-b", mode="automatic", interval=5))
            candidate = Config(str(path))
            controller = RecordingController(active)
            monitor = RecordingMonitor(active)

            applied = apply_config_reload(active, candidate, controller, monitor)

            self.assertTrue(applied)
            self.assertEqual(
                controller.calls,
                [("automatic", "node-a"), ("automatic", "node-b")],
            )
            self.assertEqual(active.hosts[0]["name"], "node-b")
            self.assertEqual(active.general["interval"], 5)
            self.assertIs(controller.config, active)
            self.assertIs(monitor.config, active)
            self.assertEqual(list(state), ["node-b"])

    def test_reload_is_rejected_when_old_manual_mode_cannot_be_restored(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fan_control_config.yaml"
            self.write(path, document())
            active = Config(str(path))
            self.write(path, document(host_name="node-b"))
            candidate = Config(str(path))
            controller = RecordingController(active, fail_restore=True)
            monitor = RecordingMonitor(active)

            applied = apply_config_reload(active, candidate, controller, monitor)

            self.assertFalse(applied)
            self.assertEqual(active.hosts[0]["name"], "node-a")
            self.assertIs(controller.config, active)
            self.assertEqual(
                controller.calls,
                [("automatic", "node-a"), ("manual", "node-a")],
            )


if __name__ == "__main__":
    unittest.main()
