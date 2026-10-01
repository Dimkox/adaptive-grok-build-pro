import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from adaptive_factory.contracts import ContractError
from adaptive_factory.execution_contracts import TaskPacketV1
from factory.tests.test_execution_contracts import valid_packet


def context(packet):
    content = "trusted exact repository rule"
    return {
        "schema_version": 1, "builder_version": "native-1", "tenant_id": packet.repository_id,
        "repository_id": packet.repository_id,
        "source_snapshot": {"base_sha": packet.authority.exact_base_sha,
                            "head_sha": packet.authority.exact_head_sha, "dirty_fingerprint": None},
        "change_id": packet.authority.change_id, "route_id": packet.authority.route_id,
        "change_spec_digest": packet.authority.spec_digest, "observed_at": "2026-10-01T00:00:00Z",
        "mandatory_sources": [{"path": "AGENTS.md", "kind": "instruction", "content": content,
                               "sha256": hashlib.sha256(content.encode()).hexdigest(), "reason": "mandatory"}],
        "selected_sources": [], "rule_bindings": [],
    }


class NativeExecutionTests(unittest.TestCase):
    def test_file_source_builds_packet_bound_sidecar_and_budget(self):
        from adaptive_factory.native_execution import (
            AnalysisBudgetV1, FileNativeContextSource, NativeExecutionConsumer,
        )
        packet = TaskPacketV1.from_dict(valid_packet())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); root.chmod(0o700)
            document = root / f"{packet.packet_digest}.json"
            document.write_text(json.dumps(context(packet)), encoding="utf-8"); document.chmod(0o600)
            consumer = NativeExecutionConsumer(
                FileNativeContextSource(root),
                AnalysisBudgetV1.from_dict({"schema_version": 1, "max_rounds": 3, "max_tool_operations": 12}),
            )
            sidecar = consumer.prepare(packet)
        self.assertEqual((sidecar.packet_digest, sidecar.run_id, sidecar.fence),
                         (packet.packet_digest, packet.run_id, packet.fence))
        self.assertEqual(sidecar.context_manifest["repository_id"], packet.repository_id)
        self.assertEqual(sidecar.analysis_budget["max_rounds"], 3)

    def test_source_rejects_handcrafted_cross_bound_context_and_missing_executor(self):
        from adaptive_factory.native_execution import (
            AnalysisBudgetV1, FileNativeContextSource, NativeExecutionConsumer,
        )
        packet = TaskPacketV1.from_dict(valid_packet())
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); root.chmod(0o700)
            with self.assertRaises(ContractError):
                NativeExecutionConsumer(None, AnalysisBudgetV1.from_dict(
                    {"schema_version": 1, "max_rounds": 1, "max_tool_operations": 1}
                ))
            facts = context(packet); facts["source_snapshot"]["head_sha"] = "f" * 40
            document = root / f"{packet.packet_digest}.json"
            document.write_text(json.dumps(facts), encoding="utf-8"); document.chmod(0o600)
            with self.assertRaisesRegex(ContractError, "context_head_mismatch"):
                NativeExecutionConsumer(
                    FileNativeContextSource(root),
                    AnalysisBudgetV1.from_dict({"schema_version": 1, "max_rounds": 1, "max_tool_operations": 1}),
                ).prepare(packet)
