import re
import unittest
from pathlib import Path
from urllib.parse import unquote

import yaml


ROOT = Path(__file__).resolve().parents[1]


class DocumentationIntegrityTests(unittest.TestCase):
    def test_local_markdown_links_resolve(self):
        link_pattern = re.compile(r"(?<!!)\[[^\]]*\]\(([^)]+)\)")

        for document in ROOT.rglob("*.md"):
            if any(part in {".git", ".venv"} for part in document.parts):
                continue
            for target in link_pattern.findall(document.read_text(encoding="utf-8")):
                target = target.split()[0].strip("<>")
                if target.startswith(("https://", "http://", "mailto:", "#")):
                    continue
                relative_path = unquote(target.partition("#")[0])
                with self.subTest(document=document.name, target=target):
                    self.assertTrue((document.parent / relative_path).exists())

    def test_readmes_cover_the_same_core_capabilities(self):
        readmes = [
            (ROOT / "README.md").read_text(encoding="utf-8"),
            (ROOT / "README.zh-TW.md").read_text(encoding="utf-8"),
        ]
        capabilities = [
            "Proxmox VE",
            "NVIDIA",
            "AMD",
            "Docker",
            "systemd",
            "Fail-safe",
            "Web monitoring",
            "runtime configuration reload",
            "nmaggioni/r710-fan-controller",
        ]

        for capability in capabilities:
            for readme in readmes:
                with self.subTest(capability=capability):
                    self.assertIn(capability.lower(), readme.lower())

    def test_architecture_mermaid_includes_required_control_path(self):
        architecture = (ROOT / "ARCHITECTURE.md").read_text(encoding="utf-8")

        self.assertEqual(architecture.count("```mermaid"), 1)
        for label in [
            "CPU Sensor",
            "Host NVIDIA / AMD GPU Sensor",
            "VM GPU Sensor",
            "Temperature Aggregation",
            "Control Policy",
            "Fail-safe",
            "Fan Curve",
            "IPMI",
            "Dell iDRAC",
        ]:
            with self.subTest(label=label):
                self.assertIn(label, architecture)

    def test_issue_forms_are_valid_yaml_with_unique_field_ids(self):
        forms = ROOT / ".github" / "ISSUE_TEMPLATE"

        for path in forms.glob("*.yml"):
            document = yaml.safe_load(path.read_text(encoding="utf-8"))
            if path.name == "config.yml":
                continue
            ids = [item["id"] for item in document.get("body", []) if "id" in item]
            with self.subTest(path=path.name):
                self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
