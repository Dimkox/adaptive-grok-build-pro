from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from pilot.authority import LiteralGrantAuthority
from pilot.contracts import CandidateValidationV1
from pilot.coordinator import PilotCoordinator
from pilot.github import GitHubPublication
from pilot.store import PilotStore
from pilot.tests.support import candidate_change, issue_snapshot, utc_time
from pilot.tests.test_github import BINDING, FakeGitHubTransport, grant, profile
from pilot.workspace import PreparedWorkspace


class FakeIssueSource:
    def __init__(self, issue) -> None:
        self.issue = issue
        self.calls = []

    def snapshot(self, **values):
        self.calls.append(values)
        return self.issue


class FakeWorkspaces:
    def __init__(self, workspace) -> None:
        self.workspace = workspace
        self.prepare_calls = []
        self.cleanup_calls = []

    def prepare(self, job_id):
        self.prepare_calls.append(job_id)
        return self.workspace

    def cleanup(self, workspace):
        self.cleanup_calls.append(workspace)


class FakeExecutor:
    def __init__(self, store, candidate) -> None:
        self.store = store
        self.candidate = candidate
        self.calls = []

    def run(self, issue, workspace, *, command_key):
        self.calls.append((issue, workspace, command_key))
        self.store.begin_invocation(issue.job_id, command_key=command_key)
        self.store.store_candidate(issue.job_id, self.candidate)
        return self.candidate


class FakeValidator:
    def __init__(self, configured, store, issue, candidate) -> None:
        self.store = store
        self.calls = []
        self.validation = CandidateValidationV1.from_facts(
            {
                "schema_version": 1,
                "job_id": issue.job_id,
                "profile_digest": configured.profile_digest,
                "candidate_digest": candidate.candidate_digest,
                "candidate_sha": candidate.candidate_sha,
                "candidate_tree": candidate.candidate_tree,
                "test_profile_digest": configured.test_profile_digest,
                "command_digest": configured.test_command_digest,
                "exit_code": 0,
                "elapsed_ms": 42,
                "stdout_sha256": "c" * 64,
                "stderr_sha256": "d" * 64,
                "pre_test_tree": candidate.candidate_tree,
                "post_test_tree": candidate.candidate_tree,
                "writer_id": candidate.writer_id,
                "evaluator_id": "landing-semantic-gate-v1",
                "semantic_profile_digest": configured.semantic_profile_digest,
                "acceptance_ids": list(issue.acceptance_ids),
                "decision": "pass",
                "reason_codes": [],
                "completed_at": "2026-09-05T12:00:04Z",
            }
        )

    def validate(self, candidate, workspace, *, command_key):
        self.calls.append((candidate, workspace, command_key))
        self.store.begin_validation(candidate.job_id, command_key=command_key)
        self.store.store_validation(candidate.job_id, self.validation)
        return self.validation


class PilotCoordinatorTests(unittest.TestCase):
    def test_one_fake_run_forms_all_five_outputs_and_replay_has_no_effect(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            control = Path(__file__).resolve().parents[2]
            store = PilotStore(Path(raw) / "state", control_repository=control, clock=lambda: utc_time(0))
            configured = profile()
            issue = issue_snapshot(profile_digest=configured.profile_digest, base_sha=configured.base_sha, base_tree=configured.base_tree)
            candidate = candidate_change(issue)
            workspace = PreparedWorkspace(
                Path(raw) / "writer", Path(raw) / "writer/app", Path(raw) / "writer/control.git",
                issue.base_sha, issue.base_tree, candidate.workspace_digest, True, True,
            )
            source = FakeIssueSource(issue)
            workspaces = FakeWorkspaces(workspace)
            executor = FakeExecutor(store, candidate)
            validator = FakeValidator(configured, store, issue, candidate)
            publication = GitHubPublication(configured, store, clock=lambda: utc_time(5))
            coordinator = PilotCoordinator(
                configured, store, source, workspaces, executor, validator, publication,
                clock=lambda: utc_time(7),
            )

            prepared = coordinator.prepare_candidate(
                job_id=issue.job_id,
                issue_number=issue.issue_number,
                acceptance_ids=issue.acceptance_ids,
            )
            self.assertEqual(prepared.job.state, "gate_passed")
            external = FakeGitHubTransport(issue, configured.base_sha)
            branch = publication.branch_request(issue.job_id)
            push = coordinator.publish_branch(
                prepared,
                LiteralGrantAuthority(BINDING, [grant(branch.resource)], now=lambda: utc_time(0)),
                external,
            )
            proposal_request = publication.proposal_request(issue.job_id, push)
            proposal, outcome = coordinator.publish_proposal(
                prepared,
                push,
                LiteralGrantAuthority(BINDING, [grant(proposal_request.resource, proposal=True)], now=lambda: utc_time(0)),
                external,
            )
            self.assertEqual((len(source.calls), len(executor.calls), len(validator.calls)), (1, 1, 1))
            self.assertEqual((len(external.push_calls), len(external.create_calls)), (1, 1))
            self.assertEqual(proposal.status, "proposal_created_merge_gate_unavailable")
            self.assertEqual(outcome.status, "merge_gate_unavailable")
            self.assertEqual(store.get(issue.job_id).outcome, outcome)
            self.assertEqual(workspaces.cleanup_calls, [workspace])
            self.assertFalse(any(hasattr(coordinator, name) for name in ("merge", "close", "deploy", "retry")))

            replay = coordinator.prepare_candidate(
                job_id=issue.job_id,
                issue_number=issue.issue_number,
                acceptance_ids=issue.acceptance_ids,
            )
            self.assertIsNone(replay.workspace)
            self.assertEqual(replay.job.outcome, outcome)
            self.assertEqual((len(source.calls), len(executor.calls), len(validator.calls)), (1, 1, 1))
            store.close()


if __name__ == "__main__":
    unittest.main()
