from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .models import FailureClass, TaskStatus


TERMINAL = frozenset({TaskStatus.DEAD, TaskStatus.CANCELLED, TaskStatus.SUPERSEDED, TaskStatus.READY_FOR_HUMAN})
TRANSITIONS = {
    TaskStatus.INBOX: {TaskStatus.TRIAGED, TaskStatus.CANCELLED, TaskStatus.SUPERSEDED, TaskStatus.NEEDS_HUMAN},
    TaskStatus.TRIAGED: {
        TaskStatus.WAITING_DESIGN_APPROVAL,
        TaskStatus.QUEUED,
        TaskStatus.CANCELLED,
        TaskStatus.SUPERSEDED,
        TaskStatus.NEEDS_HUMAN,
    },
    TaskStatus.WAITING_DESIGN_APPROVAL: {
        TaskStatus.QUEUED,
        TaskStatus.CANCELLED,
        TaskStatus.SUPERSEDED,
        TaskStatus.NEEDS_HUMAN,
    },
    TaskStatus.QUEUED: {
        TaskStatus.LEASED,
        TaskStatus.CANCELLED,
        TaskStatus.SUPERSEDED,
        TaskStatus.NEEDS_HUMAN,
        TaskStatus.DEAD,
    },
    TaskStatus.RETRY: {
        TaskStatus.QUEUED,
        TaskStatus.LEASED,
        TaskStatus.CANCELLED,
        TaskStatus.SUPERSEDED,
        TaskStatus.NEEDS_HUMAN,
        TaskStatus.DEAD,
    },
    TaskStatus.LEASED: {
        TaskStatus.ANALYZING,
        TaskStatus.RETRY,
        TaskStatus.NEEDS_HUMAN,
        TaskStatus.DEAD,
        TaskStatus.CANCELLED,
        TaskStatus.SUPERSEDED,
    },
    TaskStatus.ANALYZING: {
        TaskStatus.IMPLEMENTING,
        TaskStatus.RETRY,
        TaskStatus.NEEDS_HUMAN,
        TaskStatus.DEAD,
        TaskStatus.CANCELLED,
        TaskStatus.SUPERSEDED,
    },
    TaskStatus.IMPLEMENTING: {
        TaskStatus.VERIFYING,
        TaskStatus.RETRY,
        TaskStatus.NEEDS_HUMAN,
        TaskStatus.DEAD,
        TaskStatus.CANCELLED,
        TaskStatus.SUPERSEDED,
    },
    TaskStatus.VERIFYING: {
        TaskStatus.REVIEWING,
        TaskStatus.RETRY,
        TaskStatus.NEEDS_HUMAN,
        TaskStatus.DEAD,
        TaskStatus.CANCELLED,
        TaskStatus.SUPERSEDED,
    },
    TaskStatus.REVIEWING: {
        TaskStatus.READY_FOR_HUMAN,
        TaskStatus.RETRY,
        TaskStatus.NEEDS_HUMAN,
        TaskStatus.DEAD,
        TaskStatus.CANCELLED,
        TaskStatus.SUPERSEDED,
    },
    TaskStatus.NEEDS_HUMAN: {TaskStatus.QUEUED, TaskStatus.CANCELLED, TaskStatus.SUPERSEDED, TaskStatus.DEAD},
}


class TransitionOperation(StrEnum):
    CLAIM = "claim"
    RETRY_EXHAUSTED = "retry_exhausted"
    PHASE = "phase"
    RELEASE_COMPLETED = "release_completed"
    RELEASE_FAILURE = "release_failure"
    CANCEL = "cancel"
    SUPERSEDE = "supersede"
    RECONCILE_EXPIRED = "reconcile_expired"
    RECONCILE_DEADLINE = "reconcile_deadline"
    OPERATOR_REQUEUE = "operator_requeue"


@dataclass(frozen=True)
class TransitionCommand:
    actor_kind: str
    target: TaskStatus
    operation: TransitionOperation
    operator_decision_id: str | None = None


@dataclass(frozen=True)
class TransitionDecision:
    code: str
    reason: str


@dataclass(frozen=True)
class RetryDecision:
    retry: bool
    terminal: TaskStatus | None
    reason: str


def authorize_transition(current: TaskStatus, target: TaskStatus, command: TransitionCommand) -> TransitionDecision:
    if command.actor_kind not in {"control_plane", "operator", "worker"}:
        return TransitionDecision("forbidden", "untrusted actor cannot select state")
    if target is not command.target:
        return TransitionDecision("forbidden", "command target does not match requested state")
    if current in TERMINAL:
        return TransitionDecision("forbidden", "transition is not in the closed M4 graph")

    if command.operation is TransitionOperation.PHASE:
        phase_edges = {
            TaskStatus.LEASED: TaskStatus.ANALYZING,
            TaskStatus.ANALYZING: TaskStatus.IMPLEMENTING,
            TaskStatus.IMPLEMENTING: TaskStatus.VERIFYING,
            TaskStatus.VERIFYING: TaskStatus.REVIEWING,
        }
        if command.actor_kind == "worker" and phase_edges.get(current) is target:
            return TransitionDecision("allowed", "next fenced worker phase authorized")
        return TransitionDecision("forbidden", "phase operation permits only the next worker phase")

    if command.operation is TransitionOperation.RELEASE_COMPLETED:
        if command.actor_kind != "worker" or target is not TaskStatus.READY_FOR_HUMAN:
            return TransitionDecision("forbidden", "completed release requires a worker completion target")
        if current is TaskStatus.LEASED:
            return TransitionDecision("allowed", "legacy completed-release compatibility")
        if current is TaskStatus.REVIEWING:
            return TransitionDecision("allowed", "reviewed completion authorized")
        return TransitionDecision("forbidden", "completed release requires leased compatibility or reviewing")

    permitted = {
        TransitionOperation.CLAIM: (
            "control_plane",
            {TaskStatus.QUEUED, TaskStatus.RETRY},
            {TaskStatus.LEASED},
        ),
        TransitionOperation.RETRY_EXHAUSTED: (
            "control_plane",
            {TaskStatus.QUEUED, TaskStatus.RETRY},
            {TaskStatus.DEAD},
        ),
        TransitionOperation.RELEASE_FAILURE: (
            "worker",
            {
                TaskStatus.LEASED,
                TaskStatus.ANALYZING,
                TaskStatus.IMPLEMENTING,
                TaskStatus.VERIFYING,
                TaskStatus.REVIEWING,
            },
            {TaskStatus.RETRY, TaskStatus.NEEDS_HUMAN, TaskStatus.DEAD},
        ),
        TransitionOperation.CANCEL: (
            "control_plane",
            set(TRANSITIONS),
            {TaskStatus.CANCELLED},
        ),
        TransitionOperation.SUPERSEDE: (
            "control_plane",
            set(TRANSITIONS),
            {TaskStatus.SUPERSEDED},
        ),
        TransitionOperation.RECONCILE_EXPIRED: (
            "control_plane",
            {
                TaskStatus.LEASED,
                TaskStatus.ANALYZING,
                TaskStatus.IMPLEMENTING,
                TaskStatus.VERIFYING,
                TaskStatus.REVIEWING,
            },
            {TaskStatus.RETRY, TaskStatus.NEEDS_HUMAN, TaskStatus.DEAD},
        ),
        TransitionOperation.RECONCILE_DEADLINE: (
            "control_plane",
            {TaskStatus.QUEUED, TaskStatus.RETRY},
            {TaskStatus.NEEDS_HUMAN, TaskStatus.DEAD},
        ),
    }
    if command.operation is TransitionOperation.OPERATOR_REQUEUE:
        if current is not TaskStatus.NEEDS_HUMAN or target is not TaskStatus.QUEUED:
            return TransitionDecision("forbidden", "operator requeue applies only to needs_human")
        if command.actor_kind != "operator" or not command.operator_decision_id:
            return TransitionDecision("needs_human", "persisted operator decision required")
        return TransitionDecision("allowed", "persisted operator decision authorized")
    rule = permitted.get(command.operation)
    if rule is None:
        return TransitionDecision("forbidden", "unknown transition operation")
    actor_kind, sources, targets = rule
    if command.actor_kind != actor_kind or current not in sources or target not in targets:
        return TransitionDecision("forbidden", "transition is outside operation policy")
    if target not in TRANSITIONS.get(current, set()):
        return TransitionDecision("forbidden", "transition is not in the closed M4 graph")
    return TransitionDecision("allowed", "closed transition authorized")


_RETRYABLE = frozenset(
    {
        FailureClass.DATABASE_UNAVAILABLE,
        FailureClass.WORKER_LOST,
        FailureClass.PROVIDER_TRANSPORT_UNAVAILABLE,
        FailureClass.TEMPORARY_RESOURCE_EXHAUSTION,
    }
)


def classify_retry(
    failure: FailureClass, *, attempt_no: int, infrastructure_retries: int
) -> RetryDecision:
    if (
        type(attempt_no) is not int
        or attempt_no < 1
        or type(infrastructure_retries) is not int
        or not 0 <= infrastructure_retries <= 2
    ):
        return RetryDecision(False, TaskStatus.NEEDS_HUMAN, "invalid attempt evidence")
    if failure not in _RETRYABLE:
        return RetryDecision(False, TaskStatus.NEEDS_HUMAN, "failure class is not retryable")
    if attempt_no > infrastructure_retries:
        return RetryDecision(False, TaskStatus.DEAD, "initial attempt plus accepted retries exhausted")
    return RetryDecision(True, TaskStatus.RETRY, "typed infrastructure retry")
