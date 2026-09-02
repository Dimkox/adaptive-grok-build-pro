from copy import deepcopy
from dataclasses import fields, FrozenInstanceError
import json
from pathlib import Path
import unittest

from adaptive_factory.contracts import ContractError, canonical_digest
from adaptive_factory.shadow_contracts import (
    MANUAL_HANDOFF_INSTRUCTIONS,
    M4ControlPlaneBridgeV1,
    M5ExecutionBridgeV1,
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


def valid_bridges() -> dict[str, dict[str, object]]:
    shared: dict[str, object] = {
        "schema_version": 1,
        "dependency_state": "accepted",
        "task_id": "task-007",
        "run_id": "run-007",
        "fence": 9,
        "task_packet_digest": "a" * 64,
        "exact_head_sha": "7" * 40,
    }
    return {
        "m4": {
            **shared,
            "product_sha": "4" * 40,
            "task_record_digest": "b" * 64,
            "control_plane_evidence_digest": "c" * 64,
        },
        "m5": {
            **shared,
            "product_sha": "5" * 40,
            "run_manifest_digest": "d" * 64,
            "workspace_result_digest": "e" * 64,
            "execution_authority_digest": "f" * 64,
        },
        "m6": {
            **shared,
            "product_sha": "6" * 40,
            "semantic_subject_digest": "1" * 64,
            "semantic_verdict_digest": "2" * 64,
            "semantic_evidence_digest": "3" * 64,
            "semantic_decision": "pass",
            "coverage_millionths": 1_000_000,
            "contradicted_requirement_count": 0,
            "unsupported_pass_requirement_count": 0,
        },
    }


def valid_evidence_payload() -> dict[str, object]:
    return {
        "schema_version": 1,
        **valid_bridges(),
        "local_evidence_digest": "8" * 64,
        "receipt_set_digest": "9" * 64,
        "source_bundle_digest": "0" * 64,
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
    def test_closed_v1_bridges_accept_only_accepted_dependencies(self):
        payloads = valid_bridges()
        bridges = (
            M4ControlPlaneBridgeV1.from_dict(payloads["m4"]),
            M5ExecutionBridgeV1.from_dict(payloads["m5"]),
            M6SemanticBridgeV1.from_dict(payloads["m6"]),
        )
        self.assertEqual([item.dependency_state for item in bridges], ["accepted"] * 3)
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

    def test_provisional_or_rejected_dependency_cannot_enter_evidence(self):
        parsers = {
            "m4": M4ControlPlaneBridgeV1.from_dict,
            "m5": M5ExecutionBridgeV1.from_dict,
            "m6": M6SemanticBridgeV1.from_dict,
        }
        for name, parser in parsers.items():
            for state in ("provisional", "rejected"):
                payload = valid_bridges()[name]
                payload["dependency_state"] = state
                with self.subTest(name=name, state=state), self.assertRaisesRegex(
                    ContractError, "dependency_not_accepted"
                ):
                    parser(payload)

    def test_every_shared_identity_must_match_across_all_bridges(self):
        mutations: dict[str, object] = {
            "task_id": "task-stale",
            "run_id": "run-stale",
            "fence": 10,
            "task_packet_digest": "4" * 64,
            "exact_head_sha": "8" * 40,
        }
        for bridge_name in ("m5", "m6"):
            for field, replacement in mutations.items():
                payload = valid_evidence_payload()
                payload[bridge_name][field] = replacement
                with self.subTest(bridge=bridge_name, field=field), self.assertRaisesRegex(
                    ContractError, "stale_binding"
                ):
                    ShadowTaskEvidenceV1.from_dict(payload)

    def test_semantic_bridge_requires_complete_noncontradictory_pass(self):
        cases = {
            "semantic_not_pass": {"semantic_decision": "repair"},
            "incomplete_evidence": {"coverage_millionths": 999_999},
            "contradictory_evidence": {"contradicted_requirement_count": 1},
            "unsupported_pass": {"unsupported_pass_requirement_count": 1},
        }
        for code, mutation in cases.items():
            payload = valid_bridges()["m6"]
            payload.update(mutation)
            expected = "incomplete_evidence" if code == "unsupported_pass" else code
            with self.subTest(code=code), self.assertRaisesRegex(ContractError, expected):
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
        serialized["evidence"]["local_evidence_digest"] = "7" * 64
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

    def test_bundle_exposes_only_ready_for_human_and_no_remote_field_surface(self):
        bundle = build_bundle()
        self.assertEqual(bundle.status, "ready_for_human")
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
        payload["status"] = "ready_for_pr"
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
            self.assertEqual(predecessors[name]["properties"]["dependency_state"], {"const": "accepted"})
        self.assertEqual(predecessors["m6"]["properties"]["semantic_decision"], {"const": "pass"})
        self.assertEqual(predecessors["m6"]["properties"]["coverage_millionths"], {"const": 1_000_000})

        proposal = schemas["operator-handoff-proposal.v1.schema.json"]["properties"]
        self.assertEqual(proposal["external_capability"], {"const": "absent"})
        self.assertEqual(proposal["recommended_action"], {"const": "human_review"})
        self.assertEqual(
            [item["const"] for item in proposal["instructions"]["prefixItems"]],
            list(MANUAL_HANDOFF_INSTRUCTIONS),
        )
        bundle = schemas["ready-for-pr-bundle.v1.schema.json"]["properties"]
        self.assertEqual(bundle["status"], {"const": "ready_for_human"})

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
