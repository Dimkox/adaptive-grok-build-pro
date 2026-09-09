"""Append-only source-only controller for deterministic M9 dry runs."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import fields
from datetime import UTC, datetime
from threading import Lock

from .contracts import (
    ContractError,
    DeliveryEvidenceV1,
    DeliveryPromotionV1,
    EnvironmentObservationV1,
    canonical_digest,
)
from .evaluator import evaluate_delivery
from .fake_environment import FakeEnvironmentAdapter
from .m8_boundary import m8_gate_reasons
from .recovery import RecoverySelectionError, choose_recovery

_MAX_OBSERVATIONS = 128
_REVIEWED_ADAPTER_TYPE = FakeEnvironmentAdapter
_REVIEWED_ADAPTER_INIT = FakeEnvironmentAdapter.__init__
_REVIEWED_ADAPTER_APPLY = FakeEnvironmentAdapter.apply
_REVIEWED_ADAPTER_EFFECTS = FakeEnvironmentAdapter.effects
_REVIEWED_ADAPTER_GETATTRIBUTE = FakeEnvironmentAdapter.__getattribute__
_REVIEWED_ADAPTER_SETATTR = FakeEnvironmentAdapter.__setattr__
_REVIEWED_ADAPTER_SLOTS = FakeEnvironmentAdapter.__slots__
_REVIEWED_ADAPTER_EFFECT_SLOT = (
    FakeEnvironmentAdapter._FakeEnvironmentAdapter__effects
)
_REVIEWED_ADAPTER_SUPPORTED_EFFECTS = FakeEnvironmentAdapter.supported_effects
_RECOVERY_REASONS = frozenset(
    {"recovery_decrease", "recovery_halt", "recovery_restore_previous"}
)


class EvidenceChainError(ContractError):
    """The supplied or next evidence record is not one exact append-only chain."""


def _require_reviewed_adapter_surface(adapter: object) -> FakeEnvironmentAdapter:
    if type(adapter) is not _REVIEWED_ADAPTER_TYPE:
        raise EvidenceChainError(
            "adapter", "only the exact bounded in-memory fake adapter is accepted"
        )
    if (
        _REVIEWED_ADAPTER_TYPE.__init__ is not _REVIEWED_ADAPTER_INIT
        or _REVIEWED_ADAPTER_TYPE.apply is not _REVIEWED_ADAPTER_APPLY
        or _REVIEWED_ADAPTER_TYPE.effects is not _REVIEWED_ADAPTER_EFFECTS
        or _REVIEWED_ADAPTER_TYPE.__getattribute__
        is not _REVIEWED_ADAPTER_GETATTRIBUTE
        or _REVIEWED_ADAPTER_TYPE.__setattr__ is not _REVIEWED_ADAPTER_SETATTR
        or _REVIEWED_ADAPTER_TYPE.__slots__ is not _REVIEWED_ADAPTER_SLOTS
        or _REVIEWED_ADAPTER_TYPE._FakeEnvironmentAdapter__effects
        is not _REVIEWED_ADAPTER_EFFECT_SLOT
        or _REVIEWED_ADAPTER_TYPE.supported_effects
        is not _REVIEWED_ADAPTER_SUPPORTED_EFFECTS
    ):
        raise EvidenceChainError("adapter", "reviewed adapter class surface changed")
    return adapter


def _record_payload(record: object, digest_field: str) -> dict[str, object]:
    return {
        field.name: getattr(record, field.name)
        for field in fields(record)
        if field.name != digest_field
    }


def _parse_time(value: str, field: str) -> datetime:
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except (TypeError, ValueError) as exc:
        raise EvidenceChainError(field, "must be UTC whole-second time") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise EvidenceChainError(field, "must be UTC whole-second time")
    return parsed


def _normalize_observations(
    observation_set: EnvironmentObservationV1 | Sequence[EnvironmentObservationV1],
) -> tuple[EnvironmentObservationV1, ...]:
    if isinstance(observation_set, EnvironmentObservationV1):
        return (observation_set,)
    if isinstance(observation_set, (str, bytes)) or not isinstance(
        observation_set, Sequence
    ):
        raise EvidenceChainError("observation_set", "must be an observation sequence")
    count = len(observation_set)
    if count > _MAX_OBSERVATIONS:
        raise EvidenceChainError(
            "observation_set", f"cannot exceed {_MAX_OBSERVATIONS} observations"
        )
    observations = tuple(observation_set[index] for index in range(count))
    if len(observations) > _MAX_OBSERVATIONS:
        raise EvidenceChainError(
            "observation_set", f"cannot exceed {_MAX_OBSERVATIONS} observations"
        )
    if any(not isinstance(item, EnvironmentObservationV1) for item in observations):
        raise EvidenceChainError("observation_set", "contains a non-observation value")
    return observations


def _normalize_prior_evidence(
    prior_evidence: Sequence[DeliveryEvidenceV1],
) -> tuple[DeliveryEvidenceV1, ...]:
    if type(prior_evidence) is not tuple:
        raise EvidenceChainError(
            "prior_evidence",
            "must be the exact empty tuple sequence until Task5 trusted import",
        )
    if prior_evidence:
        raise EvidenceChainError(
            "prior_evidence",
            "non-empty import requires a trusted Task5 checkpoint witness",
        )
    return ()


def _observation_set_digest(
    observations: tuple[EnvironmentObservationV1, ...],
) -> str:
    return canonical_digest(tuple(sorted(item.observation_digest for item in observations)))


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
    raise EvidenceChainError("environment", "production is unreachable")


def _advance_state(
    promotion: DeliveryPromotionV1, environment: str, exposure: int
) -> tuple[str, int] | None:
    exposures = _planned_exposures(promotion, environment)
    if exposure not in exposures:
        raise EvidenceChainError("exposure_basis_points", "is not an exact plan step")
    index = exposures.index(exposure)
    if index + 1 < len(exposures):
        return environment, exposures[index + 1]
    if environment == "preview":
        return "staging", promotion.exposure_plan.staging_basis_points[0]
    if environment == "staging":
        return "bounded_canary", promotion.exposure_plan.canary_basis_points[0]
    return None


def _initial_state(promotion: DeliveryPromotionV1) -> tuple[str, str, int]:
    return (
        promotion.artifact.artifact_digest,
        "preview",
        promotion.exposure_plan.preview_basis_points[0],
    )


def _require_recovery_reason_shape(
    evidence: DeliveryEvidenceV1,
    expected_recovery_reason: str,
) -> None:
    reasons = set(evidence.reason_codes)
    denial_reasons = reasons - _RECOVERY_REASONS - {
        "production_requires_human",
        "thresholds_passed",
    }
    if (
        "thresholds_passed" in reasons
        or reasons.intersection(_RECOVERY_REASONS) != {expected_recovery_reason}
        or not denial_reasons
    ):
        raise EvidenceChainError(
            "reason_codes",
            "recovery requires one matching recovery code and a denial reason",
        )


def _require_recording_authority(
    promotion: DeliveryPromotionV1,
    recorded_at: datetime,
    *,
    include_previous_artifact: bool,
) -> None:
    if m8_gate_reasons(promotion.m8_evidence, recorded_at):
        raise EvidenceChainError(
            "m8_evidence", "profile is not current and eligible at recording"
        )
    windows = (
        (
            "promotion",
            _parse_time(promotion.requested_at, "requested_at"),
            min(
                _parse_time(promotion.expires_at, "expires_at"),
                _parse_time(
                    promotion.authority_expires_at,
                    "authority_expires_at",
                ),
            ),
        ),
        (
            "current artifact authority",
            _parse_time(
                promotion.artifact.authority_verified_at,
                "authority_verified_at",
            ),
            _parse_time(
                promotion.artifact.authority_expires_at,
                "authority_expires_at",
            ),
        ),
    )
    for name, valid_from, expires_at in windows:
        if recorded_at < valid_from:
            raise EvidenceChainError(
                "recorded_at", f"{name} is not yet valid at recording"
            )
        if recorded_at >= expires_at:
            raise EvidenceChainError(
                "recorded_at", f"{name} expired before recording"
            )
    if include_previous_artifact:
        previous = promotion.previous_signed_artifact
        valid_from = _parse_time(
            previous.authority_verified_at,
            "authority_verified_at",
        )
        expires_at = _parse_time(
            previous.authority_expires_at,
            "authority_expires_at",
        )
        if recorded_at < valid_from:
            raise EvidenceChainError(
                "recorded_at", "previous artifact authority is not yet valid"
            )
        if recorded_at >= expires_at:
            raise EvidenceChainError(
                "recorded_at", "previous artifact authority expired before restore"
            )


def _is_terminal(evidence: DeliveryEvidenceV1) -> bool:
    return evidence.dry_run_effect in {"halted", "restored", "needs_human"} or (
        evidence.dry_run_effect == "none"
        and bool(evidence.reason_codes)
        and "thresholds_passed" not in evidence.reason_codes
    )


def _transition_state(
    promotion: DeliveryPromotionV1,
    source: tuple[str, str, int],
    evidence: DeliveryEvidenceV1,
) -> tuple[str, str, int]:
    artifact_digest, environment, exposure = source
    current = (artifact_digest, environment, exposure)
    result = (
        evidence.artifact_digest,
        evidence.environment,
        evidence.exposure_basis_points,
    )
    has_recovery = evidence.recovery_decision_digest is not None
    effect = evidence.dry_run_effect
    if environment == "production" or evidence.environment == "production":
        raise EvidenceChainError("environment", "production is unreachable")
    if effect == "none":
        if (
            has_recovery
            or result != current
            or not evidence.reason_codes
            or "thresholds_passed" in evidence.reason_codes
            or _RECOVERY_REASONS.intersection(evidence.reason_codes)
        ):
            raise EvidenceChainError("dry_run_effect", "none cannot change state")
    elif effect in {"entered_stage", "changed_exposure"} and not has_recovery:
        if evidence.reason_codes != ("thresholds_passed",):
            raise EvidenceChainError(
                "reason_codes", "normal advance requires passed thresholds"
            )
        advanced = _advance_state(promotion, environment, exposure)
        if advanced is None:
            raise EvidenceChainError("dry_run_effect", "cannot advance past last canary")
        expected = (artifact_digest, advanced[0], advanced[1])
        expected_effect = (
            "entered_stage" if advanced[0] != environment else "changed_exposure"
        )
        if effect != expected_effect or result != expected:
            raise EvidenceChainError("dry_run_effect", "stage order is not contiguous")
    elif effect == "changed_exposure" and has_recovery:
        _require_recovery_reason_shape(evidence, "recovery_decrease")
        exposures = _planned_exposures(promotion, environment)
        if exposure not in exposures:
            raise EvidenceChainError("exposure_basis_points", "is not an exact plan step")
        index = exposures.index(exposure)
        expected = (
            artifact_digest,
            environment,
            exposures[index - 1] if index > 0 else -1,
        )
        if result != expected:
            raise EvidenceChainError(
                "dry_run_effect", "recovery must select the immediately earlier step"
            )
    elif effect == "halted":
        if not has_recovery:
            raise EvidenceChainError(
                "reason_codes", "halt requires a bound recovery decision"
            )
        _require_recovery_reason_shape(evidence, "recovery_halt")
        if result != current:
            raise EvidenceChainError("dry_run_effect", "halt must retain exact state")
    elif effect == "restored":
        expected = (
            promotion.previous_signed_artifact.artifact_digest,
            environment,
            exposure,
        )
        if not has_recovery:
            raise EvidenceChainError(
                "reason_codes", "restore requires a bound recovery decision"
            )
        _require_recovery_reason_shape(evidence, "recovery_restore_previous")
        if result != expected:
            raise EvidenceChainError(
                "dry_run_effect", "restore must name the exact previous artifact"
            )
    elif effect == "needs_human":
        is_last_canary = (
            environment == "bounded_canary"
            and exposure == promotion.exposure_plan.canary_basis_points[-1]
        )
        if (
            has_recovery
            or not is_last_canary
            or result != current
            or evidence.reason_codes
            != ("production_requires_human", "thresholds_passed")
        ):
            raise EvidenceChainError(
                "dry_run_effect", "human boundary is only after the last canary"
            )
    else:
        raise EvidenceChainError("dry_run_effect", "is inconsistent with recovery")
    return result


def _validate_chain(
    promotion: DeliveryPromotionV1,
    evidence_chain: tuple[DeliveryEvidenceV1, ...],
) -> None:
    if len(evidence_chain) > 128:
        raise EvidenceChainError("evidence", "cannot exceed 128 records")
    state = _initial_state(promotion)
    previous_digest: str | None = None
    previous_time: datetime | None = None
    evidence_ids: set[str] = set()
    evidence_digests: set[str] = set()
    observation_digests: set[str] = set()
    delivery_digests: set[str] = set()
    recovery_digests: set[str] = set()
    terminal = False

    for expected_sequence, evidence in enumerate(evidence_chain, 1):
        if not isinstance(evidence, DeliveryEvidenceV1):
            raise EvidenceChainError("evidence", "contains a non-evidence record")
        if evidence.evidence_digest != canonical_digest(
            _record_payload(evidence, "evidence_digest")
        ):
            raise EvidenceChainError("evidence_digest", "does not bind the record")
        if terminal:
            raise EvidenceChainError("evidence", "cannot follow a terminal record")
        if evidence.sequence != expected_sequence:
            raise EvidenceChainError("sequence", "must be contiguous from one")
        if evidence.previous_evidence_digest != previous_digest:
            raise EvidenceChainError("previous_evidence_digest", "does not match predecessor")
        if evidence.promotion_digest != promotion.promotion_digest:
            raise EvidenceChainError("promotion_digest", "does not match exact promotion")
        recorded_at = _parse_time(evidence.recorded_at, "recorded_at")
        if previous_time is not None and recorded_at <= previous_time:
            raise EvidenceChainError("recorded_at", "must increase with sequence")

        unique_values = (
            (evidence.evidence_id, evidence_ids, "evidence_id"),
            (evidence.evidence_digest, evidence_digests, "evidence_digest"),
            (
                evidence.observation_set_digest,
                observation_digests,
                "observation_set_digest",
            ),
            (
                evidence.delivery_decision_digest,
                delivery_digests,
                "delivery_decision_digest",
            ),
        )
        for value, seen, field in unique_values:
            if value in seen:
                raise EvidenceChainError(field, "replay is forbidden")
            seen.add(value)
        if evidence.recovery_decision_digest is not None:
            if evidence.recovery_decision_digest in recovery_digests:
                raise EvidenceChainError(
                    "recovery_decision_digest", "replay is forbidden"
                )
            recovery_digests.add(evidence.recovery_decision_digest)

        state = _transition_state(promotion, state, evidence)
        terminal = _is_terminal(evidence)
        previous_digest = evidence.evidence_digest
        previous_time = recorded_at


class DryRunController:
    """Evaluate and append evidence while applying only in-memory effects."""

    __slots__ = ("__adapter", "__evidence", "__lock", "__promotion")

    def __init__(
        self,
        promotion: DeliveryPromotionV1,
        adapter: FakeEnvironmentAdapter,
        *,
        prior_evidence: Sequence[DeliveryEvidenceV1] = (),
    ) -> None:
        if not isinstance(promotion, DeliveryPromotionV1):
            raise EvidenceChainError("promotion", "must be DeliveryPromotionV1")
        reviewed_adapter = _require_reviewed_adapter_surface(adapter)
        chain = _normalize_prior_evidence(prior_evidence)
        _validate_chain(promotion, chain)
        object.__setattr__(self, "_DryRunController__promotion", promotion)
        object.__setattr__(self, "_DryRunController__adapter", reviewed_adapter)
        object.__setattr__(self, "_DryRunController__evidence", chain)
        object.__setattr__(self, "_DryRunController__lock", Lock())

    def __setattr__(self, name: str, value: object) -> None:
        raise AttributeError("DryRunController instances are immutable")

    @property
    def evidence(self) -> tuple[DeliveryEvidenceV1, ...]:
        with self.__lock:
            return self.__evidence

    def __current_state(self) -> tuple[str, str, int]:
        if not self.__evidence:
            return _initial_state(self.__promotion)
        last = self.__evidence[-1]
        if _is_terminal(last):
            raise EvidenceChainError("evidence", "terminal state cannot accept another step")
        return last.artifact_digest, last.environment, last.exposure_basis_points

    def step(
        self,
        observation_set: EnvironmentObservationV1
        | Sequence[EnvironmentObservationV1],
        *,
        evaluation_time: str,
        recorded_at: str,
    ) -> DeliveryEvidenceV1:
        with self.__lock:
            return self.__step_locked(
                observation_set,
                evaluation_time=evaluation_time,
                recorded_at=recorded_at,
            )

    def __step_locked(
        self,
        observation_set: EnvironmentObservationV1
        | Sequence[EnvironmentObservationV1],
        *,
        evaluation_time: str,
        recorded_at: str,
    ) -> DeliveryEvidenceV1:
        adapter = _require_reviewed_adapter_surface(self.__adapter)
        if len(self.__evidence) >= 128:
            raise EvidenceChainError("evidence", "cannot exceed 128 records")
        observations = _normalize_observations(observation_set)
        set_digest = _observation_set_digest(observations)
        if any(
            item.observation_set_digest == set_digest for item in self.__evidence
        ):
            raise EvidenceChainError("observation_set_digest", "replay is forbidden")

        artifact_digest, environment, exposure = self.__current_state()
        if artifact_digest != self.__promotion.artifact.artifact_digest:
            raise EvidenceChainError(
                "artifact_digest", "only the exact current artifact can continue"
            )
        evaluated_at = _parse_time(evaluation_time, "evaluation_time")
        recorded = _parse_time(recorded_at, "recorded_at")
        if recorded < evaluated_at:
            raise EvidenceChainError("recorded_at", "cannot precede evaluation_time")
        _require_recording_authority(
            self.__promotion,
            recorded,
            include_previous_artifact=False,
        )
        if self.__evidence:
            prior_recorded = _parse_time(
                self.__evidence[-1].recorded_at, "recorded_at"
            )
            if evaluated_at < prior_recorded:
                raise EvidenceChainError(
                    "evaluation_time", "cannot precede prior recorded_at"
                )
            if recorded <= prior_recorded:
                raise EvidenceChainError("recorded_at", "must increase with sequence")

        decision = evaluate_delivery(
            self.__promotion,
            observations,
            evaluation_time,
            environment=environment,
            exposure_basis_points=exposure,
        )
        recovery = None
        result_artifact = artifact_digest
        result_environment = environment
        result_exposure = exposure
        effect = "none"

        if decision.outcome == "advance":
            if decision.next_environment is None or decision.next_exposure_basis_points is None:
                raise EvidenceChainError("decision", "advance lacks an exact next state")
            result_environment = decision.next_environment
            result_exposure = decision.next_exposure_basis_points
            effect = (
                "entered_stage"
                if result_environment != environment
                else "changed_exposure"
            )
        elif decision.outcome == "needs_human":
            effect = "needs_human"
        elif decision.outcome == "deny":
            try:
                recovery = choose_recovery(
                    self.__promotion,
                    decision,
                    recorded_at,
                )
            except RecoverySelectionError:
                recovery = None
            if recovery is not None:
                if recovery.action == "halt":
                    effect = "halted"
                elif recovery.action == "decrease_exposure":
                    effect = "changed_exposure"
                    if recovery.target_exposure_basis_points is None:
                        raise EvidenceChainError("recovery", "decrease lacks a target")
                    result_exposure = recovery.target_exposure_basis_points
                elif recovery.action == "restore_previous":
                    effect = "restored"
                    result_artifact = (
                        self.__promotion.previous_signed_artifact.artifact_digest
                    )
                    _require_recording_authority(
                        self.__promotion,
                        recorded,
                        include_previous_artifact=True,
                    )
        reasons = recovery.reason_codes if recovery is not None else decision.reason_codes
        sequence = len(self.__evidence) + 1
        previous_digest = (
            self.__evidence[-1].evidence_digest if self.__evidence else None
        )
        identity = {
            "sequence": sequence,
            "promotion_digest": self.__promotion.promotion_digest,
            "previous_evidence_digest": previous_digest,
            "delivery_decision_digest": decision.decision_digest,
            "recovery_decision_digest": (
                recovery.recovery_digest if recovery is not None else None
            ),
            "result_artifact_digest": result_artifact,
            "result_environment": result_environment,
            "result_exposure_basis_points": result_exposure,
            "recorded_at": recorded_at,
        }
        values = {
            "schema_version": 1,
            "evidence_id": f"evidence/{canonical_digest(identity)[:32]}",
            "sequence": sequence,
            "promotion_digest": self.__promotion.promotion_digest,
            "previous_evidence_digest": previous_digest,
            "artifact_digest": result_artifact,
            "environment": result_environment,
            "exposure_basis_points": result_exposure,
            "observation_set_digest": decision.observation_set_digest,
            "delivery_decision_digest": decision.decision_digest,
            "recovery_decision_digest": (
                recovery.recovery_digest if recovery is not None else None
            ),
            "dry_run_effect": effect,
            "recorded_at": recorded_at,
            "reason_codes": reasons,
        }
        values["evidence_digest"] = canonical_digest(values)
        evidence = DeliveryEvidenceV1(**values)
        candidate_chain = self.__evidence + (evidence,)
        _validate_chain(self.__promotion, candidate_chain)

        if effect in _REVIEWED_ADAPTER_SUPPORTED_EFFECTS:
            _REVIEWED_ADAPTER_APPLY(
                adapter,
                effect=effect,
                promotion_digest=self.__promotion.promotion_digest,
                artifact_digest=result_artifact,
                environment=result_environment,
                exposure_basis_points=result_exposure,
            )
        object.__setattr__(
            self,
            "_DryRunController__evidence",
            candidate_chain,
        )
        return evidence
