import unittest

from adaptive_factory.models import FailureClass, TaskStatus
from adaptive_factory.state import TransitionCommand, authorize_transition, classify_retry


class StatePolicyTests(unittest.TestCase):
    def test_every_state_pair_has_an_explicit_decision(self):
        for current in TaskStatus:
            for target in TaskStatus:
                decision = authorize_transition(current, target, TransitionCommand(actor_kind="control_plane", target=target, operator_decision_id="decision-1"))
                self.assertIn(decision.code, {"allowed", "forbidden", "needs_human"})

    def test_provider_cannot_choose_state(self):
        decision = authorize_transition(TaskStatus.IMPLEMENTING, TaskStatus.READY_FOR_HUMAN, TransitionCommand(actor_kind="provider", target=TaskStatus.READY_FOR_HUMAN))
        self.assertEqual(decision.code, "forbidden")

    def test_terminal_states_cannot_transition(self):
        for current in (TaskStatus.DEAD, TaskStatus.CANCELLED, TaskStatus.SUPERSEDED, TaskStatus.READY_FOR_HUMAN):
            self.assertEqual(authorize_transition(current, TaskStatus.QUEUED, TransitionCommand(actor_kind="control_plane", target=TaskStatus.QUEUED)).code, "forbidden")

    def test_needs_human_requeue_requires_persisted_decision(self):
        missing = authorize_transition(TaskStatus.NEEDS_HUMAN, TaskStatus.QUEUED, TransitionCommand(actor_kind="control_plane", target=TaskStatus.QUEUED))
        present = authorize_transition(TaskStatus.NEEDS_HUMAN, TaskStatus.QUEUED, TransitionCommand(actor_kind="operator", target=TaskStatus.QUEUED, operator_decision_id="decision-1"))
        self.assertEqual(missing.code, "needs_human")
        self.assertEqual(present.code, "allowed")

    def test_only_closed_infrastructure_failures_retry_twice(self):
        retryable = {
            FailureClass.DATABASE_UNAVAILABLE,
            FailureClass.WORKER_LOST,
            FailureClass.PROVIDER_TRANSPORT_UNAVAILABLE,
            FailureClass.TEMPORARY_RESOURCE_EXHAUSTION,
        }
        for failure in FailureClass:
            with self.subTest(failure=failure):
                decision = classify_retry(failure, attempt_no=1)
                self.assertEqual(decision.retry, failure in retryable)
        self.assertTrue(classify_retry(FailureClass.WORKER_LOST, attempt_no=2).retry)
        self.assertFalse(classify_retry(FailureClass.WORKER_LOST, attempt_no=3).retry)
        self.assertEqual(classify_retry(FailureClass.WORKER_LOST, attempt_no=3).terminal, TaskStatus.DEAD)

    def test_future_delivery_state_is_not_a_task_status(self):
        for name in ("pr_open", "merged", "deployed"):
            with self.assertRaises(ValueError):
                TaskStatus(name)


if __name__ == "__main__":
    unittest.main()
