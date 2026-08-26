from __future__ import annotations

import copy
import importlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

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


def _json_schema(properties: dict, required: list[str] | None = None) -> dict:
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": properties,
        "required": required or [],
        "additionalProperties": False,
    }


def _openapi(operation: dict | None = None) -> dict:
    return {
        "openapi": "3.1.0",
        "info": {"title": "Test API", "version": "1"},
        "paths": {"/items": {"get": operation or {"responses": {"200": {"description": "ok"}}}}},
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

    def _record(
        self,
        document: dict,
        *,
        kind: str = "json_schema",
        version: str = "1",
        compatibility: str = "consumer_accepts_old",
    ):
        self.assertTrue(hasattr(ARCH, "ContractRecord"), "ContractRecord is not implemented")
        return ARCH.ContractRecord(
            id="CONTRACT-TEST",
            kind=kind,
            path="engineering/contracts/test.json",
            version=version,
            role="consumer",
            compatibility=compatibility,
            digest="0" * 64,
            document=document,
        )

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

    def test_duplicate_capability_rejects_reordered_allowed_data(self) -> None:
        system = _system()
        system["data_classifications"].append(
            {
                "id": "DATA-PUBLIC",
                "classification": "public",
                "tenant_scoped": False,
                "contains_secret": False,
            }
        )
        system["edges"][0]["allowed_data"] = ["DATA-INTERNAL", "DATA-PUBLIC"]
        duplicate = copy.deepcopy(system["edges"][0])
        duplicate["id"] = "EDGE-A-B-OTHER"
        duplicate["allowed_data"] = ["DATA-PUBLIC", "DATA-INTERNAL"]
        system["edges"].append(duplicate)
        with self.assertRaisesRegex(ARCH.ArchitectureError, "duplicate capability"):
            ARCH.load_architecture(self._repo(system, _rules()))

    def test_finite_rule_selectors_reject_typos(self) -> None:
        cases = {
            "forbidden edge type": (
                "forbidden_edges",
                {
                    "id": "FIT-EDGE-TYPO",
                    "from_trust_domains": ["TD-LOCAL"],
                    "to_trust_domains": ["TD-LOCAL"],
                    "edge_types": ["dependecny"],
                    "severity": "error",
                },
            ),
            "contract kind": (
                "contract_policies",
                {
                    "id": "FIT-CONTRACT-TYPO",
                    "contract_kinds": ["openpai"],
                    "compatibility": "exact",
                    "severity": "error",
                },
            ),
            "migration phase": (
                "migration_policies",
                {
                    "id": "FIT-MIGRATION-TYPO",
                    "path_prefixes": ["migrations"],
                    "required_phases": ["expnad"],
                    "immutable_history": True,
                    "severity": "error",
                },
            ),
            "network node type": (
                "network_policies",
                {
                    "id": "FIT-NETWORK-TYPO",
                    "node_types": ["servcie"],
                    "allowed_protocols": ["https"],
                    "require_declared_edge": True,
                    "severity": "error",
                },
            ),
            "background node type": (
                "background_job_policies",
                {
                    "id": "FIT-BACKGROUND-NODE-TYPO",
                    "node_types": ["workre"],
                    "max_retries": 3,
                    "require_idempotency": True,
                    "require_correlation_id": True,
                    "terminal_actions": ["dead_letter"],
                    "severity": "error",
                },
            ),
            "background terminal action": (
                "background_job_policies",
                {
                    "id": "FIT-BACKGROUND-TERMINAL-TYPO",
                    "node_types": ["worker"],
                    "max_retries": 3,
                    "require_idempotency": True,
                    "require_correlation_id": True,
                    "terminal_actions": ["dead_leter"],
                    "severity": "error",
                },
            ),
            "workspace node type": (
                "workspace_trust_policies",
                {
                    "id": "FIT-WORKSPACE-TYPO",
                    "node_types": ["runer"],
                    "forbidden_secret_classes": [],
                    "severity": "error",
                },
            ),
        }
        for label, (collection, rule) in cases.items():
            rules = _rules()
            rules[collection] = [rule]
            with self.subTest(label=label), self.assertRaises(ARCH.ArchitectureError):
                ARCH.load_architecture(self._repo(_system(), rules))

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

    def test_authority_documents_reject_unsorted_and_compact_json(self) -> None:
        noncanonical = (
            json.dumps(_system(), ensure_ascii=False, indent=2).encode("utf-8") + b"\n",
            json.dumps(
                _system(), ensure_ascii=False, sort_keys=True, separators=(",", ":")
            ).encode("utf-8")
            + b"\n",
        )
        for raw in noncanonical:
            root = self._repo()
            (root / "architecture/system.yaml").write_bytes(raw)
            with self.subTest(raw=raw[:40]), self.assertRaisesRegex(
                ARCH.ArchitectureError, "canonical"
            ):
                ARCH.load_architecture(root)

    def test_authority_documents_reject_noncanonical_trailing_bytes(self) -> None:
        canonical = json.dumps(
            _system(), ensure_ascii=False, sort_keys=True, indent=2
        ).encode("utf-8")
        for raw in (canonical, canonical + b"\n\n", canonical + b"\n ", canonical + b" \n"):
            root = self._repo()
            (root / "architecture/system.yaml").write_bytes(raw)
            with self.subTest(trailer=raw[-4:]), self.assertRaisesRegex(
                ARCH.ArchitectureError, "canonical"
            ):
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

    def test_seed_architecture_models_current_boundaries_and_real_contracts(self) -> None:
        self.assertTrue((ROOT / "architecture/system.yaml").is_file())
        self.assertTrue((ROOT / "architecture/rules.yaml").is_file())
        snapshot = ARCH.load_architecture(ROOT)
        node_ids = {node["id"] for node in snapshot.system["nodes"]}
        self.assertTrue(
            {
                "NODE-LOCAL-ROUTE-POLICY",
                "NODE-CHANGE-SPEC-EVIDENCE",
                "NODE-LOCAL-VERIFIER",
                "NODE-TRUST-CI-API",
                "NODE-TRUST-CI-POSTGRES",
                "NODE-TRUST-CI-WORKER",
                "NODE-EXACT-SHA-WORKSPACE",
                "NODE-DOCKER-ENGINE",
                "NODE-ISOLATED-RUNNER",
                "NODE-EXTERNAL-HOLDOUT",
                "NODE-GITHUB",
                "NODE-HUMAN-APPROVAL",
            }.issubset(node_ids)
        )
        docker_edge = next(
            edge
            for edge in snapshot.system["edges"]
            if edge["from"] == "NODE-TRUST-CI-WORKER"
            and edge["to"] == "NODE-DOCKER-ENGINE"
        )
        self.assertEqual(docker_edge["protocol"], "docker_api")
        self.assertEqual(docker_edge["authentication"], "none")
        self.assertEqual(docker_edge["network_policy"], "local_only")
        self.assertTrue(
            all(node["runtime"]["evidence"] == "source_described" for node in snapshot.system["nodes"])
        )
        self.assertEqual(ARCH.validate_repository_drift(ROOT, snapshot), ())
        records = ARCH.contract_inventory(ROOT, snapshot)
        self.assertEqual(len(records), 4)
        self.assertNotIn(".gitkeep", {record.path for record in records})
        self.assertFalse(any(record.path.startswith("examples/") for record in records))
        documents = {record.id: record.document for record in records}
        self.assertEqual(
            set(documents["CONTRACT-TRUST-CI-OPENAPI"]["paths"]),
            {
                "/approvals",
                "/attestations/{job_id}",
                "/health/live",
                "/health/ready",
                "/jobs/{job_id}",
                "/metrics",
                "/webhooks/github",
            },
        )
        self.assertEqual(
            set(
                documents["CONTRACT-APPROVAL-ENVELOPE"]["properties"]["payload"][
                    "required"
                ]
            ),
            {
                "actor",
                "approval_id",
                "base_sha",
                "expires_at",
                "head_sha",
                "issued_at",
                "key_id",
                "nonce",
                "policy_digest",
                "pr_number",
                "reason",
                "repository",
                "schema_version",
                "scope",
            },
        )
        attestation_payload = documents["CONTRACT-ATTESTATION-ENVELOPE"]["properties"][
            "payload"
        ]
        self.assertIn("command_results", attestation_payload["required"])
        self.assertEqual(
            set(attestation_payload["properties"]["command_results"]["items"]["required"]),
            {"duration_seconds", "exit_code", "name", "output_sha256", "status"},
        )
        self.assertEqual(
            set(documents["CONTRACT-GITHUB-PR-PROJECTION"]["required"]),
            {"action", "pull_request", "repository"},
        )
        openapi = documents["CONTRACT-TRUST-CI-OPENAPI"]
        for path in ("/jobs/{job_id}", "/attestations/{job_id}"):
            parameter = openapi["paths"][path]["parameters"][0]
            self.assertEqual(
                (parameter["in"], parameter["name"], parameter["required"]),
                ("path", "job_id", True),
            )
        webhook_parameters = openapi["paths"]["/webhooks/github"]["post"]["parameters"]
        self.assertIn(
            ("header", "X-GitHub-Event", True),
            {
                (parameter["in"], parameter["name"], parameter["required"])
                for parameter in webhook_parameters
            },
        )
        expected_statuses = {
            "/approvals": {"200", "400", "403", "404", "409", "503"},
            "/attestations/{job_id}": {"200", "401", "404"},
            "/health/live": {"200"},
            "/health/ready": {"200", "503"},
            "/jobs/{job_id}": {"200", "401", "404"},
            "/metrics": {"200", "401"},
            "/webhooks/github": {"200", "401", "403", "503"},
        }
        for path, statuses in expected_statuses.items():
            method = next(key for key in openapi["paths"][path] if key in {"get", "post"})
            self.assertEqual(set(openapi["paths"][path][method]["responses"]), statuses)
        self.assertIn(
            "text/plain",
            openapi["paths"]["/metrics"]["get"]["responses"]["200"]["content"],
        )
        openapi_record = next(
            record for record in records if record.id == "CONTRACT-TRUST-CI-OPENAPI"
        )
        self.assertEqual(
            ARCH.compare_contracts(openapi_record, openapi_record, "bidirectional").status,
            "unsupported",
        )

    def test_repository_drift_reports_undeclared_source_and_contract(self) -> None:
        self.assertTrue(
            hasattr(ARCH, "validate_repository_drift"),
            "validate_repository_drift is not implemented",
        )
        system = _system()
        system["nodes"][0]["repository_paths"] = ["src/owned.py"]
        root = self._repo(system, _rules())
        (root / "src").mkdir()
        (root / "src/owned.py").write_text("VALUE = 1\n", encoding="utf-8")
        (root / "src/undeclared.py").write_text("VALUE = 2\n", encoding="utf-8")
        (root / "lib").mkdir()
        (root / "lib/new_component.py").write_text("VALUE = 3\n", encoding="utf-8")
        (root / "src/native.rs").write_text("fn main() {}\n", encoding="utf-8")
        (root / "engineering/contracts").mkdir(parents=True)
        (root / "engineering/contracts/.gitkeep").write_text("", encoding="utf-8")
        (root / "engineering/contracts/undeclared.json").write_text("{}\n", encoding="utf-8")
        (root / "engineering/contracts/examples").mkdir()
        (root / "engineering/contracts/examples/example.json").write_text(
            "{}\n", encoding="utf-8"
        )
        (root / "examples/contracts").mkdir(parents=True)
        (root / "examples/contracts/example.json").write_text("{}\n", encoding="utf-8")
        findings = ARCH.validate_repository_drift(root, ARCH.load_architecture(root))
        self.assertEqual(
            [(finding.code, finding.path) for finding in findings],
            [
                ("undeclared_contract", "engineering/contracts/undeclared.json"),
                ("undeclared_source", "lib/new_component.py"),
                ("undeclared_source", "src/undeclared.py"),
                ("unsupported_source_artifact", "src/native.rs"),
            ],
        )

    def test_repository_drift_traversal_is_bounded_by_entries_files_and_bytes(self) -> None:
        cases = (
            ("MAX_DRIFT_ENTRIES", 40, "entry limit"),
            ("MAX_DRIFT_FILES", 20, "file limit"),
            ("MAX_DRIFT_BYTES", 50_000, "byte limit"),
        )
        for attribute, limit, message in cases:
            root = self._repo()
            (root / "bulk").mkdir()
            for index in range(64):
                (root / f"bulk/item-{index}.txt").write_text("payload\n", encoding="utf-8")
            (root / "bulk/large.bin").write_bytes(b"x" * 100_000)
            snapshot = ARCH.load_architecture(root)
            with self.subTest(limit=attribute), mock.patch.object(ARCH, attribute, limit):
                with self.assertRaisesRegex(ARCH.ArchitectureError, message):
                    ARCH.validate_repository_drift(root, snapshot)

    def test_repository_drift_does_not_follow_directory_symlinks(self) -> None:
        root = self._repo()
        outside = Path(tempfile.mkdtemp())
        self.addCleanup(lambda: outside.rmdir())
        (outside / "outside.py").write_text("VALUE = 1\n", encoding="utf-8")
        self.addCleanup(lambda: (outside / "outside.py").unlink())
        (root / "linked-source").symlink_to(outside, target_is_directory=True)
        findings = ARCH.validate_repository_drift(root, ARCH.load_architecture(root))
        self.assertEqual(
            [(finding.code, finding.path) for finding in findings],
            [("unsafe_repository_artifact", "linked-source")],
        )

    def test_repository_drift_fails_closed_on_special_artifacts(self) -> None:
        root = self._repo()
        os.mkfifo(root / "untrusted-pipe")
        findings = ARCH.validate_repository_drift(root, ARCH.load_architecture(root))
        self.assertEqual(
            [(finding.code, finding.path) for finding in findings],
            [("unsafe_repository_artifact", "untrusted-pipe")],
        )

    def test_examples_and_gitkeep_cannot_be_declared_contracts(self) -> None:
        for path in (
            "engineering/contracts/.gitkeep",
            "engineering/contracts/examples/example.json",
        ):
            system = _system()
            system["contracts"] = [
                {
                    "id": "CONTRACT-NON-AUTHORITY",
                    "kind": "json_schema",
                    "path": path,
                    "version": "1",
                    "role": "consumer",
                    "compatibility": "exact",
                }
            ]
            with self.subTest(path=path), self.assertRaisesRegex(
                ARCH.ArchitectureError, "non-authoritative"
            ):
                ARCH.load_architecture(self._repo(system, _rules()))

    def test_contract_inventory_is_sorted_and_digest_is_deterministic(self) -> None:
        self.assertTrue(hasattr(ARCH, "contract_inventory"), "contract_inventory is not implemented")
        self.assertTrue(
            hasattr(ARCH, "contract_inventory_digest"),
            "contract_inventory_digest is not implemented",
        )
        system = _system()
        contracts = []
        for suffix in ("B", "A"):
            contracts.append(
                {
                    "id": f"CONTRACT-{suffix}",
                    "kind": "json_schema",
                    "path": f"engineering/contracts/{suffix.lower()}.json",
                    "version": "1",
                    "role": "consumer",
                    "compatibility": "exact",
                }
            )
        system["contracts"] = contracts
        system["nodes"][0]["public_contracts"] = ["CONTRACT-B", "CONTRACT-A"]
        root = self._repo(system, _rules())
        (root / "engineering/contracts").mkdir(parents=True)
        for suffix in ("a", "b"):
            self._write(root / f"engineering/contracts/{suffix}.json", _json_schema({}))
        snapshot = ARCH.load_architecture(root)
        first = ARCH.contract_inventory(root, snapshot)
        second = ARCH.contract_inventory(root, snapshot)
        self.assertEqual([record.id for record in first], ["CONTRACT-A", "CONTRACT-B"])
        self.assertEqual(first, second)
        self.assertEqual(
            ARCH.contract_inventory_digest(first),
            ARCH.contract_inventory_digest(tuple(reversed(second))),
        )

    def test_consumer_compatibility_allows_optional_addition(self) -> None:
        self.assertTrue(hasattr(ARCH, "compare_contracts"), "compare_contracts is not implemented")
        base = self._record(_json_schema({"name": {"type": "string"}}, ["name"]))
        head = self._record(
            _json_schema(
                {"name": {"type": "string"}, "age": {"type": "integer"}}, ["name"]
            )
        )
        self.assertEqual(
            ARCH.compare_contracts(base, head, "consumer_accepts_old").status,
            "compatible",
        )

    def test_contract_comparison_rejects_directional_breaks(self) -> None:
        self.assertTrue(hasattr(ARCH, "compare_contracts"), "compare_contracts is not implemented")
        cases = (
            (
                "removed property",
                "consumer_accepts_old",
                _json_schema(
                    {"name": {"type": "string"}, "alias": {"type": "string"}}, ["name"]
                ),
                _json_schema({"name": {"type": "string"}}, ["name"]),
                "removed_property",
            ),
            (
                "removed event property",
                "consumer_accepts_old",
                _json_schema(
                    {"event_id": {"type": "string"}, "meaning": {"type": "string"}},
                    ["event_id"],
                ),
                _json_schema({"event_id": {"type": "string"}}, ["event_id"]),
                "removed_property",
            ),
            (
                "new required input",
                "consumer_accepts_old",
                _json_schema({"name": {"type": "string"}}, ["name"]),
                _json_schema(
                    {"name": {"type": "string"}, "age": {"type": "integer"}},
                    ["name", "age"],
                ),
                "new_required_input",
            ),
            (
                "narrowed enum",
                "consumer_accepts_old",
                _json_schema({"mode": {"type": "string", "enum": ["a", "b"]}}),
                _json_schema({"mode": {"type": "string", "enum": ["a"]}}),
                "narrowed_enum",
            ),
            (
                "narrowed mixed scalar enum",
                "consumer_accepts_old",
                _json_schema({"mode": {"enum": [True, 1]}}),
                _json_schema({"mode": {"enum": [True]}}),
                "narrowed_enum",
            ),
            (
                "changed type",
                "consumer_accepts_old",
                _json_schema({"value": {"type": "integer"}}),
                _json_schema({"value": {"type": "string"}}),
                "changed_type",
            ),
            (
                "widened producer output",
                "producer_accepted_by_old",
                _json_schema({"name": {"type": "string"}}),
                _json_schema(
                    {"name": {"type": "string"}, "age": {"type": "integer"}}
                ),
                "widened_producer_output",
            ),
            (
                "producer output becomes optional",
                "producer_accepted_by_old",
                _json_schema({"name": {"type": "string"}}, ["name"]),
                _json_schema({"name": {"type": "string"}}),
                "widened_producer_output",
            ),
        )
        for label, policy, base_doc, head_doc, reason in cases:
            kind = "event" if label == "removed event property" else "json_schema"
            result = ARCH.compare_contracts(
                self._record(base_doc, kind=kind), self._record(head_doc, kind=kind), policy
            )
            with self.subTest(label=label):
                self.assertEqual(result.status, "incompatible")
                self.assertIn(reason, result.reasons)

    def test_openapi_comparison_rejects_removed_operation_and_weakened_authentication(self) -> None:
        self.assertTrue(hasattr(ARCH, "compare_contracts"), "compare_contracts is not implemented")
        secured = {
            "security": [{"bearerAuth": []}],
            "responses": {"200": {"description": "ok"}},
        }
        secured_base = _openapi(secured)
        secured_base["components"] = {
            "securitySchemes": {
                "bearerAuth": {"type": "http", "scheme": "bearer"},
            }
        }
        removed = copy.deepcopy(secured_base)
        removed["paths"] = {}
        weakened = _openapi({"security": [], "responses": {"200": {"description": "ok"}}})
        weakened["components"] = copy.deepcopy(secured_base["components"])
        for label, head, reason in (
            ("removed", removed, "removed_operation"),
            ("weakened", weakened, "weakened_authentication"),
        ):
            result = ARCH.compare_contracts(
                self._record(secured_base, kind="openapi"),
                self._record(head, kind="openapi"),
                "bidirectional",
            )
            with self.subTest(label=label):
                self.assertEqual(result.status, "incompatible")
                self.assertIn(reason, result.reasons)

    def test_openapi_comparison_rejects_widened_producer_response(self) -> None:
        def operation(properties: dict) -> dict:
            return {
                "responses": {
                    "200": {
                        "description": "ok",
                        "content": {
                            "application/json": {
                                "schema": _json_schema(properties),
                            }
                        },
                    }
                }
            }

        base = self._record(
            _openapi(operation({"name": {"type": "string"}})), kind="openapi"
        )
        head = self._record(
            _openapi(
                operation(
                    {"name": {"type": "string"}, "age": {"type": "integer"}}
                )
            ),
            kind="openapi",
        )
        result = ARCH.compare_contracts(base, head, "bidirectional")
        self.assertEqual(result.status, "incompatible")
        self.assertIn("widened_producer_output", result.reasons)

    def test_openapi_comparison_rejects_added_status_required_parameter_and_scheme_change(
        self,
    ) -> None:
        base = _openapi()
        added_status = copy.deepcopy(base)
        added_status["paths"]["/items"]["get"]["responses"]["201"] = {
            "description": "created"
        }

        required_parameter = copy.deepcopy(base)
        required_parameter["paths"]["/items"]["parameters"] = [
            {
                "in": "header",
                "name": "X-Required",
                "required": True,
                "schema": {"type": "string"},
            }
        ]

        secured_base = copy.deepcopy(base)
        secured_base["components"] = {
            "securitySchemes": {
                "access": {"type": "http", "scheme": "bearer"},
            }
        }
        secured_base["paths"]["/items"]["get"]["security"] = [{"access": []}]
        changed_scheme = copy.deepcopy(secured_base)
        changed_scheme["components"]["securitySchemes"]["access"] = {
            "type": "apiKey",
            "in": "query",
            "name": "access_token",
        }

        for label, base_doc, head_doc, reason in (
            ("added response", base, added_status, "added_response"),
            ("required path-level header", base, required_parameter, "new_required_input"),
            ("changed security scheme", secured_base, changed_scheme, "changed_authentication"),
        ):
            result = ARCH.compare_contracts(
                self._record(base_doc, kind="openapi"),
                self._record(head_doc, kind="openapi"),
                "bidirectional",
            )
            with self.subTest(label=label):
                self.assertEqual(result.status, "incompatible")
                self.assertIn(reason, result.reasons)

    def test_openapi_comparison_returns_unsupported_for_unhandled_applicable_constructs(
        self,
    ) -> None:
        base = _openapi()
        referenced_parameter = copy.deepcopy(base)
        referenced_parameter["paths"]["/items"]["get"]["parameters"] = [
            {"$ref": "#/components/parameters/Future"}
        ]
        malformed_info = copy.deepcopy(base)
        malformed_info["info"]["title"] = ["not", "a", "string"]
        for head in (referenced_parameter, malformed_info):
            result = ARCH.compare_contracts(
                self._record(base, kind="openapi"),
                self._record(head, kind="openapi"),
                "bidirectional",
            )
            with self.subTest(head=head):
                self.assertEqual(result.status, "unsupported")

    def test_contract_comparison_is_unsupported_or_exact_when_required(self) -> None:
        self.assertTrue(hasattr(ARCH, "compare_contracts"), "compare_contracts is not implemented")
        base_doc = _json_schema({"name": {"type": "string"}})
        unsupported = copy.deepcopy(base_doc)
        unsupported["properties"]["name"]["oneOf"] = [{"type": "string"}]
        result = ARCH.compare_contracts(
            self._record(base_doc), self._record(unsupported), "consumer_accepts_old"
        )
        self.assertEqual(result.status, "unsupported")
        self.assertIn("unsupported_schema_keyword", result.reasons)

        changed = _json_schema({"name": {"type": "integer"}})
        result = ARCH.compare_contracts(
            self._record(base_doc, compatibility="exact"),
            self._record(changed, compatibility="exact"),
            "exact",
        )
        self.assertEqual(result.status, "incompatible")
        self.assertIn("same_version_semantic_change", result.reasons)

    def test_contract_comparison_malformed_unknown_and_event_meaning_fail_typed(self) -> None:
        malformed_cases = (
            {"type": ["string", "null"]},
            {"type": "string", "minLength": "2"},
            {"type": "string", "minLength": -1},
            {"type": "array", "minItems": True},
            {"type": "number", "minimum": 3, "maximum": 2},
            {"type": "string", "pattern": "["},
            {"type": "object", "properties": {1: {"type": "string"}}},
        )
        for malformed in malformed_cases:
            result = ARCH.compare_contracts(
                self._record({"type": "string"}),
                self._record(malformed),
                "consumer_accepts_old",
            )
            with self.subTest(malformed=malformed):
                self.assertEqual(result.status, "unsupported")

        document = _json_schema({"event_id": {"type": "string"}})
        self.assertEqual(
            ARCH.compare_contracts(
                self._record(document), self._record(document), "future_mode"
            ).status,
            "unsupported",
        )
        unknown_kind = self._record(document, kind="future_contract")
        self.assertEqual(
            ARCH.compare_contracts(unknown_kind, unknown_kind, "exact").status,
            "unsupported",
        )

        changed_meaning = copy.deepcopy(document)
        document["description"] = "account approved"
        changed_meaning["description"] = "account deleted"
        result = ARCH.compare_contracts(
            self._record(document, kind="event"),
            self._record(changed_meaning, kind="event"),
            "consumer_accepts_old",
        )
        self.assertEqual(result.status, "incompatible")
        self.assertIn("event_meaning_changed", result.reasons)


if __name__ == "__main__":
    unittest.main()
