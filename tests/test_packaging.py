from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackagingContractTests(unittest.TestCase):
    def test_installer_copies_the_complete_runtime_and_canonical_config(self):
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        runtime_files = [
            "main.py",
            "config_loader.py",
            "control_policy.py",
            "fan_controller.py",
            "lifecycle.py",
            "monitoring_web.py",
            "state.py",
            "temp_monitor.py",
            "utils.py",
        ]

        for filename in runtime_files:
            self.assertIn(filename, installer)
        self.assertIn("fan_control_config.yaml.example", installer)
        self.assertNotIn("fan_control.yaml.example", installer)

    def test_docker_build_context_excludes_local_secrets(self):
        dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

        for pattern in ["fan_control_config.yaml", "keys/", ".git/", ".env", "venv/"]:
            self.assertIn(pattern, dockerignore)

    def test_docker_uses_a_directory_mounted_reloadable_config(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("ENV FAN_CONTROL_CONFIG=/config/fan_control_config.yaml", dockerfile)
        self.assertIn('-v "./config:/config:ro"', readme)

    def test_systemd_unit_applies_root_service_hardening(self):
        service = (ROOT / "fan-control.service").read_text(encoding="utf-8")

        for directive in [
            "NoNewPrivileges=true",
            "ProtectSystem=strict",
            "ProtectKernelTunables=true",
            "ProtectKernelModules=true",
            "ProtectControlGroups=true",
            "RestrictSUIDSGID=true",
            "LockPersonality=true",
        ]:
            self.assertIn(directive, service)


if __name__ == "__main__":
    unittest.main()
