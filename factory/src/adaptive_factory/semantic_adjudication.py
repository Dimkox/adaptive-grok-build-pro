from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable

from .contracts import ContractError
from .semantic_contracts import (
    MAX_ITEMS,
    SemanticCoverageV1,
    SemanticFindingV1,
    SemanticSubjectV1,
    SemanticVerdictV1,
)


HUMAN_CATEGORIES = {"security_boundary", "authority_violation", "contradiction"}


def _bounded(values: Iterable, name: str) -> tuple:
    result = tuple(values)
    if len(result) > MAX_ITEMS:
        raise ContractError("semantic_items_exceeded", name)
    return result


def adjudicate(
    subject: SemanticSubjectV1,
    findings: Iterable[SemanticFindingV1],
    coverages: Iterable[SemanticCoverageV1],
) -> SemanticVerdictV1:
    finding_values = _bounded(findings, "findings")
    coverage_values = _bounded(coverages, "coverages")
    if not coverage_values:
        raise ContractError("semantic_coverage_missing")

    for finding in finding_values:
        if not isinstance(finding, SemanticFindingV1):
            raise ContractError("semantic_finding_type")
        finding.validate_for(subject)
    for coverage in coverage_values:
        if not isinstance(coverage, SemanticCoverageV1):
            raise ContractError("semantic_coverage_type")
        coverage.validate_for(subject)

    identity_counts = Counter(item.identity_digest for item in finding_values)
    finding_identities = tuple(sorted(identity_counts))
    duplicates = tuple(sorted(identity for identity, count in identity_counts.items() if count > 1))

    identities_by_requirement: dict[str, set[str]] = defaultdict(set)
    for item in finding_values:
        identities_by_requirement[item.requirement.key].add(item.identity_digest)
    correlations = tuple(
        sorted(requirement for requirement, identities in identities_by_requirement.items() if len(identities) > 1)
    )

    statuses: dict[str, set[str]] = defaultdict(set)
    unsupported: set[str] = set()
    for report in coverage_values:
        for entry in report.entries:
            key = entry.requirement.key
            statuses[key].add(entry.status)
            if entry.status == "proven" and (not entry.evidence_refs or key in identities_by_requirement):
                unsupported.add(key)
            if entry.status == "out_of_scope":
                unsupported.add(key)

    contradictions = tuple(
        sorted(key for key, values in statuses.items() if len(values) > 1 or "contradicted" in values)
    )
    unsupported_passes = tuple(sorted(unsupported))
    human_finding = any(
        not item.repairable or item.category in HUMAN_CATEGORIES for item in finding_values
    )
    requires_human = bool(contradictions or unsupported_passes or human_finding)
    requires_repair = bool(
        finding_identities
        or any(status != "proven" for values in statuses.values() for status in values)
    )

    if requires_human:
        decision = "needs_human"
        residual_risk = "critical" if subject.risk_level == "critical" else "high"
    elif requires_repair:
        decision = "repair"
        residual_risk = subject.risk_level
    else:
        decision = "pass"
        residual_risk = "none"

    return SemanticVerdictV1.from_dict(
        {
            "schema_version": 1,
            "subject_digest": subject.digest,
            "decision": decision,
            "decision_source": "deterministic_adjudicator",
            "finding_identity_digests": list(finding_identities),
            "duplicate_identity_digests": list(duplicates),
            "correlated_requirement_keys": list(correlations),
            "contradicted_requirement_keys": list(contradictions),
            "unsupported_pass_requirement_keys": list(unsupported_passes),
            "residual_risk": residual_risk,
        }
    )
