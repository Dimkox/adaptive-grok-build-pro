from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
import re
import threading
from typing import Protocol, runtime_checkable

from .landing_contracts import (
    MEDIA_TYPES,
    LandingContractError,
    LandingInputV1,
    LandingProviderEvidenceV1,
    SiteArtifactV1,
    StaticLandingSpecV1,
    landing_digest,
)
from .landing_intake import PrivateLandingBlobStore
from .landing_provider import (
    LandingNormalizationRequest,
    LandingProvider,
    LandingProviderError,
)
from .landing_renderer import TARGET_BASE_SHA, TARGET_BASE_TREE, TARGET_REPOSITORY_ID
from .models import Actor


LANDING_STATES = frozenset(
    {
        "accepted",
        "normalizing",
        "generating",
        "evaluating",
        "artifact_ready",
        "provider_unavailable",
        "rejected",
        "cancelled",
        "needs_human",
    }
)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class LandingServiceError(RuntimeError):
    def __init__(self, code: str, status_code: int, detail: str) -> None:
        super().__init__(code)
        self.code = code
        self.status_code = status_code
        self.detail = detail


class LandingArtifactBuilder(Protocol):
    def build(
        self,
        source: LandingInputV1,
        spec: StaticLandingSpecV1,
        evidence: LandingProviderEvidenceV1,
    ) -> SiteArtifactV1: ...


@dataclass(frozen=True)
class LandingJobRecord:
    source: LandingInputV1
    state: str
    artifact: SiteArtifactV1 | None
    provider_evidence_digest: str | None
    reason_code: str | None = None
    revision: int = 0

    def job_view(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "job_id": self.source.job_id,
            "state": self.state,
            "input_digest": self.source.input_digest,
        }

    def result_view(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "job_id": self.source.job_id,
            "state": self.state,
            "artifact_digest": (
                self.artifact.artifact_digest
                if self.state == "artifact_ready" and self.artifact is not None
                else None
            ),
            "live_url": None,
        }


@dataclass(frozen=True)
class LandingSubmitResult:
    job: LandingJobRecord
    created: bool


@runtime_checkable
class LandingJobStore(Protocol):
    def get(
        self, tenant_id: str, repository_id: str, job_id: str
    ) -> LandingJobRecord: ...

    def find(
        self, tenant_id: str, repository_id: str, job_id: str
    ) -> LandingJobRecord | None: ...

    def create_or_replay(
        self,
        record: LandingJobRecord,
        *,
        command_key: str,
        request_digest: str,
    ) -> tuple[LandingJobRecord, bool]: ...

    def put(self, record: LandingJobRecord) -> LandingJobRecord: ...

    def cancel_or_replay(
        self,
        record: LandingJobRecord,
        *,
        command_key: str,
        request_digest: str,
    ) -> LandingJobRecord: ...


class InMemoryLandingJobStore:
    """Process-local landing projection, deliberately separate from M4 task state."""

    def __init__(self) -> None:
        self._records: dict[tuple[str, str, str], LandingJobRecord] = {}
        self._commands: dict[
            tuple[str, str, str, str, str], tuple[str, str]
        ] = {}
        self._lock = threading.RLock()

    def get(self, tenant_id: str, repository_id: str, job_id: str) -> LandingJobRecord:
        with self._lock:
            try:
                return self._records[(tenant_id, repository_id, job_id)]
            except KeyError as exc:
                raise LandingServiceError("not_found", 404, "landing job not found") from exc

    def find(
        self, tenant_id: str, repository_id: str, job_id: str
    ) -> LandingJobRecord | None:
        with self._lock:
            return self._records.get((tenant_id, repository_id, job_id))

    def create_or_replay(
        self,
        record: LandingJobRecord,
        *,
        command_key: str,
        request_digest: str,
    ) -> tuple[LandingJobRecord, bool]:
        self._validate_command(command_key, request_digest)
        identity = (
            record.source.tenant_id,
            record.source.repository_id,
            record.source.job_id,
        )
        command = (*identity, "submit", command_key)
        with self._lock:
            prior = self._commands.get(command)
            if prior is not None:
                if prior != (request_digest, record.source.input_digest):
                    raise LandingServiceError(
                        "idempotency_conflict", 409, "landing idempotency conflict"
                    )
                return self._records[identity], False
            existing = self._records.get(identity)
            if existing is not None and existing.source != record.source:
                raise LandingServiceError(
                    "idempotency_conflict", 409, "landing idempotency conflict"
                )
            created = existing is None
            if created:
                self._records[identity] = record
            self._commands[command] = (request_digest, record.source.input_digest)
            return self._records[identity], created

    def put(self, record: LandingJobRecord) -> LandingJobRecord:
        if record.state not in LANDING_STATES:
            raise LandingServiceError("state", 500, "landing state invalid")
        key = (record.source.tenant_id, record.source.repository_id, record.source.job_id)
        with self._lock:
            existing = self._records.get(key)
            if existing is None:
                stored = record
            else:
                if existing.source != record.source or existing.revision != record.revision:
                    raise LandingServiceError("stale_job", 409, "landing job is stale")
                _validate_transition(existing.state, record.state)
                stored = replace(record, revision=record.revision + 1)
            self._records[key] = stored
            return stored

    def cancel_or_replay(
        self,
        record: LandingJobRecord,
        *,
        command_key: str,
        request_digest: str,
    ) -> LandingJobRecord:
        self._validate_command(command_key, request_digest)
        identity = (
            record.source.tenant_id,
            record.source.repository_id,
            record.source.job_id,
        )
        command = (*identity, "cancel", command_key)
        with self._lock:
            current = self._records.get(identity)
            if current is None:
                raise LandingServiceError("not_found", 404, "landing job not found")
            prior = self._commands.get(command)
            if prior is not None:
                if prior != (request_digest, record.source.input_digest):
                    raise LandingServiceError(
                        "idempotency_conflict", 409, "landing idempotency conflict"
                    )
                return current
            cancelled = replace(
                current,
                state="cancelled",
                artifact=None,
                reason_code="cancelled",
            )
            cancelled = self.put(cancelled)
            self._commands[command] = (request_digest, record.source.input_digest)
            return cancelled

    @staticmethod
    def _validate_command(command_key: str, request_digest: str) -> None:
        if (
            not isinstance(command_key, str)
            or not _IDENTIFIER.fullmatch(command_key)
            or not isinstance(request_digest, str)
            or not _HEX64.fullmatch(request_digest)
        ):
            raise LandingServiceError("idempotency", 422, "landing idempotency invalid")


class LandingApplicationService:
    def __init__(
        self,
        store: LandingJobStore,
        blobs: PrivateLandingBlobStore,
        provider: LandingProvider,
        *,
        profile_digest: str,
        artifact_builder: LandingArtifactBuilder | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if not isinstance(store, LandingJobStore):
            raise LandingServiceError("store", 500, "landing store unavailable")
        if not isinstance(blobs, PrivateLandingBlobStore):
            raise LandingServiceError("blob_store", 500, "landing intake unavailable")
        if not isinstance(profile_digest, str) or not _HEX64.fullmatch(profile_digest):
            raise LandingServiceError("profile", 500, "landing profile unavailable")
        self._store = store
        self._blobs = blobs
        self._provider = provider
        self._profile_digest = profile_digest
        self._artifact_builder = artifact_builder
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = threading.RLock()

    def submit(
        self,
        *,
        job_id: str,
        repository_id: str,
        exact_base_sha: str,
        exact_base_tree: str,
        media_type: str,
        chunks: Iterable[bytes],
        actor: Actor,
    ) -> LandingSubmitResult:
        self._authorize(actor, repository_id)
        if exact_base_sha != TARGET_BASE_SHA or exact_base_tree != TARGET_BASE_TREE:
            raise LandingServiceError("source_identity", 409, "landing source identity mismatch")
        media_kind = _media_kind(media_type)
        with self._lock:
            existing = self._store.find(actor.actor_id, repository_id, job_id)
            received_at = existing.source.received_at if existing else self._now()
            expires_at = existing.source.expires_at if existing else received_at + timedelta(days=1)
            try:
                source = self._blobs.accept(
                    job_id=job_id,
                    tenant_id=actor.actor_id,
                    repository_id=repository_id,
                    exact_base_sha=exact_base_sha,
                    exact_base_tree=exact_base_tree,
                    site_id="therealaidarkfactory.online",
                    media_kind=media_kind,
                    media_type=media_type,
                    chunks=chunks,
                    received_at=received_at,
                    expires_at=expires_at,
                )
            except LandingContractError as exc:
                raise _service_error(exc) from exc
            accepted = LandingJobRecord(source, "accepted", None, None)
            try:
                accepted, created = self._store.create_or_replay(
                    accepted,
                    command_key=job_id,
                    request_digest=source.input_digest,
                )
            except Exception:
                self._purge(source, "rejected")
                raise
            if not created:
                self._purge(source, "normalized")
                return LandingSubmitResult(accepted, False)
            try:
                final = self._process(accepted)
            except Exception:
                current = self._store.get(
                    source.tenant_id, source.repository_id, source.job_id
                )
                final = replace(
                    current, state="needs_human", reason_code="internal_failure"
                )
            final = self._store.put(final)
            self._purge(source, "normalized")
            return LandingSubmitResult(final, True)

    def get(self, job_id: str, *, repository_id: str, actor: Actor) -> LandingJobRecord:
        self._authorize(actor, repository_id)
        return self._store.get(actor.actor_id, repository_id, job_id)

    def cancel(
        self,
        job_id: str,
        *,
        repository_id: str,
        idempotency_key: str,
        actor: Actor,
    ) -> LandingJobRecord:
        self._authorize(actor, repository_id)
        with self._lock:
            current = self._store.get(actor.actor_id, repository_id, job_id)
            request_digest = landing_digest(
                "cancel-command",
                {
                    "tenant_id": actor.actor_id,
                    "repository_id": repository_id,
                    "job_id": job_id,
                },
            )
            cancelled = self._store.cancel_or_replay(
                current,
                command_key=idempotency_key,
                request_digest=request_digest,
            )
            self._purge(cancelled.source, "cancelled")
            return cancelled

    def result(
        self, job_id: str, *, repository_id: str, actor: Actor
    ) -> LandingJobRecord:
        current = self.get(job_id, repository_id=repository_id, actor=actor)
        if current.state in {"accepted", "normalizing", "generating", "evaluating"}:
            raise LandingServiceError("not_terminal", 409, "landing result is not terminal")
        return current

    def _process(self, accepted: LandingJobRecord) -> LandingJobRecord:
        source = accepted.source
        processing = self._store.put(replace(accepted, state="normalizing"))
        try:
            outcome = self._provider.normalize(
                LandingNormalizationRequest(source, self._profile_digest),
                lambda: self._blobs.read(
                    source,
                    tenant_id=source.tenant_id,
                    repository_id=source.repository_id,
                    job_id=source.job_id,
                ),
            )
            if (
                outcome.evidence.input_digest != source.input_digest
                or outcome.evidence.profile_digest != self._profile_digest
            ):
                raise LandingServiceError(
                    "provider_binding", 500, "landing provider evidence mismatch"
                )
            if outcome.state != "normalized" or outcome.spec is None:
                return replace(
                    processing,
                    state=outcome.state,
                    provider_evidence_digest=outcome.evidence.provider_evidence_digest,
                    reason_code=outcome.reason_code,
                )
            if (
                outcome.spec.input_digest != source.input_digest
                or self._artifact_builder is None
            ):
                return replace(
                    processing,
                    state="needs_human",
                    provider_evidence_digest=outcome.evidence.provider_evidence_digest,
                    reason_code="artifact_builder_unavailable",
                )
            processing = self._store.put(
                replace(
                    processing,
                    state="generating",
                    provider_evidence_digest=outcome.evidence.provider_evidence_digest,
                )
            )
            artifact = self._artifact_builder.build(source, outcome.spec, outcome.evidence)
            self._validate_artifact(source, outcome.spec, outcome.evidence, artifact)
            return replace(
                processing,
                state="artifact_ready",
                artifact=artifact,
                provider_evidence_digest=outcome.evidence.provider_evidence_digest,
            )
        except LandingProviderError:
            return replace(
                processing,
                state="provider_unavailable",
                artifact=None,
                provider_evidence_digest=None,
                reason_code="provider_error",
            )

    @staticmethod
    def _validate_artifact(
        source: LandingInputV1,
        spec: StaticLandingSpecV1,
        evidence: LandingProviderEvidenceV1,
        artifact: SiteArtifactV1,
    ) -> None:
        if (
            not isinstance(artifact, SiteArtifactV1)
            or artifact.source_sha != source.exact_base_sha
            or artifact.source_tree != source.exact_base_tree
            or artifact.input_digest != source.input_digest
            or artifact.spec_digest != spec.spec_digest
            or artifact.profile_digest != evidence.profile_digest
            or artifact.disposition != "artifact_ready"
        ):
            raise LandingServiceError("artifact_binding", 500, "landing artifact mismatch")

    @staticmethod
    def _authorize(actor: Actor, repository_id: str) -> None:
        if not isinstance(actor, Actor):
            raise LandingServiceError("authorization", 403, "landing authorization denied")
        if repository_id != TARGET_REPOSITORY_ID:
            raise LandingServiceError("repository", 403, "landing repository denied")
        if "*" not in actor.repositories and repository_id not in actor.repositories:
            raise LandingServiceError("authorization", 403, "landing authorization denied")

    def _now(self) -> datetime:
        value = self._clock()
        if not isinstance(value, datetime) or value.tzinfo is None:
            raise LandingServiceError("clock", 500, "landing clock unavailable")
        return value.astimezone(timezone.utc)

    def _purge(self, source: LandingInputV1, reason: str) -> None:
        try:
            self._blobs.purge(source, reason=reason)
        except LandingContractError as exc:
            raise LandingServiceError("purge_failed", 500, "landing purge failed") from exc


def _media_kind(media_type: str) -> str:
    for kind, allowed in MEDIA_TYPES.items():
        if media_type in allowed:
            return kind
    raise LandingServiceError("media_type", 415, "landing media type unsupported")


def _service_error(error: LandingContractError) -> LandingServiceError:
    if error.code == "input_too_large":
        return LandingServiceError(error.code, 413, "landing input too large")
    if error.code == "media_type":
        return LandingServiceError(error.code, 415, "landing media type unsupported")
    if error.code in {"idempotency_conflict", "quarantine_collision"}:
        return LandingServiceError(error.code, 409, "landing input conflicts")
    return LandingServiceError(error.code, 422, "landing input rejected")


_IDENTIFIER = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:/@+-]{0,127}$")
_TERMINAL_STATES = frozenset(
    {"artifact_ready", "provider_unavailable", "rejected", "needs_human"}
)
_TRANSITIONS = {
    "accepted": frozenset(
        {"normalizing", "provider_unavailable", "rejected", "needs_human", "cancelled"}
    ),
    "normalizing": frozenset(
        {"generating", "provider_unavailable", "rejected", "needs_human", "cancelled"}
    ),
    "generating": frozenset(
        {"evaluating", "artifact_ready", "needs_human", "cancelled"}
    ),
    "evaluating": frozenset({"artifact_ready", "needs_human", "cancelled"}),
    "artifact_ready": frozenset({"cancelled"}),
    "provider_unavailable": frozenset({"cancelled"}),
    "rejected": frozenset({"cancelled"}),
    "needs_human": frozenset({"cancelled"}),
    "cancelled": frozenset(),
}


def _validate_transition(current: str, target: str) -> None:
    if current == target:
        return
    if target not in _TRANSITIONS.get(current, frozenset()):
        raise LandingServiceError("state_transition", 409, "landing transition invalid")
