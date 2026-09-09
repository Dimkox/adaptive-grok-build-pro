from __future__ import annotations

from collections import deque
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from pilot.authority import LiteralGrantAuthority
from pilot.github import GitHubPublication, PushReceiptV1
from pilot.live_github import CommandResult, PinnedGitHubTransport
from pilot.store import PilotStore
from pilot.tests.support import utc_time
from pilot.tests.test_github import BINDING, FakeGitHubTransport, gate_passed, grant


class FakeCommandRunner:
    def __init__(self, results: list[CommandResult]) -> None:
        self.results = deque(results)
        self.calls: list[dict] = []

    def run(self, **values) -> CommandResult:
        self.calls.append(values)
        if not self.results:
            raise AssertionError("unexpected command")
        return self.results.popleft()


def result(value, *, returncode: int = 0, stderr: bytes = b"") -> CommandResult:
    stdout = value if isinstance(value, bytes) else json.dumps(value).encode("utf-8")
    return CommandResult(returncode, stdout, stderr)


class PinnedGitHubTransportTests(unittest.TestCase):
    def _transport(self, root: Path, results: list[CommandResult]):
        gh = root / "gh"
        git = root / "git"
        gh.write_bytes(b"pinned gh")
        git.write_bytes(b"pinned git")
        gh.chmod(0o755)
        git.chmod(0o755)
        runner = FakeCommandRunner(results)
        transport = PinnedGitHubTransport(
            gh_executable=str(gh),
            gh_sha256=hashlib.sha256(gh.read_bytes()).hexdigest(),
            git_executable=str(git),
            git_sha256=hashlib.sha256(git.read_bytes()).hexdigest(),
            auth_environment=lambda: {"HOME": str(root / "operator-home")},
            runner=runner,
            clock=lambda: utc_time(5),
        )
        return transport, runner, gh, git

    def test_reads_only_exact_repo_issue_and_base_ref_facts(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            transport, runner, gh, _git = self._transport(
                root,
                [
                    result({"full_name": "Dimkox/ai-dark-factory-landing", "node_id": "R_target", "default_branch": "main"}),
                    result({"number": 1, "node_id": "I_target_1", "state": "open", "updated_at": "2026-09-05T12:00:00Z", "user": {"login": "partner"}, "author_association": "COLLABORATOR", "title": "Update release presentation", "body": "bounded", "pull_request": None}),
                    result({"object": {"sha": "6" * 40}}),
                    result({"tree": {"sha": "7" * 40}}),
                ],
            )

            issue = transport.fetch_issue("Dimkox/ai-dark-factory-landing", 1)
            base = transport.fetch_ref("Dimkox/ai-dark-factory-landing", "refs/heads/main")

            self.assertEqual((issue.repository_node_id, issue.issue_node_id), ("R_target", "I_target_1"))
            self.assertEqual((base.sha, base.tree), ("6" * 40, "7" * 40))
            self.assertEqual(
                [call["argv"] for call in runner.calls],
                [
                    (str(gh), "api", "--hostname", "github.com", "--method", "GET", "repos/Dimkox/ai-dark-factory-landing"),
                    (str(gh), "api", "--hostname", "github.com", "--method", "GET", "repos/Dimkox/ai-dark-factory-landing/issues/1"),
                    (str(gh), "api", "--hostname", "github.com", "--method", "GET", "repos/Dimkox/ai-dark-factory-landing/git/ref/heads/main"),
                    (str(gh), "api", "--hostname", "github.com", "--method", "GET", "repos/Dimkox/ai-dark-factory-landing/git/commits/" + "6" * 40),
                ],
            )
            self.assertTrue(all("CODEX_API_KEY" not in call["environment"] for call in runner.calls))

    def test_observes_then_executes_only_exact_push_and_draft_post(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state = PilotStore(root / "state", control_repository=Path(__file__).resolve().parents[2], clock=lambda: utc_time(0))
            configured, issue, candidate, writer = gate_passed(state)
            publication = GitHubPublication(configured, state, clock=lambda: utc_time(5))
            branch = publication.branch_request(issue.job_id)
            fake = FakeGitHubTransport(issue, configured.base_sha)
            fake.branch_sha = candidate.candidate_sha
            push = publication.publish_branch(
                branch,
                writer,
                LiteralGrantAuthority(BINDING, [grant(branch.resource)], now=lambda: utc_time(0)),
                fake,
                command_key="seed-exact-push",
            )
            proposal = publication.proposal_request(issue.job_id, push)
            observed_pr = {
                "number": 19,
                "node_id": "PR_target19",
                "html_url": "https://github.com/Dimkox/ai-dark-factory-landing/pull/19",
                "head": {"ref": proposal.head_ref, "sha": proposal.head_sha},
                "base": {"ref": proposal.base_ref},
                "draft": True,
                "body": proposal.body,
                "state": "open",
                "created_at": "2026-09-05T12:00:06Z",
            }
            transport, runner, gh, git = self._transport(
                root,
                [
                    result({"full_name": configured.github_name, "node_id": issue.repository_node_id, "default_branch": "main"}),
                    result({"number": 1, "node_id": issue.issue_node_id, "state": "open", "updated_at": issue.updated_at, "user": {"login": issue.author_login}, "author_association": issue.author_association, "title": issue.title, "body": issue.body, "pull_request": None}),
                    result({"object": {"sha": configured.base_sha}}),
                    result({"tree": {"sha": configured.base_tree}}),
                    result(b"", returncode=1, stderr=b"gh: Not Found (HTTP 404)\n"),
                    result(
                        b"To https://github.com/Dimkox/ai-dark-factory-landing.git\n"
                        b"*\t" + branch.branch_ref.encode("ascii") + b":"
                        + branch.branch_ref.encode("ascii") + b"\t[new branch]\n"
                        b"Done\n"
                    ),
                    result([observed_pr]),
                    result(observed_pr),
                ],
            )

            observation = transport.observe(branch)
            transport.push_exact(branch, writer)
            proposals = transport.find_proposals(proposal)
            transport.create_draft(proposal)

            self.assertIsNone(observation.branch_sha)
            self.assertEqual(proposals[0].number, 19)
            push_call = runner.calls[5]
            self.assertEqual(push_call["argv"][0], str(git))
            self.assertIn("--no-force", push_call["argv"])
            self.assertNotIn("--force", push_call["argv"])
            self.assertEqual(push_call["argv"][-1], f"{candidate.candidate_sha}:{branch.branch_ref}")
            post_call = runner.calls[7]
            self.assertEqual(post_call["argv"][:6], (str(gh), "api", "--hostname", "github.com", "--method", "POST"))
            payload = json.loads(post_call["stdin"].decode("utf-8"))
            self.assertTrue(payload["draft"])
            self.assertFalse(payload["maintainer_can_modify"])
            forbidden = " ".join((*push_call["argv"], *post_call["argv"])).lower()
            self.assertNotRegex(forbidden, r"(?:--force|merge|close|delete|tag|comment|label|deploy)")
            state.close()


if __name__ == "__main__":
    unittest.main()
