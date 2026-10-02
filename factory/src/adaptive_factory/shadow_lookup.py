"""Closed additive M7.1 facts. These values confer no external authenticity or authority."""
from __future__ import annotations

from dataclasses import dataclass, fields
from datetime import datetime, timezone
import hashlib
import unicodedata
import re
from typing import Any, ClassVar

from .contracts import ContractError, HEX40, HEX64, _closed, _hex, _id, _text, canonical_json
from .shadow_contracts import ReadyForPrBundleV1, ShadowOutcomeV1

MAX_BYTES = 1_048_576
MAX_COUNT = 2**63 - 1
KINDS = ("human_outcome", "signed_ci", "github_current", "deployed_epoch")
PROFILE_FIELDS = (
    "schema_version", "repository_id", "task_class", "m7_change_class", "m7_cohort_key_digest",
    "provider_mapping_digest", "agent_digest", "validator_digest", "provider_digest", "model_digest",
    "prompt_digest", "policy_digest", "runner_digest", "holdout_digest", "authority_digest",
    "authority_ceiling", "expires_at",
)


def _fail(reason: str) -> None:
    raise ContractError("m7_lookup_invalid", reason)


def _bounded(data: Any) -> None:
    pending = [(data, 0)]
    count = 0
    while pending:
        value, depth = pending.pop()
        count += 1
        if depth > 16 or count > 50_000:
            _fail("complexity_limit")
        if type(value) is dict:
            if len(value) > 128 or any(type(key) is not str for key in value):
                _fail("object_limit")
            pending.extend((item, depth + 1) for pair in value.items() for item in pair)
        elif type(value) is list:
            if len(value) > 1024:
                _fail("item_limit")
            pending.extend((item, depth + 1) for item in value)
        elif type(value) is str:
            if (len(value.encode("utf-8", errors="surrogatepass")) > 4096
                    or unicodedata.normalize("NFC", value) != value
                    or any(ord(c) < 32 or 127 <= ord(c) <= 159 or 0xD800 <= ord(c) <= 0xDFFF for c in value)):
                _fail("string_limit")
        elif type(value) is int and not -MAX_COUNT <= value <= MAX_COUNT:
            _fail("integer_limit")
        elif value is not None and type(value) not in (bool, int):
            _fail("json_type")
    try:
        if len(canonical_json(data)) > MAX_BYTES:
            _fail("byte_limit")
    except (UnicodeError, RecursionError, TypeError) as exc:
        raise ContractError("m7_lookup_invalid", "encoding") from exc


def canonical_m7_bytes(data: Any) -> bytes:
    """Reject noncanonical identity before using the shared UTF8 JSON encoder."""
    _bounded(data)
    return canonical_json(data)


def m7_digest(domain: str, data: Any) -> str:
    return hashlib.sha256(domain.encode("ascii") + b"\0" + canonical_m7_bytes(data)).hexdigest()


def _integer(value: Any, minimum: int = 1) -> int:
    if type(value) is not int or not minimum <= value <= MAX_COUNT:
        _fail("integer")
    return value


def _boolean(value: Any) -> bool:
    if type(value) is not bool:
        _fail("boolean")
    return value


def _identifier(value: Any) -> str:
    try:
        return _id(value, "m7_lookup")
    except (UnicodeError, TypeError) as exc:
        raise ContractError("m7_lookup_invalid", "identifier") from exc


def _check_name(value):
    return _text(value, "check_name", 256)


def _source_ref(value):
    value = _identifier(value)
    if "://" in value or value.startswith("file:"):
        _fail("source_local_reference_required")
    return value


def _time(value: Any) -> str:
    if type(value) is not str or re.fullmatch(
        r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-](?:[01]\d|2[0-3]):[0-5]\d)", value
    ) is None:
        _fail("timestamp")
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    except (ValueError, OverflowError) as exc:
        raise ContractError("m7_lookup_invalid", "timestamp") from exc


def _instant(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _enum(*values):
    def validate(value):
        if type(value) is not str or value not in values:
            _fail("enum")
        return value
    return validate


def _nullable(validator):
    return lambda value: None if value is None else validator(value)


def _digest(value):
    return _hex(value, "m7_lookup", HEX64)


def _sha(value):
    return _hex(value, "m7_lookup", HEX40)


def _nested(cls):
    return lambda value: cls.from_dict(value.to_dict() if type(value) is cls else value)


def _strings(value):
    if not isinstance(value, (list, tuple)) or len(value) > 64:
        _fail("list_limit")
    values = tuple(_identifier(item) for item in value)
    if values != tuple(sorted(set(values))):
        _fail("references_not_sorted_unique")
    return values


def _wire(value):
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if isinstance(value, tuple):
        return [_wire(item) for item in value]
    return value


class _Value:
    DOMAIN: ClassVar[str]
    VALIDATORS: ClassVar[dict]

    def __post_init__(self):
        for name, validator in self.VALIDATORS.items():
            object.__setattr__(self, name, validator(getattr(self, name)))
        self._validate()
        _bounded(self.to_dict())

    def _validate(self):
        pass

    @classmethod
    def from_dict(cls, data):
        if type(data) is not dict:
            _fail("object")
        _bounded(data)
        _closed(data, {field.name for field in fields(cls)})
        return cls(**data)

    def to_dict(self):
        return {field.name: _wire(getattr(self, field.name)) for field in fields(self)}

    @property
    def digest(self):
        return m7_digest(self.DOMAIN, self.to_dict())


def _version(value):
    if _integer(value) != 1:
        _fail("version")
    return value


@dataclass(frozen=True)
class M7ProfileMetadataV1(_Value):
    schema_version: int | None = None
    repository_id: str | None = None
    task_class: str | None = None
    m7_change_class: str | None = None
    m7_cohort_key_digest: str | None = None
    provider_mapping_digest: str | None = None
    agent_digest: str | None = None
    validator_digest: str | None = None
    provider_digest: str | None = None
    model_digest: str | None = None
    prompt_digest: str | None = None
    policy_digest: str | None = None
    runner_digest: str | None = None
    holdout_digest: str | None = None
    authority_digest: str | None = None
    authority_ceiling: str | None = None
    expires_at: str | None = None

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-profile-metadata/v1"
    VALIDATORS: ClassVar[dict] = {
        field: _nullable(_digest if field.endswith("_digest") else
                         _integer if field == "schema_version" else _time if field == "expires_at" else _identifier)
        for field in PROFILE_FIELDS
    }

    @classmethod
    def from_dict(cls, data):
        if type(data) is not dict or set(data) - set(PROFILE_FIELDS):
            _fail("profile_fields")
        return super().from_dict({field: data.get(field) for field in PROFILE_FIELDS})


@dataclass(frozen=True)
class M7LookupRequestV1(_Value):
    schema_version: int
    repository_id: str
    task_id: str
    run_id: str
    generation: int
    bundle_digest: str
    profile_digest: str | None
    pr_number: int
    base_sha: str
    head_sha: str
    app_id: int
    check_name: str
    policy_digest: str
    holdout_digest: str

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-lookup-request/v1"
    VALIDATORS: ClassVar[dict] = {
        "schema_version": _version, **{key: _identifier for key in ("repository_id", "task_id", "run_id")},
        "check_name": _check_name,
        **{key: _integer for key in ("generation", "pr_number", "app_id")},
        **{key: _digest for key in ("bundle_digest", "policy_digest", "holdout_digest")},
        "profile_digest": _nullable(_digest), "base_sha": _sha, "head_sha": _sha,
    }


@dataclass(frozen=True)
class M7BundleRegistrationV1(_Value):
    schema_version: int
    generation: int
    bundle: ReadyForPrBundleV1
    profile: M7ProfileMetadataV1 | None

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-bundle-registration/v1"
    VALIDATORS: ClassVar[dict] = {
        "schema_version": _version, "generation": _integer,
        "bundle": _nested(ReadyForPrBundleV1), "profile": _nullable(_nested(M7ProfileMetadataV1)),
    }

    def _validate(self):
        if self.profile and self.profile.repository_id not in (None, self.bundle.evidence.m5.repository_id):
            _fail("profile_repository")


@dataclass(frozen=True)
class M7SourceProvenanceV1(_Value):
    schema_version: int
    source_id: str
    source_kind: str
    adapter_version: str
    source_event_id: str
    source_revision: int
    predecessor_digest: str | None
    source_issued_at: str
    observed_at: str
    valid_until: str
    trust_config_digest: str
    evidence_ref: str
    verifier_id: str

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-source-provenance/v1"
    VALIDATORS: ClassVar[dict] = {
        "schema_version": _version, "source_kind": _enum(*KINDS), "source_revision": _integer,
        **{key: _identifier for key in ("source_id", "adapter_version", "source_event_id", "evidence_ref", "verifier_id")},
        **{key: _time for key in ("source_issued_at", "observed_at", "valid_until")},
        "predecessor_digest": _nullable(_digest), "trust_config_digest": _digest,
        "evidence_ref": _source_ref,
    }

    def _validate(self):
        if not (_instant(self.source_issued_at) <= _instant(self.observed_at) < _instant(self.valid_until)):
            _fail("provenance_time_order")
        if (self.source_revision == 1) != (self.predecessor_digest is None):
            _fail("provenance_predecessor")


@dataclass(frozen=True)
class M7MeasurementsV1(_Value):
    schema_version: int
    cost_usd_micros: int | None
    latency_ms: int | None
    repair_count: int | None
    rollback_count: int | None
    regression_count: int | None
    intervention_count: int | None
    intervention_coverage: str
    intervention_source_refs: tuple[str, ...]
    session_started_at: str | None
    session_ended_at: str | None

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-measurements/v1"
    COUNT_FIELDS: ClassVar[tuple] = ("cost_usd_micros", "latency_ms", "repair_count", "rollback_count", "regression_count", "intervention_count")
    VALIDATORS: ClassVar[dict] = {
        "schema_version": _version, **{key: _nullable(lambda value: _integer(value, 0)) for key in COUNT_FIELDS},
        "intervention_coverage": _enum("unknown", "partial", "complete"),
        "intervention_source_refs": _strings,
        "session_started_at": _nullable(_time), "session_ended_at": _nullable(_time),
    }

    def _validate(self):
        measured = self.intervention_coverage != "unknown"
        if measured != (self.intervention_count is not None) or (measured and not self.intervention_source_refs):
            _fail("intervention_coverage")
        start, end = self.session_started_at, self.session_ended_at
        if self.intervention_coverage == "complete" and (start is None or end is None):
            _fail("session_missing")
        if start is not None and end is not None and _instant(start) > _instant(end):
            _fail("session_order")


@dataclass(frozen=True)
class M7OutcomeObservationV1(_Value):
    schema_version: int
    repository_id: str
    bundle_digest: str
    result_head_sha: str
    provenance: M7SourceProvenanceV1
    decision: str
    outcome: ShadowOutcomeV1 | None
    profile: M7ProfileMetadataV1 | None
    measurements: M7MeasurementsV1

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-outcome-observation/v1"
    VALIDATORS: ClassVar[dict] = {
        "schema_version": _version, "repository_id": _identifier, "bundle_digest": _digest, "result_head_sha": _sha,
        "provenance": _nested(M7SourceProvenanceV1), "decision": _enum("accepted", "rejected", "withdrawn"),
        "outcome": _nullable(_nested(ShadowOutcomeV1)), "profile": _nullable(_nested(M7ProfileMetadataV1)),
        "measurements": _nested(M7MeasurementsV1),
    }

    def _validate(self):
        if self.provenance.source_kind != "human_outcome":
            _fail("source_kind")
        if self.profile and self.profile.repository_id not in (None, self.repository_id):
            _fail("profile_repository")
        if self.outcome and (self.outcome.bundle_digest != self.bundle_digest or
                             (self.outcome.human_decision == "merged_accepted") != (self.decision == "accepted")):
            _fail("outcome_binding")
        if self.outcome and self.profile and self.profile.m7_cohort_key_digest not in (None, self.outcome.cohort_key_digest):
            _fail("outcome_profile")
        for boundary in (self.measurements.session_started_at, self.measurements.session_ended_at):
            if boundary and _instant(boundary) > _instant(self.provenance.observed_at):
                _fail("future_session")


@dataclass(frozen=True)
class M7CheckObservationV1(_Value):
    schema_version: int
    repository_id: str
    pr_number: int
    base_sha: str
    head_sha: str
    policy_digest: str
    holdout_digest: str
    external_job_id: str
    attestation_digest: str
    signer_key_id: str
    result: str
    provenance: M7SourceProvenanceV1

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-check-observation/v1"
    VALIDATORS: ClassVar[dict] = {
        "schema_version": _version, "pr_number": _integer,
        **{key: _identifier for key in ("repository_id", "external_job_id", "signer_key_id")},
        **{key: _digest for key in ("policy_digest", "holdout_digest", "attestation_digest")},
        "base_sha": _sha, "head_sha": _sha, "result": _enum("passed", "failed", "revoked"),
        "provenance": _nested(M7SourceProvenanceV1),
    }

    def _validate(self):
        if self.provenance.source_kind != "signed_ci":
            _fail("source_kind")


@dataclass(frozen=True)
class M7GitHubContextV1(_Value):
    schema_version: int
    repository_id: str
    pr_number: int
    base_sha: str
    head_sha: str
    app_id: int
    check_name: str
    external_job_id: str
    check_id: int
    check_state: str
    check_conclusion: str
    revoked: bool
    provenance: M7SourceProvenanceV1

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-github-context/v1"
    VALIDATORS: ClassVar[dict] = {
        "schema_version": _version, **{key: _integer for key in ("pr_number", "app_id", "check_id")},
        **{key: _identifier for key in ("repository_id", "external_job_id")}, "check_name": _check_name,
        "base_sha": _sha, "head_sha": _sha, "revoked": _boolean,
        "check_state": _enum("queued", "in_progress", "completed"),
        "check_conclusion": _enum("unknown", "success", "failure", "cancelled", "action_required", "timed_out", "neutral", "skipped"),
        "provenance": _nested(M7SourceProvenanceV1),
    }

    def _validate(self):
        if self.provenance.source_kind != "github_current":
            _fail("source_kind")


@dataclass(frozen=True)
class M7EpochContextV1(_Value):
    schema_version: int
    repository_id: str
    policy_digest: str
    holdout_digest: str
    app_id: int
    check_name: str
    revoked: bool
    provenance: M7SourceProvenanceV1

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-epoch-context/v1"
    VALIDATORS: ClassVar[dict] = {
        "schema_version": _version, "repository_id": _identifier, "app_id": _integer,
        "check_name": _check_name, "policy_digest": _digest, "holdout_digest": _digest,
        "revoked": _boolean, "provenance": _nested(M7SourceProvenanceV1),
    }

    def _validate(self):
        if self.provenance.source_kind != "deployed_epoch":
            _fail("source_kind")


@dataclass(frozen=True)
class SourceUnavailable(_Value):
    schema_version: int = 1
    reason: str = "source_unconfigured"

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-source-unavailable/v1"
    VALIDATORS: ClassVar[dict] = {"schema_version": _version, "reason": _identifier}


@dataclass(frozen=True)
class M7LookupResultV1(_Value):
    schema_version: int
    request: M7LookupRequestV1
    observed_at: str | None
    registration: M7BundleRegistrationV1 | None
    outcome: M7OutcomeObservationV1 | None
    check: M7CheckObservationV1 | None
    github: M7GitHubContextV1 | None
    epoch: M7EpochContextV1 | None
    unavailable_reasons: tuple[str, ...]
    source_modes: tuple[str, ...]

    DOMAIN: ClassVar[str] = "adaptive-factory.m7-lookup-result/v1"
    VALIDATORS: ClassVar[dict] = {
        "schema_version": _version, "request": _nested(M7LookupRequestV1), "observed_at": _nullable(_time),
        "registration": _nullable(_nested(M7BundleRegistrationV1)), "outcome": _nullable(_nested(M7OutcomeObservationV1)),
        "check": _nullable(_nested(M7CheckObservationV1)), "github": _nullable(_nested(M7GitHubContextV1)),
        "epoch": _nullable(_nested(M7EpochContextV1)), "unavailable_reasons": _strings, "source_modes": _strings,
    }
    DERIVED: ClassVar[tuple] = ("request_digest", "snapshot_digest", "acceptance", "signed_check", "currentness",
                              "coverage", "status", "m8_qualification", "authority_effect", "lookup_outcome")

    def _validate(self):
        if any(mode not in ("synthetic", "imported", "authenticated") for mode in self.source_modes):
            _fail("source_mode")
        request = self.request
        if self.registration:
            evidence = self.registration.bundle.evidence
            if (self.registration.bundle.digest != request.bundle_digest or self.registration.generation != request.generation or
                evidence.m5.repository_id != request.repository_id or evidence.m4.task_id != request.task_id or
                evidence.m4.run_id != request.run_id or evidence.m5.result_exact_head_sha != request.head_sha):
                _fail("registration_binding")
            if request.profile_digest is not None and (self.registration.profile is None or self.registration.profile.digest != request.profile_digest):
                _fail("registration_profile")
        for observation in (self.outcome, self.check, self.github, self.epoch):
            if observation and observation.repository_id != request.repository_id:
                _fail("observation_repository")
            if observation and self.observed_at is None:
                _fail("observation_time_missing")
        if self.outcome and (self.outcome.bundle_digest != request.bundle_digest or self.outcome.result_head_sha != request.head_sha):
            _fail("outcome_subject")
        if any(item and item.pr_number != request.pr_number for item in (self.check, self.github)):
            _fail("pr_binding")

    def _usable(self, observation):
        if observation is None or self.observed_at is None or not self.source_modes or "imported" in self.source_modes:
            return False
        now = _instant(self.observed_at)
        return _instant(observation.provenance.observed_at) <= now < _instant(observation.provenance.valid_until)

    @property
    def acceptance(self):
        return self.outcome.decision if self._usable(self.outcome) else "unavailable"

    @property
    def signed_check(self):
        if not self._usable(self.check):
            return "unavailable"
        matches = all(getattr(self.check, key) == getattr(self.request, key)
                      for key in ("base_sha", "head_sha", "policy_digest", "holdout_digest"))
        return "valid" if self.check.result == "passed" and matches else "invalid"

    @property
    def currentness(self):
        context_reasons = tuple(reason for reason in self.unavailable_reasons if not reason.startswith("outcome_"))
        if any("conflict" in reason for reason in context_reasons):
            return "conflict"
        if not self._usable(self.github) or not self._usable(self.epoch):
            return "unavailable"
        if context_reasons or not self.registration or self.signed_check != "valid":
            return "stale"
        github_matches = all(getattr(self.github, key) == getattr(self.request, key)
                             for key in ("base_sha", "head_sha", "app_id", "check_name"))
        epoch_matches = all(getattr(self.epoch, key) == getattr(self.request, key)
                            for key in ("policy_digest", "holdout_digest", "app_id", "check_name"))
        return "current" if (github_matches and epoch_matches and not self.github.revoked and not self.epoch.revoked
                             and self.github.check_state == "completed" and self.github.check_conclusion == "success"
                             and self.check.external_job_id == self.github.external_job_id) else "stale"

    @property
    def coverage(self):
        profile = self.outcome.profile if self.outcome else None
        if profile is None and self.registration:
            profile = self.registration.profile
        missing = sorted(field for field in PROFILE_FIELDS if profile is None or getattr(profile, field) is None)
        measured = self.outcome.measurements if self.outcome else None
        missing_metrics = sorted(field for field in M7MeasurementsV1.COUNT_FIELDS if measured is None or getattr(measured, field) is None)
        task_class = profile.task_class if profile else None
        return {
            "producer_bindings": "complete" if self.registration else "unknown",
            "profile": "unknown" if len(missing) == len(PROFILE_FIELDS) else "partial" if missing else "complete",
            "profile_provenance": "not_evaluated", "missing_profile_fields": missing,
            "task_class": "unknown" if task_class is None else "supported" if task_class == "low_risk_text_only" else "unsupported",
            "outcome": "complete" if self.outcome and self.outcome.outcome else "unknown",
            "measurements": "unknown" if len(missing_metrics) == len(M7MeasurementsV1.COUNT_FIELDS) else "partial" if missing_metrics else "complete",
            "missing_measurements": missing_metrics,
            "interventions": measured.intervention_coverage if measured else "unknown",
        }

    @property
    def status(self):
        if self.registration and all(value != "unavailable" for value in (self.acceptance, self.signed_check, self.currentness)):
            return "resolved"
        return "partial" if any((self.registration, self.outcome, self.check, self.github, self.epoch)) else "unavailable"

    @property
    def m8_qualification(self):
        return "not_evaluated"

    @property
    def authority_effect(self):
        return "none"

    @property
    def lookup_outcome(self):
        reasons = self.unavailable_reasons
        if any("conflict" in reason for reason in reasons):
            return "ambiguous"
        if any("corrupt" in reason or "invalid" in reason for reason in reasons):
            return "invalid"
        if any("expired" in reason or "stale" in reason or "subject_mismatch" in reason for reason in reasons):
            return "stale"
        if any(reason.endswith("_missing") for reason in reasons):
            return "not_found"
        if self.currentness == "current":
            return "found"
        if self.currentness == "stale":
            return "stale"
        return "unavailable"

    def to_dict(self):
        raw = super().to_dict()
        snapshot_digest = m7_digest("adaptive-factory.m7-lookup-snapshot/v1", raw)
        return {**raw, "request_digest": self.request.digest, "snapshot_digest": snapshot_digest,
                **{key: getattr(self, key) for key in self.DERIVED[2:]}}

    @classmethod
    def from_dict(cls, data):
        if type(data) is not dict:
            _fail("result_object")
        _bounded(data)
        names = {field.name for field in fields(cls)}
        _closed(data, names | set(cls.DERIVED))
        result = cls(**{name: data[name] for name in names})
        if result.to_dict() != data:
            _fail("result_derived_binding")
        return result


def build_lookup_result(*, request, observed_at=None, registration=None, outcome=None, check=None,
                        github=None, epoch=None, unavailable_reasons=(), source_modes=()):
    return M7LookupResultV1(1, request, observed_at, registration, outcome, check, github, epoch,
                            unavailable_reasons, source_modes)
