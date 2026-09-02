import unittest

from adaptive_factory.workspace import (
    FakeGitBroker,
    FakeWorkspaceBroker,
    HostIsolationReport,
    WorkspaceError,
    WorkspaceHandle,
    WorkspacePolicy,
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
    def test_fake_workspace_allows_only_bound_relative_paths(self):
        broker = FakeWorkspaceBroker()
        broker.register(handle(), policy())
        decision = broker.authorize(handle(), operation="write", path="factory/src/a.py")
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.code, "allowed")

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


if __name__ == "__main__":
    unittest.main()
