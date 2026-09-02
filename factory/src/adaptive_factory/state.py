from __future__ import annotations

from dataclasses import dataclass

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


@dataclass(frozen=True)
class TransitionCommand:
    actor_kind: str
    target: TaskStatus
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
    if current in TERMINAL or target not in TRANSITIONS.get(current, set()):
        return TransitionDecision("forbidden", "transition is not in the closed M4 graph")
    if current is TaskStatus.NEEDS_HUMAN and target is TaskStatus.QUEUED:
        if command.actor_kind != "operator" or not command.operator_decision_id:
            return TransitionDecision("needs_human", "persisted operator decision required")
    if (
        current
        in {
            TaskStatus.LEASED,
            TaskStatus.ANALYZING,
            TaskStatus.IMPLEMENTING,
            TaskStatus.VERIFYING,
            TaskStatus.REVIEWING,
        }
        and command.actor_kind == "operator"
        and target not in {TaskStatus.CANCELLED, TaskStatus.NEEDS_HUMAN}
    ):
        return TransitionDecision("forbidden", "leased phases are worker/control-plane guarded")
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
