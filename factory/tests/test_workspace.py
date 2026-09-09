import unittest
from unittest.mock import patch

import psycopg

from adaptive_factory.store import PostgresArtifactAttestationStore
from adaptive_factory.workspace import (
    ArtifactAttestationRequest,
    ArtifactAttestationUnavailable,
    ArtifactAttestationV1,
    FakeGitBroker,
    FakeWorkspaceBroker,
    HostIsolationReport,
    WorkspaceSnapshotUnavailable,
    WorkspaceSnapshotV1,
    WorkspaceError,
    WorkspaceHandle,
    WorkspacePolicy,
    WorkspaceReleaseOutcome,
)


def handle(task="task-001", run="run-001"):
    return WorkspaceHandle(task, run, "workspace:" + "a" * 64)


def policy():
    return WorkspacePolicy(
        allowed_paths=("factory/src", "factory/tests"),
        allowed_operations=("read", "write"),
        environment_names=("LANG", "PATH"),
        network_destinations=(),
    )


class WorkspaceTests(unittest.TestCase):
    def test_artifact_attestor_database_errors_are_typed_and_fixed_reason(self):
        store = PostgresArtifactAttestationStore("postgresql://fixture.invalid/factory")
        with patch.object(
            store, "_connect", side_effect=psycopg.OperationalError("fixture failure"),
        ):
            result = store.record_artifact_attestation(object())
        self.assertEqual(
            (result.status, result.disposition, result.reason),
            (
                "unavailable", "needs_human",
                "trusted_artifact_attestation_unavailable",
            ),
        )

    def test_fake_workspace_allows_only_bound_relative_paths(self):
        broker = FakeWorkspaceBroker()
        broker.register(handle(), policy())
        decision = broker.authorize(handle(), operation="write", path="factory/src/a.py")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.code, "allowed")

    def test_fake_workspace_release_is_idempotent_and_revokes_every_operation(self):
        broker = FakeWorkspaceBroker()
        broker.register(handle(), policy())
        git = FakeGitBroker(broker)
        self.assertEqual(
            broker.release(handle(), timeout_seconds=5),
            WorkspaceReleaseOutcome("released"),
        )
        self.assertEqual(
            broker.release(handle(), timeout_seconds=5),
            WorkspaceReleaseOutcome("already_absent"),
        )
        operations = (
            lambda: broker.authorize(handle(), operation="read", path="factory/src/a.py"),
            lambda: broker.sanitize_environment(handle(), {"LANG": "C.UTF-8"}),
            lambda: git.perform(handle(), "status"),
        )
        for operation in operations:
            with self.subTest(operation=operation), self.assertRaisesRegex(
                WorkspaceError, "unknown_workspace",
            ):
                operation()

    def test_traversal_absolute_git_symlink_and_cross_task_are_denied(self):
        broker = FakeWorkspaceBroker(symlinks=("factory/src/link",))
        broker.register(handle(), policy())
        cases = [
            (handle(), "../outside", "path_escape"),
            (handle(), "/tmp/outside", "path_escape"),
            (handle(), ".git/config", "git_boundary"),
            (handle(), "factory/src/link/secret", "symlink_boundary"),
            (handle(task="other"), "factory/src/a.py", "unknown_workspace"),
        ]
        for workspace, path, code in cases:
            with self.subTest(code=code), self.assertRaisesRegex(WorkspaceError, code):
                broker.authorize(workspace, operation="read", path=path)

    def test_environment_is_allowlisted_and_credential_names_are_removed(self):
        broker = FakeWorkspaceBroker()
        broker.register(handle(), policy())
        sanitized = broker.sanitize_environment(handle(), {"LANG": "C.UTF-8", "PATH": "/usr/bin", "OPENAI_API_KEY": "secret", "TRUST_CI_KEY": "secret", "HOME": "/private"})
        self.assertEqual(sanitized, {"LANG": "C.UTF-8", "PATH": "/usr/bin"})

    def test_network_and_external_git_operations_are_absent(self):
        broker = FakeWorkspaceBroker()
        broker.register(handle(), policy())
        with self.assertRaisesRegex(WorkspaceError, "network_forbidden"):
            broker.authorize(handle(), operation="network", network_destination="https://example.test")
        git = FakeGitBroker(broker)
        self.assertEqual(git.perform(handle(), "status").code, "allowed")
        for operation in ("push", "fetch", "remote", "pr", "merge", "tag"):
            with self.subTest(operation=operation), self.assertRaisesRegex(WorkspaceError, "external_git_forbidden"):
                git.perform(handle(), operation)

    def test_host_isolation_report_requires_complete_rootless_toolchain(self):
        missing = HostIsolationReport.probe(lambda _name: None, lambda: (False, "EPERM"))
        self.assertEqual(missing.status, "blocked")
        self.assertIn("userns:EPERM", missing.reasons)
        self.assertIn("sandbox_launcher", missing.reasons)
        ready_tools = {"bwrap": "/usr/bin/bwrap", "newuidmap": "/usr/bin/newuidmap", "slirp4netns": "/usr/bin/slirp4netns"}
        ready = HostIsolationReport.probe(ready_tools.get, lambda: (True, "ok"))
        self.assertEqual(ready.status, "ready")
        self.assertEqual(ready.reasons, ())

    def test_trusted_workspace_snapshot_is_closed_and_binds_output_head(self):
        value = {
            "contract_version": 1,
            "repository_id": "owner/repository",
            "workspace_handle": handle().value,
            "input_head_sha": "1" * 40,
            "result_head_sha": "2" * 40,
            "diff_digest": "3" * 64,
            "diff_lines": 12,
            "source": "trusted_git_broker",
        }
        first = WorkspaceSnapshotV1.from_facts(value)
        changed = dict(value, result_head_sha="4" * 40)
        self.assertNotEqual(first.workspace_snapshot_digest, WorkspaceSnapshotV1.from_facts(changed).workspace_snapshot_digest)
        for invalid in (dict(value, source="provider"), dict(value, reported_head="5" * 40)):
            with self.assertRaises(WorkspaceError):
                WorkspaceSnapshotV1.from_facts(invalid)

    def test_fake_git_broker_reports_snapshot_unavailable_without_claiming_git_evidence(self):
        broker = FakeWorkspaceBroker()
        broker.register(handle(), policy())
        result = FakeGitBroker(broker).snapshot(handle(), timeout_seconds=5.0)
        self.assertIsInstance(result, WorkspaceSnapshotUnavailable)
        self.assertEqual((result.status, result.disposition), ("unavailable", "needs_human"))
        self.assertFalse(hasattr(result, "result_head_sha"))

    def test_artifact_attestation_is_closed_exact_and_content_bound(self):
        request = ArtifactAttestationRequest.from_facts({
            "task_id": "task-001", "run_id": "run-001",
            "repository_id": "owner/repository", "packet_digest": "b" * 64,
            "workspace_handle": handle().value, "producer_sequence": 1, "fence": 7,
            "author_role": "writer", "artifact_class": "report", "path": "factory/src/a.py",
            "sha256": "c" * 64, "size_bytes": 12, "media_type": "text/x-python",
        })
        for unsafe_path in (
            "factory/src/password=hunter2",
            "factory/src/ghp_secret",
            "factory/src/../outside",
            "factory/src/.git/config",
            "factory/src/" + "x" * (1025 - len("factory/src/")),
            "factory/src/\ud800",
        ):
            with self.subTest(unsafe_path=unsafe_path), self.assertRaises(WorkspaceError):
                ArtifactAttestationRequest.from_facts({
                    **request.to_dict(), "path": unsafe_path,
                })
        with self.assertRaises(WorkspaceError):
            ArtifactAttestationRequest.from_facts({
                **request.to_dict(), "author_role": [],
            })
        numeric_class = ArtifactAttestationRequest.from_facts({
            **request.to_dict(), "artifact_class": "9:patch",
        })
        self.assertEqual(numeric_class.artifact_class, "9:patch")
        value = {
            "contract_version": 1, **request.to_dict(), "source": "trusted_workspace_broker",
        }
        attestation = ArtifactAttestationV1.from_facts(value)
        self.assertEqual(request.request_digest, request.request_digest)
        self.assertNotEqual(
            request.request_digest,
            ArtifactAttestationRequest.from_facts(
                {**request.to_dict(), "sha256": "d" * 64}
            ).request_digest,
        )
        self.assertEqual(
            ArtifactAttestationV1.from_dict(attestation.to_dict()), attestation
        )
        changed = dict(value, sha256="d" * 64)
        self.assertNotEqual(
            ArtifactAttestationV1.from_facts(changed).artifact_attestation_digest,
            attestation.artifact_attestation_digest,
        )
        for invalid in (
            dict(value, source="provider"), dict(value, symlink=False),
            dict(value, contract_version=True),
        ):
            with self.subTest(invalid=invalid), self.assertRaises(WorkspaceError):
                ArtifactAttestationV1.from_facts(invalid)

    def test_fake_workspace_artifact_attestation_is_truthfully_unavailable(self):
        request = ArtifactAttestationRequest.from_facts({
            "task_id": "task-001", "run_id": "run-001",
            "repository_id": "owner/repository", "packet_digest": "b" * 64,
            "workspace_handle": handle().value, "producer_sequence": 1, "fence": 7,
            "author_role": "writer", "artifact_class": "report", "path": "factory/src/a.py",
            "sha256": "c" * 64, "size_bytes": 12, "media_type": "text/x-python",
        })
        result = FakeWorkspaceBroker().attest_artifact(request)
        self.assertIsInstance(result, ArtifactAttestationUnavailable)
        self.assertFalse(hasattr(result, "artifact_attestation_digest"))


if __name__ == "__main__":
    unittest.main()
