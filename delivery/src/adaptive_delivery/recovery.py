"""Pure recovery selection that can only narrow an exact M9 promotion."""

from __future__ import annotations

from dataclasses import fields
from datetime import UTC, datetime

from .contracts import (
    ContractError,
    DeliveryDecisionV1,
    DeliveryPromotionV1,
    RecoveryDecisionV1,
    SignedArtifactRefV1,
    canonical_digest,
)
from .m8_boundary import m8_gate_reasons


class RecoverySelectionError(ContractError):
    """The exact failed decision has no authorized narrowing recovery."""


def _parse_time(value: str, field: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except (TypeError, ValueError) as exc:
        raise RecoverySelectionError(field, "must be UTC whole-second time") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise RecoverySelectionError(field, "must be UTC whole-second time")
    return parsed


def _record_payload(record: object, digest_field: str) -> dict[str, object]:
    return {
        field.name: getattr(record, field.name)
        for field in fields(record)
        if field.name != digest_field
    }


def _artifact_resource(artifact: SignedArtifactRefV1) -> dict[str, object]:
    names = (
        "schema_version",
        "repository_id",
        "merged_sha",
        "artifact_digest",
        "sbom_digest",
        "provenance_digest",
        "supply_chain_manifest_digest",
        "image_digest",
    )
    return {name: getattr(artifact, name) for name in names}


def _promotion_resource(promotion: DeliveryPromotionV1) -> dict[str, object]:
    names = (
        "schema_version",
        "promotion_id",
        "repository_id",
        "artifact",
        "previous_signed_artifact",
        "m8_evidence",
        "policy_digest",
        "holdout_digest",
        "runner_image_digest",
        "environment_set_digest",
        "exposure_plan",
        "requested_at",
        "expires_at",
    )
    return {name: getattr(promotion, name) for name in names}


def _authority_valid(artifact: SignedArtifactRefV1, at: datetime) -> bool:
    return (
        artifact.authority_scope == "signed_artifact_use"
        and artifact.authority_resource_digest
        == canonical_digest(_artifact_resource(artifact))
        and _parse_time(artifact.authority_verified_at, "authority_verified_at")
        <= at
        < _parse_time(artifact.authority_expires_at, "authority_expires_at")
    )


def _validate_current_authority(
    promotion: DeliveryPromotionV1, decision_time: datetime
) -> None:
    promotion_valid = (
        promotion.authority_scope == "nonproduction_staged_delivery"
        and promotion.authority_resource_digest
        == canonical_digest(_promotion_resource(promotion))
        and promotion.promotion_digest
        == canonical_digest(_record_payload(promotion, "promotion_digest"))
        and _parse_time(promotion.requested_at, "requested_at")
        <= decision_time
        < _parse_time(promotion.expires_at, "expires_at")
        and _parse_time(promotion.authority_verified_at, "authority_verified_at")
        <= decision_time
        < _parse_time(promotion.authority_expires_at, "authority_expires_at")
    )
    if not promotion_valid or not _authority_valid(promotion.artifact, decision_time):
        raise RecoverySelectionError(
            "validity", "promotion and current artifact must be valid at decision_time"
        )
    if m8_gate_reasons(promotion.m8_evidence, decision_time):
        raise RecoverySelectionError("m8_evidence", "is not current and eligible")


def _planned_exposures(
    promotion: DeliveryPromotionV1, environment: str
) -> tuple[int, ...]:
    plan = promotion.exposure_plan
    if environment == "preview":
        return plan.preview_basis_points
    if environment == "staging":
        return plan.staging_basis_points
    if environment == "bounded_canary":
        return plan.canary_basis_points
    raise RecoverySelectionError("environment", "production recovery is unreachable")


def _validate_failed_decision(
    promotion: DeliveryPromotionV1,
    failed_decision: DeliveryDecisionV1,
    decision_time: datetime,
) -> tuple[int, ...]:
    if not isinstance(failed_decision, DeliveryDecisionV1):
        raise RecoverySelectionError("failed_decision", "must be DeliveryDecisionV1")
    if failed_decision.decision_digest != canonical_digest(
        _record_payload(failed_decision, "decision_digest")
    ):
        raise RecoverySelectionError("failed_decision", "digest binding is invalid")
    if failed_decision.outcome != "deny" or "thresholds_passed" in failed_decision.reason_codes:
        raise RecoverySelectionError("failed_decision", "must be a fail-closed denial")
    if failed_decision.promotion_digest != promotion.promotion_digest:
        raise RecoverySelectionError("promotion_digest", "does not match promotion")
    if failed_decision.artifact_digest != promotion.artifact.artifact_digest:
        raise RecoverySelectionError("artifact_digest", "does not match current artifact")
    if _parse_time(failed_decision.evaluation_time, "evaluation_time") > decision_time:
        raise RecoverySelectionError(
            "decision_time", "cannot precede the failed evaluation"
        )
    exposures = _planned_exposures(promotion, failed_decision.environment)
    if failed_decision.exposure_basis_points not in exposures:
        raise RecoverySelectionError(
            "current_exposure_basis_points", "is not an exact plan step"
        )
    return exposures


def _build_recovery(
    promotion: DeliveryPromotionV1,
    failed_decision: DeliveryDecisionV1,
    decision_time: str,
    *,
    action: str,
    target_exposure_basis_points: int | None = None,
    restore_artifact_digest: str | None = None,
) -> RecoveryDecisionV1:
    action_reason = {
        "halt": "recovery_halt",
        "decrease_exposure": "recovery_decrease",
        "restore_previous": "recovery_restore_previous",
    }[action]
    reasons = tuple(sorted(set(failed_decision.reason_codes + (action_reason,))))
    identity = {
        "promotion_digest": promotion.promotion_digest,
        "failed_decision_digest": failed_decision.decision_digest,
        "decision_time": decision_time,
        "action": action,
        "target_exposure_basis_points": target_exposure_basis_points,
        "restore_artifact_digest": restore_artifact_digest,
    }
    values = {
        "schema_version": 1,
        "recovery_id": f"recovery/{canonical_digest(identity)[:32]}",
        "promotion_digest": promotion.promotion_digest,
        "failed_decision_digest": failed_decision.decision_digest,
        "environment": failed_decision.environment,
        "current_exposure_basis_points": failed_decision.exposure_basis_points,
        "action": action,
        "target_exposure_basis_points": target_exposure_basis_points,
        "restore_artifact_digest": restore_artifact_digest,
        "reason_codes": reasons,
        "decision_time": decision_time,
    }
    values["recovery_digest"] = canonical_digest(values)
    return RecoveryDecisionV1(**values)


def choose_recovery(
    promotion: DeliveryPromotionV1,
    failed_decision: DeliveryDecisionV1,
    decision_time: str,
) -> RecoveryDecisionV1:
    """Select the least-authority plan action valid at ``decision_time``."""

    if not isinstance(promotion, DeliveryPromotionV1):
        raise RecoverySelectionError("promotion", "must be DeliveryPromotionV1")
    decided_at = _parse_time(decision_time, "decision_time")
    _validate_current_authority(promotion, decided_at)
    exposures = _validate_failed_decision(promotion, failed_decision, decided_at)

    previous_invalid = False
    for action in promotion.exposure_plan.allowed_recovery_actions:
        if action == "halt":
            return _build_recovery(
                promotion,
                failed_decision,
                decision_time,
                action="halt",
            )
        if action == "decrease_exposure":
            current_index = exposures.index(failed_decision.exposure_basis_points)
            if current_index > 0:
                return _build_recovery(
                    promotion,
                    failed_decision,
                    decision_time,
                    action="decrease_exposure",
                    target_exposure_basis_points=exposures[current_index - 1],
                )
        if action == "restore_previous":
            if _authority_valid(promotion.previous_signed_artifact, decided_at):
                return _build_recovery(
                    promotion,
                    failed_decision,
                    decision_time,
                    action="restore_previous",
                    restore_artifact_digest=(
                        promotion.previous_signed_artifact.artifact_digest
                    ),
                )
            previous_invalid = True

    if previous_invalid:
        raise RecoverySelectionError(
            "previous artifact validity", "cannot authorize exact restoration"
        )
    raise RecoverySelectionError(
        "recovery", "no plan-authorized narrowing action is valid for this state"
    )
