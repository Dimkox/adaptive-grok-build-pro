from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Literal

from .contracts import ContractError, HEX40, HEX64, _hex, _id
from .semantic_contracts import MAX_ITEMS, RISK_LEVELS, RepairDirectiveV1, SemanticSubjectV1, SemanticVerdictV1


RISK_ORDER = {"low": 0, "medium": 1, "high": 2, "critical": 3}


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
