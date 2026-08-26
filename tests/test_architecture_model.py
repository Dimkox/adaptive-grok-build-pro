from __future__ import annotations

import copy
import importlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / ".grok-stack"))


def _architecture_module():
    try:
        return importlib.import_module("adaptive_grok.architecture")
    except ModuleNotFoundError as exc:
        if exc.name != "adaptive_grok.architecture":
            raise
        return None


ARCH = _architecture_module()


def _system() -> dict:
    return {
        "schema_version": 1,
        "architecture_id": "ARCH-TEST",
        "trust_domains": [
            {"id": "TD-LOCAL", "kind": "local_preflight", "owner": "engineering"}
        ],
        "data_classifications": [
            {
                "id": "DATA-INTERNAL",
                "classification": "internal",
                "tenant_scoped": False,
                "contains_secret": False,
            }
        ],
        "secret_classes": [],
        "signals": [{"id": "SIG-EDGE-FAILURE", "description": "edge failure"}],
        "contracts": [],
        "nodes": [
            {
                "id": "NODE-A",
                "type": "local_component",
                "owner": "engineering",
                "trust_domain": "TD-LOCAL",
                "data_classification": "DATA-INTERNAL",
                "secrets": [],
                "runtime": {
                    "kind": "python_process",
                    "lifecycle": "on_demand",
                    "network": "none",
                    "evidence": "source_described",
                },
                "repository_paths": [],
                "public_contracts": [],
            },
            {
                "id": "NODE-B",
                "type": "repository",
                "owner": "engineering",
                "trust_domain": "TD-LOCAL",
                "data_classification": "DATA-INTERNAL",
                "secrets": [],
                "runtime": {
                    "kind": "none",
                    "lifecycle": "none",
                    "network": "none",
                    "evidence": "source_described",
                },
                "repository_paths": [],
                "public_contracts": [],
            },
        ],
        "edges": [
            {
                "id": "EDGE-A-B",
                "from": "NODE-A",
                "to": "NODE-B",
                "type": "dependency",
                "protocol": "filesystem",
                "direction": "from_to",
                "authentication": "local_os",
                "network_policy": "no_network",
                "sync_or_async": "synchronous",
                "allowed_data": ["DATA-INTERNAL"],
                "failure_behavior": {
                    "mode": "fail_closed",
                    "timeout_ms": 1000,
                    "max_retries": 0,
                    "idempotency": "not_required",
                    "correlation_id": "not_required",
                    "terminal_action": "reject",
                    "observable_signal": "SIG-EDGE-FAILURE",
                },
            }
        ],
    }


def _rules() -> dict:
    return {
        "schema_version": 1,
        "architecture_id": "ARCH-TEST",
        "forbidden_edges": [],
        "path_boundaries": [],
        "contract_policies": [],
        "migration_policies": [],
        "tenant_authorization_policies": [],
        "network_policies": [],
        "change_separation_policies": [],
        "code_budgets": [],
        "background_job_policies": [],
        "secret_flow_policies": [],
        "workspace_trust_policies": [],
        "risk_escalations": [],
    }


class ArchitectureModelTests(unittest.TestCase):
    def setUp(self) -> None:
        if ARCH is None:
            self.fail("adaptive_grok.architecture is not implemented")

    def _repo(self, system: dict | None = None, rules: dict | None = None):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / "architecture").mkdir()
        (root / "schemas").mkdir()
        for name in ("architecture-system.schema.json", "architecture-rules.schema.json"):
            (root / "schemas" / name).write_bytes((ROOT / "schemas" / name).read_bytes())
        self._write(root / "architecture/system.yaml", system or _system())
        self._write(root / "architecture/rules.yaml", rules or _rules())
        self.addCleanup(temp.cleanup)
        return root

    @staticmethod
    def _write(path: Path, value: dict) -> None:
        path.write_text(
            json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
            encoding="utf-8",
        )

    def test_valid_minimal_documents_load_and_validate(self) -> None:
        root = self._repo()
        snapshot = ARCH.load_architecture(root)
        self.assertEqual(snapshot.system["architecture_id"], "ARCH-TEST")
        self.assertEqual(snapshot.rules["architecture_id"], "ARCH-TEST")
        self.assertEqual(ARCH.validate_architecture(snapshot, root), ())

    def test_every_authoritative_object_is_closed_and_required(self) -> None:
        system = _system()
        rules = _rules()
        cases: list[tuple[str, dict, dict]] = []
        for key in tuple(system):
            changed = copy.deepcopy(system)
            del changed[key]
            cases.append((f"system root {key}", changed, rules))
        for key in tuple(system["nodes"][0]):
            changed = copy.deepcopy(system)
            del changed["nodes"][0][key]
            cases.append((f"node {key}", changed, rules))
        for key in tuple(system["nodes"][0]["runtime"]):
            changed = copy.deepcopy(system)
            del changed["nodes"][0]["runtime"][key]
            cases.append((f"runtime {key}", changed, rules))
        for key in tuple(system["edges"][0]):
            changed = copy.deepcopy(system)
            del changed["edges"][0][key]
            cases.append((f"edge {key}", changed, rules))
        for key in tuple(system["edges"][0]["failure_behavior"]):
            changed = copy.deepcopy(system)
            del changed["edges"][0]["failure_behavior"][key]
            cases.append((f"failure behavior {key}", changed, rules))
        for key in tuple(rules):
            changed = copy.deepcopy(rules)
            del changed[key]
            cases.append((f"rules root {key}", system, changed))
        for label, changed_system, changed_rules in cases:
            with self.subTest(label=label):
                root = self._repo(changed_system, changed_rules)
                with self.assertRaises(ARCH.ArchitectureError):
                    ARCH.load_architecture(root)

        system = _system()
        system["nodes"][0]["unknown"] = True
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(self._repo(system, _rules()))
        system = _system()
        system["edges"][0]["failure_behavior"]["unknown"] = True
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(self._repo(system, _rules()))
        rules = _rules()
        rules["unknown"] = True
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(self._repo(_system(), rules))

    def test_unknown_versions_and_non_from_to_direction_fail(self) -> None:
        for target in ("system", "rules"):
            system, rules = _system(), _rules()
            (system if target == "system" else rules)["schema_version"] = 2
            with self.subTest(target=target), self.assertRaises(ARCH.ArchitectureError):
                ARCH.load_architecture(self._repo(system, rules))
        system = _system()
        system["edges"][0]["direction"] = "bidirectional"
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(self._repo(system, _rules()))

    def test_duplicate_json_keys_and_ids_fail(self) -> None:
        root = self._repo()
        (root / "architecture/system.yaml").write_text(
            '{"schema_version":1,"schema_version":1}', encoding="utf-8"
        )
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(root)

        for collection in (
            "trust_domains",
            "data_classifications",
            "signals",
            "nodes",
            "edges",
        ):
            system = _system()
            system[collection].append(copy.deepcopy(system[collection][0]))
            with self.subTest(collection=collection), self.assertRaises(ARCH.ArchitectureError):
                ARCH.load_architecture(self._repo(system, _rules()))

        rules = _rules()
        rules["risk_escalations"] = [
            {
                "id": "FIT-DUPLICATE",
                "triggers": ["new_edge"],
                "risk": "yellow",
                "severity": "error",
            }
        ]
        rules["forbidden_edges"] = [
            {
                "id": "FIT-DUPLICATE",
                "from_trust_domains": ["TD-LOCAL"],
                "to_trust_domains": ["TD-LOCAL"],
                "edge_types": ["dependency"],
                "severity": "error",
            }
        ]
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(self._repo(_system(), rules))

    def test_unresolved_references_and_architecture_id_mismatch_fail(self) -> None:
        mutations = (
            ("node trust domain", lambda doc: doc["nodes"][0].update(trust_domain="TD-MISSING")),
            ("node data", lambda doc: doc["nodes"][0].update(data_classification="DATA-MISSING")),
            ("node secret", lambda doc: doc["nodes"][0]["secrets"].append("SECRET-MISSING")),
            ("node contract", lambda doc: doc["nodes"][0]["public_contracts"].append("CONTRACT-MISSING")),
            ("edge from", lambda doc: doc["edges"][0].update({"from": "NODE-MISSING"})),
            ("edge to", lambda doc: doc["edges"][0].update(to="NODE-MISSING")),
            ("edge data", lambda doc: doc["edges"][0]["allowed_data"].append("DATA-MISSING")),
            (
                "edge signal",
                lambda doc: doc["edges"][0]["failure_behavior"].update(
                    observable_signal="SIG-MISSING"
                ),
            ),
        )
        for label, mutate in mutations:
            system = _system()
            mutate(system)
            with self.subTest(label=label), self.assertRaises(ARCH.ArchitectureError):
                ARCH.load_architecture(self._repo(system, _rules()))
        rules = _rules()
        rules["architecture_id"] = "ARCH-OTHER"
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(self._repo(_system(), rules))

    def test_duplicate_capability_edges_fail_even_with_distinct_ids(self) -> None:
        system = _system()
        duplicate = copy.deepcopy(system["edges"][0])
        duplicate["id"] = "EDGE-A-B-OTHER"
        system["edges"].append(duplicate)
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(self._repo(system, _rules()))

    def test_model_paths_reject_absolute_backslash_parent_and_controls(self) -> None:
        for raw in (
            "/absolute",
            ".",
            "./relative",
            "dir/./file",
            "..",
            "../escape",
            "dir\\file",
            "dir\nfile",
            "dir\x7ffile",
        ):
            system = _system()
            system["nodes"][0]["repository_paths"] = [raw]
            with self.subTest(raw=ascii(raw)), self.assertRaises(ARCH.ArchitectureError):
                ARCH.load_architecture(self._repo(system, _rules()))
        system = _system()
        system["contracts"] = [
            {
                "id": "CONTRACT-ONE",
                "kind": "json_schema",
                "path": "/outside.json",
                "version": "1",
                "role": "consumer",
                "compatibility": "exact",
            }
        ]
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(self._repo(system, _rules()))

    def test_document_paths_reject_escape_symlink_and_non_regular_files(self) -> None:
        root = self._repo()
        outside = root.parent / "outside-system.json"
        self._write(outside, _system())
        self.addCleanup(outside.unlink)
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(root, system_path=outside)

        system_path = root / "architecture/system.yaml"
        system_path.unlink()
        system_path.symlink_to(outside)
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(root)

        system_path.unlink()
        system_path.mkdir()
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(root)

    def test_surrogates_bom_trailing_and_non_finite_numbers_fail(self) -> None:
        invalid = (
            b'\xef\xbb\xbf{"schema_version":1}',
            b'{"schema_version":1} trailing',
            b'{"schema_version":NaN}',
            b'{"schema_version":1,"bad":"\\ud800"}',
        )
        for raw in invalid:
            root = self._repo()
            (root / "architecture/system.yaml").write_bytes(raw)
            with self.subTest(raw=raw[:20]), self.assertRaises(ARCH.ArchitectureError):
                ARCH.load_architecture(root)

    def test_document_byte_depth_and_total_node_limits_fail(self) -> None:
        root = self._repo()
        (root / "architecture/system.yaml").write_bytes(b" " * (ARCH.MAX_DOCUMENT_BYTES + 1))
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(root)

        root = self._repo()
        deep: object = None
        for _ in range(ARCH.MAX_DEPTH + 1):
            deep = [deep]
        raw = json.dumps({"padding": deep}).encode()
        (root / "architecture/system.yaml").write_bytes(raw)
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(root)

        root = self._repo()
        raw = json.dumps({"padding": [None] * (ARCH.MAX_PARSED_NODES + 1)}).encode()
        self.assertLessEqual(len(raw), ARCH.MAX_DOCUMENT_BYTES)
        (root / "architecture/system.yaml").write_bytes(raw)
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(root)

    def test_model_node_edge_and_rule_limits_fail(self) -> None:
        system = _system()
        template = system["nodes"][0]
        system["nodes"] = []
        for index in range(ARCH.MAX_MODEL_NODES + 1):
            node = copy.deepcopy(template)
            node["id"] = f"NODE-{index:03d}"
            system["nodes"].append(node)
        system["edges"] = []
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(self._repo(system, _rules()))

        system = _system()
        template_edge = system["edges"][0]
        system["edges"] = []
        for index in range(ARCH.MAX_MODEL_EDGES + 1):
            edge = copy.deepcopy(template_edge)
            edge["id"] = f"EDGE-{index:03d}"
            edge["protocol"] = f"custom-{index:03d}"
            system["edges"].append(edge)
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(self._repo(system, _rules()))

        rules = _rules()
        rules["risk_escalations"] = [
            {
                "id": f"FIT-RISK-{index:03d}",
                "triggers": ["new_edge"],
                "risk": "yellow",
                "severity": "error",
            }
            for index in range(129)
        ]
        rules["forbidden_edges"] = [
            {
                "id": f"FIT-EDGE-{index:03d}",
                "from_trust_domains": ["TD-LOCAL"],
                "to_trust_domains": ["TD-LOCAL"],
                "edge_types": ["dependency"],
                "severity": "error",
            }
            for index in range(128)
        ]
        with self.assertRaises(ARCH.ArchitectureError):
            ARCH.load_architecture(self._repo(_system(), rules))

    def test_normalization_and_digests_are_order_independent_and_stable(self) -> None:
        system = _system()
        system["nodes"].reverse()
        system["edges"][0]["allowed_data"] = ["DATA-INTERNAL"]
        root_a = self._repo(system, _rules())
        first = ARCH.load_architecture(root_a)

        reordered = json.loads(json.dumps(system, sort_keys=True))
        reordered["nodes"].reverse()
        root_b = self._repo(reordered, json.loads(json.dumps(_rules(), sort_keys=True)))
        second = ARCH.load_architecture(root_b)
        self.assertEqual(first.system, second.system)
        self.assertEqual(ARCH.architecture_digests(first), ARCH.architecture_digests(second))
        digests = ARCH.architecture_digests(first)
        self.assertEqual(
            set(digests),
            {
                "system_schema_digest",
                "rules_schema_digest",
                "schema_digest",
                "system_digest",
                "rules_digest",
                "architecture_digest",
            },
        )
        self.assertTrue(all(len(value) == 64 for value in digests.values()))

    def test_semantic_edits_change_component_composite_and_fingerprint(self) -> None:
        root = self._repo()
        first = ARCH.load_architecture(root)
        first_digests = ARCH.architecture_digests(first)
        changed = _system()
        changed["nodes"][0]["owner"] = "security"
        self._write(root / "architecture/system.yaml", changed)
        second = ARCH.load_architecture(root)
        second_digests = ARCH.architecture_digests(second)
        self.assertNotEqual(first_digests["system_digest"], second_digests["system_digest"])
        self.assertEqual(first_digests["rules_digest"], second_digests["rules_digest"])
        self.assertNotEqual(
            first_digests["architecture_digest"], second_digests["architecture_digest"]
        )

        kwargs = {
            "base_sha": "a" * 40,
            "head_sha": "b" * 40,
            "contract_digests": {"contracts/a.json": "c" * 64},
        }
        fingerprint = ARCH.architecture_fingerprint(root, first, **kwargs)
        self.assertEqual(fingerprint, ARCH.architecture_fingerprint(root, first, **kwargs))
        self.assertNotEqual(fingerprint, ARCH.architecture_fingerprint(root, second, **kwargs))
        changed_kwargs = dict(kwargs)
        changed_kwargs["head_sha"] = "d" * 40
        self.assertNotEqual(
            fingerprint, ARCH.architecture_fingerprint(root, first, **changed_kwargs)
        )

    def test_repository_validation_reports_missing_symlink_and_non_regular_contracts(self) -> None:
        system = _system()
        system["nodes"][0]["repository_paths"] = ["src"]
        system["contracts"] = [
            {
                "id": "CONTRACT-ONE",
                "kind": "json_schema",
                "path": "contracts/one.json",
                "version": "1",
                "role": "consumer",
                "compatibility": "exact",
            }
        ]
        system["nodes"][0]["public_contracts"] = ["CONTRACT-ONE"]
        root = self._repo(system, _rules())
        findings = ARCH.validate_architecture(ARCH.load_architecture(root), root)
        self.assertEqual(
            [finding.code for finding in findings],
            ["missing_contract", "missing_repository_path"],
        )

        (root / "src").mkdir()
        (root / "contracts").mkdir()
        (root / "contract-target").mkdir()
        (root / "contracts/one.json").symlink_to(root / "contract-target", target_is_directory=True)
        findings = ARCH.validate_architecture(ARCH.load_architecture(root), root)
        self.assertEqual([finding.code for finding in findings], ["unsafe_contract_path"])


if __name__ == "__main__":
    unittest.main()
