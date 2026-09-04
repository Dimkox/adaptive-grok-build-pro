from __future__ import annotations

import hashlib
import json
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from datetime import UTC, datetime
from typing import Any

from .m8_boundary import M8BoundaryError, M8DeliveryHandoffV1

_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9._:/-]{1,128}$", re.ASCII)
_UTC_SECONDS = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$", re.ASCII)

ENVIRONMENT_ORDER = ("preview", "staging", "bounded_canary", "production")
METRIC_FAMILIES = ("health", "error", "latency", "security", "business")
RECOVERY_ACTIONS = ("halt", "decrease_exposure", "restore_previous")
DECISION_OUTCOMES = ("advance", "hold", "deny", "needs_human")
DRY_RUN_EFFECTS = (
    "none",
    "entered_stage",
    "changed_exposure",
    "halted",
    "restored",
    "needs_human",
)
REASON_CODES = frozenset(
    {
        "artifact_mismatch",
        "authority_expired",
        "authority_not_yet_valid",
        "authority_resource_mismatch",
        "authority_scope_mismatch",
        "business_below_minimum",
        "environment_mismatch",
        "environment_set_mismatch",
        "error_above_maximum",
        "exposure_mismatch",
        "health_below_minimum",
        "latency_above_maximum",
        "m8_evidence_expired",
        "m8_evidence_not_current",
        "m8_profile_ineligible",
        "m8_recommendation_ineligible",
        "observation_contradictory",
        "observation_duplicate",
        "observation_incomplete",
        "observation_replay",
        "observation_stale",
        "observation_time_invalid",
        "policy_mismatch",
        "production_requires_human",
        "promotion_expired",
        "promotion_mismatch",
        "recovery_decrease",
        "recovery_halt",
        "recovery_restore_previous",
        "security_critical",
        "thresholds_passed",
    }
)

_MAX_POSITIVE_INTEGER = 2_147_483_647


class ContractError(ValueError):
    def __init__(self, field: str, detail: str = "") -> None:
        message = f"{field}: {detail}" if detail else field
        super().__init__(message)
        self.field = field
        self.detail = detail


def _canonical_value(value: Any) -> Any:
    if type(value) is M8DeliveryHandoffV1:
        return _canonical_value(value.to_dict())
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _canonical_value(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ContractError("canonical_digest", "mapping keys must be strings")
        return {key: _canonical_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_canonical_value(item) for item in value]
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise ContractError("canonical_digest", f"unsupported value type {type(value).__name__}")


def canonical_digest(value: object) -> str:
    try:
        encoded = json.dumps(
            _canonical_value(value),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ContractError("canonical_digest", "value is not canonical JSON") from exc
    return hashlib.sha256(encoded).hexdigest()


def _version(value: object) -> None:
    if type(value) is not int or value != 1:
        raise ContractError("schema_version", "must equal 1")


def _identifier(value: object, field: str) -> None:
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ContractError(field, "must be a bounded ASCII identifier")


def _sha(value: object, field: str) -> None:
    if not isinstance(value, str) or not _HEX40.fullmatch(value):
        raise ContractError(field, "must be lowercase 40-hex")


def _digest(value: object, field: str) -> None:
    if not isinstance(value, str) or not _HEX64.fullmatch(value):
        raise ContractError(field, "must be lowercase 64-hex")


def _optional_digest(value: object, field: str) -> None:
    if value is not None:
        _digest(value, field)


def _timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str) or not _UTC_SECONDS.fullmatch(value):
        raise ContractError(field, "must be UTC RFC3339 whole seconds ending in Z")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError as exc:
        raise ContractError(field, "must be a valid UTC timestamp") from exc


def _integer(value: object, field: str, minimum: int, maximum: int) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ContractError(field, f"must be an integer from {minimum} through {maximum}")


def _environment(value: object, field: str = "environment") -> None:
    if value not in ENVIRONMENT_ORDER:
        raise ContractError(field, "unsupported environment")


def _tuple(value: object, field: str) -> tuple[object, ...]:
    if not isinstance(value, tuple):
        raise ContractError(field, "must be an immutable tuple")
    return value


def _reason_codes(value: object) -> None:
    reasons = _tuple(value, "reason_codes")
    if any(not isinstance(reason, str) or reason not in REASON_CODES for reason in reasons):
        raise ContractError("reason_codes", "contains an unsupported reason")
    if tuple(sorted(set(reasons))) != reasons:
        raise ContractError("reason_codes", "must be sorted and unique")


def _exposure_steps(value: object, field: str, *, allow_full: bool) -> None:
    steps = _tuple(value, field)
    maximum = 10000 if allow_full else 9999
    if (
        not 1 <= len(steps) <= 16
        or any(type(step) is not int or not 1 <= step <= maximum for step in steps)
        or tuple(sorted(set(steps))) != steps
    ):
        detail = "must contain 1-16 strictly increasing exposures"
        if not allow_full:
            detail += " below 10000"
        raise ContractError(field, detail)


def _record_payload(record: object, digest_field: str) -> dict[str, object]:
    return {
        field.name: getattr(record, field.name)
        for field in fields(record)
        if field.name != digest_field
    }


def _bound_digest(record: object, digest_field: str) -> None:
    supplied = getattr(record, digest_field)
    _digest(supplied, digest_field)
    expected = canonical_digest(_record_payload(record, digest_field))
    if supplied != expected:
        raise ContractError(digest_field, "does not bind the canonical record")


@dataclass(frozen=True, slots=True)
class SignedArtifactRefV1:
    schema_version: int
    repository_id: str
    merged_sha: str
    artifact_digest: str
    sbom_digest: str
    provenance_digest: str
    supply_chain_manifest_digest: str
    image_digest: str
    authority_envelope_digest: str
    authority_verifier_id: str
    authority_verified_at: str
    authority_expires_at: str
    authority_scope: str
    authority_resource_digest: str

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.repository_id, "repository_id")
        _sha(self.merged_sha, "merged_sha")
        for field in (
            "artifact_digest",
            "sbom_digest",
            "provenance_digest",
            "supply_chain_manifest_digest",
            "image_digest",
            "authority_envelope_digest",
            "authority_resource_digest",
        ):
            _digest(getattr(self, field), field)
        _identifier(self.authority_verifier_id, "authority_verifier_id")
        verified_at = _timestamp(self.authority_verified_at, "authority_verified_at")
        expires_at = _timestamp(self.authority_expires_at, "authority_expires_at")
        if verified_at >= expires_at:
            raise ContractError("authority_expires_at", "must be after authority_verified_at")
        if self.authority_scope != "signed_artifact_use":
            raise ContractError("authority_scope", "must equal signed_artifact_use")
        resource = {
            field: getattr(self, field)
            for field in (
                "schema_version",
                "repository_id",
                "merged_sha",
                "artifact_digest",
                "sbom_digest",
                "provenance_digest",
                "supply_chain_manifest_digest",
                "image_digest",
            )
        }
        if self.authority_resource_digest != canonical_digest(resource):
            raise ContractError(
                "authority_resource_digest", "does not bind the artifact resource"
            )


@dataclass(frozen=True, slots=True)
class ExposurePlanV1:
    schema_version: int
    plan_id: str
    environment_order: tuple[str, ...]
    preview_basis_points: tuple[int, ...]
    staging_basis_points: tuple[int, ...]
    canary_basis_points: tuple[int, ...]
    max_observation_age_seconds: int
    evaluation_window_seconds: int
    required_metric_families: tuple[str, ...]
    health_min_basis_points: int
    error_max_basis_points: int
    latency_p95_max_ms: int
    security_critical_max: int
    business_min_basis_points: int
    allowed_recovery_actions: tuple[str, ...]
    plan_digest: str

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.plan_id, "plan_id")
        if _tuple(self.environment_order, "environment_order") != ENVIRONMENT_ORDER:
            raise ContractError("environment_order", "must use the exact four-stage order")
        _exposure_steps(self.preview_basis_points, "preview_basis_points", allow_full=True)
        _exposure_steps(self.staging_basis_points, "staging_basis_points", allow_full=True)
        _exposure_steps(self.canary_basis_points, "canary_basis_points", allow_full=False)
        _integer(
            self.max_observation_age_seconds,
            "max_observation_age_seconds",
            1,
            3600,
        )
        _integer(self.evaluation_window_seconds, "evaluation_window_seconds", 1, 3600)
        if _tuple(self.required_metric_families, "required_metric_families") != METRIC_FAMILIES:
            raise ContractError("required_metric_families", "must name the exact five families")
        _integer(self.health_min_basis_points, "health_min_basis_points", 0, 10000)
        _integer(self.error_max_basis_points, "error_max_basis_points", 0, 10000)
        _integer(self.latency_p95_max_ms, "latency_p95_max_ms", 1, _MAX_POSITIVE_INTEGER)
        if type(self.security_critical_max) is not int or self.security_critical_max != 0:
            raise ContractError("security_critical_max", "must equal 0")
        _integer(self.business_min_basis_points, "business_min_basis_points", 0, 10000)
        actions = _tuple(self.allowed_recovery_actions, "allowed_recovery_actions")
        if not actions or any(action not in RECOVERY_ACTIONS for action in actions):
            raise ContractError("allowed_recovery_actions", "contains an unsupported action")
        indexes = tuple(RECOVERY_ACTIONS.index(action) for action in actions)
        if tuple(sorted(set(indexes))) != indexes:
            raise ContractError("allowed_recovery_actions", "must be ordered and unique")
        _bound_digest(self, "plan_digest")


@dataclass(frozen=True, slots=True)
class DeliveryPromotionV1:
    schema_version: int
    promotion_id: str
    repository_id: str
    artifact: SignedArtifactRefV1
    previous_signed_artifact: SignedArtifactRefV1
    m8_evidence: M8DeliveryHandoffV1
    policy_digest: str
    holdout_digest: str
    runner_image_digest: str
    environment_set_digest: str
    exposure_plan: ExposurePlanV1
    requested_at: str
    expires_at: str
    authority_envelope_digest: str
    authority_verifier_id: str
    authority_verified_at: str
    authority_expires_at: str
    authority_scope: str
    authority_resource_digest: str
    promotion_digest: str

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.promotion_id, "promotion_id")
        _identifier(self.repository_id, "repository_id")
        if not isinstance(self.artifact, SignedArtifactRefV1):
            raise ContractError("artifact", "must be SignedArtifactRefV1")
        if not isinstance(self.previous_signed_artifact, SignedArtifactRefV1):
            raise ContractError(
                "previous_signed_artifact", "must be SignedArtifactRefV1"
            )
        if (
            self.artifact.repository_id != self.repository_id
            or self.previous_signed_artifact.repository_id != self.repository_id
        ):
            raise ContractError("repository_id", "must match both signed artifacts")
        if self.artifact.artifact_digest == self.previous_signed_artifact.artifact_digest:
            raise ContractError(
                "previous_signed_artifact", "must identify a different artifact"
            )
        for field in (
            "policy_digest",
            "holdout_digest",
            "runner_image_digest",
            "environment_set_digest",
            "authority_envelope_digest",
            "authority_resource_digest",
            "promotion_digest",
        ):
            _digest(getattr(self, field), field)
        if type(self.m8_evidence) is not M8DeliveryHandoffV1:
            raise ContractError("m8_evidence", "must be M8DeliveryHandoffV1")
        autonomy_tuple = self.m8_evidence.cohort.autonomy_tuple
        bindings = {
            "repository_id": self.repository_id,
            "policy_digest": self.policy_digest,
            "holdout_digest": self.holdout_digest,
            "runner_digest": self.runner_image_digest,
        }
        for name, expected in bindings.items():
            if getattr(autonomy_tuple, name) != expected:
                raise ContractError("m8_evidence", f"{name} does not match promotion")
        if not isinstance(self.exposure_plan, ExposurePlanV1):
            raise ContractError("exposure_plan", "must be ExposurePlanV1")
        requested_at = _timestamp(self.requested_at, "requested_at")
        expires_at = _timestamp(self.expires_at, "expires_at")
        if requested_at >= expires_at:
            raise ContractError("expires_at", "must be after requested_at")
        _identifier(self.authority_verifier_id, "authority_verifier_id")
        authority_verified_at = _timestamp(
            self.authority_verified_at, "authority_verified_at"
        )
        authority_expires_at = _timestamp(
            self.authority_expires_at, "authority_expires_at"
        )
        if authority_verified_at >= authority_expires_at:
            raise ContractError("authority_expires_at", "must follow verification")
        if requested_at < authority_verified_at or expires_at > authority_expires_at:
            raise ContractError(
                "authority_expires_at", "must cover the complete promotion interval"
            )
        if self.authority_scope != "nonproduction_staged_delivery":
            raise ContractError(
                "authority_scope", "must equal nonproduction_staged_delivery"
            )
        resource = {
            field: getattr(self, field)
            for field in (
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
        }
        try:
            expected_resource_digest = canonical_digest(resource)
        except M8BoundaryError as exc:
            raise ContractError("m8_evidence", str(exc)) from exc
        if self.authority_resource_digest != expected_resource_digest:
            raise ContractError(
                "authority_resource_digest", "does not bind promotion resources"
            )
        _bound_digest(self, "promotion_digest")


@dataclass(frozen=True, slots=True)
class EnvironmentObservationV1:
    schema_version: int
    observation_id: str
    promotion_digest: str
    artifact_digest: str
    environment_set_digest: str
    environment: str
    exposure_basis_points: int
    policy_digest: str
    captured_at: str
    window_started_at: str
    window_ended_at: str
    health_basis_points: int
    error_basis_points: int
    latency_p95_ms: int
    security_critical_count: int
    business_basis_points: int
    sample_count: int
    source_snapshot_digest: str
    observation_digest: str

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.observation_id, "observation_id")
        for field in (
            "promotion_digest",
            "artifact_digest",
            "environment_set_digest",
            "policy_digest",
            "source_snapshot_digest",
            "observation_digest",
        ):
            _digest(getattr(self, field), field)
        _environment(self.environment)
        _integer(self.exposure_basis_points, "exposure_basis_points", 0, 10000)
        captured_at = _timestamp(self.captured_at, "captured_at")
        window_started_at = _timestamp(self.window_started_at, "window_started_at")
        window_ended_at = _timestamp(self.window_ended_at, "window_ended_at")
        if window_started_at > window_ended_at:
            raise ContractError("window_started_at", "must not follow window_ended_at")
        if window_ended_at > captured_at:
            raise ContractError("window_ended_at", "must not follow captured_at")
        _integer(self.health_basis_points, "health_basis_points", 0, 10000)
        _integer(self.error_basis_points, "error_basis_points", 0, 10000)
        _integer(self.latency_p95_ms, "latency_p95_ms", 1, _MAX_POSITIVE_INTEGER)
        _integer(
            self.security_critical_count,
            "security_critical_count",
            0,
            _MAX_POSITIVE_INTEGER,
        )
        _integer(self.business_basis_points, "business_basis_points", 0, 10000)
        _integer(self.sample_count, "sample_count", 1, _MAX_POSITIVE_INTEGER)
        _bound_digest(self, "observation_digest")


@dataclass(frozen=True, slots=True)
class DeliveryDecisionV1:
    schema_version: int
    decision_id: str
    promotion_digest: str
    artifact_digest: str
    environment: str
    exposure_basis_points: int
    observation_set_digest: str
    evaluation_time: str
    outcome: str
    reason_codes: tuple[str, ...]
    next_environment: str | None
    next_exposure_basis_points: int | None
    decision_digest: str

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.decision_id, "decision_id")
        for field in (
            "promotion_digest",
            "artifact_digest",
            "observation_set_digest",
            "decision_digest",
        ):
            _digest(getattr(self, field), field)
        _environment(self.environment)
        _integer(self.exposure_basis_points, "exposure_basis_points", 0, 10000)
        _timestamp(self.evaluation_time, "evaluation_time")
        if self.outcome not in DECISION_OUTCOMES:
            raise ContractError("outcome", "unsupported delivery outcome")
        _reason_codes(self.reason_codes)
        if self.outcome == "advance":
            if self.next_environment is None:
                raise ContractError("next_environment", "advance requires a next environment")
            _environment(self.next_environment, "next_environment")
            if self.next_exposure_basis_points is None:
                raise ContractError(
                    "next_exposure_basis_points", "advance requires a next exposure"
                )
            _integer(
                self.next_exposure_basis_points,
                "next_exposure_basis_points",
                0,
                10000,
            )
        elif self.next_environment is not None or self.next_exposure_basis_points is not None:
            raise ContractError(
                "next_environment", "non-advance outcomes cannot name a next state"
            )
        if self.environment == "production" and self.outcome != "needs_human":
            raise ContractError("production", "always requires a human decision")
        _bound_digest(self, "decision_digest")


@dataclass(frozen=True, slots=True)
class RecoveryDecisionV1:
    schema_version: int
    recovery_id: str
    promotion_digest: str
    failed_decision_digest: str
    environment: str
    current_exposure_basis_points: int
    action: str
    target_exposure_basis_points: int | None
    restore_artifact_digest: str | None
    reason_codes: tuple[str, ...]
    decision_time: str
    recovery_digest: str

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.recovery_id, "recovery_id")
        _digest(self.promotion_digest, "promotion_digest")
        _digest(self.failed_decision_digest, "failed_decision_digest")
        _digest(self.recovery_digest, "recovery_digest")
        _environment(self.environment)
        if self.environment == "production":
            raise ContractError("environment", "production recovery is unreachable")
        _integer(
            self.current_exposure_basis_points,
            "current_exposure_basis_points",
            0,
            10000,
        )
        if self.action not in RECOVERY_ACTIONS:
            raise ContractError("action", "unsupported recovery action")
        _reason_codes(self.reason_codes)
        _timestamp(self.decision_time, "decision_time")
        if self.action == "halt":
            if self.target_exposure_basis_points is not None:
                raise ContractError("target_exposure_basis_points", "halt has no target")
            if self.restore_artifact_digest is not None:
                raise ContractError("restore_artifact_digest", "halt has no artifact")
        elif self.action == "decrease_exposure":
            if self.target_exposure_basis_points is None:
                raise ContractError(
                    "target_exposure_basis_points", "decrease requires a target"
                )
            _integer(
                self.target_exposure_basis_points,
                "target_exposure_basis_points",
                0,
                9999,
            )
            if self.target_exposure_basis_points >= self.current_exposure_basis_points:
                raise ContractError(
                    "target_exposure_basis_points", "must be lower than current exposure"
                )
            if self.restore_artifact_digest is not None:
                raise ContractError(
                    "restore_artifact_digest", "decrease cannot name an artifact"
                )
        else:
            if self.target_exposure_basis_points is not None:
                raise ContractError(
                    "target_exposure_basis_points", "restore has no exposure target"
                )
            _digest(self.restore_artifact_digest, "restore_artifact_digest")
        _bound_digest(self, "recovery_digest")


@dataclass(frozen=True, slots=True)
class DeliveryEvidenceV1:
    schema_version: int
    evidence_id: str
    sequence: int
    promotion_digest: str
    previous_evidence_digest: str | None
    artifact_digest: str
    environment: str
    exposure_basis_points: int
    observation_set_digest: str
    delivery_decision_digest: str
    recovery_decision_digest: str | None
    dry_run_effect: str
    recorded_at: str
    reason_codes: tuple[str, ...]
    evidence_digest: str

    def __post_init__(self) -> None:
        _version(self.schema_version)
        _identifier(self.evidence_id, "evidence_id")
        _integer(self.sequence, "sequence", 1, 128)
        for field in (
            "promotion_digest",
            "artifact_digest",
            "observation_set_digest",
            "delivery_decision_digest",
            "evidence_digest",
        ):
            _digest(getattr(self, field), field)
        _optional_digest(self.previous_evidence_digest, "previous_evidence_digest")
        _optional_digest(self.recovery_decision_digest, "recovery_decision_digest")
        if self.sequence == 1 and self.previous_evidence_digest is not None:
            raise ContractError(
                "previous_evidence_digest", "the first record has no predecessor"
            )
        if self.sequence > 1 and self.previous_evidence_digest is None:
            raise ContractError(
                "previous_evidence_digest", "later records require a predecessor"
            )
        _environment(self.environment)
        _integer(self.exposure_basis_points, "exposure_basis_points", 0, 10000)
        if self.dry_run_effect not in DRY_RUN_EFFECTS:
            raise ContractError("dry_run_effect", "unsupported dry-run effect")
        _timestamp(self.recorded_at, "recorded_at")
        _reason_codes(self.reason_codes)
        _bound_digest(self, "evidence_digest")
