import unittest
from unittest import mock

from adaptive_factory.models import FailureClass, TaskStatus
from adaptive_factory.state import (
    TransitionCommand,
    TransitionOperation,
    TRANSITIONS,
    authorize_transition,
    classify_retry,
)


class StatePolicyTests(unittest.TestCase):
    def test_every_state_pair_has_an_explicit_decision(self):
        for current in TaskStatus:
            for target in TaskStatus:
                decision = authorize_transition(
                    current,
                    target,
                    TransitionCommand(
                        actor_kind="control_plane",
                        target=target,
                        operation=TransitionOperation.RECONCILE_DEADLINE,
                        operator_decision_id="decision-1",
                    ),
                )
                self.assertIn(decision.code, {"allowed", "forbidden", "needs_human"})

    def test_provider_cannot_choose_state(self):
        decision = authorize_transition(
            TaskStatus.IMPLEMENTING,
            TaskStatus.READY_FOR_HUMAN,
            TransitionCommand(
                actor_kind="provider",
                target=TaskStatus.READY_FOR_HUMAN,
                operation=TransitionOperation.RELEASE_COMPLETED,
            ),
        )
        self.assertEqual(decision.code, "forbidden")

    def test_terminal_states_cannot_transition(self):
        for current in (TaskStatus.DEAD, TaskStatus.CANCELLED, TaskStatus.SUPERSEDED, TaskStatus.READY_FOR_HUMAN):
            self.assertEqual(
                authorize_transition(
                    current,
                    TaskStatus.QUEUED,
                    TransitionCommand(
                        actor_kind="control_plane",
                        target=TaskStatus.QUEUED,
                        operation=TransitionOperation.CLAIM,
                    ),
                ).code,
                "forbidden",
            )

    def test_needs_human_requeue_requires_persisted_decision(self):
        missing = authorize_transition(
            TaskStatus.NEEDS_HUMAN,
            TaskStatus.QUEUED,
            TransitionCommand(
                actor_kind="control_plane",
                target=TaskStatus.QUEUED,
                operation=TransitionOperation.OPERATOR_REQUEUE,
            ),
        )
        present = authorize_transition(
            TaskStatus.NEEDS_HUMAN,
            TaskStatus.QUEUED,
            TransitionCommand(
                actor_kind="operator",
                target=TaskStatus.QUEUED,
                operation=TransitionOperation.OPERATOR_REQUEUE,
                operator_decision_id="decision-1",
            ),
        )
        self.assertEqual(missing.code, "needs_human")
        self.assertEqual(present.code, "allowed")

    def test_phase_operation_allows_only_the_next_worker_phase(self):
        allowed = {
            TaskStatus.LEASED: TaskStatus.ANALYZING,
            TaskStatus.ANALYZING: TaskStatus.IMPLEMENTING,
            TaskStatus.IMPLEMENTING: TaskStatus.VERIFYING,
            TaskStatus.VERIFYING: TaskStatus.REVIEWING,
        }
        for current in (
            TaskStatus.LEASED,
            TaskStatus.ANALYZING,
            TaskStatus.IMPLEMENTING,
            TaskStatus.VERIFYING,
            TaskStatus.REVIEWING,
        ):
            for target in TaskStatus:
                with self.subTest(current=current, target=target):
                    decision = authorize_transition(
                        current,
                        target,
                        TransitionCommand(
                            actor_kind="worker",
                            target=target,
                            operation=TransitionOperation.PHASE,
                        ),
                    )
                    self.assertEqual(decision.code, "allowed" if allowed.get(current) is target else "forbidden")

    def test_completed_release_compatibility_edge_is_operation_scoped(self):
        compatible = authorize_transition(
            TaskStatus.LEASED,
            TaskStatus.READY_FOR_HUMAN,
            TransitionCommand(
                actor_kind="worker",
                target=TaskStatus.READY_FOR_HUMAN,
                operation=TransitionOperation.RELEASE_COMPLETED,
            ),
        )
        phase_skip = authorize_transition(
            TaskStatus.LEASED,
            TaskStatus.READY_FOR_HUMAN,
            TransitionCommand(
                actor_kind="worker",
                target=TaskStatus.READY_FOR_HUMAN,
                operation=TransitionOperation.PHASE,
            ),
        )
        self.assertEqual(compatible.code, "allowed")
        self.assertIn("compatibility", compatible.reason)
        self.assertEqual(phase_skip.code, "forbidden")

    def test_completed_release_rejects_intermediate_phase_skips(self):
        for current in (TaskStatus.ANALYZING, TaskStatus.IMPLEMENTING, TaskStatus.VERIFYING):
            with self.subTest(current=current):
                decision = authorize_transition(
                    current,
                    TaskStatus.READY_FOR_HUMAN,
                    TransitionCommand(
                        actor_kind="worker",
                        target=TaskStatus.READY_FOR_HUMAN,
                        operation=TransitionOperation.RELEASE_COMPLETED,
                    ),
                )
                self.assertEqual(decision.code, "forbidden")
        self.assertEqual(
            authorize_transition(
                TaskStatus.REVIEWING,
                TaskStatus.READY_FOR_HUMAN,
                TransitionCommand(
                    actor_kind="worker",
                    target=TaskStatus.READY_FOR_HUMAN,
                    operation=TransitionOperation.RELEASE_COMPLETED,
                ),
            ).code,
            "allowed",
        )

    def test_retry_deadline_quarantine_can_enter_needs_human(self):
        self.assertEqual(
            authorize_transition(
                TaskStatus.RETRY,
                TaskStatus.NEEDS_HUMAN,
                TransitionCommand(
                    actor_kind="control_plane",
                    target=TaskStatus.NEEDS_HUMAN,
                    operation=TransitionOperation.RECONCILE_DEADLINE,
                ),
            ).code,
            "allowed",
        )

    def test_normal_operation_cannot_bypass_the_closed_graph(self):
        without_completion = TRANSITIONS[TaskStatus.REVIEWING] - {
            TaskStatus.READY_FOR_HUMAN
        }
        with mock.patch.dict(
            TRANSITIONS,
            {TaskStatus.REVIEWING: without_completion},
        ):
            decision = authorize_transition(
                TaskStatus.REVIEWING,
                TaskStatus.READY_FOR_HUMAN,
                TransitionCommand(
                    actor_kind="worker",
                    target=TaskStatus.READY_FOR_HUMAN,
                    operation=TransitionOperation.RELEASE_COMPLETED,
                ),
            )
        self.assertEqual(decision.code, "forbidden")

    def test_only_closed_infrastructure_failures_retry_twice(self):
        retryable = {
            FailureClass.DATABASE_UNAVAILABLE,
            FailureClass.WORKER_LOST,
            FailureClass.PROVIDER_TRANSPORT_UNAVAILABLE,
            FailureClass.TEMPORARY_RESOURCE_EXHAUSTION,
        }
        for failure in FailureClass:
            with self.subTest(failure=failure):
                decision = classify_retry(failure, attempt_no=1, infrastructure_retries=2)
                self.assertEqual(decision.retry, failure in retryable)
        self.assertTrue(
            classify_retry(FailureClass.WORKER_LOST, attempt_no=2, infrastructure_retries=2).retry
        )
        self.assertFalse(
            classify_retry(FailureClass.WORKER_LOST, attempt_no=3, infrastructure_retries=2).retry
        )
        self.assertEqual(
            classify_retry(
                FailureClass.WORKER_LOST, attempt_no=3, infrastructure_retries=2
            ).terminal,
            TaskStatus.DEAD,
        )

    def test_accepted_infrastructure_retry_limit_is_exact(self):
        for infrastructure_retries in range(3):
            for attempt_no in range(1, infrastructure_retries + 2):
                with self.subTest(
                    infrastructure_retries=infrastructure_retries,
                    attempt_no=attempt_no,
                ):
                    decision = classify_retry(
                        FailureClass.WORKER_LOST,
                        attempt_no=attempt_no,
                        infrastructure_retries=infrastructure_retries,
                    )
                    self.assertEqual(decision.retry, attempt_no <= infrastructure_retries)
                    self.assertEqual(
                        decision.terminal,
                        TaskStatus.RETRY
                        if attempt_no <= infrastructure_retries
                        else TaskStatus.DEAD,
                    )

    def test_future_delivery_state_is_not_a_task_status(self):
        for name in ("pr_open", "merged", "deployed"):
            with self.assertRaises(ValueError):
                TaskStatus(name)


if __name__ == "__main__":
    unittest.main()
