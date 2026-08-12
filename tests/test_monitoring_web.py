import json
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from monitoring_web import MonitoringServer, WebSettings, build_status_snapshot


class MonitoringWebTests(unittest.TestCase):
    def test_default_binding_is_loopback_only(self):
        settings = WebSettings()

        self.assertEqual(settings.host, "127.0.0.1")

    def test_status_snapshot_exposes_health_without_credentials(self):
        runtime_state = {
            "node-a": {
                "fan_control_mode": "manual",
                "fan_speed": 35,
                "cpu_temps": [42.0, 48.0],
                "gpu_temps": [55.0],
                "control_temperature": 55.0,
                "sensor_status": "ok",
                "last_error": None,
                "last_updated": "2026-08-12T10:00:00+08:00",
                "ipmi_credentials": {"password": "must-not-leak"},
                "vms": {},
            }
        }

        snapshot = build_status_snapshot(runtime_state)
        encoded = json.dumps(snapshot)

        self.assertEqual(snapshot["hosts"][0]["name"], "node-a")
        self.assertEqual(snapshot["hosts"][0]["gpu_temps"], [55.0])
        self.assertNotIn("must-not-leak", encoded)
        self.assertNotIn("ipmi_credentials", encoded)

    def test_status_snapshot_marks_old_sensor_data_as_stale(self):
        runtime_state = {
            "node-a": {
                "sensor_status": "ok",
                "last_updated": "2020-01-01T00:00:00+00:00",
                "vms": {},
            }
        }

        snapshot = build_status_snapshot(runtime_state, stale_after_seconds=180)

        self.assertEqual(snapshot["hosts"][0]["sensor_status"], "stale")

    def test_server_is_read_only(self):
        server = MonitoringServer({}, WebSettings(host="127.0.0.1", port=0))
        server.start()
        self.addCleanup(server.stop)
        host, port = server.address

        with urlopen(f"http://{host}:{port}/api/status", timeout=2) as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(json.load(response)["hosts"], [])

        request = Request(f"http://{host}:{port}/api/status", method="POST", data=b"{}")
        with self.assertRaises(HTTPError) as error:
            urlopen(request, timeout=2)
        self.assertEqual(error.exception.code, 405)


if __name__ == "__main__":
    unittest.main()
