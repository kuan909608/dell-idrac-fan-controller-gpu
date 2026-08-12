import sys
import unittest

from fan_controller import build_ipmi_control_command
from utils import configure_ssh_client, format_command, redact_mapping, run_command


class FakeSSHClient:
    def __init__(self):
        self.loaded_system_keys = False
        self.policy = None

    def load_system_host_keys(self):
        self.loaded_system_keys = True

    def set_missing_host_key_policy(self, policy):
        self.policy = policy


class FakeParamiko:
    class RejectPolicy:
        pass


class CommandSecurityTests(unittest.TestCase):
    def test_structured_local_arguments_are_not_interpreted_by_a_shell(self):
        untrusted_argument = "safe; printf injected"

        output, error = run_command(
            {},
            [
                sys.executable,
                "-c",
                "import sys; print(sys.argv[1])",
                untrusted_argument,
            ],
        )

        self.assertEqual(output, untrusted_argument)
        self.assertEqual(error, "")

    def test_ipmi_password_is_passed_via_stdin_and_is_safe_to_log(self):
        password = "secret-value-that-must-not-be-logged"
        host = {
            "name": "node-a",
            "fan_control_mode": "manual",
            "temperatures": [40, 80],
            "speeds": [20, 100],
            "hysteresis": 0,
            "ipmi_credentials": {
                "host": "192.0.2.10",
                "username": "admin",
                "password": password,
            },
        }
        command = build_ipmi_control_command(host, "manual")

        self.assertEqual(command.stdin_data, password + "\n")
        self.assertNotIn(password, command.argv)
        self.assertNotIn(password, format_command(command))

    def test_sensitive_config_values_are_redacted_recursively(self):
        config = {
            "name": "node-a",
            "ipmi_credentials": {"username": "admin", "password": "ipmi-secret"},
            "vms": [
                {
                    "ssh_credentials": {
                        "password": "ssh-secret",
                        "key_path": "/keys/id_rsa",
                    }
                }
            ],
        }

        redacted = redact_mapping(config)

        self.assertEqual(redacted["name"], "node-a")
        self.assertEqual(redacted["ipmi_credentials"]["password"], "***")
        self.assertEqual(redacted["vms"][0]["ssh_credentials"]["password"], "***")
        self.assertEqual(redacted["vms"][0]["ssh_credentials"]["key_path"], "***")

    def test_ssh_rejects_unknown_host_keys(self):
        client = FakeSSHClient()

        configure_ssh_client(client, FakeParamiko)

        self.assertTrue(client.loaded_system_keys)
        self.assertIsInstance(client.policy, FakeParamiko.RejectPolicy)


if __name__ == "__main__":
    unittest.main()
