from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class PackagingContractTests(unittest.TestCase):
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

    def test_installer_copies_the_complete_runtime_and_canonical_config(self):
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")

        for filename in self.runtime_files:
            self.assertIn(filename, installer)
        self.assertIn("fan_control_config.yaml.example", installer)
        self.assertNotIn("fan_control.yaml.example", installer)
        self.assertIn('SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")"', installer)
        self.assertIn('touch "$TARGETDIR/.fan-control-installation"', installer)

    def test_clean_installed_runtime_can_import_its_startup_module(self):
        with tempfile.TemporaryDirectory() as directory:
            install_root = Path(directory)
            for filename in self.runtime_files:
                shutil.copy2(ROOT / filename, install_root / filename)
            shutil.copy2(
                ROOT / "fan_control_config.yaml.example",
                install_root / "fan_control_config.yaml",
            )

            result = subprocess.run(
                [sys.executable, "-c", "import main"],
                cwd=install_root,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)

    def test_installer_uses_runtime_packages_and_pinned_python_dependencies(self):
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

        for package in ["python3-venv", "lm-sensors", "ipmitool"]:
            self.assertIn(package, installer)
        for obsolete_package in ["python3-virtualenv", "libsensors4-dev"]:
            self.assertNotIn(obsolete_package, installer)

        dependency_lines = [
            line for line in requirements.splitlines() if line and not line.startswith("#")
        ]
        self.assertTrue(dependency_lines)
        for dependency in dependency_lines:
            self.assertRegex(dependency, r"^[A-Za-z0-9_.-]+==[^=]+$")

    def test_online_installer_only_bootstraps_the_repository_installer(self):
        bootstrap = (ROOT / "install-online.sh").read_text(encoding="utf-8")

        self.assertIn('readonly VERSION="v1.1.0-rc.3"', bootstrap)
        self.assertIn(
            "https://github.com/$REPOSITORY/archive/$VERSION.tar.gz", bootstrap
        )
        self.assertIn("--proto '=https'", bootstrap)
        self.assertIn('bash "$source_dir/install.sh" "$TARGETDIR"', bootstrap)
        self.assertNotIn('exec bash "$source_dir/install.sh"', bootstrap)
        self.assertNotIn("apt-get install", bootstrap)
        self.assertNotIn("systemctl", bootstrap)

    def test_uninstaller_stops_service_before_removing_owned_files(self):
        uninstaller = (ROOT / "uninstall.sh").read_text(encoding="utf-8")

        stop_position = uninstaller.index("systemctl stop fan-control.service")
        target_removal_position = uninstaller.index('rm -rf -- "$TARGETDIR"')
        unit_removal_position = uninstaller.index('rm -f -- "$UNIT_PATH"')

        self.assertLess(stop_position, target_removal_position)
        self.assertLess(stop_position, unit_removal_position)
        self.assertIn("systemctl is-active --quiet fan-control.service", uninstaller)
        self.assertIn(
            '[[ ! "$TARGETDIR" =~ ^/opt/[A-Za-z0-9][A-Za-z0-9._-]*$ ]]',
            uninstaller,
        )
        self.assertIn('$TARGETDIR/.fan-control-installation', uninstaller)
        self.assertIn('grep -Fqx "WorkingDirectory=$TARGETDIR" "$UNIT_PATH"', uninstaller)
        for shared_package in ["python3-venv", "lm-sensors", "ipmitool"]:
            self.assertNotIn(f"remove {shared_package}", uninstaller)

    def test_online_uninstaller_only_bootstraps_the_repository_uninstaller(self):
        bootstrap = (ROOT / "uninstall-online.sh").read_text(encoding="utf-8")

        self.assertIn('readonly VERSION="v1.1.0-rc.3"', bootstrap)
        self.assertIn(
            "https://github.com/$REPOSITORY/archive/$VERSION.tar.gz", bootstrap
        )
        self.assertIn("--proto '=https'", bootstrap)
        self.assertIn('bash "$source_dir/uninstall.sh" "$TARGETDIR"', bootstrap)
        self.assertNotIn("systemctl", bootstrap)
        self.assertNotIn("rm -rf -- /opt", bootstrap)

    def test_installer_restricts_the_root_owned_install_target(self):
        installer = (ROOT / "install.sh").read_text(encoding="utf-8")

        self.assertIn(
            '[[ ! "$TARGETDIR" =~ ^/opt/[A-Za-z0-9][A-Za-z0-9._-]*$ ]]',
            installer,
        )

    def test_docker_build_context_excludes_local_secrets(self):
        dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")

        for pattern in ["fan_control_config.yaml", "keys/", ".git/", ".env", "venv/"]:
            self.assertIn(pattern, dockerignore)

    def test_docker_uses_a_directory_mounted_reloadable_config(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("ENV FAN_CONTROL_CONFIG=/config/fan_control_config.yaml", dockerfile)
        self.assertIn('-v "./config:/config:ro"', readme)

    def test_docker_image_copies_only_runtime_files(self):
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

        self.assertNotIn("COPY . .", dockerfile)
        for filename in self.runtime_files:
            self.assertIn(filename, dockerfile)

    def test_ci_builds_and_import_checks_the_docker_image(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("docker build", workflow)
        self.assertIn("import main", workflow)
        self.assertIn(
            "bash -n install.sh install-online.sh uninstall.sh uninstall-online.sh",
            workflow,
        )

    def test_compose_uses_safe_controller_lifecycle_and_mounts(self):
        compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

        for expected in [
            '"127.0.0.1:8080:8080"',
            "./config:/config:ro",
            "./keys:/app/keys:ro",
            "known_hosts:/root/.ssh/known_hosts:ro",
            "restart: unless-stopped",
            "stop_grace_period: 30s",
        ]:
            self.assertIn(expected, compose)

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
            "Environment=FAN_CONTROL_CONFIG={TARGETDIR}/fan_control_config.yaml",
        ]:
            self.assertIn(directive, service)


if __name__ == "__main__":
    unittest.main()
