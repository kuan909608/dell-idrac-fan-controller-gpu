import json
import unittest
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from monitoring_web import (
    MonitoringServer,
    WebSettings,
    build_dashboard_html,
    build_status_snapshot,
)
from main import configure_hosts
from state import init_state_from_config, state


class RecordingController:
    def set_fan_control(self, mode, host):
        state[host["name"]]["fan_control_mode"] = mode


class MonitoringWebTests(unittest.TestCase):
    def test_default_binding_is_loopback_only(self):
        settings = WebSettings()

        self.assertEqual(settings.host, "127.0.0.1")

    def test_dashboard_uses_configured_refresh_interval_and_minimal_footer(self):
        dashboard = build_dashboard_html(7)

        self.assertIn('<footer id="refresh-status">AUTO REFRESH 7s</footer>', dashboard)
        self.assertIn("applyRefreshInterval(data.refresh_interval_seconds)", dashboard)
        self.assertIn("clearInterval(refreshTimer)", dashboard)
        self.assertIn("refreshTimer=setInterval(refresh,seconds*1000)", dashboard)
        self.assertNotIn("READ-ONLY //", dashboard)
        self.assertNotIn("LOCAL BINDING BY DEFAULT", dashboard)

    def test_dashboard_uses_unambiguous_fan_control_display(self):
        dashboard = build_dashboard_html(3)

        self.assertIn("metric('FAN',host.fan_display||'--')", dashboard)
        self.assertNotIn("host.fan_speed??'--'", dashboard)

    def test_status_snapshot_exposes_dashboard_refresh_interval(self):
        snapshot = build_status_snapshot({}, refresh_interval_seconds=7)

        self.assertEqual(snapshot["refresh_interval_seconds"], 7)

    def test_status_snapshot_distinguishes_fan_control_states(self):
        runtime_state = {
            "dry-run": {
                "dry_run": True,
                "fan_control_mode": "manual",
                "fan_speed": 20,
                "vms": {},
            },
            "idrac": {
                "dry_run": False,
                "fan_control_mode": "automatic",
                "fan_speed": 20,
                "vms": {},
            },
            "script": {
                "dry_run": False,
                "fan_control_mode": "manual",
                "fan_speed": 20,
                "vms": {},
            },
        }

        hosts = {
            host["name"]: host for host in build_status_snapshot(runtime_state)["hosts"]
        }

        self.assertEqual(hosts["dry-run"]["control_state"], "dry_run")
        self.assertEqual(hosts["idrac"]["control_state"], "idrac_auto")
        self.assertEqual(hosts["script"]["control_state"], "script_control")
        self.assertEqual(hosts["dry-run"]["fan_display"], "20% / DRY RUN")
        self.assertEqual(hosts["idrac"]["fan_display"], "iDRAC AUTO")
        self.assertEqual(hosts["script"]["fan_display"], "20% / SCRIPT CONTROL")

    def test_host_configuration_exposes_dry_run_through_status_api(self):
        host = {
            "name": "node-a",
            "fan_control_mode": "manual",
            "temperatures": [40.0, 80.0],
            "speeds": [20, 80],
            "hysteresis": 2.0,
        }
        config = SimpleNamespace(general={"debug": True}, hosts=[host])
        init_state_from_config(config.hosts)

        configure_hosts(config, RecordingController())
        snapshot = build_status_snapshot(state)

        self.assertEqual(snapshot["hosts"][0]["control_state"], "dry_run")

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

    def test_status_snapshot_replaces_raw_remote_errors(self):
        runtime_state = {
            "node-a": {
                "sensor_status": "error",
                "last_error": "Authentication failed for password=must-not-leak",
                "vms": {},
            }
        }

        encoded = json.dumps(build_status_snapshot(runtime_state))

        self.assertIn("SSH authentication failed", encoded)
        self.assertNotIn("must-not-leak", encoded)

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

        for method in ("POST", "PUT", "PATCH", "DELETE"):
            request = Request(
                f"http://{host}:{port}/api/status", method=method, data=b"{}"
            )
            with self.subTest(method=method), self.assertRaises(HTTPError) as error:
                urlopen(request, timeout=2)
            self.assertEqual(error.exception.code, 405)

    def test_dashboard_renders_vm_status_update_time_and_error(self):
        server = MonitoringServer({}, WebSettings(host="127.0.0.1", port=0))
        server.start()
        self.addCleanup(server.stop)
        host, port = server.address

        with urlopen(f"http://{host}:{port}/", timeout=2) as response:
            dashboard = response.read().decode("utf-8")

        self.assertIn("vm.sensor_status", dashboard)
        self.assertIn("timestamp(vm.last_updated)", dashboard)
        self.assertIn("new Date(value)", dashboard)
        self.assertIn("date.toLocaleString", dashboard)
        self.assertIn("vm.last_error", dashboard)
        self.assertNotIn(".innerHTML", dashboard)


if __name__ == "__main__":
    unittest.main()
