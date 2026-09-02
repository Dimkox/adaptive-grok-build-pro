from dataclasses import FrozenInstanceError
import json
from pathlib import Path
import unittest

from adaptive_factory.execution_contracts import (
    ExecutionContractError,
    RunManifestV1,
    TaskPacketV1,
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


if __name__ == "__main__":
    unittest.main()
