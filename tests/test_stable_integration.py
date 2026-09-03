from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class StableIntegrationContractTest(unittest.TestCase):
    def test_units_are_inert_and_no_github_actions_exist(self) -> None:
        service = (ROOT / "systemd/adaptive-stable-synthesis.service").read_text()
        timer = (ROOT / "systemd/adaptive-stable-synthesis.timer").read_text()
        self.assertNotIn("WantedBy", service + timer)
        self.assertNotIn("Authorization", service)
        self.assertIn("ReadWritePaths=-/opt/adaptive-grok-build-pro/.grok-stack/runtime\n", service)
        self.assertNotIn("ReadWritePaths=-/opt/adaptive-grok-build-pro/.grok-stack/runtime/stable-synthesis", service)
        self.assertFalse((ROOT / ".github/workflows").exists())

    def test_architecture_declares_only_read_only_github_monitor_edge(self) -> None:
        import json
        model = json.loads((ROOT / "architecture/system.yaml").read_text())
        node = next(item for item in model["nodes"] if item["id"] == "NODE-STABLE-SYNTHESIS-MONITOR")
        self.assertEqual(node["secrets"], [])
        edges = [edge for edge in model["edges"] if edge["from"] == node["id"]]
        self.assertEqual([edge["id"] for edge in edges], ["EDGE-STABLE-SYNTHESIS-GITHUB-READ"])
        self.assertEqual(edges[0]["to"], "NODE-GITHUB")
        self.assertEqual(edges[0]["network_policy"], "allowlisted_egress")

    def test_installer_carries_local_contract_and_cli_but_not_timer_activation(self) -> None:
        import runpy
        module = runpy.run_path(str(ROOT / "scripts/install_into.py"))
        self.assertIn("engineering/stable-synthesis/stable-synthesis-upstreams.v1.json", module["MANAGED_FILES"])
        self.assertIn("engineering/contracts/schemas/stable-synthesis-upstreams.v1.schema.json", module["MANAGED_FILES"])
        self.assertIn("scripts/grok_stable_synthesis.py", module["MANAGED_FILES"])
        self.assertNotIn("systemd", module["MANAGED_DIRS"])


if __name__ == "__main__":
    unittest.main()
