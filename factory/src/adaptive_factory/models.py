from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


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
class TaskProjection:
    task_id: str
    repository_id: str
    status: TaskStatus
    generation: int
    intent_digest: str
    packet_digest: str
    deadline_at: datetime


@dataclass(frozen=True)
class LeaseGrant:
    task_id: str
    run_id: str
    owner: str
    role: RunRole
    fence: int
    expires_at: datetime
    packet_digest: str
