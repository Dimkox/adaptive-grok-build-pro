from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import unittest

from adaptive_factory.brokers import ArtifactProposal, TerminalProposal, proposal_idempotency_key
from adaptive_factory.contracts import ContractError
from adaptive_factory.execution_contracts import RunManifestV1, TaskPacketV1, WorkspaceResultV1, workspace_evidence_digest
from adaptive_factory.semantic_bridge import (
    SemanticExecutionBindingV1,
    SemanticValidationInputsV1,
    build_semantic_subject,
)
from adaptive_factory.workspace import ArtifactAttestationV1, WorkspaceSnapshotV1
from .test_execution_contracts import valid_packet


SCHEMAS = Path(__file__).parents[1] / "contracts" / "jsonschema"


def _keyed(proposal):
    return replace(proposal, idempotency_key=proposal_idempotency_key(proposal))


def bridge_material():
    packet = TaskPacketV1.from_dict(valid_packet())
    manifest = RunManifestV1.from_packet(packet, deadline="2026-09-02T01:00:00Z")
    snapshot = WorkspaceSnapshotV1.from_facts(
        {
            "contract_version": 1,
            "repository_id": packet.repository_id,
            "workspace_handle": packet.workspace_handle,
            "input_head_sha": packet.authority.exact_head_sha,
            "result_head_sha": "e" * 40,
            "diff_digest": "f" * 64,
            "diff_lines": 23,
            "source": "trusted_git_broker",
        }
    )
    artifact = _keyed(
        ArtifactProposal(
            packet.task_id,
            packet.run_id,
            packet.packet_digest,
            packet.fence,
            4,
            "writer",
            "patch",
            "factory/result.patch",
            "a" * 64,
            321,
            "text/plain",
            "0" * 64,
            "0" * 64,
        )
    )
    attestation = ArtifactAttestationV1.from_facts(
        {
            "contract_version": 1,
            "task_id": packet.task_id,
            "run_id": packet.run_id,
            "repository_id": packet.repository_id,
            "packet_digest": packet.packet_digest,
            "workspace_handle": packet.workspace_handle,
            "producer_sequence": artifact.sequence,
            "fence": packet.fence,
            "author_role": "writer",
            "artifact_class": artifact.artifact_class,
            "path": artifact.path,
            "sha256": artifact.sha256,
            "size_bytes": artifact.size_bytes,
            "media_type": artifact.media_type,
            "source": "trusted_workspace_broker",
        }
    )
    artifact = replace(artifact, artifact_attestation_digest=attestation.artifact_attestation_digest)
    artifact = replace(artifact, idempotency_key=proposal_idempotency_key(artifact))
    terminal = _keyed(
        TerminalProposal(
            packet.task_id,
            packet.run_id,
            packet.packet_digest,
            packet.fence,
            5,
            "writer",
            "run.completed",
            "bounded completion summary",
            None,
            None,
            None,
            "0" * 64,
        )
    )
    result = WorkspaceResultV1.from_facts(
        {
            "contract_version": 1,
            "task_id": packet.task_id,
            "run_id": packet.run_id,
            "task_packet_digest": packet.packet_digest,
            "run_manifest_digest": manifest.manifest_digest,
            "exact_head_sha": snapshot.result_head_sha,
            "workspace_snapshot_digest": snapshot.workspace_snapshot_digest,
            "terminal_stage": "completed",
            "terminal_proposal_digest": terminal.idempotency_key,
            "artifact_manifest_digest": workspace_evidence_digest("artifacts", [artifact.idempotency_key]),
            "note_manifest_digest": workspace_evidence_digest("notes", []),
            "usage_evidence_digest": workspace_evidence_digest("usage", []),
            "diagnostics_digest": workspace_evidence_digest("diagnostics", []),
            "m4_status": "ready_for_human",
            "failure_class": None,
            "failure_reason": None,
        }
    )
    inputs = {
        "schema_version": 1,
        "workspace_result_digest": result.workspace_result_digest,
        "requirements": [
            {"kind": "acceptance_criterion", "requirement_id": "AC-001"},
            {"kind": "acceptance_criterion", "requirement_id": "AC-002"},
            {"kind": "invariant", "requirement_id": "INV-001"},
        ],
        "holdout_evidence_digest": "b" * 64,
        "review_evidence_digest": "c" * 64,
        "original_writer_context_digest": "d" * 64,
        "risk_level": "high",
        "diff_limit": 100,
    }
    return packet, manifest, snapshot, result, terminal, (artifact,), (attestation,), inputs


class SemanticBridgeTests(unittest.TestCase):
    def build(self, **changes):
        values = list(bridge_material())
        names = (
            "packet",
            "manifest",
            "snapshot",
            "result",
            "terminal_proposal",
            "artifact_proposals",
            "artifact_attestations",
            "validation_inputs",
        )
        for name, value in changes.items():
            values[names.index(name)] = value
        return build_semantic_subject(*values)

    def test_bridge_contracts_are_closed_versioned_and_invent_no_m5_fields(self):
        expected = {
            "repair-directive.v1.schema.json",
            "semantic-coverage.v1.schema.json",
            "semantic-execution-binding.v1.schema.json",
            "semantic-finding.v1.schema.json",
            "semantic-subject.v1.schema.json",
            "semantic-validation-inputs.v1.schema.json",
            "semantic-verdict.v1.schema.json",
        }
        self.assertEqual({path.name for path in SCHEMAS.glob("*.json")}, expected)
        for name in ("semantic-execution-binding.v1.schema.json", "semantic-validation-inputs.v1.schema.json"):
            schema = json.loads((SCHEMAS / name).read_text(encoding="utf-8"))
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
            self.assertFalse(schema["additionalProperties"])
            self.assertEqual(schema["properties"]["schema_version"], {"const": 1})
        built = self.build()
        for name, value in (
            ("semantic-execution-binding.v1.schema.json", built.binding.to_dict()),
            ("semantic-validation-inputs.v1.schema.json", built.validation_inputs.to_dict()),
        ):
            command = ["jsonschema", str(SCHEMAS / name)]
            self.assertEqual(
                subprocess.run(
                    command,
                    input=json.dumps(value),
                    text=True,
                    capture_output=True,
                ).returncode,
                0,
                name,
            )

    def test_exact_verified_bundle_derives_subject_without_reinterpreting_m5(self):
        packet, manifest, snapshot, result, terminal, artifacts, attestations, inputs = bridge_material()
        built = build_semantic_subject(
            packet, manifest, snapshot, result, terminal, artifacts, attestations, inputs
        )
        self.assertIsInstance(built.binding, SemanticExecutionBindingV1)
        self.assertIsInstance(built.validation_inputs, SemanticValidationInputsV1)
        self.assertEqual(built.binding.task_id, packet.task_id)
        self.assertEqual(built.binding.run_id, packet.run_id)
        self.assertEqual(built.binding.fence, packet.fence)
        self.assertEqual(built.binding.task_packet_digest, packet.packet_digest)
        self.assertEqual(built.binding.run_manifest_digest, manifest.manifest_digest)
        self.assertEqual(built.binding.workspace_result_digest, result.workspace_result_digest)
        self.assertEqual(built.binding.artifact_proposal_digests, (artifacts[0].idempotency_key,))
        self.assertEqual(
            built.binding.artifact_attestation_digests,
            (attestations[0].artifact_attestation_digest,),
        )
        self.assertEqual(built.subject.deterministic_evidence_digest, built.binding.digest)
        self.assertEqual(built.subject.original_writer_id, packet.owner)
        self.assertEqual(built.subject.exact_base_sha, packet.authority.exact_base_sha)
        self.assertEqual(built.subject.exact_head_sha, result.exact_head_sha)
        self.assertEqual(built.subject.diff_digest, snapshot.diff_digest)
        self.assertEqual(built.subject.diff_lines, snapshot.diff_lines)
        self.assertEqual(built.subject.holdout_evidence_digest, inputs["holdout_evidence_digest"])
        self.assertEqual(built.subject.review_evidence_digest, inputs["review_evidence_digest"])

    def test_digest_and_subject_are_stable_across_canonical_round_trip(self):
        first = self.build()
        binding = SemanticExecutionBindingV1.from_json(json.dumps(first.binding.to_dict(), sort_keys=True))
        inputs = SemanticValidationInputsV1.from_json(
            json.dumps(first.validation_inputs.to_dict(), sort_keys=True)
        )
        self.assertEqual(binding, first.binding)
        self.assertEqual(inputs, first.validation_inputs)
        self.assertEqual(binding.digest, first.binding.digest)
        self.assertEqual(inputs.digest, first.validation_inputs.digest)
        self.assertEqual(first.envelope_digest, self.build().envelope_digest)

    def test_cross_task_run_packet_manifest_snapshot_and_result_substitution_fail_closed(self):
        packet, manifest, snapshot, result, terminal, artifacts, attestations, inputs = bridge_material()
        mutations = {
            "manifest": replace(manifest, run_id="run-other"),
            "result": replace(result, task_id="task-other"),
            "terminal_proposal": replace(terminal, run_id="run-other"),
            "artifact_proposals": (replace(artifacts[0], fence=packet.fence + 1),),
            "artifact_attestations": (replace(attestations[0], run_id="run-other"),),
        }
        # Rebuild the snapshot mutation without its derived field.
        snapshot_facts = snapshot.to_dict()
        snapshot_facts.pop("workspace_snapshot_digest")
        snapshot_facts["input_head_sha"] = "9" * 40
        mutations["snapshot"] = WorkspaceSnapshotV1.from_facts(snapshot_facts)
        for name, mutation in mutations.items():
            with self.subTest(name=name), self.assertRaises(ContractError):
                self.build(**{name: mutation})

    def test_terminal_and_artifact_body_mutation_cannot_reuse_old_digest(self):
        _, _, _, _, terminal, artifacts, attestations, _ = bridge_material()
        with self.assertRaises(ContractError) as terminal_error:
            self.build(terminal_proposal=replace(terminal, summary="changed"))
        self.assertEqual(terminal_error.exception.code, "semantic_terminal_digest_mismatch")
        with self.assertRaises(ContractError) as artifact_error:
            self.build(artifact_proposals=(replace(artifacts[0], path="factory/other.patch"),))
        self.assertEqual(artifact_error.exception.code, "semantic_artifact_digest_mismatch")
        with self.assertRaises(ContractError) as attestation_error:
            self.build(artifact_attestations=(replace(attestations[0], size_bytes=999),))
        self.assertEqual(attestation_error.exception.code, "semantic_attestation_digest_mismatch")

    def test_artifact_manifest_and_one_to_one_attestation_are_required(self):
        packet, manifest, snapshot, result, terminal, artifacts, attestations, inputs = bridge_material()
        changed_result = WorkspaceResultV1.from_facts(
            {
                **result.to_dict(include_digest=False),
                "artifact_manifest_digest": workspace_evidence_digest("artifacts", []),
            }
        )
        with self.assertRaises(ContractError) as manifest_error:
            self.build(result=changed_result)
        self.assertEqual(manifest_error.exception.code, "semantic_artifact_manifest_mismatch")
        with self.assertRaises(ContractError) as missing_error:
            self.build(artifact_attestations=())
        self.assertEqual(missing_error.exception.code, "semantic_artifact_attestation_set_mismatch")
        stored = self.build().binding.to_dict()
        stored["artifact_attestation_digests"] = []
        with self.assertRaises(ContractError) as stored_error:
            SemanticExecutionBindingV1.from_dict(stored)
        self.assertEqual(stored_error.exception.code, "semantic_artifact_attestation_set_mismatch")

    def test_only_writer_ready_for_human_results_enter_semantic_validation(self):
        packet, manifest, snapshot, result, terminal, artifacts, attestations, inputs = bridge_material()
        reader_wire = packet.to_dict(include_digest=False)
        reader_wire["role"] = "reader"
        reader = TaskPacketV1.from_dict(reader_wire)
        with self.assertRaises(ContractError) as role_error:
            self.build(packet=reader)
        self.assertEqual(role_error.exception.code, "semantic_writer_required")

        failed_terminal = _keyed(
            replace(
                terminal,
                terminal_type="run.failed",
                summary="failed",
                failure_class="provider_transport_unavailable",
                diagnostic="bounded",
            )
        )
        failed = WorkspaceResultV1.from_facts(
            {
                **result.to_dict(include_digest=False),
                "terminal_stage": "failed",
                "terminal_proposal_digest": failed_terminal.idempotency_key,
                "m4_status": "retry",
                "failure_class": "provider_transport_unavailable",
                "failure_reason": "bounded",
            }
        )
        failed_inputs = dict(inputs, workspace_result_digest=failed.workspace_result_digest)
        with self.assertRaises(ContractError) as status_error:
            self.build(result=failed, terminal_proposal=failed_terminal, validation_inputs=failed_inputs)
        self.assertEqual(status_error.exception.code, "semantic_result_not_ready")

    def test_missing_m5_facts_are_explicit_result_bound_inputs(self):
        *_, inputs = bridge_material()
        for field, value in (
            ("workspace_result_digest", "0" * 64),
            ("holdout_evidence_digest", None),
            ("review_evidence_digest", None),
            ("original_writer_context_digest", None),
            ("risk_level", None),
            ("diff_limit", None),
        ):
            changed = deepcopy(inputs)
            if value is None:
                changed.pop(field)
            else:
                changed[field] = value
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.build(validation_inputs=changed)

    def test_acceptance_requirements_equal_packet_acceptance_ids_exactly(self):
        *_, inputs = bridge_material()
        missing = deepcopy(inputs)
        missing["requirements"] = missing["requirements"][1:]
        with self.assertRaises(ContractError) as missing_error:
            self.build(validation_inputs=missing)
        self.assertEqual(missing_error.exception.code, "semantic_acceptance_set_mismatch")
        invented = deepcopy(inputs)
        invented["requirements"].insert(
            2, {"kind": "acceptance_criterion", "requirement_id": "AC-999"}
        )
        with self.assertRaises(ContractError) as invented_error:
            self.build(validation_inputs=invented)
        self.assertEqual(invented_error.exception.code, "semantic_acceptance_set_mismatch")

    def test_input_and_binding_json_reject_unknown_fields_and_duplicate_keys(self):
        built = self.build()
        unknown = built.validation_inputs.to_dict()
        unknown["provider_verdict"] = "pass"
        with self.assertRaises(ContractError):
            SemanticValidationInputsV1.from_dict(unknown)
        raw = json.dumps(built.binding.to_dict())[:-1] + ',"task_id":"task-other"}'
        with self.assertRaises(ContractError) as duplicate:
            SemanticExecutionBindingV1.from_json(raw)
        self.assertEqual(duplicate.exception.code, "duplicate_json_key")


if __name__ == "__main__":
    unittest.main()
