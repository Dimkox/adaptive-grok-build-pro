from __future__ import annotations

from pathlib import Path
import tempfile
import unittest

from pilot.authority import ControlBinding, LiteralGrantAuthority
from pilot.contracts import CandidateValidationV1
from pilot.github import (
    ExactGitPushCommand,
    GhDraftProposalCommand,
    GitHubPublication,
    ProposalObservation,
    PublicationObservation,
)
from pilot.profile import exact_landing_profile
from pilot.store import PilotStore
from pilot.tests.support import candidate_change, issue_snapshot, utc_time
from pilot.workspace import PreparedWorkspace


BINDING = ControlBinding(
    repository="Dimkox/adaptive-grok-build-pro",
    route_id="0ce2d62a018e",
    change_id="20260905-feature-implement-a-single-operator-codex-github-0ce2d6",
    git_head="a" * 40,
    tree_fingerprint="b" * 64,
)


def profile():
    return exact_landing_profile(
        codex_executable="/opt/pilot/bin/codex",
        codex_sha256="a" * 64,
        codex_version="0.153.4",
        model_id="gpt-5.3-codex",
        python_executable="/usr/bin/python3",
        python_sha256="b" * 64,
    )


def grant(resource: str, *, proposal: bool = False) -> dict:
    return {
        "schema_version": 2,
        "id": "fedcba9876543210" if proposal else "0123456789abcdef",
        "authorization": "delegated-local-grant",
        "source": "explicit-user-consent",
        "scope": "external-write" if proposal else "production",
        "actions": ["external-write" if proposal else "git-push-branch"],
        "resources": [resource],
        "reason": "one exact proposal effect",
        "repository": BINDING.repository,
        "route_id": BINDING.route_id,
        "change_id": BINDING.change_id,
        "git_head": BINDING.git_head,
        "tree_fingerprint": BINDING.tree_fingerprint,
        "created_at": "2026-09-05T11:55:00+00:00",
        "expires_at": "2026-09-05T12:05:00+00:00",
    }


def gate_passed(store: PilotStore):
    configured = profile()
    issue = issue_snapshot(
        profile_digest=configured.profile_digest,
        base_sha=configured.base_sha,
        base_tree=configured.base_tree,
    )
    candidate = candidate_change(issue)
    validation = CandidateValidationV1.from_facts(
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
    store.create_or_replay(issue, command_key="submit-1")
    store.mark_workspace_ready(issue.job_id, workspace_digest=candidate.workspace_digest)
    store.begin_invocation(issue.job_id, command_key="codex-1")
    store.store_candidate(issue.job_id, candidate)
    store.begin_validation(issue.job_id, command_key="validation-1")
    store.store_validation(issue.job_id, validation)
    writer = PreparedWorkspace(
        Path("/private/writer"), Path("/private/writer/app"), Path("/private/writer/control.git"),
        issue.base_sha, issue.base_tree, candidate.workspace_digest, True, True,
    )
    return configured, issue, candidate, writer


class FakeGitHubTransport:
    def __init__(self, issue, base_sha: str) -> None:
        self.issue = issue
        self.base_sha = base_sha
        self.branch_sha = None
        self.proposals = []
        self.push_calls = []
        self.create_calls = []
        self.hard_crash_push = False
        self.hard_crash_create = False

    def observe(self, request):
        return PublicationObservation(
            self.base_sha,
            self.issue.issue_node_id,
            self.issue.updated_at,
            self.branch_sha,
            "2026-09-05T12:00:05Z",
        )

    def push_exact(self, request, writer):
        self.push_calls.append((request, writer))
        self.branch_sha = request.candidate_sha
        if self.hard_crash_push:
            raise KeyboardInterrupt("simulated process death")

    def find_proposals(self, request):
        return tuple(self.proposals)

    def create_draft(self, request):
        self.create_calls.append(request)
        self.proposals.append(
            ProposalObservation(
                19,
                "PR_target19",
                "https://github.com/Dimkox/ai-dark-factory-landing/pull/19",
                request.head_ref,
                request.head_sha,
                request.base_ref,
                True,
                request.marker,
                "open",
                "2026-09-05T12:00:06Z",
            )
        )
        if self.hard_crash_create:
            raise KeyboardInterrupt("simulated process death")


class GitHubPublicationTests(unittest.TestCase):
    def test_exact_command_shapes_are_non_force_single_ref_and_draft_only(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            store = PilotStore(Path(raw) / "state", control_repository=Path(__file__).resolve().parents[2])
            configured, issue, candidate, writer = gate_passed(store)
            publication = GitHubPublication(configured, store)
            branch = publication.branch_request("pilot-job-1")
            push_argv, push_env = ExactGitPushCommand().invocation(branch, writer)
            self.assertIn("--no-force", push_argv)
            self.assertNotIn("--force", push_argv)
            self.assertEqual(push_argv[-1], f"{branch.candidate_sha}:{branch.branch_ref}")
            self.assertFalse(any("tag" in item for item in push_argv))
            self.assertFalse(any(key.startswith(("GH_", "GITHUB_")) for key in push_env))

            external = FakeGitHubTransport(issue, configured.base_sha)
            external.branch_sha = candidate.candidate_sha
            push_receipt = publication.publish_branch(
                branch,
                writer,
                LiteralGrantAuthority(BINDING, [grant(branch.resource)], now=lambda: utc_time(0)),
                external,
                command_key="push-shape",
            )
            proposal = publication.proposal_request("pilot-job-1", push_receipt)
            pr_argv, payload = GhDraftProposalCommand().invocation(proposal)
            self.assertEqual(pr_argv[-1], "-")
            self.assertEqual(payload["draft"], True)
            self.assertEqual(payload["maintainer_can_modify"], False)
            self.assertNotIn("merge", " ".join(pr_argv).lower())
            self.assertNotRegex(payload["body"], r"(?i)\b(?:fixes|closes)\s+#")
            store.close()

    def test_ambiguous_restart_reconciles_branch_and_pr_without_second_write(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            state_root = Path(raw) / "state"
            control = Path(__file__).resolve().parents[2]
            store = PilotStore(state_root, control_repository=control, clock=lambda: utc_time(0))
            configured, issue, _candidate, writer = gate_passed(store)
            external = FakeGitHubTransport(issue, configured.base_sha)
            publication = GitHubPublication(configured, store, clock=lambda: utc_time(5))
            branch_request = publication.branch_request(issue.job_id)
            branch_authority = LiteralGrantAuthority(BINDING, [grant(branch_request.resource)], now=lambda: utc_time(0))
            external.hard_crash_push = True
            with self.assertRaises(KeyboardInterrupt):
                publication.publish_branch(branch_request, writer, branch_authority, external, command_key="push-1")
            self.assertEqual(len(external.push_calls), 1)
            store.close()

            external.hard_crash_push = False
            recovered = PilotStore(state_root, control_repository=control, clock=lambda: utc_time(6))
            publication = GitHubPublication(configured, recovered, clock=lambda: utc_time(6))
            push_receipt = publication.publish_branch(branch_request, writer, branch_authority, external, command_key="push-1")
            self.assertEqual(push_receipt.outcome, "reconciled_exact")
            self.assertEqual(len(external.push_calls), 1)

            proposal_request = publication.proposal_request(issue.job_id, push_receipt)
            proposal_authority = LiteralGrantAuthority(BINDING, [grant(proposal_request.resource, proposal=True)], now=lambda: utc_time(0))
            external.hard_crash_create = True
            with self.assertRaises(KeyboardInterrupt):
                publication.publish_proposal(proposal_request, push_receipt, proposal_authority, external, command_key="pr-1")
            self.assertEqual(len(external.create_calls), 1)
            recovered.close()

            external.hard_crash_create = False
            final_store = PilotStore(state_root, control_repository=control, clock=lambda: utc_time(7))
            proposal = GitHubPublication(configured, final_store, clock=lambda: utc_time(7)).publish_proposal(
                proposal_request, push_receipt, proposal_authority, external, command_key="pr-1"
            )
            self.assertEqual(proposal.push_outcome, "reconciled_exact")
            self.assertEqual(proposal.status, "proposal_created_merge_gate_unavailable")
            self.assertFalse(proposal.merge_eligible)
            self.assertEqual(len(external.create_calls), 1)
            self.assertEqual(final_store.get(issue.job_id).state, "awaiting_human")
            final_store.close()


if __name__ == "__main__":
    unittest.main()
