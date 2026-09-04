from copy import deepcopy
from dataclasses import fields, FrozenInstanceError
import json
from pathlib import Path
import unittest
from urllib.parse import urldefrag

from adaptive_factory.contracts import ContractError, canonical_digest
from adaptive_factory.shadow_contracts import (
    MANUAL_HANDOFF_INSTRUCTIONS,
    M4ControlPlaneBridgeV1,
    M5ExecutionBridgeV1,
    M6PassVerdictV1,
    M6SemanticBridgeV1,
    OperatorHandoffProposalV1,
    ReadyForPrBundleV1,
    ShadowCohortKeyV1,
    ShadowCohortV1,
    ShadowOutcomeV1,
    ShadowTaskEvidenceV1,
)


FACTORY_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_ROOT = FACTORY_ROOT / "contracts" / "jsonschema"
M7_SCHEMA_NAMES = {
    "m7-predecessor-bridges.v1.schema.json",
    "operator-handoff-proposal.v1.schema.json",
    "ready-for-pr-bundle.v1.schema.json",
    "shadow-cohort.v1.schema.json",
    "shadow-outcome.v1.schema.json",
    "shadow-task-evidence.v1.schema.json",
}


def load_m7_schemas() -> dict[str, dict[str, object]]:
    return {
        name: json.loads((SCHEMA_ROOT / name).read_text(encoding="utf-8"))
        for name in sorted(M7_SCHEMA_NAMES)
    }


def dataclass_field_names(contract: type[object]) -> set[str]:
    return {field.name for field in fields(contract)}


def object_nodes(value: object):
    if isinstance(value, dict):
        if value.get("type") == "object":
            yield value
        for nested in value.values():
            yield from object_nodes(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from object_nodes(nested)


def resolve_schema_pointer(document: object, fragment: str) -> object:
    value = document
    if not fragment:
        return value
    if not fragment.startswith("/"):
        raise AssertionError(f"unsupported schema fragment: {fragment}")
    for part in fragment.removeprefix("/").split("/"):
        key = part.replace("~1", "/").replace("~0", "~")
        if not isinstance(value, dict) or key not in value:
            raise AssertionError(f"unresolvable schema fragment: {fragment}")
        value = value[key]
    return value


def valid_bridges() -> dict[str, dict[str, object]]:
    payload = producer_accurate_evidence_payload()
    return {name: deepcopy(payload[name]) for name in ("m4", "m5", "m6")}


def valid_evidence_payload() -> dict[str, object]:
    return producer_accurate_evidence_payload()


def producer_accurate_evidence_payload() -> dict[str, object]:
    verdict = {
        "schema_version": 1,
        "subject_digest": "5" * 64,
        "decision": "pass",
        "decision_source": "deterministic_adjudicator",
        "finding_identity_digests": [],
        "duplicate_identity_digests": [],
        "correlated_requirement_keys": [],
        "contradicted_requirement_keys": [],
        "unsupported_pass_requirement_keys": [],
        "residual_risk": "none",
    }
    return {
        "schema_version": 1,
        "m4": {
            "schema_version": 1,
            "task_id": "task-007",
            "run_id": "run-007",
            "owner": "worker-007",
            "role": "writer",
            "fence": 9,
            "intent_digest": "a" * 64,
            "lease_packet_digest": "a" * 64,
        },
        "m5": {
            "schema_version": 1,
            "task_id": "task-007",
            "run_id": "run-007",
            "owner": "worker-007",
            "role": "writer",
            "fence": 9,
            "repository_id": "owner/repository",
            "legacy_intent_digest": "a" * 64,
            "task_packet_digest": "b" * 64,
            "run_manifest_digest": "c" * 64,
            "workspace_snapshot_digest": "d" * 64,
            "workspace_result_digest": "e" * 64,
            "authority_exact_head_sha": "1" * 40,
            "snapshot_input_head_sha": "1" * 40,
            "snapshot_result_head_sha": "2" * 40,
            "result_exact_head_sha": "2" * 40,
        },
        "m6": {
            "schema_version": 1,
            "task_id": "task-007",
            "run_id": "run-007",
            "owner": "worker-007",
            "role": "writer",
            "fence": 9,
            "repository_id": "owner/repository",
            "legacy_intent_digest": "a" * 64,
            "task_packet_digest": "b" * 64,
            "run_manifest_digest": "c" * 64,
            "workspace_snapshot_digest": "d" * 64,
            "workspace_result_digest": "e" * 64,
            "binding_input_head_sha": "1" * 40,
            "binding_exact_head_sha": "2" * 40,
            "subject_exact_head_sha": "2" * 40,
            "envelope_digest": "19362fff9403d96463d77b0fea2c73fb2ba9cda00f648b2a634ad1345ae4acae",
            "binding_digest": "3" * 64,
            "validation_inputs_digest": "4" * 64,
            "subject_digest": "5" * 64,
            "evidence_set_digest": "6" * 64,
            "verdict_digest": "42d7a7abb14f4c3ea02671b5e1b821a8f7b03c832b92735d2907a97eaf39e13c",
            "verdict": verdict,
        },
    }


def build_bundle() -> ReadyForPrBundleV1:
    evidence = ShadowTaskEvidenceV1.from_dict(valid_evidence_payload())
    proposal = OperatorHandoffProposalV1.from_dict(
        {
            "schema_version": 1,
            "subject_digest": evidence.digest,
            "external_capability": "absent",
            "recommended_action": "human_review",
            "instructions": list(MANUAL_HANDOFF_INSTRUCTIONS),
        }
    )
    return ReadyForPrBundleV1.from_components(evidence=evidence, operator_handoff=proposal)


def nested_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {key for item in value.values() for key in nested_keys(item)}
    if isinstance(value, list):
        return {key for item in value for key in nested_keys(item)}
    return set()


class ShadowContractTests(unittest.TestCase):
    def test_m4_legacy_digest_and_m5_task_packet_are_separate_bound_fields(self):
        evidence = ShadowTaskEvidenceV1.from_dict(producer_accurate_evidence_payload())
        self.assertEqual(evidence.m4.intent_digest, evidence.m4.lease_packet_digest)
        self.assertEqual(evidence.m4.intent_digest, evidence.m5.legacy_intent_digest)
        self.assertIn("intent_digest", dataclass_field_names(M4ControlPlaneBridgeV1))
        self.assertIn("task_packet_digest", dataclass_field_names(M5ExecutionBridgeV1))

        collision = producer_accurate_evidence_payload()
        collision["m5"]["task_packet_digest"] = "a" * 64
        collision["m6"]["task_packet_digest"] = "a" * 64
        self.assertEqual(
            ShadowTaskEvidenceV1.from_dict(collision).m5.task_packet_digest,
            "a" * 64,
        )

    def test_input_authority_and_result_heads_are_separate_but_factually_bound(self):
        evidence = ShadowTaskEvidenceV1.from_dict(producer_accurate_evidence_payload())
        self.assertEqual(evidence.m5.authority_exact_head_sha, evidence.m5.snapshot_input_head_sha)
        self.assertEqual(evidence.m5.snapshot_result_head_sha, evidence.m5.result_exact_head_sha)
        self.assertEqual(evidence.m5.result_exact_head_sha, evidence.m6.subject_exact_head_sha)
        self.assertNotEqual(evidence.m5.authority_exact_head_sha, evidence.m5.result_exact_head_sha)

    def test_closed_v1_bridges_are_content_addressed(self):
        payloads = valid_bridges()
        bridges = (
            M4ControlPlaneBridgeV1.from_dict(payloads["m4"]),
            M5ExecutionBridgeV1.from_dict(payloads["m5"]),
            M6SemanticBridgeV1.from_dict(payloads["m6"]),
        )
        self.assertTrue(all(len(item.digest) == 64 for item in bridges))
        self.assertNotEqual(bridges[0].digest, canonical_digest(bridges[0].to_dict()))

    def test_unknown_versions_and_remote_capability_fields_fail_closed(self):
        cases = []
        for name, payload in valid_bridges().items():
            unknown = deepcopy(payload)
            unknown["command"] = "git push"
            cases.append((name, unknown, "unknown_fields"))
            version = deepcopy(payload)
            version["schema_version"] = 2
            cases.append((name, version, "unsupported_version"))
        parsers = {
            "m4": M4ControlPlaneBridgeV1.from_dict,
            "m5": M5ExecutionBridgeV1.from_dict,
            "m6": M6SemanticBridgeV1.from_dict,
        }
        for name, payload, code in cases:
            with self.subTest(name=name, code=code), self.assertRaisesRegex(ContractError, code):
                parsers[name](payload)

    def test_caller_cannot_invent_dependency_or_evidence_authority_fields(self):
        parsers = {
            "m4": M4ControlPlaneBridgeV1.from_dict,
            "m5": M5ExecutionBridgeV1.from_dict,
            "m6": M6SemanticBridgeV1.from_dict,
        }
        for name, parser in parsers.items():
            for field in ("product_sha", "dependency_state"):
                payload = valid_bridges()[name]
                payload[field] = "accepted"
                with self.subTest(name=name, field=field), self.assertRaisesRegex(
                    ContractError, "unknown_fields"
                ):
                    parser(payload)
        for field in ("local_evidence_digest", "receipt_set_digest", "source_bundle_digest"):
            payload = valid_evidence_payload()
            payload[field] = "8" * 64
            with self.subTest(field=field), self.assertRaisesRegex(ContractError, "unknown_fields"):
                ShadowTaskEvidenceV1.from_dict(payload)

    def test_every_shared_identity_must_match_across_all_bridges(self):
        mutations: dict[str, object] = {
            "task_id": "task-stale",
            "run_id": "run-stale",
            "fence": 10,
            "owner": "worker-stale",
        }
        for bridge_name in ("m5", "m6"):
            for field, replacement in mutations.items():
                payload = valid_evidence_payload()
                payload[bridge_name][field] = replacement
                with self.subTest(bridge=bridge_name, field=field), self.assertRaisesRegex(
                    ContractError, "stale_binding"
                ):
                    ShadowTaskEvidenceV1.from_dict(payload)

        cases = (
            ("m5", "legacy_intent_digest", "7" * 64),
            ("m6", "task_packet_digest", "7" * 64),
            ("m6", "run_manifest_digest", "7" * 64),
            ("m6", "workspace_snapshot_digest", "7" * 64),
            ("m6", "workspace_result_digest", "7" * 64),
            ("m6", "binding_input_head_sha", "7" * 40),
            ("m6", "binding_exact_head_sha", "7" * 40),
            ("m6", "subject_exact_head_sha", "7" * 40),
        )
        for bridge_name, field, replacement in cases:
            payload = valid_evidence_payload()
            payload[bridge_name][field] = replacement
            with self.subTest(bridge=bridge_name, field=field), self.assertRaisesRegex(
                ContractError, "stale_binding"
            ):
                ShadowTaskEvidenceV1.from_dict(payload)

    def test_semantic_bridge_requires_the_exact_closed_pass_verdict(self):
        cases = {
            "decision": "repair",
            "finding_identity_digests": ["7" * 64],
            "contradicted_requirement_keys": ["AC-001"],
            "unsupported_pass_requirement_keys": ["AC-002"],
            "residual_risk": "high",
        }
        for field, replacement in cases.items():
            payload = valid_bridges()["m6"]
            payload["verdict"][field] = replacement
            with self.subTest(field=field), self.assertRaisesRegex(ContractError, "semantic_not_pass"):
                M6SemanticBridgeV1.from_dict(payload)

        payload = valid_bridges()["m6"]
        payload["verdict_digest"] = "7" * 64
        with self.assertRaisesRegex(ContractError, "digest_mismatch"):
            M6SemanticBridgeV1.from_dict(payload)

    def test_public_values_are_deeply_frozen(self):
        bundle = build_bundle()
        with self.assertRaises(FrozenInstanceError):
            bundle.status = "ready_for_pr"
        with self.assertRaises(FrozenInstanceError):
            bundle.evidence.m4.task_id = "changed"
        with self.assertRaises(TypeError):
            bundle.operator_handoff.instructions[0] = "push"

    def test_bundle_digest_covers_every_nested_field(self):
        original = build_bundle()
        serialized = original.to_dict()
        serialized["evidence"]["m6"]["evidence_set_digest"] = "7" * 64
        with self.assertRaisesRegex(ContractError, "digest_mismatch"):
            ReadyForPrBundleV1.from_dict(serialized)

        changed_evidence = ShadowTaskEvidenceV1.from_dict(serialized["evidence"])
        changed_proposal = OperatorHandoffProposalV1.from_dict(
            {
                **serialized["operator_handoff"],
                "subject_digest": changed_evidence.digest,
            }
        )
        changed = ReadyForPrBundleV1.from_components(
            evidence=changed_evidence,
            operator_handoff=changed_proposal,
        )
        self.assertNotEqual(original.bundle_digest, changed.bundle_digest)

    def test_operator_proposal_is_fixed_manual_and_subject_bound(self):
        evidence = ShadowTaskEvidenceV1.from_dict(valid_evidence_payload())
        base = {
            "schema_version": 1,
            "subject_digest": evidence.digest,
            "external_capability": "absent",
            "recommended_action": "human_review",
            "instructions": list(MANUAL_HANDOFF_INSTRUCTIONS),
        }
        proposal = OperatorHandoffProposalV1.from_dict(base)
        self.assertEqual(proposal.instructions, MANUAL_HANDOFF_INSTRUCTIONS)
        self.assertEqual(proposal.recommended_action, "human_review")

        for field, replacement, code in (
            ("external_capability", "present", "external_capability_forbidden"),
            ("recommended_action", "push", "invalid_recommendation"),
            ("instructions", ["git_push"], "invalid_instructions"),
        ):
            payload = deepcopy(base)
            payload[field] = replacement
            with self.subTest(field=field), self.assertRaisesRegex(ContractError, code):
                OperatorHandoffProposalV1.from_dict(payload)

        stale = OperatorHandoffProposalV1.from_dict({**base, "subject_digest": "6" * 64})
        with self.assertRaisesRegex(ContractError, "stale_binding"):
            ReadyForPrBundleV1.from_components(evidence=evidence, operator_handoff=stale)

    def test_pure_bundle_is_blocked_without_durable_lookup_and_has_no_remote_surface(self):
        bundle = build_bundle()
        self.assertEqual(bundle.status, "blocked_pending_durable_lookup")
        self.assertEqual(ReadyForPrBundleV1.from_dict(bundle.to_dict()), bundle)
        forbidden = {
            "command",
            "url",
            "token",
            "credential",
            "push",
            "merge",
            "auto_merge",
            "remote_target",
            "pull_request_url",
        }
        self.assertTrue(forbidden.isdisjoint(nested_keys(bundle.to_dict())))

        payload = bundle.to_dict()
        payload["status"] = "ready_for_human"
        with self.assertRaisesRegex(ContractError, "invalid_bundle_status"):
            ReadyForPrBundleV1.from_dict(payload)

    def test_m7_schema_inventory_and_dialect_are_exact(self):
        self.assertTrue(SCHEMA_ROOT.is_dir())
        actual = {
            path.name
            for path in SCHEMA_ROOT.glob("*.json")
            if json.loads(path.read_text(encoding="utf-8")).get("$id", "").startswith(
                "urn:adaptive-factory:m7:"
            )
        }
        self.assertEqual(actual, M7_SCHEMA_NAMES)
        for name, schema in load_m7_schemas().items():
            with self.subTest(name=name):
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_m7_schema_registry_resolves_every_ref_without_network(self):
        schemas = load_m7_schemas()
        registry = {schema["$id"]: schema for schema in schemas.values()}
        visited: set[tuple[str, str]] = set()

        def visit(value: object, base_id: str) -> None:
            if isinstance(value, dict):
                reference = value.get("$ref")
                if reference is not None:
                    self.assertIsInstance(reference, str)
                    document_id, fragment = urldefrag(reference)
                    document_id = document_id or base_id
                    self.assertIn(document_id, registry)
                    identity = (document_id, fragment)
                    if identity not in visited:
                        visited.add(identity)
                        visit(resolve_schema_pointer(registry[document_id], fragment), document_id)
                for nested in value.values():
                    visit(nested, base_id)
            elif isinstance(value, list):
                for nested in value:
                    visit(nested, base_id)

        for schema in schemas.values():
            visit(schema, schema["$id"])
        self.assertTrue(visited)

    def test_every_m7_schema_object_is_closed_complete_and_versioned(self):
        for name, schema in load_m7_schemas().items():
            for index, node in enumerate(object_nodes(schema)):
                with self.subTest(name=name, object=index):
                    self.assertIs(node.get("additionalProperties"), False)
                    self.assertEqual(set(node.get("required", [])), set(node.get("properties", {})))
                    properties = node.get("properties", {})
                    if "schema_version" in properties:
                        self.assertEqual(properties["schema_version"], {"const": 1})

    def test_m7_schema_fields_match_python_v1_surfaces(self):
        schemas = load_m7_schemas()
        predecessors = schemas["m7-predecessor-bridges.v1.schema.json"]
        for definition, contract in (
            ("m4", M4ControlPlaneBridgeV1),
            ("m5", M5ExecutionBridgeV1),
            ("m6", M6SemanticBridgeV1),
        ):
            self.assertEqual(
                set(predecessors["$defs"][definition]["properties"]),
                dataclass_field_names(contract),
            )
        self.assertEqual(
            set(predecessors["$defs"]["verdict"]["properties"]),
            dataclass_field_names(M6PassVerdictV1),
        )
        parity = (
            ("shadow-task-evidence.v1.schema.json", ShadowTaskEvidenceV1),
            ("operator-handoff-proposal.v1.schema.json", OperatorHandoffProposalV1),
            ("ready-for-pr-bundle.v1.schema.json", ReadyForPrBundleV1),
            ("shadow-outcome.v1.schema.json", ShadowOutcomeV1),
            ("shadow-cohort.v1.schema.json", ShadowCohortV1),
        )
        for name, contract in parity:
            with self.subTest(name=name):
                self.assertEqual(set(schemas[name]["properties"]), dataclass_field_names(contract))
        cohort_key = schemas["shadow-cohort.v1.schema.json"]["$defs"]["cohort_key"]
        self.assertEqual(set(cohort_key["properties"]), dataclass_field_names(ShadowCohortKeyV1))

    def test_m7_schema_enums_are_authority_safe_and_have_no_remote_fields(self):
        schemas = load_m7_schemas()
        predecessors = schemas["m7-predecessor-bridges.v1.schema.json"]["$defs"]
        for name in ("m4", "m5", "m6"):
            self.assertEqual(predecessors[name]["properties"]["role"], {"const": "writer"})
        verdict = predecessors["verdict"]["properties"]
        self.assertEqual(verdict["decision"], {"const": "pass"})
        self.assertEqual(verdict["decision_source"], {"const": "deterministic_adjudicator"})
        self.assertEqual(verdict["residual_risk"], {"const": "none"})
        for field in (
            "finding_identity_digests",
            "duplicate_identity_digests",
            "correlated_requirement_keys",
            "contradicted_requirement_keys",
            "unsupported_pass_requirement_keys",
        ):
            self.assertEqual(verdict[field]["maxItems"], 0)

        proposal = schemas["operator-handoff-proposal.v1.schema.json"]["properties"]
        self.assertEqual(proposal["external_capability"], {"const": "absent"})
        self.assertEqual(proposal["recommended_action"], {"const": "human_review"})
        self.assertEqual(
            [item["const"] for item in proposal["instructions"]["prefixItems"]],
            list(MANUAL_HANDOFF_INSTRUCTIONS),
        )
        bundle = schemas["ready-for-pr-bundle.v1.schema.json"]["properties"]
        self.assertEqual(bundle["status"], {"const": "blocked_pending_durable_lookup"})

        forbidden = {
            "auto_merge",
            "command",
            "credential",
            "merge",
            "network",
            "pull_request",
            "push",
            "remote_target",
            "token",
            "url",
        }
        for name, schema in schemas.items():
            for node in object_nodes(schema):
                with self.subTest(name=name):
                    self.assertTrue(forbidden.isdisjoint(node.get("properties", {})))


if __name__ == "__main__":
    unittest.main()
