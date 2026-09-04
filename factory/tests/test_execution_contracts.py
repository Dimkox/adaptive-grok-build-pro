from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import subprocess
import unittest

from adaptive_factory.execution_contracts import (
    ExecutionContractError,
    RunManifestV1,
    TaskPacketV1,
    WorkspaceResultV1,
)


ROOT = Path(__file__).resolve().parents[1]


def valid_packet():
    return {
        "contract_version": 1,
        "protocol_version": "adaptive-factory.execution/v1",
        "task_id": "task-001",
        "run_id": "run-001",
        "owner": "writer-01",
        "fence": 7,
        "role": "writer",
        "repository_id": "owner/repository",
        "legacy_intent_digest": "0" * 64,
        "authority": {
            "exact_base_sha": "1" * 40,
            "exact_head_sha": "2" * 40,
            "route_id": "37b05f579320",
            "change_id": "20260901-m5-execution",
            "spec_digest": "3" * 64,
            "architecture_digest": "4" * 64,
            "governance_digest": "5" * 64,
            "policy_digest": "6" * 64,
            "prompt_template_digest": "7" * 64,
            "role_definition_digest": "8" * 64,
            "tool_policy_digest": "9" * 64,
            "output_schema_digest": "a" * 64,
        },
        "provider": {
            "provider_id": "codex",
            "adapter_id": "adaptive-factory.codex",
            "adapter_version": "1.0.0",
            "adapter_digest": "b" * 64,
            "native_version": "0.152.1",
            "native_digest": "c" * 64,
            "model_id": "configured-model",
            "capabilities": ["cancellation", "structured_output", "usage"],
            "eligible": True,
        },
        "capability_policy": {
            "allowed_paths": ["factory/src"],
            "allowed_tools": ["read_file", "write_file"],
            "network_destinations": [],
            "artifact_classes": ["patch", "report"],
            "environment_names": ["LANG", "PATH"],
        },
        "plan": {
            "stages": [
                {"name": "prepare", "owner": "broker", "wall_seconds": 30},
                {"name": "invoke", "owner": "adapter", "wall_seconds": 300},
                {"name": "collect", "owner": "broker", "wall_seconds": 30},
                {"name": "finalize", "owner": "control_plane", "wall_seconds": 30},
            ]
        },
        "workspace_handle": "workspace:" + "d" * 64,
        "acceptance_ids": ["AC-001", "AC-002"],
        "limits": {
            "wall_seconds": 390,
            "max_cost_usd_micros": 1_000_000,
            "max_token_units": 100_000,
            "max_output_bytes": 1_000_000,
            "max_events": 1_000,
            "infrastructure_retries": 2,
            "semantic_repairs": 3,
        },
    }


def valid_workspace_result():
    return {
        "contract_version": 1,
        "task_id": "task-001",
        "run_id": "run-001",
        "task_packet_digest": "1" * 64,
        "run_manifest_digest": "2" * 64,
        "exact_head_sha": "3" * 40,
        "workspace_snapshot_digest": "4" * 64,
        "terminal_stage": "completed",
        "terminal_proposal_digest": "5" * 64,
        "artifact_manifest_digest": "6" * 64,
        "note_manifest_digest": "7" * 64,
        "usage_evidence_digest": "8" * 64,
        "diagnostics_digest": "9" * 64,
        "m4_status": "ready_for_human",
        "failure_class": None,
        "failure_reason": None,
    }


class ExecutionContractTests(unittest.TestCase):
    def test_packet_is_deeply_immutable_and_has_new_digest_domain(self):
        source = valid_packet()
        packet = TaskPacketV1.from_dict(source)
        source["provider"]["capabilities"].append("network")
        source["plan"]["stages"][0]["owner"] = "attacker"
        self.assertEqual(packet.provider.capabilities, ("cancellation", "structured_output", "usage"))
        self.assertEqual(packet.plan.stages[0].owner, "broker")
        self.assertNotEqual(packet.packet_digest, packet.legacy_intent_digest)
        with self.assertRaises(FrozenInstanceError):
            packet.owner = "other"

    def test_packet_canonical_round_trip_is_stable(self):
        first = TaskPacketV1.from_dict(valid_packet())
        second = TaskPacketV1.from_dict(first.to_dict(include_digest=False))
        self.assertEqual(first.packet_digest, second.packet_digest)
        self.assertEqual(first.canonical_bytes, second.canonical_bytes)

    def test_manifest_binds_packet_provider_workspace_and_initial_stage(self):
        packet = TaskPacketV1.from_dict(valid_packet())
        manifest = RunManifestV1.from_packet(packet, deadline="2026-09-02T01:00:00Z")
        self.assertEqual(manifest.packet_digest, packet.packet_digest)
        self.assertEqual(manifest.provider_id, "codex")
        self.assertEqual(manifest.workspace_handle, "workspace:" + "d" * 64)
        self.assertEqual(manifest.stage, "prepared")
        self.assertEqual(len(manifest.manifest_digest), 64)

    def test_closed_invalid_or_excessive_control_values_fail(self):
        cases = []
        unknown = valid_packet()
        unknown["provider"]["fallback_provider"] = "grok"
        cases.append((unknown, "unknown_fields"))
        ineligible = valid_packet()
        ineligible["provider"]["eligible"] = False
        cases.append((ineligible, "provider_ineligible"))
        network = valid_packet()
        network["capability_policy"]["network_destinations"] = ["https://example.test"]
        cases.append((network, "network_forbidden"))
        stage_order = valid_packet()
        stage_order["plan"]["stages"].reverse()
        cases.append((stage_order, "stage_order"))
        excessive = valid_packet()
        excessive["limits"]["wall_seconds"] = 14_401
        cases.append((excessive, "limit_exceeded"))
        surrogate = valid_packet()
        surrogate["provider"]["model_id"] = "bad\ud800"
        cases.append((surrogate, "invalid_text"))
        for value, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(ExecutionContractError, code):
                TaskPacketV1.from_dict(value)

    def test_wire_schema_files_are_closed_and_versioned(self):
        for name, required in {
            "task-packet.v1.json": {"contract_version", "protocol_version", "task_id", "run_id"},
            "execution-invocation.v1.json": {"protocol_version", "message_type", "packet"},
            "execution-event.v1.json": {"protocol_version", "task_id", "run_id", "packet_digest", "sequence", "event_type", "payload"},
        }.items():
            schema = json.loads((ROOT / "contracts" / "schemas" / name).read_text())
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertFalse(schema["additionalProperties"])
            self.assertTrue(required.issubset(schema["required"]))

    def test_workspace_result_is_canonical_immutable_and_domain_separated(self):
        value = valid_workspace_result()
        result = WorkspaceResultV1.from_facts(value)
        replay = WorkspaceResultV1.from_dict(result.to_dict())
        self.assertEqual(result.workspace_result_digest, replay.workspace_result_digest)
        self.assertNotEqual(result.workspace_result_digest, result.task_packet_digest)
        self.assertEqual(result.terminal_stage, "completed")
        self.assertEqual(result.m4_status, "ready_for_human")
        with self.assertRaises(FrozenInstanceError):
            result.exact_head_sha = "f" * 40

    def test_workspace_result_mutation_staleness_and_nonterminal_values_fail_closed(self):
        original = WorkspaceResultV1.from_facts(valid_workspace_result())
        changed = valid_workspace_result()
        changed["exact_head_sha"] = "e" * 40
        self.assertNotEqual(original.workspace_result_digest, WorkspaceResultV1.from_facts(changed).workspace_result_digest)
        cases = []
        unknown = valid_workspace_result()
        unknown["semantic_verdict"] = "pass"
        cases.append((unknown, "unknown_fields"))
        nonterminal = valid_workspace_result()
        nonterminal["terminal_stage"] = "running"
        cases.append((nonterminal, "invalid_terminal"))
        orphan = valid_workspace_result()
        orphan["terminal_stage"] = "orphaned"
        cases.append((orphan, "invalid_terminal"))
        for value, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(ExecutionContractError, code):
                WorkspaceResultV1.from_facts(value)

        mismatched = original.to_dict()
        mismatched["workspace_result_digest"] = "f" * 64
        with self.assertRaisesRegex(ExecutionContractError, "digest_mismatch"):
            WorkspaceResultV1.from_dict(mismatched)

    def test_workspace_result_schema_is_closed_and_names_m6_bridge_digests(self):
        schema = json.loads((ROOT / "contracts" / "schemas" / "workspace-result.v1.json").read_text())
        self.assertFalse(schema["additionalProperties"])
        self.assertTrue({"task_packet_digest", "run_manifest_digest", "workspace_result_digest"}.issubset(schema["required"]))
        self.assertNotIn("semantic_verdict", schema["properties"])
        valid = WorkspaceResultV1.from_facts(valid_workspace_result()).to_dict()
        command = ["jsonschema", str(ROOT / "contracts" / "schemas" / "workspace-result.v1.json")]
        self.assertEqual(subprocess.run(command, input=json.dumps(valid), text=True, capture_output=True).returncode, 0)
        invalid = dict(valid, terminal_stage="cancelled", terminal_proposal_digest=None)
        self.assertNotEqual(subprocess.run(command, input=json.dumps(invalid), text=True, capture_output=True).returncode, 0)


if __name__ == "__main__":
    unittest.main()
