from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Self, Sequence

from .brokers import ArtifactProposal, TerminalProposal, proposal_idempotency_key
from .contracts import ContractError, HEX40, HEX64, _closed, _hex, canonical_digest
from .execution_contracts import (
    RunManifestV1,
    TaskPacketV1,
    WorkspaceResultV1,
    workspace_evidence_digest,
)
from .semantic_contracts import (
    MAX_ITEMS,
    RISK_LEVELS,
    RequirementRefV1,
    SemanticSubjectV1,
    _id,
    _integer,
    _object,
    _parse_json,
    _sorted_unique,
    _to_dict,
)
from .workspace import ArtifactAttestationV1, WorkspaceSnapshotV1


def _domain_digest(contract: str, value: Mapping[str, Any]) -> str:
    return canonical_digest({"contract": contract, **value})


def _digests(values: Any, name: str) -> tuple[str, ...]:
    if not isinstance(values, list) or len(values) > MAX_ITEMS:
        raise ContractError(name)
    result = tuple(_hex(value, name, HEX64) for value in values)
    if result != tuple(sorted(set(result))):
        raise ContractError(name)
    return result


class _BridgeContract:
    @classmethod
    def from_json(cls, raw: str | bytes | bytearray) -> Self:
        return cls.from_dict(_parse_json(raw, cls.__name__))

    def to_dict(self) -> dict[str, Any]:
        return _to_dict(self)


@dataclass(frozen=True)
class SemanticExecutionBindingV1(_BridgeContract):
    schema_version: int
    task_id: str
    run_id: str
    owner: str
    fence: int
    role: str
    repository_id: str
    workspace_handle: str
    legacy_intent_digest: str
    task_packet_digest: str
    run_manifest_digest: str
    workspace_result_digest: str
    workspace_snapshot_digest: str
    terminal_proposal_digest: str
    artifact_manifest_digest: str
    note_manifest_digest: str
    usage_evidence_digest: str
    diagnostics_digest: str
    exact_base_sha: str
    input_head_sha: str
    exact_head_sha: str
    terminal_stage: str
    m4_status: str
    failure_class: str | None
    failure_reason: str | None
    artifact_proposal_digests: tuple[str, ...]
    artifact_attestation_digests: tuple[str, ...]

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SemanticExecutionBindingV1":
        data = _object(data, "semantic_execution_binding")
        _closed(data, set(cls.__dataclass_fields__))
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version", "semantic_execution_binding")
        if data["role"] != "writer":
            raise ContractError("semantic_writer_required")
        if data["terminal_stage"] != "completed" or data["m4_status"] != "ready_for_human":
            raise ContractError("semantic_result_not_ready")
        if data["failure_class"] is not None or data["failure_reason"] is not None:
            raise ContractError("semantic_result_failure_mismatch")
        proposal_digests = _digests(
            data["artifact_proposal_digests"], "artifact_proposal_digests"
        )
        attestation_digests = _digests(
            data["artifact_attestation_digests"], "artifact_attestation_digests"
        )
        if len(proposal_digests) != len(attestation_digests):
            raise ContractError("semantic_artifact_attestation_set_mismatch")
        return cls(
            1,
            _id(data["task_id"], "task_id"),
            _id(data["run_id"], "run_id"),
            _id(data["owner"], "owner"),
            _integer(data["fence"], "fence", 1, 2**63 - 1),
            "writer",
            _id(data["repository_id"], "repository_id"),
            _workspace(data["workspace_handle"]),
            _hex(data["legacy_intent_digest"], "legacy_intent_digest", HEX64),
            _hex(data["task_packet_digest"], "task_packet_digest", HEX64),
            _hex(data["run_manifest_digest"], "run_manifest_digest", HEX64),
            _hex(data["workspace_result_digest"], "workspace_result_digest", HEX64),
            _hex(data["workspace_snapshot_digest"], "workspace_snapshot_digest", HEX64),
            _hex(data["terminal_proposal_digest"], "terminal_proposal_digest", HEX64),
            _hex(data["artifact_manifest_digest"], "artifact_manifest_digest", HEX64),
            _hex(data["note_manifest_digest"], "note_manifest_digest", HEX64),
            _hex(data["usage_evidence_digest"], "usage_evidence_digest", HEX64),
            _hex(data["diagnostics_digest"], "diagnostics_digest", HEX64),
            _hex(data["exact_base_sha"], "exact_base_sha", HEX40),
            _hex(data["input_head_sha"], "input_head_sha", HEX40),
            _hex(data["exact_head_sha"], "exact_head_sha", HEX40),
            "completed",
            "ready_for_human",
            None,
            None,
            proposal_digests,
            attestation_digests,
        )

    @property
    def digest(self) -> str:
        return _domain_digest("adaptive-factory.semantic-execution-binding/v1", self.to_dict())


def _workspace(value: Any) -> str:
    if not isinstance(value, str) or not value.startswith("workspace:"):
        raise ContractError("semantic_workspace_handle")
    digest = value.removeprefix("workspace:")
    _hex(digest, "workspace_handle", HEX64)
    return value


@dataclass(frozen=True)
class SemanticValidationInputsV1(_BridgeContract):
    schema_version: int
    workspace_result_digest: str
    requirements: tuple[RequirementRefV1, ...]
    holdout_evidence_digest: str
    review_evidence_digest: str
    original_writer_context_digest: str
    risk_level: str
    diff_limit: int

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SemanticValidationInputsV1":
        data = _object(data, "semantic_validation_inputs")
        _closed(data, set(cls.__dataclass_fields__))
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version", "semantic_validation_inputs")
        requirements = _sorted_unique(
            data["requirements"],
            "requirements",
            RequirementRefV1.from_dict,
            allow_empty=False,
        )
        risk = data["risk_level"]
        if risk not in RISK_LEVELS - {"none"}:
            raise ContractError("risk_level")
        return cls(
            1,
            _hex(data["workspace_result_digest"], "workspace_result_digest", HEX64),
            requirements,
            _hex(data["holdout_evidence_digest"], "holdout_evidence_digest", HEX64),
            _hex(data["review_evidence_digest"], "review_evidence_digest", HEX64),
            _hex(
                data["original_writer_context_digest"],
                "original_writer_context_digest",
                HEX64,
            ),
            risk,
            _integer(data["diff_limit"], "diff_limit", 1, 1_000_000),
        )

    @property
    def digest(self) -> str:
        return _domain_digest("adaptive-factory.semantic-validation-inputs/v1", self.to_dict())


@dataclass(frozen=True)
class SemanticBridgeResult:
    binding: SemanticExecutionBindingV1
    validation_inputs: SemanticValidationInputsV1
    subject: SemanticSubjectV1

    @property
    def envelope_digest(self) -> str:
        return _domain_digest(
            "adaptive-factory.semantic-subject-envelope/v1",
            {
                "binding_digest": self.binding.digest,
                "validation_inputs_digest": self.validation_inputs.digest,
                "subject_digest": self.subject.digest,
            },
        )


def _validated_packet(packet: Any) -> TaskPacketV1:
    if not isinstance(packet, TaskPacketV1):
        raise ContractError("semantic_packet_type")
    try:
        parsed = TaskPacketV1.from_dict(packet.to_dict(include_digest=False))
    except ValueError as exc:
        raise ContractError("semantic_packet_invalid") from exc
    if parsed != packet:
        raise ContractError("semantic_packet_digest_mismatch")
    if packet.role != "writer":
        raise ContractError("semantic_writer_required")
    return packet


def _validated_manifest(packet: TaskPacketV1, manifest: Any) -> RunManifestV1:
    if not isinstance(manifest, RunManifestV1):
        raise ContractError("semantic_manifest_type")
    try:
        expected = RunManifestV1.from_packet(packet, deadline=manifest.deadline)
    except ValueError as exc:
        raise ContractError("semantic_manifest_invalid") from exc
    if manifest != expected:
        raise ContractError("semantic_manifest_binding_mismatch")
    return manifest


def _validated_snapshot(snapshot: Any) -> WorkspaceSnapshotV1:
    if not isinstance(snapshot, WorkspaceSnapshotV1):
        raise ContractError("semantic_snapshot_type")
    try:
        parsed = WorkspaceSnapshotV1.from_dict(snapshot.to_dict())
    except ValueError as exc:
        raise ContractError("semantic_snapshot_invalid") from exc
    if parsed != snapshot:
        raise ContractError("semantic_snapshot_digest_mismatch")
    return snapshot


def _validated_result(result: Any) -> WorkspaceResultV1:
    if not isinstance(result, WorkspaceResultV1):
        raise ContractError("semantic_result_type")
    try:
        parsed = WorkspaceResultV1.from_dict(result.to_dict())
    except ValueError as exc:
        raise ContractError("semantic_result_invalid") from exc
    if parsed != result:
        raise ContractError("semantic_result_digest_mismatch")
    if result.terminal_stage != "completed" or result.m4_status != "ready_for_human":
        raise ContractError("semantic_result_not_ready")
    if result.failure_class is not None or result.failure_reason is not None:
        raise ContractError("semantic_result_failure_mismatch")
    return result


def _validated_terminal(packet: TaskPacketV1, terminal: Any) -> TerminalProposal:
    if not isinstance(terminal, TerminalProposal):
        raise ContractError("semantic_terminal_type")
    if proposal_idempotency_key(terminal) != terminal.idempotency_key:
        raise ContractError("semantic_terminal_digest_mismatch")
    if (
        terminal.task_id != packet.task_id
        or terminal.run_id != packet.run_id
        or terminal.packet_digest != packet.packet_digest
        or terminal.fence != packet.fence
        or terminal.author_role != "writer"
        or terminal.terminal_type != "run.completed"
        or terminal.failure_class is not None
        or terminal.reason is not None
        or terminal.diagnostic is not None
    ):
        raise ContractError("semantic_terminal_binding_mismatch")
    return terminal


def _validated_artifacts(
    packet: TaskPacketV1,
    proposals: Sequence[ArtifactProposal],
    attestations: Sequence[ArtifactAttestationV1],
) -> tuple[tuple[ArtifactProposal, ...], tuple[ArtifactAttestationV1, ...]]:
    if not isinstance(proposals, (tuple, list)) or len(proposals) > MAX_ITEMS:
        raise ContractError("semantic_artifact_proposals")
    if not isinstance(attestations, (tuple, list)) or len(attestations) > MAX_ITEMS:
        raise ContractError("semantic_artifact_attestations")
    proposal_values = tuple(proposals)
    attestation_values = tuple(attestations)
    if any(not isinstance(value, ArtifactProposal) for value in proposal_values):
        raise ContractError("semantic_artifact_type")
    if any(not isinstance(value, ArtifactAttestationV1) for value in attestation_values):
        raise ContractError("semantic_attestation_type")
    proposal_values = tuple(sorted(proposal_values, key=lambda value: value.idempotency_key))
    attestation_values = tuple(
        sorted(attestation_values, key=lambda value: value.artifact_attestation_digest)
    )
    proposal_keys = tuple(value.idempotency_key for value in proposal_values)
    attestation_keys = tuple(value.artifact_attestation_digest for value in attestation_values)
    if len(set(proposal_keys)) != len(proposal_keys):
        raise ContractError("semantic_artifact_proposals")
    if len(set(attestation_keys)) != len(attestation_keys):
        raise ContractError("semantic_artifact_attestations")
    for value in proposal_values:
        if proposal_idempotency_key(value) != value.idempotency_key:
            raise ContractError("semantic_artifact_digest_mismatch")
        if (
            value.task_id != packet.task_id
            or value.run_id != packet.run_id
            or value.packet_digest != packet.packet_digest
            or value.fence != packet.fence
            or value.author_role != "writer"
        ):
            raise ContractError("semantic_artifact_binding_mismatch")
    for value in attestation_values:
        try:
            parsed = ArtifactAttestationV1.from_dict(value.to_dict())
        except ValueError as exc:
            raise ContractError("semantic_attestation_digest_mismatch") from exc
        if parsed != value:
            raise ContractError("semantic_attestation_digest_mismatch")
        if (
            value.task_id != packet.task_id
            or value.run_id != packet.run_id
            or value.repository_id != packet.repository_id
            or value.packet_digest != packet.packet_digest
            or value.workspace_handle != packet.workspace_handle
            or value.fence != packet.fence
            or value.author_role != "writer"
        ):
            raise ContractError("semantic_attestation_binding_mismatch")
    if len(proposal_values) != len(attestation_values):
        raise ContractError("semantic_artifact_attestation_set_mismatch")
    attestations_by_digest = {
        value.artifact_attestation_digest: value for value in attestation_values
    }
    for proposal in proposal_values:
        attestation = attestations_by_digest.get(proposal.artifact_attestation_digest)
        if attestation is None:
            raise ContractError("semantic_artifact_attestation_set_mismatch")
        if (
            proposal.sequence != attestation.producer_sequence
            or proposal.artifact_class != attestation.artifact_class
            or proposal.path != attestation.path
            or proposal.sha256 != attestation.sha256
            or proposal.size_bytes != attestation.size_bytes
            or proposal.media_type != attestation.media_type
        ):
            raise ContractError("semantic_artifact_attestation_binding_mismatch")
    return proposal_values, attestation_values


def build_semantic_subject(
    packet: TaskPacketV1,
    manifest: RunManifestV1,
    snapshot: WorkspaceSnapshotV1,
    result: WorkspaceResultV1,
    terminal_proposal: TerminalProposal,
    artifact_proposals: Sequence[ArtifactProposal],
    artifact_attestations: Sequence[ArtifactAttestationV1],
    validation_inputs: SemanticValidationInputsV1 | Mapping[str, Any],
) -> SemanticBridgeResult:
    packet = _validated_packet(packet)
    manifest = _validated_manifest(packet, manifest)
    snapshot = _validated_snapshot(snapshot)
    result = _validated_result(result)
    terminal = _validated_terminal(packet, terminal_proposal)
    artifacts, attestations = _validated_artifacts(
        packet, artifact_proposals, artifact_attestations
    )
    artifact_sequences = tuple(value.sequence for value in artifacts)
    if len(set(artifact_sequences)) != len(artifact_sequences) or any(
        sequence >= terminal.sequence for sequence in artifact_sequences
    ):
        raise ContractError("semantic_artifact_sequence_mismatch")
    if not isinstance(validation_inputs, SemanticValidationInputsV1):
        validation_inputs = SemanticValidationInputsV1.from_dict(validation_inputs)

    if (
        result.task_id != packet.task_id
        or result.run_id != packet.run_id
        or result.task_packet_digest != packet.packet_digest
        or result.run_manifest_digest != manifest.manifest_digest
        or snapshot.repository_id != packet.repository_id
        or snapshot.workspace_handle != packet.workspace_handle
        or snapshot.input_head_sha != packet.authority.exact_head_sha
        or snapshot.result_head_sha != result.exact_head_sha
        or snapshot.workspace_snapshot_digest != result.workspace_snapshot_digest
    ):
        raise ContractError("semantic_execution_bundle_binding_mismatch")
    if result.terminal_proposal_digest != terminal.idempotency_key:
        raise ContractError("semantic_terminal_result_mismatch")
    artifact_keys = [value.idempotency_key for value in artifacts]
    if result.artifact_manifest_digest != workspace_evidence_digest("artifacts", artifact_keys):
        raise ContractError("semantic_artifact_manifest_mismatch")
    if validation_inputs.workspace_result_digest != result.workspace_result_digest:
        raise ContractError("semantic_validation_result_mismatch")

    acceptance_ids = {
        value.requirement_id
        for value in validation_inputs.requirements
        if value.kind == "acceptance_criterion"
    }
    if acceptance_ids != set(packet.acceptance_ids):
        raise ContractError("semantic_acceptance_set_mismatch")

    authority_digest = _domain_digest(
        "adaptive-factory.semantic-authority-binding/v1",
        {"authority": packet.to_dict(include_digest=False)["authority"]},
    )
    binding = SemanticExecutionBindingV1.from_dict(
        {
            "schema_version": 1,
            "task_id": packet.task_id,
            "run_id": packet.run_id,
            "owner": packet.owner,
            "fence": packet.fence,
            "role": packet.role,
            "repository_id": packet.repository_id,
            "workspace_handle": packet.workspace_handle,
            "legacy_intent_digest": packet.legacy_intent_digest,
            "task_packet_digest": packet.packet_digest,
            "run_manifest_digest": manifest.manifest_digest,
            "workspace_result_digest": result.workspace_result_digest,
            "workspace_snapshot_digest": snapshot.workspace_snapshot_digest,
            "terminal_proposal_digest": terminal.idempotency_key,
            "artifact_manifest_digest": result.artifact_manifest_digest,
            "note_manifest_digest": result.note_manifest_digest,
            "usage_evidence_digest": result.usage_evidence_digest,
            "diagnostics_digest": result.diagnostics_digest,
            "exact_base_sha": packet.authority.exact_base_sha,
            "input_head_sha": snapshot.input_head_sha,
            "exact_head_sha": result.exact_head_sha,
            "terminal_stage": result.terminal_stage,
            "m4_status": result.m4_status,
            "failure_class": result.failure_class,
            "failure_reason": result.failure_reason,
            "artifact_proposal_digests": artifact_keys,
            "artifact_attestation_digests": [
                value.artifact_attestation_digest for value in attestations
            ],
        }
    )
    subject = SemanticSubjectV1.from_dict(
        {
            "schema_version": 1,
            "subject_id": f"semantic:{result.workspace_result_digest}",
            "requirements": [value.to_dict() for value in validation_inputs.requirements],
            "exact_base_sha": packet.authority.exact_base_sha,
            "exact_head_sha": result.exact_head_sha,
            "spec_digest": packet.authority.spec_digest,
            "architecture_digest": packet.authority.architecture_digest,
            "authority_digest": authority_digest,
            "diff_digest": snapshot.diff_digest,
            "deterministic_evidence_digest": binding.digest,
            "holdout_evidence_digest": validation_inputs.holdout_evidence_digest,
            "review_evidence_digest": validation_inputs.review_evidence_digest,
            "original_writer_id": packet.owner,
            "original_writer_context_digest": validation_inputs.original_writer_context_digest,
            "risk_level": validation_inputs.risk_level,
            "diff_lines": snapshot.diff_lines,
            "diff_limit": validation_inputs.diff_limit,
        }
    )
    return SemanticBridgeResult(binding, validation_inputs, subject)
