from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import MappingProxyType
from typing import Any


class TaskStatus(StrEnum):
    INBOX = "inbox"
    TRIAGED = "triaged"
    WAITING_DESIGN_APPROVAL = "waiting_design_approval"
    QUEUED = "queued"
    LEASED = "leased"
    ANALYZING = "analyzing"
    IMPLEMENTING = "implementing"
    VERIFYING = "verifying"
    REVIEWING = "reviewing"
    READY_FOR_HUMAN = "ready_for_human"
    RETRY = "retry"
    NEEDS_HUMAN = "needs_human"
    DEAD = "dead"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


class RunRole(StrEnum):
    READER = "reader"
    WRITER = "writer"


class RunStatus(StrEnum):
    LEASED = "leased"
    RELEASED = "released"
    FAILED = "failed"
    EXPIRED = "expired"
    COMPLETED = "completed"


class FailureClass(StrEnum):
    DATABASE_UNAVAILABLE = "database_unavailable"
    WORKER_LOST = "worker_lost"
    PROVIDER_TRANSPORT_UNAVAILABLE = "provider_transport_unavailable"
    TEMPORARY_RESOURCE_EXHAUSTION = "temporary_resource_exhaustion"
    VALIDATION = "validation"
    POLICY = "policy"
    AUTHENTICATION = "authentication"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    BUDGET = "budget"
    SECURITY = "security"
    STALE_INPUT = "stale_input"
    PROTOCOL = "protocol"
    PROVIDER_QUALITY = "provider_quality"


@dataclass(frozen=True)
class Actor:
    actor_id: str
    kind: str
    scopes: frozenset[str]
    repositories: frozenset[str]


@dataclass(frozen=True)
class FactoryTaskV1:
    task_id: str
    repository_id: str
    status: TaskStatus
    generation: int
    intent_digest: str
    packet_digest: str
    deadline_at: datetime


# The old name remains an identity alias so callers do not receive an
# unversioned wire or Python compatibility break.
TaskProjection = FactoryTaskV1


@dataclass(frozen=True)
class FactoryRunV1:
    run_id: str
    task_id: str
    owner: str
    role: RunRole
    packet_digest: str
    fence: int
    state: RunStatus
    lease_expires_at: datetime
    deadline_at: datetime
    created_at: datetime
    released_at: datetime | None


@dataclass(frozen=True)
class FactoryAttemptV1:
    attempt_id: str
    task_id: str
    run_id: str
    attempt_no: int
    failure_class: FailureClass | None
    failure_code: str | None
    failure_digest: str | None
    created_at: datetime
    finished_at: datetime | None


def _deep_freeze(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(_deep_freeze(item) for item in value)
    return value


@dataclass(frozen=True)
class FactoryEventV1:
    event_id: str
    task_id: str
    event_sequence: int
    idempotency_key: str
    actor_id: str
    action: str
    metadata: Mapping[str, Any]
    mandatory_cleanup: bool
    created_at: datetime

    def __post_init__(self) -> None:
        object.__setattr__(self, "metadata", _deep_freeze(self.metadata))


@dataclass(frozen=True)
class FactoryRunAttemptV1:
    run: FactoryRunV1
    attempt: FactoryAttemptV1


@dataclass(frozen=True)
class FactoryRunHistoryPageV1:
    items: tuple[FactoryRunAttemptV1, ...]
    cursor: str | None


@dataclass(frozen=True)
class FactoryEventHistoryPageV1:
    items: tuple[FactoryEventV1, ...]
    cursor: int | None


@dataclass(frozen=True)
class LeaseGrant:
    task_id: str
    run_id: str
    owner: str
    role: RunRole
    fence: int
    expires_at: datetime
    packet_digest: str
