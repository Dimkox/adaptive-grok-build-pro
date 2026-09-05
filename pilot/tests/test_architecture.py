from __future__ import annotations

from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / ".grok-stack"))

from adaptive_grok.architecture import load_architecture  # noqa: E402


class PilotArchitectureTests(unittest.TestCase):
    def test_pilot_has_separate_trust_domains_and_factory_has_no_external_edge(self) -> None:
        snapshot = load_architecture(ROOT)
        domains = {item["id"]: item for item in snapshot.system["trust_domains"]}
        nodes = {item["id"]: item for item in snapshot.system["nodes"]}
        edges = {item["id"]: item for item in snapshot.system["edges"]}

        self.assertEqual(domains["TD-PILOT-OPERATOR"]["kind"], "local_preflight")
        self.assertEqual(domains["TD-PILOT-EXECUTION"]["kind"], "local_preflight")
        for node in (
            "NODE-PILOT-CONTROL",
            "NODE-PILOT-SQLITE",
            "NODE-PILOT-GITHUB-BROKER",
            "NODE-PILOT-CODEX-SUPERVISOR",
            "NODE-PILOT-SANDBOX",
        ):
            self.assertIn(node, nodes)
            self.assertTrue(any(path == "pilot" or path.startswith("pilot/") for path in nodes[node]["repository_paths"]))

        self.assertEqual(edges["EDGE-PILOT-GITHUB"]["from"], "NODE-PILOT-GITHUB-BROKER")
        self.assertEqual(edges["EDGE-PILOT-CODEX"]["from"], "NODE-PILOT-CODEX-SUPERVISOR")
        self.assertIn("pilot/live.py", nodes["NODE-PILOT-CONTROL"]["repository_paths"])
        self.assertTrue(
            {"pilot/live_github.py", "pilot/runtime_authority.py"}
            <= set(nodes["NODE-PILOT-GITHUB-BROKER"]["repository_paths"])
        )
        for edge in edges.values():
            source = nodes[edge["from"]]
            target = nodes[edge["to"]]
            self.assertFalse(
                source["trust_domain"] == "TD-FACTORY-CONTROL"
                and target["trust_domain"] in {"TD-EXTERNAL-PLATFORM", "TD-PRODUCTION-TRUST"},
                edge["id"],
            )

    def test_all_five_pilot_contracts_are_in_the_executable_inventory(self) -> None:
        snapshot = load_architecture(ROOT)
        contracts = {item["id"]: item for item in snapshot.system["contracts"]}
        expected = {
            "CONTRACT-PILOT-ISSUE-SNAPSHOT",
            "CONTRACT-PILOT-CANDIDATE-CHANGE",
            "CONTRACT-PILOT-CANDIDATE-VALIDATION",
            "CONTRACT-PILOT-PULL-REQUEST-PROPOSAL",
            "CONTRACT-PILOT-DESIGN-PARTNER-OUTCOME",
        }
        self.assertEqual(expected - contracts.keys(), set())
        for contract_id in expected:
            self.assertEqual(contracts[contract_id]["kind"], "json_schema")
            self.assertTrue(contracts[contract_id]["path"].startswith("pilot/contracts/jsonschema/"))


if __name__ == "__main__":
    unittest.main()
