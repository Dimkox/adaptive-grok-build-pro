from pathlib import Path
import subprocess
import tempfile
import unittest

from adaptive_factory.contracts import ContractError
from adaptive_factory.execution_contracts import TaskPacketV1
from factory.tests.test_execution_contracts import valid_packet


class NativeExecutionTests(unittest.TestCase):
    @staticmethod
    def repository(root):
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "test"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True)
        (root / "AGENTS.md").write_text("trusted exact repository rule", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "AGENTS.md"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "base"], check=True)
        base = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        (root / "AGENTS.md").write_text("trusted exact repository rule\nhead", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "commit", "-qam", "head"], check=True)
        head = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
        facts = valid_packet()
        facts["authority"]["exact_base_sha"] = base
        facts["authority"]["exact_head_sha"] = head
        return TaskPacketV1.from_dict(facts)

    def test_repository_source_builds_packet_bound_sidecar_and_budget(self):
        from adaptive_factory.native_execution import (
            AnalysisBudgetV1, RepositoryNativeContextSource, NativeExecutionConsumer,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            packet = self.repository(root)
            consumer = NativeExecutionConsumer(
                RepositoryNativeContextSource(root),
                AnalysisBudgetV1.from_dict({"schema_version": 1, "max_rounds": 3, "max_tool_operations": 12}),
            )
            sidecar = consumer.prepare(packet)
        self.assertEqual((sidecar.packet_digest, sidecar.run_id, sidecar.fence),
                         (packet.packet_digest, packet.run_id, packet.fence))
        self.assertEqual(sidecar.context_manifest["repository_id"], packet.repository_id)
        self.assertEqual(sidecar.analysis_budget["max_rounds"], 3)

    def test_source_rejects_handcrafted_cross_bound_context_and_missing_executor(self):
        from adaptive_factory.native_execution import (
            AnalysisBudgetV1, RepositoryNativeContextSource, NativeExecutionConsumer,
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            root.chmod(0o700)
            with self.assertRaises(ContractError):
                NativeExecutionConsumer(None, AnalysisBudgetV1.from_dict(
                    {"schema_version": 1, "max_rounds": 1, "max_tool_operations": 1}
                ))
            packet = self.repository(root)
            forged = packet.to_dict()
            forged["authority"]["exact_base_sha"] = "f" * 40
            forged.pop("packet_digest")
            with self.assertRaisesRegex(ContractError, "context_base_mismatch"):
                NativeExecutionConsumer(
                    RepositoryNativeContextSource(root),
                    AnalysisBudgetV1.from_dict({"schema_version": 1, "max_rounds": 1, "max_tool_operations": 1}),
                ).prepare(TaskPacketV1.from_dict(forged))
