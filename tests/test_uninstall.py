from pathlib import Path
import os
import stat
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class UninstallScriptTests(unittest.TestCase):
    def _write_command(self, directory, name, body):
        command = directory / name
        command.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
        command.chmod(command.stat().st_mode | stat.S_IXUSR)

    def test_missing_installation_is_an_idempotent_success(self):
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            removal_log = temp / "removals"
            self._write_command(temp, "whoami", "echo root")
            self._write_command(
                temp,
                "systemctl",
                'if [ "$1" = "is-active" ]; then exit 1; fi\nexit 0',
            )
            self._write_command(temp, "rm", f'echo "$*" >> "{removal_log}"')

            env = os.environ.copy()
            env["PATH"] = f"{temp}:{env['PATH']}"
            result = subprocess.run(
                ["bash", str(ROOT / "uninstall.sh"), "/opt/fan-control-test"],
                capture_output=True,
                text=True,
                check=False,
                env=env,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(removal_log.exists())
            self.assertIn("already uninstalled", result.stdout)


if __name__ == "__main__":
    unittest.main()
