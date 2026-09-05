from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest

from pilot.authority import AuthorityError, LiteralGrantAuthority
from pilot.coordinator import PilotCoordinator
from pilot.github import GitHubPublication
from pilot.live import (
    ApiKeyCapability,
    LIVE_ACCEPTANCE_IDS,
    LivePilotError,
    PilotPhases,
    _validate_roots,
)
from pilot.store import PilotStore, PilotStoreError
from pilot.tests.support import candidate_change, issue_snapshot, utc_time
from pilot.tests.test_coordinator import FakeExecutor, FakeIssueSource, FakeValidator
from pilot.tests.test_github import BINDING, FakeGitHubTransport, grant, profile
from pilot.tests.test_github import gate_passed
from pilot.workspace import PreparedWorkspace


class RecoverableFakeWorkspaces:
    def __init__(self, workspace: PreparedWorkspace) -> None:
        self.workspace = workspace
        self.prepare_calls = []
        self.recover_calls = []
        self.cleanup_calls = []

    def prepare(self, job_id):
        self.prepare_calls.append(job_id)
        return self.workspace

    def recover(self, job_id, candidate=None):
        self.recover_calls.append((job_id, candidate))
        return self.workspace

    def cleanup(self, workspace):
        self.cleanup_calls.append(workspace)


class StaticAuthorityLoader:
    def __init__(self) -> None:
        self.authority = LiteralGrantAuthority(BINDING, [], now=lambda: utc_time(0))

    def load(self):
        return self.authority


def phases(
    store,
    configured,
    source,
    workspaces,
    executor,
    validator,
    external,
    loader,
    *,
    preflight=lambda: None,
):
    publication = GitHubPublication(configured, store, clock=lambda: utc_time(5))
    coordinator = PilotCoordinator(
        configured,
        store,
        source,
        workspaces,
        executor,
        validator,
        publication,
        clock=lambda: utc_time(7),
    )
    return PilotPhases(
        configured,
        store,
        coordinator,
        workspaces,
        publication,
        external,
        loader,
        job_id="pilot-job-1",
        issue_number=1,
        provider_preflight=preflight,
    )


class PilotPhasesTests(unittest.TestCase):
    def test_runtime_roots_reject_a_symlinked_parent_into_control(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            control = root / "control"
            source = root / "source"
            control.mkdir()
            source.mkdir()
            alias = root / "control-alias"
            alias.symlink_to(control, target_is_directory=True)
            config = SimpleNamespace(
                source_repository=source,
                state_root=root / "state",
                workspace_root=alias / "workspaces",
                validation_root=root / "validation",
            )

            with self.assertRaisesRegex(LivePilotError, "runtime_path_boundary"):
                _validate_roots(config, control)

    def test_three_process_phases_use_distinct_grants_and_replay_zero_writes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            state_root = root / "state"
            control = Path(__file__).resolve().parents[2]
            configured = profile()
            issue = issue_snapshot(
                profile_digest=configured.profile_digest,
                base_sha=configured.base_sha,
                base_tree=configured.base_tree,
            )
            self.assertEqual(issue.acceptance_ids, LIVE_ACCEPTANCE_IDS)
            candidate = candidate_change(issue)
            workspace = PreparedWorkspace(
                root / "writer",
                root / "writer/app",
                root / "writer/control.git",
                issue.base_sha,
                issue.base_tree,
                candidate.workspace_digest,
                True,
                True,
            )
            source = FakeIssueSource(issue)
            workspaces = RecoverableFakeWorkspaces(workspace)
            external = FakeGitHubTransport(issue, configured.base_sha)
            loader = StaticAuthorityLoader()

            store = PilotStore(state_root, control_repository=control, clock=lambda: utc_time(0))
            executor = FakeExecutor(store, candidate)
            validator = FakeValidator(configured, store, issue, candidate)
            first = phases(store, configured, source, workspaces, executor, validator, external, loader)
            prepared = first.prepare()
            self.assertEqual(prepared["state"], "gate_passed")
            self.assertFalse(prepared["external_effect"])
            branch_resource = prepared["branch_request"]["resource"]
            store.close()

            store = PilotStore(state_root, control_repository=control, clock=lambda: utc_time(1))
            second = phases(store, configured, source, workspaces, FakeExecutor(store, candidate), FakeValidator(configured, store, issue, candidate), external, loader)
            loader.authority = LiteralGrantAuthority(BINDING, [grant(branch_resource)], now=lambda: utc_time(0))
            pushed = second.publish_branch()
            self.assertEqual(pushed["state"], "branch_observed")
            proposal_resource = pushed["proposal_request"]["resource"]
            pushed_replay = second.publish_branch()
            self.assertFalse(pushed_replay["external_effect"])
            self.assertEqual(len(external.push_calls), 1)
            store.close()

            store = PilotStore(state_root, control_repository=control, clock=lambda: utc_time(2))
            third = phases(store, configured, source, workspaces, FakeExecutor(store, candidate), FakeValidator(configured, store, issue, candidate), external, loader)
            with self.assertRaises(AuthorityError):
                third.publish_proposal()
            self.assertEqual(len(external.create_calls), 0)
            loader.authority = LiteralGrantAuthority(BINDING, [grant(proposal_resource, proposal=True)], now=lambda: utc_time(0))
            proposed = third.publish_proposal()
            self.assertEqual(proposed["state"], "merge_gate_unavailable")
            self.assertEqual(proposed["proposal"]["pr_number"], 19)
            writes = (len(external.push_calls), len(external.create_calls))
            replay = third.publish_proposal()
            self.assertEqual(replay["state"], "merge_gate_unavailable")
            self.assertEqual((len(external.push_calls), len(external.create_calls)), writes)
            self.assertEqual((len(source.calls), len(executor.calls), len(validator.calls)), (1, 1, 1))
            self.assertEqual(writes, (1, 1))
            self.assertGreaterEqual(len(workspaces.recover_calls), 2)
            store.close()

    def test_missing_api_key_stops_before_snapshot_or_invocation_and_secret_is_not_persisted(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            control = Path(__file__).resolve().parents[2]
            configured = profile()
            issue = issue_snapshot(profile_digest=configured.profile_digest, base_sha=configured.base_sha, base_tree=configured.base_tree)
            candidate = candidate_change(issue)
            source = FakeIssueSource(issue)
            workspace = PreparedWorkspace(root / "w", root / "w/app", root / "w/git", issue.base_sha, issue.base_tree, candidate.workspace_digest, True, True)
            workspaces = RecoverableFakeWorkspaces(workspace)
            store = PilotStore(root / "state", control_repository=control)
            capability = ApiKeyCapability({})
            runtime = phases(
                store,
                configured,
                source,
                workspaces,
                FakeExecutor(store, candidate),
                FakeValidator(configured, store, issue, candidate),
                FakeGitHubTransport(issue, configured.base_sha),
                StaticAuthorityLoader(),
                preflight=capability.preflight,
            )

            with self.assertRaisesRegex(LivePilotError, "provider_credential_unavailable"):
                runtime.prepare()

            self.assertEqual(source.calls, [])
            with self.assertRaisesRegex(PilotStoreError, "not_found"):
                store.get(issue.job_id)
            secret = "secret-must" + "-never-persist"
            present = ApiKeyCapability({"CODEX_API_KEY": secret})
            present.preflight()
            self.assertEqual(present.environment(), {"CODEX_API_KEY": secret})
            state_bytes = b"".join(path.read_bytes() for path in (root / "state").glob("*") if path.is_file())
            self.assertNotIn(secret.encode("utf-8"), state_bytes)
            self.assertNotIn(secret, json.dumps({"status": "provider_ready"}))
            store.close()

    def test_in_flight_branch_restart_observes_without_a_second_push(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            control = Path(__file__).resolve().parents[2]
            state_root = root / "state"
            store = PilotStore(state_root, control_repository=control, clock=lambda: utc_time(0))
            configured, issue, candidate, workspace = gate_passed(store)
            source = FakeIssueSource(issue)
            workspaces = RecoverableFakeWorkspaces(workspace)
            external = FakeGitHubTransport(issue, configured.base_sha)
            publication = GitHubPublication(configured, store, clock=lambda: utc_time(5))
            request = publication.branch_request(issue.job_id)
            loader = StaticAuthorityLoader()
            loader.authority = LiteralGrantAuthority(BINDING, [grant(request.resource)], now=lambda: utc_time(0))
            runtime = phases(store, configured, source, workspaces, FakeExecutor(store, candidate), FakeValidator(configured, store, issue, candidate), external, loader)
            external.hard_crash_push = True
            with self.assertRaises(KeyboardInterrupt):
                runtime.publish_branch()
            self.assertEqual(len(external.push_calls), 1)
            store.close()

            external.hard_crash_push = False
            reopened = PilotStore(state_root, control_repository=control, clock=lambda: utc_time(1))
            loader.authority = LiteralGrantAuthority(BINDING, [], now=lambda: utc_time(0))
            recovered = phases(reopened, configured, source, workspaces, FakeExecutor(reopened, candidate), FakeValidator(configured, reopened, issue, candidate), external, loader)

            result = recovered.publish_branch()

            self.assertEqual(result["push_receipt"]["outcome"], "reconciled_exact")
            self.assertEqual(len(external.push_calls), 1)
            reopened.close()


if __name__ == "__main__":
    unittest.main()
