from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Literal, Mapping

from .contracts import ContractError, HEX40, HEX64, _hex, _id
from .semantic_contracts import (
    MAX_ITEMS,
    RISK_LEVELS,
    JsonContract,
    RepairDirectiveV1,
    SemanticSubjectV1,
    SemanticVerdictV1,
    _closed,
    _integer,
    _object,
    _sorted_unique,
    _time,
)


RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}
ESCALATION_REASONS = {
    "architecture_changed",
    "authority_changed",
    "base_changed",
    "budget_exhausted",
    "context_not_fresh",
    "deadline_exhausted",
    "diff_changed",
    "diff_limit_exceeded",
    "finding_recurrence",
    "head_changed",
    "original_writer_mismatch",
    "repair_cycle_out_of_bounds",
    "risk_increased",
    "stale_fence",
    "stale_semantic_evidence",
    "unsupported_result_disposition",
    "verdict_not_repair",
    "workspace_result_changed",
}


@dataclass(frozen=True)
class SemanticRepairRequestV1(JsonContract):
    schema_version: int
    subject_digest: str
    verdict_digest: str
    requested_cycle: int
    previous_child_proposal_digest: str | None
    writer_id: str
    context_digest: str
    expected_workspace_result_digest: str
    expected_fence: int
    expected_head_sha: str
    expected_base_sha: str
    expected_architecture_digest: str
    expected_authority_digest: str
    expected_diff_digest: str
    expected_risk_level: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SemanticRepairRequestV1":
        data = _object(data, "semantic_repair_request")
        _closed(data, set(cls.__dataclass_fields__))
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version", "semantic_repair_request")
        risk = data["expected_risk_level"]
        if risk not in RISK_LEVELS - {"none"}:
            raise ContractError("expected_risk_level")
        cycle = _integer(data["requested_cycle"], "requested_cycle", 0, 1_000_000)
        previous = (
            None
            if data["previous_child_proposal_digest"] is None
            else _hex(
                data["previous_child_proposal_digest"],
                "previous_child_proposal_digest",
                HEX64,
            )
        )
        if (cycle == 1 and previous is not None) or (cycle >= 2 and previous is None):
            raise ContractError("repair_cycle_sequence")
        return cls(
            1,
            _hex(data["subject_digest"], "subject_digest", HEX64),
            _hex(data["verdict_digest"], "verdict_digest", HEX64),
            cycle,
            previous,
            _id(data["writer_id"], "writer_id"),
            _hex(data["context_digest"], "context_digest", HEX64),
            _hex(
                data["expected_workspace_result_digest"],
                "expected_workspace_result_digest",
                HEX64,
            ),
            _integer(data["expected_fence"], "expected_fence", 1, 2**63 - 1),
            _hex(data["expected_head_sha"], "expected_head_sha", HEX40),
            _hex(data["expected_base_sha"], "expected_base_sha", HEX40),
            _hex(
                data["expected_architecture_digest"],
                "expected_architecture_digest",
                HEX64,
            ),
            _hex(
                data["expected_authority_digest"],
                "expected_authority_digest",
                HEX64,
            ),
            _hex(data["expected_diff_digest"], "expected_diff_digest", HEX64),
            risk,
        )


@dataclass(frozen=True)
class RepairChildProposalV1(JsonContract):
    schema_version: int
    subject_digest: str
    verdict_digest: str
    directive_digest: str
    cycle: int
    previous_child_proposal_digest: str | None
    parent_task_id: str
    parent_run_id: str
    parent_fence: int
    parent_task_packet_digest: str
    parent_run_manifest_digest: str
    parent_workspace_result_digest: str
    parent_exact_head_sha: str
    writer_id: str
    context_digest: str
    exact_base_sha: str
    architecture_digest: str
    authority_digest: str
    diff_digest: str
    finding_identity_digests: tuple[str, ...]
    baseline_risk_level: str
    max_cost_usd_micros: int
    max_token_units: int
    max_output_bytes: int
    max_events: int
    infrastructure_retries_remaining: int
    budget_remaining_units: int
    deadline_at: datetime
    proposal_state: str
    requires_new_workspace_result: bool
    requires_new_semantic_subject: bool

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RepairChildProposalV1":
        data = _object(data, "repair_child_proposal")
        _closed(data, set(cls.__dataclass_fields__))
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version", "repair_child_proposal")
        for requirement in (
            "requires_new_workspace_result",
            "requires_new_semantic_subject",
        ):
            if data[requirement] is not True:
                raise ContractError(requirement)
        if data["proposal_state"] != "pending_handoff":
            raise ContractError("proposal_state")
        cycle = _integer(data["cycle"], "repair_cycle", 1, 3)
        previous = (
            None
            if data["previous_child_proposal_digest"] is None
            else _hex(
                data["previous_child_proposal_digest"],
                "previous_child_proposal_digest",
                HEX64,
            )
        )
        if (cycle == 1 and previous is not None) or (cycle > 1 and previous is None):
            raise ContractError("repair_cycle_sequence")
        return cls(
            1,
            _hex(data["subject_digest"], "subject_digest", HEX64),
            _hex(data["verdict_digest"], "verdict_digest", HEX64),
            _hex(data["directive_digest"], "directive_digest", HEX64),
            cycle,
            previous,
            _id(data["parent_task_id"], "parent_task_id"),
            _id(data["parent_run_id"], "parent_run_id"),
            _integer(data["parent_fence"], "parent_fence", 1, 2**63 - 1),
            _hex(
                data["parent_task_packet_digest"],
                "parent_task_packet_digest",
                HEX64,
            ),
            _hex(
                data["parent_run_manifest_digest"],
                "parent_run_manifest_digest",
                HEX64,
            ),
            _hex(
                data["parent_workspace_result_digest"],
                "parent_workspace_result_digest",
                HEX64,
            ),
            _hex(data["parent_exact_head_sha"], "parent_exact_head_sha", HEX40),
            _id(data["writer_id"], "writer_id"),
            _hex(data["context_digest"], "context_digest", HEX64),
            _hex(data["exact_base_sha"], "exact_base_sha", HEX40),
            _hex(data["architecture_digest"], "architecture_digest", HEX64),
            _hex(data["authority_digest"], "authority_digest", HEX64),
            _hex(data["diff_digest"], "diff_digest", HEX64),
            _sorted_unique(
                data["finding_identity_digests"],
                "finding_identity_digests",
                lambda value: _hex(value, "finding_identity_digest", HEX64),
            ),
            _risk(data["baseline_risk_level"], "baseline_risk_level"),
            _integer(
                data["max_cost_usd_micros"],
                "max_cost_usd_micros",
                0,
                2**63 - 1,
            ),
            _integer(data["max_token_units"], "max_token_units", 0, 2**63 - 1),
            _integer(data["max_output_bytes"], "max_output_bytes", 0, 2**63 - 1),
            _integer(data["max_events"], "max_events", 0, 2**63 - 1),
            _integer(
                data["infrastructure_retries_remaining"],
                "infrastructure_retries_remaining",
                0,
                2,
            ),
            _integer(
                data["budget_remaining_units"],
                "budget_remaining_units",
                1,
                2**63 - 1,
            ),
            _time(data["deadline_at"], "deadline_at"),
            "pending_handoff",
            True,
            True,
        )


def _risk(value: Any, name: str) -> str:
    if value not in RISK_LEVELS - {"none"}:
        raise ContractError(name)
    return value


@dataclass(frozen=True)
class RepairChildTaskBindingV1(JsonContract):
    schema_version: int
    child_proposal_digest: str
    child_task_id: str
    child_intent_digest: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RepairChildTaskBindingV1":
        data = _object(data, "repair_child_task_binding")
        _closed(data, set(cls.__dataclass_fields__))
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version", "repair_child_task_binding")
        return cls(
            1,
            _hex(data["child_proposal_digest"], "child_proposal_digest", HEX64),
            _id(data["child_task_id"], "child_task_id"),
            _hex(data["child_intent_digest"], "child_intent_digest", HEX64),
        )


@dataclass(frozen=True)
class RepairEscalationV1(JsonContract):
    schema_version: int
    subject_digest: str
    verdict_digest: str
    requested_cycle: int
    reason: str
    request_digest: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RepairEscalationV1":
        data = _object(data, "repair_escalation")
        _closed(data, set(cls.__dataclass_fields__))
        if data["schema_version"] != 1:
            raise ContractError("unsupported_version", "repair_escalation")
        if data["reason"] not in ESCALATION_REASONS:
            raise ContractError("repair_escalation_reason")
        return cls(
            1,
            _hex(data["subject_digest"], "subject_digest", HEX64),
            _hex(data["verdict_digest"], "verdict_digest", HEX64),
            _integer(data["requested_cycle"], "requested_cycle", 0, 1_000_000),
            data["reason"],
            _hex(data["request_digest"], "request_digest", HEX64),
        )


@dataclass(frozen=True)
class RepairLifecycleResult:
    decision: Literal["repair", "needs_human"]
    reason: str
    subject_digest: str
    verdict_digest: str
    cycle: int
    directive_digest: str | None
    directive: RepairDirectiveV1 | None
    child_proposal_digest: str | None
    child_proposal: RepairChildProposalV1 | None
    escalation_digest: str | None
    escalation: RepairEscalationV1 | None

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "RepairLifecycleResult":
        data = _object(data, "repair_lifecycle_result")
        _closed(data, set(cls.__dataclass_fields__))
        decision = data["decision"]
        if decision not in {"repair", "needs_human"}:
            raise ContractError("repair_lifecycle_decision")
        subject_digest = _hex(data["subject_digest"], "subject_digest", HEX64)
        verdict_digest = _hex(data["verdict_digest"], "verdict_digest", HEX64)
        cycle = _integer(data["cycle"], "requested_cycle", 0, 1_000_000)
        if decision == "repair":
            if data["reason"] != "repair_allowed":
                raise ContractError("repair_lifecycle_reason")
            directive = RepairDirectiveV1.from_dict(data["directive"])
            child = RepairChildProposalV1.from_dict(data["child_proposal"])
            directive_digest = _hex(
                data["directive_digest"], "directive_digest", HEX64
            )
            child_digest = _hex(
                data["child_proposal_digest"], "child_proposal_digest", HEX64
            )
            if (
                directive.digest != directive_digest
                or child.digest != child_digest
                or directive.subject_digest != subject_digest
                or directive.verdict_digest != verdict_digest
                or directive.cycle != cycle
                or child.subject_digest != subject_digest
                or child.verdict_digest != verdict_digest
                or child.directive_digest != directive_digest
                or child.cycle != cycle
                or data["escalation_digest"] is not None
                or data["escalation"] is not None
            ):
                raise ContractError("repair_lifecycle_binding")
            escalation_digest = None
            escalation = None
        else:
            if data["reason"] not in ESCALATION_REASONS:
                raise ContractError("repair_lifecycle_reason")
            escalation = RepairEscalationV1.from_dict(data["escalation"])
            escalation_digest = _hex(
                data["escalation_digest"], "escalation_digest", HEX64
            )
            if (
                escalation.digest != escalation_digest
                or escalation.subject_digest != subject_digest
                or escalation.verdict_digest != verdict_digest
                or escalation.requested_cycle != cycle
                or escalation.reason != data["reason"]
                or any(
                    data[field] is not None
                    for field in (
                        "directive_digest",
                        "directive",
                        "child_proposal_digest",
                        "child_proposal",
                    )
                )
            ):
                raise ContractError("repair_lifecycle_binding")
            directive_digest = None
            directive = None
            child_digest = None
            child = None
        return cls(
            decision,
            data["reason"],
            subject_digest,
            verdict_digest,
            cycle,
            directive_digest,
            directive,
            child_digest,
            child,
            escalation_digest,
            escalation,
        )


@dataclass(frozen=True)
class RepairPolicyDecision:
    decision: Literal["repair", "needs_human"]
    reason: str
    directive: RepairDirectiveV1 | None


def _human(reason: str) -> RepairPolicyDecision:
    return RepairPolicyDecision("needs_human", reason, None)


def _digests(values: Iterable[str], name: str) -> tuple[str, ...]:
    result = tuple(values)
    if len(result) > MAX_ITEMS or result != tuple(sorted(set(result))):
        raise ContractError(name)
    return tuple(_hex(value, name, HEX64) for value in result)


def _remaining(value: int, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ContractError(name)
    return value


def plan_repair(
    subject: SemanticSubjectV1,
    verdict: SemanticVerdictV1,
    *,
    requested_cycle: int,
    writer_id: str,
    context_digest: str,
    prior_context_digests: Iterable[str],
    prior_finding_identity_digests: Iterable[str],
    expected_base_sha: str,
    expected_architecture_digest: str,
    expected_authority_digest: str,
    baseline_risk_level: str,
    budget_remaining_units: int,
    deadline_remaining_seconds: int,
) -> RepairPolicyDecision:
    try:
        verdict.validate_for(subject)
    except ContractError as exc:
        if exc.code == "stale_semantic_evidence":
            return _human("stale_semantic_evidence")
        raise

    writer = _id(writer_id, "writer_id")
    context = _hex(context_digest, "context_digest", HEX64)
    prior_contexts = _digests(prior_context_digests, "prior_context_digests")
    prior_findings = _digests(prior_finding_identity_digests, "prior_finding_identity_digests")
    expected_base = _hex(expected_base_sha, "expected_base_sha", HEX40)
    expected_architecture = _hex(expected_architecture_digest, "expected_architecture_digest", HEX64)
    expected_authority = _hex(expected_authority_digest, "expected_authority_digest", HEX64)
    if baseline_risk_level not in RISK_LEVELS - {"none"}:
        raise ContractError("baseline_risk_level")
    budget = _remaining(budget_remaining_units, "budget_remaining_units")
    deadline = _remaining(deadline_remaining_seconds, "deadline_remaining_seconds")

    if writer != subject.original_writer_id:
        return _human("original_writer_mismatch")
    if type(requested_cycle) is not int or requested_cycle not in {1, 2, 3}:
        return _human("repair_cycle_out_of_bounds")
    if set(verdict.finding_identity_digests) & set(prior_findings):
        return _human("finding_recurrence")
    if RISK_ORDER[subject.risk_level] > RISK_ORDER[baseline_risk_level]:
        return _human("risk_increased")
    if subject.diff_lines > subject.diff_limit:
        return _human("diff_limit_exceeded")
    if subject.architecture_digest != expected_architecture:
        return _human("architecture_changed")
    if subject.authority_digest != expected_authority:
        return _human("authority_changed")
    if subject.exact_base_sha != expected_base:
        return _human("base_changed")
    if budget == 0:
        return _human("budget_exhausted")
    if deadline == 0:
        return _human("deadline_exhausted")
    if context == subject.original_writer_context_digest or context in set(prior_contexts):
        return _human("context_not_fresh")
    if verdict.decision != "repair":
        return _human("verdict_not_repair")

    directive = RepairDirectiveV1.from_dict(
        {
            "schema_version": 1,
            "subject_digest": subject.digest,
            "verdict_digest": verdict.digest,
            "cycle": requested_cycle,
            "writer_id": subject.original_writer_id,
            "context_digest": context,
            "exact_head_sha": subject.exact_head_sha,
            "finding_identity_digests": list(verdict.finding_identity_digests),
        }
    )
    return RepairPolicyDecision("repair", "repair_allowed", directive)
