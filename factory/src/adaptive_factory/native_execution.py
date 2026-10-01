"""Concrete pre-model context consumer for the existing execution claim path."""

from dataclasses import dataclass
from pathlib import Path
import hashlib
import subprocess
from datetime import datetime, timezone

from .context_contracts import ContextManifestV1
from .contracts import ContractError, canonical_digest
from .execution_contracts import TaskPacketV1
from .v15_contracts import closed, integer, version


@dataclass(frozen=True)
class AnalysisBudgetV1:
    max_rounds: int
    max_tool_operations: int

    @classmethod
    def from_dict(cls, data):
        closed(data, ("schema_version", "max_rounds", "max_tool_operations"))
        version(data)
        return cls(
            integer(data["max_rounds"], "max_rounds", 1, 64),
            integer(data["max_tool_operations"], "max_tool_operations", 1, 10_000),
        )

    def to_dict(self):
        return {
            "schema_version": 1,
            "max_rounds": self.max_rounds,
            "max_tool_operations": self.max_tool_operations,
        }


@dataclass(frozen=True)
class NativeContextSidecarV1:
    task_id: str
    run_id: str
    packet_digest: str
    fence: int
    repository_id: str
    context_digest: str
    context_manifest: dict
    analysis_budget: dict
    sidecar_digest: str

    @classmethod
    def from_packet(cls, packet, manifest, budget):
        if not isinstance(packet, TaskPacketV1) or not isinstance(manifest, ContextManifestV1):
            raise ContractError("native_execution_input_required")
        if not isinstance(budget, AnalysisBudgetV1):
            raise ContractError("analysis_budget_required")
        facts = {
            "schema_version": 1,
            "task_id": packet.task_id,
            "run_id": packet.run_id,
            "packet_digest": packet.packet_digest,
            "fence": packet.fence,
            "repository_id": packet.repository_id,
            "context_digest": manifest.context_digest,
            "context_manifest": manifest.to_dict(),
            "analysis_budget": budget.to_dict(),
        }
        return cls(
            packet.task_id, packet.run_id, packet.packet_digest, packet.fence,
            packet.repository_id, manifest.context_digest, manifest.to_dict(),
            budget.to_dict(), canonical_digest(facts),
        )

    def to_dict(self):
        return {
            "schema_version": 1, "task_id": self.task_id, "run_id": self.run_id,
            "packet_digest": self.packet_digest, "fence": self.fence,
            "repository_id": self.repository_id, "context_digest": self.context_digest,
            "context_manifest": self.context_manifest, "analysis_budget": self.analysis_budget,
            "sidecar_digest": self.sidecar_digest,
        }


class RepositoryNativeContextSource:
    """Build context directly from the packet's exact trusted Git snapshot."""

    def __init__(self, root: Path):
        if not isinstance(root, Path) or not root.is_absolute():
            raise ContractError("context_source_required")
        if not (root / ".git").exists():
            raise ContractError("context_repository_required")
        self._root = root

    def read(self, packet: TaskPacketV1) -> ContextManifestV1:
        try:
            ancestry = subprocess.run(
                ["git", "-C", str(self._root), "merge-base", "--is-ancestor",
                 packet.authority.exact_base_sha, packet.authority.exact_head_sha],
                check=False, capture_output=True, timeout=5,
            )
            if ancestry.returncode != 0:
                raise ContractError("context_base_mismatch")
            raw_content = subprocess.run(
                ["git", "-C", str(self._root), "show", f"{packet.authority.exact_head_sha}:AGENTS.md"],
                check=True, capture_output=True, timeout=5,
            ).stdout.decode("utf-8")
        except (OSError, subprocess.SubprocessError, UnicodeDecodeError) as exc:
            raise ContractError("context_source_unavailable") from exc
        content = " ".join(raw_content.splitlines())
        while len(content.encode("utf-8")) > 4096:
            content = content[:-1]
        entry = {
            "path": "AGENTS.md", "kind": "instruction", "content": content,
            "sha256": hashlib.sha256(content.encode()).hexdigest(), "reason": "mandatory",
        }
        return ContextManifestV1.from_dict({
            "schema_version": 1, "builder_version": "native-git-1",
            "tenant_id": packet.repository_id, "repository_id": packet.repository_id,
            "source_snapshot": {"base_sha": packet.authority.exact_base_sha,
                                "head_sha": packet.authority.exact_head_sha,
                                "dirty_fingerprint": None},
            "change_id": packet.authority.change_id, "route_id": packet.authority.route_id,
            "change_spec_digest": packet.authority.spec_digest,
            "observed_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "mandatory_sources": [entry], "selected_sources": [], "rule_bindings": [],
        }, expected_tenant=packet.repository_id, expected_repository=packet.repository_id)


class NativeExecutionConsumer:
    """Build the exact pre-model sidecar consumed by a qualified execution profile."""

    def __init__(self, source: RepositoryNativeContextSource, budget: AnalysisBudgetV1):
        if not isinstance(source, RepositoryNativeContextSource):
            raise ContractError("native_executor_required")
        if not isinstance(budget, AnalysisBudgetV1):
            raise ContractError("analysis_budget_required")
        self._source, self._budget = source, budget

    def prepare(self, packet: TaskPacketV1) -> NativeContextSidecarV1:
        return NativeContextSidecarV1.from_packet(packet, self._source.read(packet), self._budget)
