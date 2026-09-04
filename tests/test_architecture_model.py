from __future__ import annotations

import copy
import contextlib
import importlib
import importlib.util
import io
import json
import os
import subprocess
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
try:
    DIAGRAMS = importlib.import_module("adaptive_grok.architecture_diagrams")
except ModuleNotFoundError:
    DIAGRAMS = None


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

    def test_factory_control_plane_is_local_and_separate_from_trust_ci(self) -> None:
        snapshot = ARCH.load_architecture(ROOT)
        nodes = {node["id"]: node for node in snapshot.system["nodes"]}
        expected = {"NODE-FACTORY-LOCAL-API", "NODE-FACTORY-CONTROL", "NODE-FACTORY-POSTGRES"}
        self.assertTrue(expected <= set(nodes))
        for node_id in expected:
            self.assertEqual(nodes[node_id]["trust_domain"], "TD-FACTORY-CONTROL")
        prohibited = {"NODE-TRUST-CI-POSTGRES", "NODE-TRUST-CI-API", "NODE-TRUST-CI-WORKER", "NODE-GITHUB", "NODE-DOCKER-ENGINE", "NODE-ISOLATED-RUNNER"}
        for edge in snapshot.system["edges"]:
            self.assertFalse(edge["from"] in expected and edge["to"] in prohibited, edge["id"])
            self.assertFalse(edge["to"] in expected and edge["from"] in prohibited, edge["id"])
        factory_edges = [edge for edge in snapshot.system["edges"] if edge["from"] in expected or edge["to"] in expected]
        self.assertTrue(factory_edges)
        self.assertTrue(all(edge["network_policy"] in {"no_network", "local_only"} for edge in factory_edges))

    def test_repository_code_budgets_restore_m2_and_bound_factory_independently(self) -> None:
        snapshot = ARCH.load_architecture(ROOT)
        expected = {
            rule["id"]: rule
            for rule in [
                {
                    "id": "FIT-BOUNDED-ARCHITECTURE-CHANGE",
                    "path_prefixes": [
                        ".grok-stack/adaptive_grok",
                        "architecture",
                        "delivery",
                        "engineering/contracts",
                        "governance",
                        "schemas",
                        "scripts",
                    ],
                    "max_changed_bytes": 1_000_000,
                    "max_changed_lines": 10_820,
                    "max_ast_complexity": 5_000,
                    "severity": "error",
                },
                {
                    "id": "FIT-BOUNDED-ALL-GOVERNED-CHANGE",
                    "path_prefixes": [
                        ".grok-stack/adaptive_grok",
                        "architecture",
                        "engineering/contracts",
                        "factory",
                        "governance",
                        "schemas",
                        "scripts",
                    ],
                    "max_changed_bytes": 1_300_000,
                    "max_changed_lines": 24_000,
                    "max_ast_complexity": 5_000,
                    "severity": "error",
                },
                {
                    "id": "FIT-BOUNDED-FACTORY-CHANGE",
                    "path_prefixes": ["factory"],
                    "max_changed_bytes": 950_000,
                    "max_changed_lines": 22_000,
                    "max_ast_complexity": 1_450,
                    "severity": "error",
                },
                {
                    "id": "FIT-BOUNDED-FACTORY-SOURCE-CHANGE",
                    "path_prefixes": ["factory/src"],
                    "max_changed_bytes": 235_000,
                    "max_changed_lines": 5_500,
                    "max_ast_complexity": 1_000,
                    "severity": "error",
                },
                {
                    "id": "FIT-BOUNDED-FACTORY-CONTRACT-CHANGE",
                    "path_prefixes": ["factory/contracts"],
                    "max_changed_bytes": 285_000,
                    "max_changed_lines": 8_500,
                    "max_ast_complexity": 1,
                    "severity": "error",
                },
                {
                    "id": "FIT-BOUNDED-FACTORY-TEST-CHANGE",
                    "path_prefixes": ["factory/tests"],
                    "max_changed_bytes": 510_000,
                    "max_changed_lines": 7_500,
                    "max_ast_complexity": 425,
                    "severity": "error",
                },
            ]
        }
        actual = {rule["id"]: rule for rule in snapshot.rules["code_budgets"]}

        self.assertEqual(tuple(actual), tuple(sorted(expected)))
        self.assertEqual(actual, expected)

    def test_factory_execution_components_have_local_default_deny_ownership(self) -> None:
        snapshot = ARCH.load_architecture(ROOT)
        nodes = {node["id"]: node for node in snapshot.system["nodes"]}
        expected_paths = {
            "NODE-FACTORY-EXECUTION-CORE": {
                "factory/contracts/schemas",
                "factory/src/adaptive_factory/execution_contracts.py",
                "factory/src/adaptive_factory/protocol.py",
                "factory/src/adaptive_factory/semantic_bridge.py",
            },
            "NODE-FACTORY-PROVIDER-ADAPTERS": {
                "factory/src/adaptive_factory/adapters/__init__.py",
                "factory/src/adaptive_factory/adapters/base.py",
                "factory/src/adaptive_factory/adapters/codex.py",
                "factory/src/adaptive_factory/adapters/grok.py",
            },
            "NODE-FACTORY-PROPOSAL-BROKER": {"factory/src/adaptive_factory/brokers.py"},
            "NODE-FACTORY-WORKSPACE-BROKER": {"factory/src/adaptive_factory/workspace.py"},
        }
        for node_id, paths in expected_paths.items():
            node = nodes[node_id]
            self.assertEqual(set(node["repository_paths"]), paths)
            self.assertEqual(node["trust_domain"], "TD-FACTORY-CONTROL")
            self.assertEqual(node["runtime"]["network"], "none")
            self.assertEqual(node["secrets"], [])
        self.assertIn(
            "factory/src/adaptive_factory/recovery.py",
            nodes["NODE-FACTORY-CONTROL"]["repository_paths"],
        )

        edges = {edge["id"]: edge for edge in snapshot.system["edges"]}
        workspace_edges = {
            "EDGE-FACTORY-CONTROL-WORKSPACE",
            "EDGE-FACTORY-WORKSPACE-CONTROL",
        }
        for edge_id in workspace_edges:
            edge = edges[edge_id]
            self.assertEqual(edge["network_policy"], "no_network")
            self.assertEqual(edge["failure_behavior"]["mode"], "fail_closed")
            self.assertEqual(edge["failure_behavior"]["terminal_action"], "reject")

        execution_edges = {
            "EDGE-FACTORY-CONTROL-EXECUTION-CORE",
            "EDGE-FACTORY-ADAPTERS-EXECUTION-CORE",
            "EDGE-FACTORY-CONTROL-PROPOSAL-BROKER",
            "EDGE-FACTORY-PROPOSAL-BROKER-EXECUTION-CORE",
            *workspace_edges,
        }
        self.assertTrue(all(edges[edge_id]["authentication"] == "local_os" for edge_id in execution_edges))

        adapter_edges = [
            edge
            for edge in snapshot.system["edges"]
            if edge["from"] == "NODE-FACTORY-PROVIDER-ADAPTERS"
            or edge["to"] == "NODE-FACTORY-PROVIDER-ADAPTERS"
        ]
        self.assertEqual(
            {(edge["from"], edge["to"]) for edge in adapter_edges},
            {("NODE-FACTORY-PROVIDER-ADAPTERS", "NODE-FACTORY-EXECUTION-CORE")},
        )
        self.assertTrue(all(edge["network_policy"] == "no_network" for edge in adapter_edges))

        policies = {rule["id"]: rule for rule in snapshot.rules["path_boundaries"]}
        self.assertIn("FIT-FACTORY-ADAPTER-BOUNDARY", policies)
        self.assertIn("FIT-FACTORY-EXECUTION-CORE-BOUNDARY", policies)
        self.assertIn("FIT-FACTORY-SEMANTIC-BRIDGE-BOUNDARY", policies)
        self.assertIn("FIT-FACTORY-PROPOSAL-BROKER-BOUNDARY", policies)
        self.assertIn("FIT-FACTORY-WORKSPACE-BROKER-BOUNDARY", policies)
        adapter_forbidden = set(policies["FIT-FACTORY-ADAPTER-BOUNDARY"]["forbidden_dependency_prefixes"])
        self.assertTrue(
            {
                "adaptive_factory.store",
                "adaptive_factory.workspace",
                "psycopg",
                "celery",
                "rq",
                "git",
                "requests",
                "httpx",
                "socket",
                "subprocess",
            }
            <= adapter_forbidden
        )
        execution_nodes = set(expected_paths)
        external_or_privileged = {
            "NODE-FACTORY-POSTGRES",
            "NODE-TRUST-CI-API",
            "NODE-TRUST-CI-POSTGRES",
            "NODE-TRUST-CI-WORKER",
            "NODE-GITHUB",
            "NODE-DOCKER-ENGINE",
            "NODE-ISOLATED-RUNNER",
        }
        self.assertFalse(
            any(
                (edge["from"] in execution_nodes and edge["to"] in external_or_privileged)
                or (edge["to"] in execution_nodes and edge["from"] in external_or_privileged)
                for edge in snapshot.system["edges"]
            )
        )

    def test_factory_semantic_validation_is_inert_read_only_and_contract_closed(self) -> None:
        snapshot = ARCH.load_architecture(ROOT)
        nodes = {node["id"]: node for node in snapshot.system["nodes"]}
        semantic = nodes["NODE-FACTORY-SEMANTIC-VALIDATION"]
        self.assertEqual(
            set(semantic["repository_paths"]),
            {
                "factory/src/adaptive_factory/semantic_adjudication.py",
                "factory/src/adaptive_factory/semantic_contracts.py",
                "factory/src/adaptive_factory/semantic_repair.py",
            },
        )
        self.assertEqual(semantic["runtime"]["network"], "none")
        self.assertEqual(semantic["secrets"], [])
        self.assertEqual(
            set(semantic["public_contracts"]),
            {
                "CONTRACT-FACTORY-SEMANTIC-COVERAGE-V1",
                "CONTRACT-FACTORY-SEMANTIC-FINDING-V1",
                "CONTRACT-FACTORY-SEMANTIC-REPAIR-DIRECTIVE-V1",
                "CONTRACT-FACTORY-SEMANTIC-SUBJECT-V1",
                "CONTRACT-FACTORY-SEMANTIC-VERDICT-V1",
            },
        )
        semantic_edges = [
            edge
            for edge in snapshot.system["edges"]
            if semantic["id"] in {edge["from"], edge["to"]}
        ]
        self.assertEqual(
            [(edge["from"], edge["to"]) for edge in semantic_edges],
            [("NODE-FACTORY-EXECUTION-CORE", semantic["id"])],
        )
        self.assertEqual(semantic_edges[0]["network_policy"], "no_network")
        self.assertEqual(semantic_edges[0]["failure_behavior"]["mode"], "fail_closed")
        self.assertEqual(
            semantic_edges[0]["failure_behavior"]["terminal_action"], "reject"
        )
        policies = {rule["id"]: rule for rule in snapshot.rules["path_boundaries"]}
        forbidden = set(
            policies["FIT-FACTORY-SEMANTIC-VALIDATION-BOUNDARY"][
                "forbidden_dependency_prefixes"
            ]
        )
        self.assertTrue(
            {
                "adaptive_factory.adapters",
                "adaptive_factory.api",
                "adaptive_factory.brokers",
                "adaptive_factory.execution_contracts",
                "adaptive_factory.migrations",
                "adaptive_factory.service",
                "adaptive_factory.store",
                "adaptive_factory.workspace",
                "psycopg",
                "git",
                "requests",
                "httpx",
                "urllib",
                "socket",
                "subprocess",
            }
            <= forbidden
        )

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
    def _write_diagram_fixture(root: Path, rendered: dict[str, str]) -> None:
        generated = root / "architecture/generated"
        generated.mkdir()
        for name, value in rendered.items():
            (generated / f"{name}.mmd").write_text(value, encoding="utf-8")

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

    def test_repository_path_ownership_rejects_exact_ties(self) -> None:
        system = _system()
        system["nodes"][0]["repository_paths"] = ["src"]
        system["nodes"][1]["repository_paths"] = ["src"]
        with self.assertRaisesRegex(ARCH.ArchitectureError, "repository path ownership"):
            ARCH.load_architecture(self._repo(system, _rules()))

        system["nodes"][1]["repository_paths"] = ["src/special"]
        snapshot = ARCH.load_architecture(self._repo(system, _rules()))
        self.assertEqual(len(snapshot.system["nodes"]), 2)

    def test_five_mermaid_projections_are_deterministic_sorted_and_escaped(self) -> None:
        self.assertIsNotNone(DIAGRAMS, "architecture_diagrams is not implemented")
        system = _system()
        system["trust_domains"][0]["owner"] = 'engineering"]\nsubgraph injected'
        root = self._repo(system, _rules())
        first = DIAGRAMS.render_diagrams(ARCH.load_architecture(root))
        second = DIAGRAMS.render_diagrams(ARCH.load_architecture(root))
        self.assertEqual(first, second)
        self.assertEqual(
            tuple(first),
            ("context", "container", "deployment", "data-flow", "trust-boundary"),
        )
        for content in first.values():
            self.assertTrue(content.startswith("flowchart "))
            self.assertTrue(content.endswith("\n"))
            self.assertNotIn("timestamp", content.lower())
            self.assertNotIn("\nsubgraph injected", content)
        self.assertIn("&quot;", first["context"])

    def test_diagram_render_is_repository_read_only(self) -> None:
        root = self._repo()
        before_inventory = tuple(
            sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))
        )
        before_bytes = {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file()
        }
        spec = importlib.util.spec_from_file_location(
            "grok_architecture_task6",
            ROOT / "scripts/grok_architecture.py",
        )
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        command = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(command)
        real_open = os.open

        def read_only_open(path, flags, *args, **kwargs):
            mutation_flags = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_EXCL
            if flags & mutation_flags:
                self.fail(f"diagram render attempted a mutation-shaped open: {path}")
            return real_open(path, flags, *args, **kwargs)

        def reject_mutation(*args, **kwargs):
            self.fail(f"diagram render attempted repository mutation: {args!r} {kwargs!r}")

        class GuardedOs:
            open = staticmethod(read_only_open)
            rename = staticmethod(reject_mutation)
            unlink = staticmethod(reject_mutation)
            rmdir = staticmethod(reject_mutation)
            mkdir = staticmethod(reject_mutation)
            chmod = staticmethod(reject_mutation)
            replace = staticmethod(reject_mutation)

            def __getattr__(self, name):
                return getattr(os, name)

        output = io.StringIO()
        with (
            mock.patch.object(sys, "argv", ["grok_architecture.py", "--root", str(root), "diagram", "--json"]),
            mock.patch.object(DIAGRAMS, "os", GuardedOs()),
            contextlib.redirect_stdout(output),
        ):
            returncode = command.main()
        payload = json.loads(output.getvalue())
        self.assertEqual(returncode, 0, payload)
        self.assertEqual(payload["checked"], False)
        self.assertEqual(payload["mismatches"], [])
        self.assertEqual(payload["ok"], True)
        self.assertEqual(
            tuple(payload["artifacts"]),
            ("container", "context", "data-flow", "deployment", "trust-boundary"),
        )
        for artifact in payload["artifacts"].values():
            self.assertTrue(artifact.startswith("flowchart "))
            self.assertTrue(artifact.endswith("\n"))
        self.assertEqual(
            tuple(sorted(path.relative_to(root).as_posix() for path in root.rglob("*"))),
            before_inventory,
        )
        self.assertEqual(
            {
                path.relative_to(root).as_posix(): path.read_bytes()
                for path in root.rglob("*")
                if path.is_file()
            },
            before_bytes,
        )

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

        for schema_name, expected_objects in (
            ("architecture-system.schema.json", 10),
            ("architecture-rules.schema.json", 13),
        ):
            schema = json.loads((ROOT / "schemas" / schema_name).read_text(encoding="utf-8"))
            objects: list[dict] = []

            def collect(value) -> None:
                if isinstance(value, dict):
                    if value.get("type") == "object":
                        objects.append(value)
                    for child in value.values():
                        collect(child)
                elif isinstance(value, list):
                    for child in value:
                        collect(child)

            collect(schema)
            self.assertEqual(len(objects), expected_objects, schema_name)
            for index, object_schema in enumerate(objects):
                with self.subTest(schema=schema_name, object=index):
                    self.assertIs(object_schema.get("additionalProperties"), False)
                    self.assertEqual(
                        set(object_schema.get("required", [])),
                        set(object_schema.get("properties", {})),
                    )

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

    def test_secret_bearing_data_requires_authenticated_secret_flow(self) -> None:
        for label, edge_type, authentication in (
            ("deployment", "deployment", "none"),
            ("unauthenticated secret flow", "secret_flow", "none"),
        ):
            system = _system()
            system["data_classifications"].append(
                {
                    "id": "DATA-TRUST-MATERIAL",
                    "classification": "restricted",
                    "tenant_scoped": False,
                    "contains_secret": True,
                }
            )
            system["edges"][0].update(
                allowed_data=["DATA-TRUST-MATERIAL"],
                type=edge_type,
                authentication=authentication,
            )
            with self.subTest(label=label), self.assertRaisesRegex(
                ARCH.ArchitectureError, "secret-bearing"
            ):
                ARCH.load_architecture(self._repo(system, _rules()))

        system = _system()
        system["data_classifications"].append(
            {
                "id": "DATA-TRUST-MATERIAL",
                "classification": "restricted",
                "tenant_scoped": False,
                "contains_secret": True,
            }
        )
        system["edges"][0].update(
            allowed_data=["DATA-TRUST-MATERIAL"],
            type="secret_flow",
            authentication="local_os",
        )
        self.assertEqual(
            ARCH.load_architecture(self._repo(system, _rules())).system["edges"][0]["id"],
            "EDGE-A-B",
        )

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

    def test_migration_policy_rejects_empty_path_prefixes_semantically(self) -> None:
        rules = _rules()
        rules["migration_policies"] = [{
            "id": "FIT-MIGRATION-EMPTY",
            "path_prefixes": [],
            "required_phases": ["expand", "migrate", "contract"],
            "immutable_history": True,
            "severity": "error",
        }]
        with self.assertRaisesRegex(ARCH.ArchitectureError, "path_prefixes must not be empty"):
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

    def test_authority_and_repository_reads_fail_when_nofollow_is_unavailable(self) -> None:
        system = _system()
        system["contracts"] = [{
            "id": "CONTRACT-ONE",
            "kind": "json_schema",
            "path": "contracts/one.json",
            "version": "1",
            "role": "consumer",
            "compatibility": "exact",
        }]
        root = self._repo(system, _rules())
        (root / "contracts").mkdir()
        self._write(root / "contracts/one.json", _json_schema({"id": {"type": "string"}}))
        snapshot = ARCH.load_architecture(root)
        with mock.patch.object(ARCH.os, "O_NOFOLLOW", 0):
            with self.assertRaisesRegex(ARCH.ArchitectureError, "no-follow"):
                ARCH.load_architecture(root)
            with self.assertRaisesRegex(ARCH.ArchitectureError, "no-follow"):
                ARCH._load_schema(root, ARCH.SYSTEM_SCHEMA_PATH)
            with self.assertRaisesRegex(ARCH.ArchitectureError, "no-follow"):
                ARCH.contract_inventory(root, snapshot)
            self.assertEqual(
                ARCH._inspect_repository_path(root, "architecture/system.yaml", regular=True),
                "unsafe",
            )

    def test_generated_diagrams_reject_unavailable_nofollow_and_unsafe_files(self) -> None:
        root = self._repo()
        rendered = DIAGRAMS.render_diagrams(ARCH.load_architecture(root))
        self._write_diagram_fixture(root, rendered)
        generated = root / "architecture/generated"
        with mock.patch.object(ARCH.os, "O_NOFOLLOW", 0):
            with self.assertRaisesRegex(ARCH.ArchitectureError, "no-follow"):
                DIAGRAMS.compare_generated(root, rendered)

        context = generated / "context.mmd"
        context.write_bytes(b"x" * (len(rendered["context"].encode()) + 2))
        with self.assertRaisesRegex(ARCH.ArchitectureError, "byte limit"):
            DIAGRAMS.compare_generated(root, rendered)
        context.unlink()
        os.mkfifo(context)
        with self.assertRaisesRegex(ARCH.ArchitectureError, "regular file|safely read"):
            DIAGRAMS.compare_generated(root, rendered)

    def test_generated_diagrams_never_follow_ancestor_or_final_symlinks(self) -> None:
        root = self._repo()
        rendered = DIAGRAMS.render_diagrams(ARCH.load_architecture(root))
        outside_temp = tempfile.TemporaryDirectory()
        self.addCleanup(outside_temp.cleanup)
        outside = Path(outside_temp.name)
        generated = root / "architecture/generated"
        generated.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ARCH.ArchitectureError):
            DIAGRAMS.compare_generated(root, rendered)
        self.assertEqual(tuple(outside.iterdir()), ())

        generated.unlink()
        generated.mkdir()
        target = outside / "target.mmd"
        target.write_text("outside\n", encoding="utf-8")
        (generated / "context.mmd").symlink_to(target)
        with self.assertRaises(ARCH.ArchitectureError):
            DIAGRAMS.compare_generated(root, rendered)
        self.assertEqual(target.read_text(encoding="utf-8"), "outside\n")

    def test_generated_diagram_compare_rejects_directory_swap_without_outside_read(self) -> None:
        root = self._repo()
        rendered = DIAGRAMS.render_diagrams(ARCH.load_architecture(root))
        self._write_diagram_fixture(root, rendered)
        generated = root / "architecture/generated"
        original = root / "architecture/generated-original"
        outside_temp = tempfile.TemporaryDirectory()
        self.addCleanup(outside_temp.cleanup)
        outside = Path(outside_temp.name)
        sentinel = outside / "context.mmd"
        sentinel.write_text("outside-sensitive-content\n", encoding="utf-8")
        real_rename = os.rename
        real_read = DIAGRAMS._read_generated
        swapped = False

        def swapping_read(descriptor, filename, limit):
            nonlocal swapped
            if filename == "context.mmd" and not swapped:
                real_rename(generated, original)
                os.symlink(outside, generated, target_is_directory=True)
                swapped = True
            return real_read(descriptor, filename, limit)

        with mock.patch.object(DIAGRAMS, "_read_generated", side_effect=swapping_read):
            with self.assertRaisesRegex(ARCH.ArchitectureError, "changed"):
                DIAGRAMS.compare_generated(root, rendered)
        self.assertTrue(swapped)
        self.assertEqual(sentinel.read_text(encoding="utf-8"), "outside-sensitive-content\n")

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
        self.assertIn("NODE-GOVERNANCE-VALIDATOR", node_ids)
        self.assertIn("NODE-GOVERNANCE-REGISTRIES", node_ids)
        self.assertNotIn("NODE-FACTORY-CONTROL-PLANE", node_ids)
        governance_validator = next(
            node
            for node in snapshot.system["nodes"]
            if node["id"] == "NODE-GOVERNANCE-VALIDATOR"
        )
        governance_registries = next(
            node
            for node in snapshot.system["nodes"]
            if node["id"] == "NODE-GOVERNANCE-REGISTRIES"
        )
        self.assertEqual(governance_validator["runtime"]["network"], "none")
        self.assertEqual(governance_registries["runtime"]["kind"], "none")
        self.assertEqual(governance_registries["runtime"]["network"], "none")
        self.assertEqual(governance_validator["secrets"], [])
        self.assertEqual(governance_registries["secrets"], [])
        docker_edge = next(
            edge
            for edge in snapshot.system["edges"]
            if edge["from"] == "NODE-TRUST-CI-WORKER"
            and edge["to"] == "NODE-DOCKER-ENGINE"
        )
        self.assertEqual(docker_edge["protocol"], "docker_api")
        self.assertEqual(docker_edge["authentication"], "none")
        self.assertEqual(docker_edge["network_policy"], "local_only")
        compose_owners = [
            node["id"]
            for node in snapshot.system["nodes"]
            if "trust-ci/compose.yaml" in node["repository_paths"]
        ]
        self.assertEqual(compose_owners, ["NODE-TRUST-CI-WORKER"])
        owners = {
            path: node["id"]
            for node in snapshot.system["nodes"]
            for path in node["repository_paths"]
        }
        self.assertEqual(
            owners["trust-ci/src/adaptive_trust_ci/runner.py"],
            "NODE-TRUST-CI-WORKER",
        )
        worker_source = (ROOT / "trust-ci/src/adaptive_trust_ci/worker.py").read_text()
        runner_source = (ROOT / "trust-ci/src/adaptive_trust_ci/runner.py").read_text()
        self.assertIn("from .runner import JobRunner", worker_source)
        self.assertIn("self.store.has_valid_approval", runner_source)
        self.assertIn("self.store.record_attestation", runner_source)
        edges = {edge["id"]: edge for edge in snapshot.system["edges"]}
        self.assertEqual(
            set(edges["EDGE-API-POSTGRES"]["allowed_data"]),
            {"DATA-APPROVAL", "DATA-ATTESTATION", "DATA-JOB-STATE"},
        )
        self.assertEqual(
            set(edges["EDGE-WORKER-POSTGRES"]["allowed_data"]),
            {"DATA-APPROVAL", "DATA-ATTESTATION", "DATA-JOB-STATE"},
        )
        self.assertTrue(
            all(node["runtime"]["evidence"] == "source_described" for node in snapshot.system["nodes"])
        )
        self.assertEqual(ARCH.validate_repository_drift(ROOT, snapshot), ())
        records = ARCH.contract_inventory(ROOT, snapshot)
        self.assertEqual(len(records), 33)
        self.assertNotIn(".gitkeep", {record.path for record in records})
        self.assertFalse(any(record.path.startswith("examples/") for record in records))
        documents = {record.id: record.document for record in records}
        factory_api = next(record for record in records if record.id == "CONTRACT-FACTORY-CONTROL-OPENAPI")
        self.assertEqual(factory_api.kind, "openapi")
        self.assertEqual(factory_api.role, "bidirectional")
        self.assertNotIn("/v1/providers/run", documents[factory_api.id]["paths"])
        semantic_records = {
            record.id: (record.kind, record.role, record.compatibility, record.path)
            for record in records
            if "SEMANTIC" in record.id
        }
        self.assertEqual(
            set(semantic_records),
            {
                "CONTRACT-FACTORY-EXECUTION-SEMANTIC-BINDING-V1",
                "CONTRACT-FACTORY-EXECUTION-SEMANTIC-INPUTS-V1",
                "CONTRACT-FACTORY-SEMANTIC-COVERAGE-V1",
                "CONTRACT-FACTORY-SEMANTIC-FINDING-V1",
                "CONTRACT-FACTORY-SEMANTIC-OPENAPI",
                "CONTRACT-FACTORY-SEMANTIC-REPAIR-DIRECTIVE-V1",
                "CONTRACT-FACTORY-SEMANTIC-SUBJECT-V1",
                "CONTRACT-FACTORY-SEMANTIC-VERDICT-V1",
            },
        )
        semantic_node = next(
            node
            for node in snapshot.system["nodes"]
            if node["id"] == "NODE-FACTORY-SEMANTIC-VALIDATION"
        )
        self.assertEqual(
            set(semantic_node["public_contracts"]),
            {
                key
                for key, (kind, _role, _compatibility, _path) in semantic_records.items()
                if key.startswith("CONTRACT-FACTORY-SEMANTIC-")
                and kind == "json_schema"
            },
        )
        landing_records = {
            record.id: (record.kind, record.role, record.compatibility, record.path)
            for record in records
            if "LANDING" in record.id
        }
        self.assertEqual(
            set(landing_records),
            {
                "CONTRACT-FACTORY-LANDING-ATTEMPT-V1",
                "CONTRACT-FACTORY-LANDING-EVALUATION-V1",
                "CONTRACT-FACTORY-LANDING-INPUT-V1",
                "CONTRACT-FACTORY-LANDING-OPENAPI-V1",
                "CONTRACT-FACTORY-LANDING-PROVIDER-EVIDENCE-V1",
                "CONTRACT-FACTORY-LANDING-SITE-ARTIFACT-V1",
                "CONTRACT-FACTORY-LANDING-SPEC-V1",
            },
        )
        landing_node = next(
            node
            for node in snapshot.system["nodes"]
            if node["id"] == "NODE-FACTORY-LANDING-DOGFOOD"
        )
        self.assertEqual(
            set(landing_node["public_contracts"]),
            set(landing_records) - {"CONTRACT-FACTORY-LANDING-OPENAPI-V1"},
        )
        landing_edge = next(
            edge
            for edge in snapshot.system["edges"]
            if edge["id"] == "EDGE-FACTORY-API-LANDING-DOGFOOD"
        )
        self.assertEqual(landing_edge["network_policy"], "no_network")
        self.assertEqual(landing_edge["allowed_data"], ["DATA-FACTORY-LANDING-INPUT"])
        governance_handoff = next(
            record
            for record in records
            if record.id == "CONTRACT-GOVERNANCE-HANDOFF-V1"
        )
        self.assertEqual(governance_handoff.kind, "json_schema")
        self.assertEqual(governance_handoff.role, "producer")
        self.assertEqual(
            governance_handoff.compatibility,
            "producer_accepted_by_old",
        )
        self.assertEqual(governance_handoff.version, "1")
        self.assertEqual(
            set(documents["CONTRACT-GOVERNANCE-HANDOFF-V1"]["required"]),
            {
                "architecture_digest",
                "exact_base_sha",
                "exact_head_sha",
                "governance_contract_version",
                "governance_digest",
                "governance_evidence_digest",
            },
        )
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
            ("header", "X-GitHub-Event", False),
            {
                (parameter["in"], parameter["name"], parameter["required"])
                for parameter in webhook_parameters
            },
        )
        webhook_body = openapi["paths"]["/webhooks/github"]["post"]["requestBody"]
        self.assertFalse(webhook_body["required"])
        self.assertEqual(
            set(webhook_body["content"]),
            {"application/json", "application/octet-stream"},
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
            "compatible",
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
        (root / "hidden.example").mkdir()
        (root / "hidden.example/evil.py").write_text("VALUE = 4\n", encoding="utf-8")
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
                ("undeclared_source", "hidden.example/evil.py"),
                ("undeclared_source", "lib/new_component.py"),
                ("undeclared_source", "src/undeclared.py"),
                ("unsupported_source_artifact", "src/native.rs"),
            ],
        )

    def test_repository_drift_ignores_exact_dot_venv_components_on_repeated_runs(self) -> None:
        root = self._repo()
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        for owner in ("factory", "trust-ci"):
            environment = root / owner / ".venv"
            (environment / "lib").mkdir(parents=True)
            (environment / "bin").mkdir()
            (environment / "lib/dependency.py").write_text(
                "VALUE = 'tooling-only'\n", encoding="utf-8"
            )
            (environment / "bin/python").symlink_to("../lib/dependency.py")

        (root / "factory/.venv-project").mkdir()
        (root / "factory/.venv-project/project.py").write_text(
            "VALUE = 'repository-source'\n", encoding="utf-8"
        )
        (root / "factory/venv").mkdir()
        (root / "factory/venv/project.py").write_text(
            "VALUE = 'repository-source'\n", encoding="utf-8"
        )
        snapshot = ARCH.load_architecture(root)
        expected = [
            ("undeclared_source", "factory/.venv-project/project.py"),
            ("undeclared_source", "factory/venv/project.py"),
        ]

        for run in range(2):
            with self.subTest(run=run):
                findings = ARCH.validate_repository_drift(root, snapshot)
                self.assertEqual(
                    [(finding.code, finding.path) for finding in findings], expected
                )

    def test_repository_drift_detects_force_added_source_under_dot_venv(self) -> None:
        root = self._repo()
        source = root / "factory/.venv/project.py"
        source.parent.mkdir(parents=True)
        source.write_text("VALUE = 'repository-source'\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(
            ["git", "add", "-f", "factory/.venv/project.py"], cwd=root, check=True
        )

        findings = ARCH.validate_repository_drift(root, ARCH.load_architecture(root))

        self.assertEqual(
            [(finding.code, finding.path) for finding in findings],
            [("undeclared_source", "factory/.venv/project.py")],
        )

    def test_repository_drift_detects_force_added_symlink_under_dot_venv(self) -> None:
        root = self._repo()
        (root / "payload.txt").write_text("payload\n", encoding="utf-8")
        link = root / "factory/.venv/bin/python"
        link.parent.mkdir(parents=True)
        link.symlink_to("../../../payload.txt")
        subprocess.run(["git", "init", "-q"], cwd=root, check=True)
        subprocess.run(
            ["git", "add", "-f", "factory/.venv/bin/python"], cwd=root, check=True
        )

        findings = ARCH.validate_repository_drift(root, ARCH.load_architecture(root))

        self.assertEqual(
            [(finding.code, finding.path) for finding in findings],
            [("unsafe_repository_artifact", "factory/.venv/bin/python")],
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

    def test_repository_drift_rejects_directory_to_symlink_swap(self) -> None:
        root = self._repo()
        victim = root / "victim"
        victim.mkdir()
        (victim / "inside.py").write_text("VALUE = 1\n", encoding="utf-8")
        outside_temp = tempfile.TemporaryDirectory()
        self.addCleanup(outside_temp.cleanup)
        outside = Path(outside_temp.name)
        (outside / "outside.py").write_text("VALUE = 2\n", encoding="utf-8")
        real_scandir = os.scandir
        swapped = False

        class SwapAfterRootScan:
            def __init__(self, argument):
                self._iterator = real_scandir(argument)

            def __enter__(self):
                return self._iterator.__enter__()

            def __exit__(self, exc_type, exc_value, traceback):
                nonlocal swapped
                result = self._iterator.__exit__(exc_type, exc_value, traceback)
                if not swapped:
                    victim.rename(root / "victim-original")
                    victim.symlink_to(outside, target_is_directory=True)
                    swapped = True
                return result

        with mock.patch.object(ARCH.os, "scandir", side_effect=SwapAfterRootScan):
            with self.assertRaisesRegex(ARCH.ArchitectureError, "changed|symlink|no-follow"):
                ARCH.validate_repository_drift(root, ARCH.load_architecture(root))
        self.assertTrue(swapped)

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

    def test_governance_handoff_closed_schema_is_supported_in_self_comparison(self) -> None:
        snapshot = ARCH.load_architecture(ROOT)
        record = next(
            item
            for item in ARCH.contract_inventory(ROOT, snapshot)
            if item.id == "CONTRACT-GOVERNANCE-HANDOFF-V1"
        )

        result = ARCH.compare_contracts(record, record, record.compatibility)

        self.assertEqual(result.status, "compatible")
        self.assertEqual(result.reasons, ())

    def test_governance_handoff_exception_rejects_changed_supported_copies(self) -> None:
        snapshot = ARCH.load_architecture(ROOT)
        frozen = next(
            item
            for item in ARCH.contract_inventory(ROOT, snapshot)
            if item.id == "CONTRACT-GOVERNANCE-HANDOFF-V1"
        )
        supported_copy = copy.deepcopy(frozen.document)
        supported_copy.pop("$defs")
        for property_schema in supported_copy["properties"].values():
            if "$ref" in property_schema:
                property_schema.clear()
                property_schema["type"] = "string"
            property_schema.pop("const", None)
        altered_supported_copy = copy.deepcopy(supported_copy)
        altered_supported_copy["properties"]["architecture_digest"]["type"] = [
            "string",
            "null",
        ]

        for label, changed_document in (
            ("constraints removed", supported_copy),
            ("supported copy altered", altered_supported_copy),
        ):
            changed = self._record(changed_document)
            changed = ARCH.ContractRecord(
                id=frozen.id,
                kind=frozen.kind,
                path=frozen.path,
                version=frozen.version,
                role=frozen.role,
                compatibility=frozen.compatibility,
                digest=changed.digest,
                document=changed.document,
            )
            for direction, base, head in (
                ("frozen base", frozen, changed),
                ("frozen head", changed, frozen),
            ):
                with self.subTest(label=label, direction=direction):
                    result = ARCH.compare_contracts(
                        base, head, "consumer_accepts_old"
                    )
                    self.assertEqual(result.status, "unsupported")
                    self.assertEqual(result.reasons, ("unsupported_schema_keyword",))

    def test_schema_type_arrays_are_bounded_sets_with_directional_semantics(self) -> None:
        string = {"type": "string"}
        nullable = {"type": ["string", "null"]}
        reordered = {"type": ["null", "string"]}
        cases = (
            ("consumer reordered", nullable, reordered, "consumer_accepts_old", "compatible"),
            ("consumer widened", string, nullable, "consumer_accepts_old", "compatible"),
            ("consumer narrowed", nullable, string, "consumer_accepts_old", "incompatible"),
            ("producer narrowed", nullable, string, "producer_accepted_by_old", "compatible"),
            ("producer widened", string, nullable, "producer_accepted_by_old", "incompatible"),
        )
        for label, base, head, policy, status in cases:
            with self.subTest(label=label):
                self.assertEqual(
                    ARCH.compare_contracts(
                        self._record(base), self._record(head), policy
                    ).status,
                    status,
                )

        for malformed in (
            {"type": []},
            {"type": ["string", "string"]},
            {"type": ["string", "future"]},
            {"type": ["string", 1]},
            {"$ref": "#/$defs/string"},
        ):
            with self.subTest(malformed=malformed):
                self.assertEqual(
                    ARCH.compare_contracts(
                        self._record(malformed),
                        self._record(malformed),
                        "consumer_accepts_old",
                    ).status,
                    "unsupported",
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

    def test_openapi_validates_present_operation_ids_and_path_parameters(self) -> None:
        duplicate = _openapi(
            {"operationId": "sameOperation", "responses": {"200": {"description": "ok"}}}
        )
        duplicate["paths"]["/other"] = copy.deepcopy(duplicate["paths"]["/items"])
        malformed = _openapi(
            {"operationId": "", "responses": {"200": {"description": "ok"}}}
        )
        missing_path_parameter = _openapi()
        missing_path_parameter["paths"] = {
            "/items/{item_id}": missing_path_parameter["paths"]["/items"]
        }
        extra_path_parameter = _openapi()
        extra_path_parameter["paths"]["/items"]["parameters"] = [
            {
                "in": "path",
                "name": "item_id",
                "required": True,
                "schema": {"type": "string"},
            }
        ]
        for document in (
            duplicate,
            malformed,
            missing_path_parameter,
            extra_path_parameter,
        ):
            with self.subTest(document=document):
                result = ARCH.compare_contracts(
                    self._record(_openapi(), kind="openapi"),
                    self._record(document, kind="openapi"),
                    "bidirectional",
                )
                self.assertEqual(result.status, "unsupported")
                self.assertIn("unsupported_openapi_construct", result.reasons)

    def test_openapi_operation_ids_have_no_undocumented_charset_or_length_cap(self) -> None:
        for operation_id in ("operation id/λ", "x" * 1024):
            document = _openapi(
                {
                    "operationId": operation_id,
                    "responses": {"200": {"description": "ok"}},
                }
            )
            with self.subTest(operation_id=operation_id):
                result = ARCH.compare_contracts(
                    self._record(document, kind="openapi"),
                    self._record(document, kind="openapi"),
                    "bidirectional",
                )
                self.assertEqual(result.status, "compatible")

    def test_openapi_rejects_invalid_header_names_and_ambiguous_template_siblings(self) -> None:
        base = _openapi()
        for header_name in ("Bad Header", "X-Ünicode", ":authority"):
            malformed = copy.deepcopy(base)
            malformed["paths"]["/items"]["get"]["responses"]["200"]["headers"] = {
                header_name: {"schema": {"type": "string"}}
            }
            with self.subTest(header_name=header_name):
                result = ARCH.compare_contracts(
                    self._record(base, kind="openapi"),
                    self._record(malformed, kind="openapi"),
                    "bidirectional",
                )
                self.assertEqual(result.status, "unsupported")

        ambiguous = _openapi()
        ambiguous["paths"] = {
            f"/items/{{{name}}}": {
                "get": {
                    "parameters": [
                        {
                            "in": "path",
                            "name": name,
                            "required": True,
                            "schema": {"type": "string"},
                        }
                    ],
                    "responses": {"200": {"description": "ok"}},
                }
            }
            for name in ("id", "name")
        }
        result = ARCH.compare_contracts(
            self._record(base, kind="openapi"),
            self._record(ambiguous, kind="openapi"),
            "bidirectional",
        )
        self.assertEqual(result.status, "unsupported")

    def test_openapi_operation_id_and_response_headers_are_compatibility_checked(self) -> None:
        base = _openapi(
            {
                "operationId": "getItems",
                "responses": {
                    "200": {
                        "description": "ok",
                        "headers": {
                            "X-Correlation-ID": {
                                "required": True,
                                "schema": {"type": "string", "minLength": 1},
                            },
                            "X-Optional": {
                                "required": False,
                                "schema": {"type": "string"},
                            },
                        },
                    }
                },
            }
        )
        case_only = copy.deepcopy(base)
        headers = case_only["paths"]["/items"]["get"]["responses"]["200"]["headers"]
        headers["x-correlation-id"] = headers.pop("X-Correlation-ID")
        optional = headers.pop("X-Optional")
        headers["x-optional"] = optional
        self.assertEqual(
            ARCH.compare_contracts(
                self._record(base, kind="openapi"),
                self._record(case_only, kind="openapi"),
                "bidirectional",
            ).status,
            "compatible",
        )

        changed_id = copy.deepcopy(base)
        changed_id["paths"]["/items"]["get"]["operationId"] = "listItems"
        removed_required = copy.deepcopy(base)
        del removed_required["paths"]["/items"]["get"]["responses"]["200"]["headers"][
            "X-Correlation-ID"
        ]
        demoted_required = copy.deepcopy(base)
        demoted_required["paths"]["/items"]["get"]["responses"]["200"]["headers"][
            "X-Correlation-ID"
        ]["required"] = False
        changed_schema = copy.deepcopy(base)
        changed_schema["paths"]["/items"]["get"]["responses"]["200"]["headers"][
            "X-Correlation-ID"
        ]["schema"]["type"] = "integer"
        for label, head, reason in (
            ("operation id", changed_id, "changed_operation_id"),
            ("removed required header", removed_required, "removed_response_header"),
            ("demoted required header", demoted_required, "changed_response_header_requirement"),
            ("changed header schema", changed_schema, "changed_type"),
        ):
            result = ARCH.compare_contracts(
                self._record(base, kind="openapi"),
                self._record(head, kind="openapi"),
                "bidirectional",
            )
            with self.subTest(label=label):
                self.assertEqual(result.status, "incompatible")
                self.assertIn(reason, result.reasons)

        added_optional = copy.deepcopy(base)
        added_optional["paths"]["/items"]["get"]["responses"]["200"]["headers"][
            "X-New"
        ] = {"required": False, "schema": {"type": "string"}}
        result = ARCH.compare_contracts(
            self._record(base, kind="openapi"),
            self._record(added_optional, kind="openapi"),
            "bidirectional",
        )
        self.assertEqual(result.status, "compatible")

    def test_openapi_comparison_rejects_optional_webhook_inputs_becoming_required(
        self,
    ) -> None:
        base = _openapi(
            {
                "parameters": [
                    {
                        "in": "header",
                        "name": "X-GitHub-Event",
                        "required": False,
                        "schema": {"type": "string"},
                    }
                ],
                "requestBody": {
                    "content": {
                        "application/json": {
                            "schema": {"additionalProperties": True, "type": "object"}
                        }
                    },
                    "required": False,
                },
                "responses": {"200": {"description": "accepted or ignored"}},
            }
        )
        required_header = copy.deepcopy(base)
        required_header["paths"]["/items"]["get"]["parameters"][0]["required"] = True
        required_body = copy.deepcopy(base)
        required_body["paths"]["/items"]["get"]["requestBody"]["required"] = True
        for label, head in (("header", required_header), ("body", required_body)):
            result = ARCH.compare_contracts(
                self._record(base, kind="openapi"),
                self._record(head, kind="openapi"),
                "bidirectional",
            )
            with self.subTest(label=label):
                self.assertEqual(result.status, "incompatible")
                self.assertIn("new_required_input", result.reasons)

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
        unsupported["properties"]["name"]["dependentRequired"] = {
            "name": ["future"]
        }
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

    def test_contract_comparison_rejects_unencodable_root_dependency_and_depth(self) -> None:
        malformed_root = self._record(
            {"type": "string", "description": "\ud800"}
        )
        self.assertEqual(
            ARCH.compare_contracts(
                malformed_root, malformed_root, malformed_root.compatibility
            ).status,
            "unsupported",
        )

        event = ARCH.ContractRecord(
            "CONTRACT-EVENT",
            "event",
            "engineering/contracts/event.json",
            "1",
            "consumer",
            "consumer_accepts_old",
            "1" * 64,
            {"$ref": "common.json"},
        )
        common_base = ARCH.ContractRecord(
            "CONTRACT-COMMON",
            "json_schema",
            "engineering/contracts/common.json",
            "1",
            "producer",
            "producer_accepted_by_old",
            "2" * 64,
            {"type": "string", "description": "safe"},
        )
        common_head = ARCH.ContractRecord(
            common_base.id,
            common_base.kind,
            common_base.path,
            common_base.version,
            common_base.role,
            common_base.compatibility,
            "3" * 64,
            {"type": "string", "description": "\ud800"},
        )
        self.assertEqual(
            ARCH.compare_contracts(
                event,
                event,
                event.compatibility,
                base_inventory=(event, common_base),
                head_inventory=(event, common_head),
            ).status,
            "unsupported",
        )

        too_deep: dict = {"type": "string"}
        for _ in range(10_000):
            too_deep = {"type": "array", "items": too_deep}
        deep_record = self._record(too_deep)
        self.assertEqual(
            ARCH.compare_contracts(
                deep_record, deep_record, deep_record.compatibility
            ).status,
            "unsupported",
        )

    def test_event_meaning_follows_bounded_declared_multihop_schema_refs(self) -> None:
        common_base = ARCH.ContractRecord(
            "CONTRACT-COMMON", "json_schema", "engineering/contracts/common.json",
            "1", "producer", "producer_accepted_by_old", "1" * 64,
            {
                "type": "object",
                "description": "money is measured in cents",
                "properties": {
                    "amount": {
                        "oneOf": [
                            {"type": "integer", "description": "whole cents"},
                            {"type": "null"},
                        ]
                    }
                },
            },
        )
        common_head = ARCH.ContractRecord(
            common_base.id, common_base.kind, common_base.path, common_base.version,
            common_base.role, common_base.compatibility, "2" * 64,
            {
                **common_base.document,
                "description": "money is measured in dollars",
            },
        )
        envelope = ARCH.ContractRecord(
            "CONTRACT-ENVELOPE", "json_schema",
            "engineering/contracts/envelope.json", "1", "producer",
            "producer_accepted_by_old", "3" * 64, {"$ref": "common.json"},
        )
        event = ARCH.ContractRecord(
            "CONTRACT-EVENT", "event", "engineering/contracts/event.json", "1",
            "consumer", "consumer_accepts_old", "4" * 64,
            {"$ref": "envelope.json"},
        )
        for head_version in ("1", "2"):
            event_head = ARCH.ContractRecord(
                event.id, event.kind, event.path, head_version, event.role,
                event.compatibility, event.digest, event.document,
            )
            result = ARCH.compare_contracts(
                event,
                event_head,
                event.compatibility,
                base_inventory=(event, envelope, common_base),
                head_inventory=(event_head, envelope, common_head),
            )
            with self.subTest(head_version=head_version):
                self.assertEqual(result.status, "incompatible")
                self.assertIn("event_meaning_changed", result.reasons)

        bounded_base = {
            "type": "object",
            "description": "base meaning",
            "properties": {
                f"value_{index}": {
                    "type": "string",
                    "description": f"meaning {index}",
                }
                for index in range(4)
            },
        }
        bounded_head = copy.deepcopy(bounded_base)
        bounded_head["description"] = "changed meaning"
        with mock.patch.object(ARCH, "MAX_PARSED_NODES", 8):
            bounded_result = ARCH.compare_contracts(
                self._record(bounded_base, kind="event"),
                self._record(bounded_head, kind="event"),
                "consumer_accepts_old",
            )
        self.assertEqual(bounded_result.status, "unsupported")

    def test_rich_schema_subset_is_supported_but_composition_changes_are_conservative(self) -> None:
        rich = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "https://adaptive-grok.invalid/contracts/rich.json",
            "title": "Rich contract",
            "type": "object",
            "additionalProperties": False,
            "required": ["kind", "values"],
            "properties": {
                "kind": {"const": "current"},
                "values": {
                    "type": "array",
                    "uniqueItems": True,
                    "items": {
                        "oneOf": [
                            {"type": "string"},
                            {"type": "integer"},
                        ]
                    },
                },
            },
            "allOf": [
                {
                    "if": {
                        "properties": {"kind": {"const": "current"}},
                    },
                    "then": {"required": ["values"]},
                }
            ],
        }
        self.assertEqual(
            ARCH.compare_contracts(
                self._record(rich), self._record(copy.deepcopy(rich)),
                "consumer_accepts_old",
            ).status,
            "compatible",
        )
        changes = []
        changed_const = copy.deepcopy(rich)
        changed_const["properties"]["kind"]["const"] = "next"
        changes.append(changed_const)
        changed_composition = copy.deepcopy(rich)
        changed_composition["properties"]["values"]["items"]["oneOf"].append(
            {"type": "boolean"}
        )
        changes.append(changed_composition)
        changed_id = copy.deepcopy(rich)
        changed_id["$id"] = "https://adaptive-grok.invalid/contracts/other.json"
        changes.append(changed_id)
        for changed in changes:
            with self.subTest(changed=changed):
                self.assertEqual(
                    ARCH.compare_contracts(
                        self._record(rich), self._record(changed),
                        "consumer_accepts_old",
                    ).status,
                    "incompatible",
                )
        without_unique = copy.deepcopy(rich)
        without_unique["properties"]["values"]["uniqueItems"] = False
        self.assertEqual(
            ARCH.compare_contracts(
                self._record(rich), self._record(without_unique),
                "consumer_accepts_old",
            ).status,
            "compatible",
        )
        self.assertEqual(
            ARCH.compare_contracts(
                self._record(without_unique), self._record(rich),
                "consumer_accepts_old",
            ).status,
            "incompatible",
        )
        without_const = copy.deepcopy(rich)
        without_const["properties"]["kind"].pop("const")
        self.assertEqual(
            ARCH.compare_contracts(
                self._record(without_const), self._record(rich),
                "consumer_accepts_old",
            ).status,
            "incompatible",
        )
        self.assertEqual(
            ARCH.compare_contracts(
                self._record(rich), self._record(without_const),
                "consumer_accepts_old",
            ).status,
            "compatible",
        )
        self.assertEqual(
            ARCH.compare_contracts(
                self._record(rich), self._record(without_const),
                "producer_accepted_by_old",
            ).status,
            "incompatible",
        )
        changed_schema = copy.deepcopy(rich)
        changed_schema["$schema"] = "https://json-schema.org/draft/next/schema"
        self.assertEqual(
            ARCH.compare_contracts(
                self._record(rich), self._record(changed_schema),
                "consumer_accepts_old",
            ).status,
            "incompatible",
        )
        self.assertEqual(
            ARCH.compare_contracts(
                self._record(rich), self._record(without_unique),
                "producer_accepted_by_old",
            ).status,
            "incompatible",
        )

    def test_schema_refs_resolve_only_from_bounded_declared_in_memory_inventory(self) -> None:
        packet_base = self._record(
            _json_schema({"value": {"type": "string"}}, ["value"])
        )
        packet_base = ARCH.ContractRecord(
            "CONTRACT-PACKET", "json_schema", "contracts/packet.json", "1",
            "producer", "producer_accepted_by_old", "1" * 64,
            packet_base.document,
        )
        packet_head = ARCH.ContractRecord(
            packet_base.id, packet_base.kind, packet_base.path, packet_base.version,
            packet_base.role, packet_base.compatibility, "2" * 64,
            _json_schema({"value": {"type": "integer"}}, ["value"]),
        )
        invocation_document = _json_schema(
            {"packet": {"$ref": "packet.json"}}, ["packet"]
        )
        invocation_base = ARCH.ContractRecord(
            "CONTRACT-INVOKE", "json_schema", "contracts/invoke.json", "1",
            "producer", "producer_accepted_by_old", "3" * 64,
            invocation_document,
        )
        invocation_head = copy.deepcopy(invocation_base)
        self.assertEqual(
            ARCH.compare_contracts(
                invocation_base,
                invocation_head,
                "producer_accepted_by_old",
                base_inventory=(invocation_base, packet_base),
                head_inventory=(invocation_head, packet_base),
            ).status,
            "compatible",
        )
        result = ARCH.compare_contracts(
            invocation_base,
            invocation_head,
            "producer_accepted_by_old",
            base_inventory=(invocation_base, packet_base),
            head_inventory=(invocation_head, packet_head),
        )
        self.assertEqual(result.status, "incompatible")

        envelope = ARCH.ContractRecord(
            "CONTRACT-ENVELOPE", "json_schema", "contracts/envelope.json", "1",
            "producer", "producer_accepted_by_old", "5" * 64,
            {"$ref": "packet.json"},
        )
        chained_document = _json_schema(
            {"envelope": {"$ref": "envelope.json"}}, ["envelope"]
        )
        chained_invocation = ARCH.ContractRecord(
            invocation_base.id, invocation_base.kind, invocation_base.path,
            invocation_base.version, invocation_base.role,
            invocation_base.compatibility, "6" * 64, chained_document,
        )
        self.assertEqual(
            ARCH.compare_contracts(
                chained_invocation,
                chained_invocation,
                chained_invocation.compatibility,
                base_inventory=(chained_invocation, envelope, packet_base),
                head_inventory=(chained_invocation, envelope, packet_head),
            ).status,
            "incompatible",
        )

        unsafe_refs = (
            "https://example.invalid/schema.json",
            "/absolute/schema.json",
            "packet.json?variant=1",
            "packet%2ejson",
            "../../packet.json",
            "#/components/schemas/Missing",
            "#/components/schemas/Bad~0Name",
        )
        for reference in unsafe_refs:
            document = _json_schema({"packet": {"$ref": reference}}, ["packet"])
            record = ARCH.ContractRecord(
                invocation_base.id, invocation_base.kind, invocation_base.path,
                invocation_base.version, invocation_base.role,
                invocation_base.compatibility, invocation_base.digest, document,
            )
            with self.subTest(reference=reference):
                self.assertEqual(
                    ARCH.compare_contracts(
                        record,
                        record,
                        "producer_accepted_by_old",
                        base_inventory=(record, packet_base),
                        head_inventory=(record, packet_base),
                    ).status,
                    "unsupported",
                )
        ref_with_sibling = _json_schema(
            {"packet": {"$ref": "packet.json", "description": "unsafe sibling"}},
            ["packet"],
        )
        sibling_record = ARCH.ContractRecord(
            invocation_base.id, invocation_base.kind, invocation_base.path,
            invocation_base.version, invocation_base.role,
            invocation_base.compatibility, invocation_base.digest, ref_with_sibling,
        )
        self.assertEqual(
            ARCH.compare_contracts(
                sibling_record,
                sibling_record,
                sibling_record.compatibility,
                base_inventory=(sibling_record, packet_base),
                head_inventory=(sibling_record, packet_base),
            ).status,
            "unsupported",
        )

        conflicting = ARCH.ContractRecord(
            "CONTRACT-CONFLICT", "json_schema", invocation_base.path, "1",
            "producer", "producer_accepted_by_old", "4" * 64,
            _json_schema({}),
        )
        self.assertEqual(
            ARCH.compare_contracts(
                invocation_base,
                invocation_base,
                invocation_base.compatibility,
                base_inventory=(invocation_base, conflicting, packet_base),
                head_inventory=(invocation_base, packet_base),
            ).status,
            "unsupported",
        )

        metadata_changes = {
            "version": {"version": "2"},
            "role": {"role": "consumer"},
            "compatibility": {"compatibility": "consumer_accepts_old"},
            "digest": {"digest": "9" * 64},
        }
        baseline = {
            "id": invocation_base.id,
            "kind": invocation_base.kind,
            "path": invocation_base.path,
            "version": invocation_base.version,
            "role": invocation_base.role,
            "compatibility": invocation_base.compatibility,
            "digest": invocation_base.digest,
            "document": invocation_base.document,
        }
        for field, change in metadata_changes.items():
            inventory_current = ARCH.ContractRecord(**(baseline | change))
            with self.subTest(conflicting_current_metadata=field):
                self.assertEqual(
                    ARCH.compare_contracts(
                        invocation_base,
                        invocation_base,
                        invocation_base.compatibility,
                        base_inventory=(inventory_current, packet_base),
                        head_inventory=(invocation_base, packet_base),
                    ).status,
                    "unsupported",
                )

        conflicting_document = copy.deepcopy(invocation_base.document)
        conflicting_document["description"] = "different current document"
        inventory_current = ARCH.ContractRecord(
            **(baseline | {"document": conflicting_document})
        )
        self.assertEqual(
            ARCH.compare_contracts(
                invocation_base,
                invocation_base,
                invocation_base.compatibility,
                base_inventory=(inventory_current, packet_base),
                head_inventory=(invocation_base, packet_base),
            ).status,
            "unsupported",
        )

    def test_openapi_component_refs_headers_and_unreferenced_schemas_are_closed(self) -> None:
        base = _openapi(
            {
                "responses": {
                    "200": {
                        "description": "ok",
                        "headers": {
                            "X-Result": {
                                "description": "bounded result",
                                "required": True,
                                "schema": {"type": "string", "maxLength": 8},
                            }
                        },
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/Result"}
                            }
                        },
                    }
                }
            }
        )
        base["components"] = {
            "schemas": {
                "Result": _json_schema({"value": {"type": "string"}}, ["value"]),
                "Unreferenced": {"type": "string", "maxLength": 8},
            },
            "securitySchemes": {},
        }
        record = self._record(base, kind="openapi", compatibility="bidirectional")
        self.assertEqual(
            ARCH.compare_contracts(record, record, "bidirectional").status,
            "compatible",
        )

        changed_component = copy.deepcopy(base)
        changed_component["components"]["schemas"]["Unreferenced"]["maxLength"] = 9
        changed_header = copy.deepcopy(base)
        changed_header["paths"]["/items"]["get"]["responses"]["200"]["headers"][
            "X-Result"
        ]["required"] = False
        removed_header = copy.deepcopy(base)
        removed_header["paths"]["/items"]["get"]["responses"]["200"].pop("headers")
        for head, reason in (
            (changed_component, "widened_producer_output"),
            (changed_header, "changed_response_header_requirement"),
            (removed_header, "removed_response_header"),
        ):
            result = ARCH.compare_contracts(
                record,
                self._record(head, kind="openapi", compatibility="bidirectional"),
                "bidirectional",
            )
            with self.subTest(reason=reason):
                self.assertEqual(result.status, "incompatible")
                self.assertIn(reason, result.reasons)

        malformed_documents = []
        duplicate_header = copy.deepcopy(base)
        duplicate_header["paths"]["/items"]["get"]["responses"]["200"]["headers"][
            "x-result"
        ] = {"schema": {"type": "string"}}
        malformed_documents.append(duplicate_header)
        malformed_header = copy.deepcopy(base)
        malformed_header["paths"]["/items"]["get"]["responses"]["200"]["headers"] = {
            "Bad Header": {"schema": {"type": "string"}}
        }
        malformed_documents.append(malformed_header)
        malformed_request_header = copy.deepcopy(base)
        malformed_request_header["paths"]["/items"]["get"]["parameters"] = [
            {"in": "header", "name": "Bad Header", "schema": {"type": "string"}}
        ]
        malformed_documents.append(malformed_request_header)
        duplicate_request_header = copy.deepcopy(base)
        duplicate_request_header["paths"]["/items"]["get"]["parameters"] = [
            {"in": "header", "name": "X-Request", "schema": {"type": "string"}},
            {"in": "header", "name": "x-request", "schema": {"type": "string"}},
        ]
        malformed_documents.append(duplicate_request_header)
        malformed_api_key = copy.deepcopy(base)
        malformed_api_key["components"]["securitySchemes"] = {
            "HeaderAuth": {"type": "apiKey", "in": "header", "name": "Bad Header"}
        }
        malformed_documents.append(malformed_api_key)
        malformed_scheme_name = copy.deepcopy(base)
        malformed_scheme_name["components"]["securitySchemes"] = {
            "Bad Scheme": {"type": "http", "scheme": "bearer"}
        }
        malformed_documents.append(malformed_scheme_name)
        for malformed_http_scheme in ("bad scheme", "bad\nscheme"):
            malformed_scheme = copy.deepcopy(base)
            malformed_scheme["components"]["securitySchemes"] = {
                "HttpAuth": {"type": "http", "scheme": malformed_http_scheme}
            }
            malformed_documents.append(malformed_scheme)
        unsupported_component_headers = copy.deepcopy(base)
        unsupported_component_headers["components"]["headers"] = {
            "X-Shared": {"schema": {"type": "string"}}
        }
        malformed_documents.append(unsupported_component_headers)
        malformed_operation_id = copy.deepcopy(base)
        malformed_operation_id["paths"]["/items"]["get"]["operationId"] = "\ud800"
        malformed_documents.append(malformed_operation_id)
        dangling = copy.deepcopy(base)
        dangling["components"]["schemas"]["Result"] = {
            "$ref": "#/components/schemas/Missing"
        }
        malformed_documents.append(dangling)
        cycle = copy.deepcopy(base)
        cycle["components"]["schemas"].update(
            {
                "A": {"$ref": "#/components/schemas/B"},
                "B": {"$ref": "#/components/schemas/A"},
            }
        )
        malformed_documents.append(cycle)
        for malformed in malformed_documents:
            malformed_record = self._record(
                malformed, kind="openapi", compatibility="bidirectional"
            )
            with self.subTest(malformed=malformed):
                self.assertEqual(
                    ARCH.compare_contracts(
                        malformed_record, malformed_record, "bidirectional"
                    ).status,
                    "unsupported",
                )

        renamed_operation = copy.deepcopy(base)
        renamed_operation["paths"]["/items"]["get"]["operationId"] = "renamed"
        renamed_result = ARCH.compare_contracts(
            record,
            self._record(
                renamed_operation, kind="openapi", compatibility="bidirectional"
            ),
            "bidirectional",
        )
        self.assertEqual(renamed_result.status, "incompatible")
        self.assertIn("operation_identity_changed", renamed_result.reasons)

        duplicate_operation = copy.deepcopy(base)
        duplicate_operation["paths"]["/items"]["get"]["operationId"] = "duplicate"
        duplicate_operation["paths"]["/other"] = copy.deepcopy(
            duplicate_operation["paths"]["/items"]
        )
        duplicate_record = self._record(
            duplicate_operation, kind="openapi", compatibility="bidirectional"
        )
        self.assertEqual(
            ARCH.compare_contracts(
                duplicate_record, duplicate_record, "bidirectional"
            ).status,
            "unsupported",
        )
        empty_operation = copy.deepcopy(base)
        empty_operation["paths"]["/items"]["get"]["operationId"] = ""
        empty_record = self._record(
            empty_operation, kind="openapi", compatibility="bidirectional"
        )
        self.assertEqual(
            ARCH.compare_contracts(empty_record, empty_record, "bidirectional").status,
            "unsupported",
        )

        scheme_base = copy.deepcopy(base)
        scheme_base["components"]["securitySchemes"] = {
            "UnusedAuth": {"type": "http", "scheme": "bearer"}
        }
        scheme_record = self._record(
            scheme_base, kind="openapi", compatibility="bidirectional"
        )
        removed_scheme = copy.deepcopy(scheme_base)
        removed_scheme["components"]["securitySchemes"] = {}
        changed_scheme = copy.deepcopy(scheme_base)
        changed_scheme["components"]["securitySchemes"]["UnusedAuth"][
            "scheme"
        ] = "basic"
        added_scheme = copy.deepcopy(scheme_base)
        added_scheme["components"]["securitySchemes"]["OtherAuth"] = {
            "type": "apiKey",
            "in": "header",
            "name": "X-Other-Key",
        }
        for changed in (removed_scheme, changed_scheme, added_scheme):
            result = ARCH.compare_contracts(
                scheme_record,
                self._record(
                    changed, kind="openapi", compatibility="bidirectional"
                ),
                "bidirectional",
            )
            with self.subTest(security_schemes=changed["components"]):
                self.assertEqual(result.status, "incompatible")
                self.assertIn("changed_authentication", result.reasons)

    def test_openapi_non_schema_traversal_consumes_shared_work_budget(self) -> None:
        document = _openapi()
        document["paths"] = {
            f"/items/{index}": {
                "get": {
                    "operationId": f"getItem{index}",
                    "responses": {"200": {"description": "ok"}},
                }
            }
            for index in range(200)
        }
        record = self._record(
            document, kind="openapi", compatibility="bidirectional"
        )
        budget = [0]
        with mock.patch.object(ARCH, "MAX_PARSED_NODES", 1):
            result = ARCH.compare_contracts(
                record,
                record,
                record.compatibility,
                _work_budget=budget,
            )
        self.assertEqual(result.status, "unsupported")
        self.assertGreater(budget[0], 0)

        changed = copy.deepcopy(document)
        changed["info"]["description"] = "semantically unchanged metadata"
        changed_record = self._record(
            changed, kind="openapi", compatibility="bidirectional"
        )
        validation_budget = [0]
        base_validation_resolver = ARCH._SchemaResolver(
            record, None, validation_budget
        )
        self.assertTrue(
            ARCH._bounded_json_document(record.document, base_validation_resolver)
        )
        self.assertIsNotNone(
            ARCH._openapi_schemas(
                record.document,
                base_validation_resolver,
                record,
            )
        )
        head_validation_resolver = ARCH._SchemaResolver(
            changed_record, None, validation_budget
        )
        self.assertTrue(
            ARCH._bounded_json_document(
                changed_record.document, head_validation_resolver
            )
        )
        self.assertIsNotNone(
            ARCH._openapi_schemas(
                changed_record.document,
                head_validation_resolver,
                changed_record,
            )
        )
        comparison_budget = [0]
        with mock.patch.object(ARCH, "MAX_PARSED_NODES", validation_budget[0]):
            result = ARCH.compare_contracts(
                record,
                changed_record,
                record.compatibility,
                _work_budget=comparison_budget,
            )
        self.assertEqual(result.status, "unsupported")
        self.assertGreater(comparison_budget[0], validation_budget[0])

        linear = _openapi()
        linear["paths"] = {
            f"/items/{index}": {
                "get": {
                    "operationId": f"getLinearItem{index}",
                    "responses": {"200": {"description": "ok"}},
                }
            }
            for index in range(100)
        }
        linear["components"] = {
            "schemas": {},
            "securitySchemes": {
                f"Auth{index}": {"type": "http", "scheme": "bearer"}
                for index in range(100)
            },
        }
        linear_head = copy.deepcopy(linear)
        linear_head["info"]["description"] = "comparison required"
        linear_base_record = self._record(
            linear, kind="openapi", compatibility="bidirectional"
        )
        linear_head_record = self._record(
            linear_head, kind="openapi", compatibility="bidirectional"
        )
        linear_budget = [0]
        with (
            mock.patch.object(ARCH, "MAX_PARSED_NODES", 50_000),
            mock.patch.object(
                ARCH, "_security_schemes", wraps=ARCH._security_schemes
            ) as schemes,
        ):
            result = ARCH.compare_contracts(
                linear_base_record,
                linear_head_record,
                linear_base_record.compatibility,
                _work_budget=linear_budget,
            )
        self.assertEqual(result.status, "compatible")
        self.assertEqual(schemes.call_count, 4)
        self.assertLessEqual(linear_budget[0], 50_000)

        tags = _openapi()
        tags["paths"]["/items"]["get"]["tags"] = [
            f"tag{index}" for index in range(1_000)
        ]
        nested_security = _openapi()
        nested_security["components"] = {
            "schemas": {},
            "securitySchemes": {
                f"Auth{index}": {"type": "http", "scheme": "bearer"}
                for index in range(100)
            },
        }
        nested_security["security"] = [
            {f"Auth{index}": [] for index in range(100)} for _ in range(100)
        ]
        unknown_map = _openapi()
        unknown_map["paths"]["/items"]["get"].update(
            {f"unknown{index}": None for index in range(1_000)}
        )
        budget_adversaries = (
            self._record(
                {"type": "object", "required": [f"p{index}" for index in range(1_000)]}
            ),
            self._record({"type": "integer", "enum": list(range(1_000))}),
            self._record(tags, kind="openapi", compatibility="bidirectional"),
            self._record(
                nested_security, kind="openapi", compatibility="bidirectional"
            ),
            self._record(
                unknown_map, kind="openapi", compatibility="bidirectional"
            ),
        )
        for adversary in budget_adversaries:
            with (
                self.subTest(kind=adversary.kind, document=adversary.document.get("type")),
                mock.patch.object(ARCH, "MAX_PARSED_NODES", 100),
            ):
                self.assertEqual(
                    ARCH.compare_contracts(
                        adversary,
                        adversary,
                        adversary.compatibility,
                    ).status,
                    "unsupported",
                )

        for scalar_key, scalar_values in (
            ("required", [f"p{index}" for index in range(100)]),
            ("enum", list(range(100))),
        ):
            scalar_base = {"type": "object", scalar_key: scalar_values}
            if scalar_key == "enum":
                scalar_base["type"] = "integer"
            scalar_head = copy.deepcopy(scalar_base)
            scalar_head["description"] = "comparison required"
            scalar_base_record = self._record(scalar_base)
            scalar_head_record = self._record(scalar_head)
            scalar_validation_budget = [0]
            scalar_base_resolver = ARCH._SchemaResolver(
                scalar_base_record, None, scalar_validation_budget
            )
            self.assertTrue(
                ARCH._bounded_json_document(scalar_base, scalar_base_resolver)
            )
            self.assertFalse(
                ARCH._unsupported_schema(
                    scalar_base,
                    scalar_base_resolver,
                    scalar_base_record,
                )
            )
            scalar_head_resolver = ARCH._SchemaResolver(
                scalar_head_record, None, scalar_validation_budget
            )
            self.assertTrue(
                ARCH._bounded_json_document(scalar_head, scalar_head_resolver)
            )
            self.assertFalse(
                ARCH._unsupported_schema(
                    scalar_head,
                    scalar_head_resolver,
                    scalar_head_record,
                )
            )
            scalar_limit = scalar_validation_budget[0] + 2
            scalar_comparison_budget = [0]
            with (
                self.subTest(scalar_key=scalar_key),
                mock.patch.object(ARCH, "MAX_PARSED_NODES", scalar_limit),
            ):
                result = ARCH.compare_contracts(
                    scalar_base_record,
                    scalar_head_record,
                    scalar_base_record.compatibility,
                    _work_budget=scalar_comparison_budget,
                )
                self.assertEqual(result.status, "unsupported")
                self.assertGreater(scalar_comparison_budget[0], scalar_limit)

    def test_schema_resolution_depth_and_shared_node_budget_fail_closed(self) -> None:
        document: dict = {"type": "string"}
        for _ in range(ARCH.MAX_DEPTH + 1):
            document = {"type": "array", "items": document}
        deep = self._record(document)
        self.assertEqual(
            ARCH.compare_contracts(deep, deep, deep.compatibility).status,
            "unsupported",
        )
        wide = self._record(
            _json_schema({f"p{index}": {"type": "string"} for index in range(10)})
        )
        with mock.patch.object(ARCH, "MAX_PARSED_NODES", 8):
            self.assertEqual(
                ARCH.compare_contracts(wide, wide, wide.compatibility).status,
                "unsupported",
            )
        paired_base = self._record(
            {
                "type": "object",
                "description": "base",
                "properties": {
                    f"p{index}": {"type": "string"} for index in range(3)
                },
            }
        )
        paired_head_document = copy.deepcopy(paired_base.document)
        paired_head_document["description"] = "head"
        paired_head = self._record(paired_head_document)
        with mock.patch.object(ARCH, "MAX_PARSED_NODES", 7):
            paired_result = ARCH.compare_contracts(
                paired_base, paired_head, paired_base.compatibility
            )
        self.assertEqual(paired_result.status, "unsupported")

        inventory_visits = [0]

        class CountingInventory:
            def __iter__(self):
                inventory_visits[0] += 1
                return iter((paired_base,))

        exhausted_result = ARCH.compare_contracts(
            paired_base,
            paired_base,
            paired_base.compatibility,
            base_inventory=CountingInventory(),
            head_inventory=CountingInventory(),
            _work_budget=[ARCH.MAX_PARSED_NODES],
        )
        self.assertEqual(exhausted_result.status, "unsupported")
        self.assertEqual(inventory_visits[0], 0)

    def test_factory_execution_contract_inventory_is_exact_and_self_comparable(self) -> None:
        snapshot = ARCH.load_architecture(ROOT)
        records = ARCH.contract_inventory(ROOT, snapshot)
        by_id = {record.id: record for record in records}
        expected = {
            "CONTRACT-FACTORY-EXECUTION-OPENAPI": (
                "openapi", "factory/contracts/openapi/factory-execution.v1.json",
                "bidirectional", "bidirectional", "NODE-FACTORY-LOCAL-API",
            ),
            "CONTRACT-FACTORY-EXECUTION-OPENAPI-V2": (
                "openapi", "factory/contracts/openapi/factory-execution.v2.json",
                "bidirectional", "bidirectional", "NODE-FACTORY-LOCAL-API",
            ),
            "CONTRACT-FACTORY-TASK-PACKET": (
                "json_schema", "factory/contracts/schemas/task-packet.v1.json",
                "producer", "producer_accepted_by_old", "NODE-FACTORY-EXECUTION-CORE",
            ),
            "CONTRACT-FACTORY-EXECUTION-INVOCATION": (
                "json_schema", "factory/contracts/schemas/execution-invocation.v1.json",
                "producer", "producer_accepted_by_old", "NODE-FACTORY-EXECUTION-CORE",
            ),
            "CONTRACT-FACTORY-EXECUTION-EVENT": (
                "event", "factory/contracts/schemas/execution-event.v1.json",
                "consumer", "consumer_accepts_old", "NODE-FACTORY-EXECUTION-CORE",
            ),
            "CONTRACT-FACTORY-WORKSPACE-RESULT": (
                "json_schema", "factory/contracts/schemas/workspace-result.v1.json",
                "producer", "producer_accepted_by_old", "NODE-FACTORY-EXECUTION-CORE",
            ),
            "CONTRACT-FACTORY-EXECUTION-SEMANTIC-BINDING-V1": (
                "json_schema", "factory/contracts/jsonschema/semantic-execution-binding.v1.schema.json",
                "producer", "producer_accepted_by_old", "NODE-FACTORY-EXECUTION-CORE",
            ),
            "CONTRACT-FACTORY-EXECUTION-SEMANTIC-INPUTS-V1": (
                "json_schema", "factory/contracts/jsonschema/semantic-validation-inputs.v1.schema.json",
                "consumer", "consumer_accepts_old", "NODE-FACTORY-EXECUTION-CORE",
            ),
        }
        nodes = {node["id"]: node for node in snapshot.system["nodes"]}
        for identity, (kind, path, role, compatibility, node_id) in expected.items():
            with self.subTest(contract=identity):
                record = by_id[identity]
                self.assertEqual(
                    (record.kind, record.path, record.role, record.compatibility),
                    (kind, path, role, compatibility),
                )
                self.assertIn(identity, nodes[node_id]["public_contracts"])
                self.assertEqual(
                    ARCH.compare_contracts(
                        record,
                        record,
                        record.compatibility,
                        base_inventory=records,
                        head_inventory=records,
                    ).status,
                    "compatible",
                )
        self.assertIn(
            "factory/contracts/schemas",
            nodes["NODE-FACTORY-EXECUTION-CORE"]["repository_paths"],
        )


if __name__ == "__main__":
    unittest.main()
