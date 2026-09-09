from __future__ import annotations

from collections import deque
from pathlib import Path
import unittest

from pilot.codex_executor import AppServerCodexRunner, CodexExecutionError, confined_configuration
from pilot.profile import CODEX_OUTPUT_SCHEMA, exact_landing_profile


class FakeJsonRpcSession:
    def __init__(self, incoming: list[dict]) -> None:
        self.incoming = deque(incoming)
        self.sent: list[dict] = []
        self.closed = False

    def send(self, message: dict) -> None:
        self.sent.append(message)

    def receive(self, timeout_seconds: float) -> dict:
        if timeout_seconds <= 0 or not self.incoming:
            raise TimeoutError
        return self.incoming.popleft()

    def close(self) -> None:
        self.closed = True


class SessionFactory:
    def __init__(self, session: FakeJsonRpcSession) -> None:
        self.session = session
        self.calls: list[dict] = []

    def __call__(self, **values):
        self.calls.append(values)
        return self.session


def profile():
    return exact_landing_profile(
        codex_executable="/opt/pilot/bin/codex",
        codex_sha256="a" * 64,
        codex_version="0.153.4",
        model_id="gpt-6-astra",
        python_executable="/usr/bin/python3",
        python_sha256="b" * 64,
        provider_mode="app_server_chatgpt",
    )


def successful_messages() -> list[dict]:
    return [
        {"jsonrpc": "2.0", "id": 1, "result": {"serverInfo": {"name": "codex", "version": "0.153.4"}}},
        {
            "jsonrpc": "2.0",
            "id": 2,
            "result": {
                "thread": {"id": "thread-1"},
                "model": "gpt-6-astra",
                "modelProvider": "openai",
                "activePermissionProfile": {"id": "pilot_confined", "extends": ":workspace"},
                "cwd": "/private/writer/app",
                "runtimeWorkspaceRoots": ["/private/writer/app"],
                "approvalPolicy": "never",
                "sandbox": {
                    "type": "workspaceWrite",
                    "writableRoots": [],
                    "networkAccess": False,
                    "excludeTmpdirEnvVar": True,
                    "excludeSlashTmp": True,
                },
                "instructionSources": [],
            },
        },
        {"jsonrpc": "2.0", "id": 3, "result": {"turn": {"id": "turn-1", "status": "inProgress"}}},
        {
            "jsonrpc": "2.0",
            "method": "turn/completed",
            "params": {
                "threadId": "thread-1",
                "turn": {"id": "turn-1", "status": "completed", "error": None, "items": []},
            },
        },
    ]


def app_server_argv(configured) -> tuple[str, ...]:
    return (
        configured.codex_executable,
        *confined_configuration(configured.codex_executable),
        "-c",
        "mcp_servers={}",
        "-c",
        'web_search="disabled"',
        "-c",
        'shell_environment_policy.inherit="none"',
        "-c",
        "shell_environment_policy.ignore_default_excludes=false",
        "app-server",
        "--stdio",
        "--strict-config",
    )


class AppServerCodexRunnerTests(unittest.TestCase):
    def test_broad_workspace_profile_is_rejected_before_model_turn(self) -> None:
        configured = profile()
        messages = successful_messages()
        messages[1]['result']['activePermissionProfile'] = {'id': ':workspace', 'extends': None}
        session = FakeJsonRpcSession(messages)
        runner = AppServerCodexRunner(
            configured, session_factory=SessionFactory(session),
            auth_environment=lambda: {'HOME': '/private/operator'},
        )
        with self.assertRaisesRegex(CodexExecutionError, 'provider_confinement'):
            runner.run(argv=app_server_argv(configured), cwd=Path('/private/writer/app'),
                       environment={}, stdin=b'prompt', timeout_seconds=30, max_output_bytes=65536)
        self.assertFalse(any(item.get('method') == 'turn/start' for item in session.sent))
        self.assertTrue(session.closed)

    def test_one_closed_app_server_thread_and_turn_returns_synthetic_success(self) -> None:
        configured = profile()
        session = FakeJsonRpcSession(successful_messages())
        factory = SessionFactory(session)
        runner = AppServerCodexRunner(
            configured,
            session_factory=factory,
            auth_environment=lambda: {
                "HOME": "/private/operator",
                "CODEX_HOME": "/private/operator/.codex",
            },
        )
        cwd = Path("/private/writer/app")

        result = runner.run(
            argv=app_server_argv(configured),
            cwd=cwd,
            environment={"PATH": "/usr/bin:/bin", "CODEX_HOME": "/empty"},
            stdin=b"trusted prompt plus untrusted issue",
            timeout_seconds=30,
            max_output_bytes=65_536,
        )

        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'{"type":"turn.completed"}\n')
        self.assertEqual(result.stderr, b"")
        self.assertEqual(len(factory.calls), 1)
        child_env = factory.calls[0]["environment"]
        self.assertEqual(child_env["CODEX_HOME"], "/private/operator/.codex")
        self.assertFalse(any(key.endswith("TOKEN") or key.endswith("API_KEY") for key in child_env))
        self.assertEqual(factory.calls[0]["argv"], app_server_argv(configured))
        initialize, initialized, thread, turn = session.sent
        self.assertEqual(initialize["method"], "initialize")
        self.assertIs(initialize["params"]["capabilities"]["experimentalApi"], True)
        self.assertEqual(initialized, {"jsonrpc": "2.0", "method": "initialized", "params": {}})
        self.assertEqual(
            thread["params"],
            {
                "cwd": str(cwd),
                "model": "gpt-6-astra",
                "approvalPolicy": "never",
                "permissions": "pilot_confined",
                "ephemeral": True,
                "dynamicTools": [],
                "runtimeWorkspaceRoots": [str(cwd)],
            },
        )
        self.assertEqual(turn["params"]["threadId"], "thread-1")
        self.assertEqual(turn["params"]["input"], [{"type": "text", "text": "trusted prompt plus untrusted issue"}])
        self.assertEqual(turn["params"]["outputSchema"], CODEX_OUTPUT_SCHEMA)
        self.assertTrue(session.closed)

    def test_any_server_request_is_denied_without_response(self) -> None:
        messages = successful_messages()[:3]
        messages.append(
            {
                "jsonrpc": "2.0",
                "id": 91,
                "method": "item/commandExecution/requestApproval",
                "params": {"command": "git push"},
            }
        )
        session = FakeJsonRpcSession(messages)
        configured = profile()
        runner = AppServerCodexRunner(
            configured,
            session_factory=SessionFactory(session),
            auth_environment=lambda: {"HOME": "/private/operator"},
        )

        with self.assertRaisesRegex(CodexExecutionError, "provider_request_denied"):
            runner.run(
                argv=app_server_argv(configured),
                cwd=Path("/private/writer/app"),
                environment={"PATH": "/usr/bin:/bin"},
                stdin=b"prompt",
                timeout_seconds=30,
                max_output_bytes=65_536,
            )

        self.assertEqual(len(session.sent), 4)
        self.assertTrue(session.closed)

    def test_malformed_or_non_success_terminal_fails_closed(self) -> None:
        configured = profile()
        mutations = {
            "jsonrpc": {"jsonrpc": "1.0"},
            "thread": {"params": {"threadId": "other", "turn": {"id": "turn-1", "status": "completed", "error": None, "items": []}}},
            "turn": {"params": {"threadId": "thread-1", "turn": {"id": "other", "status": "completed", "error": None, "items": []}}},
            "status": {"params": {"threadId": "thread-1", "turn": {"id": "turn-1", "status": "failed", "error": None, "items": []}}},
            "error": {"params": {"threadId": "thread-1", "turn": {"id": "turn-1", "status": "completed", "error": {"message": "denied"}, "items": []}}},
        }
        for name, replacement in mutations.items():
            messages = successful_messages()
            messages[-1] = {**messages[-1], **replacement}
            session = FakeJsonRpcSession(messages)
            runner = AppServerCodexRunner(
                configured,
                session_factory=SessionFactory(session),
                auth_environment=lambda: {"HOME": "/private/operator"},
            )
            with self.subTest(name=name), self.assertRaises(CodexExecutionError):
                runner.run(
                    argv=app_server_argv(configured),
                    cwd=Path("/private/writer/app"),
                    environment={},
                    stdin=b"prompt",
                    timeout_seconds=30,
                    max_output_bytes=65_536,
                )

    def test_wrong_response_id_or_timeout_fails_closed(self) -> None:
        configured = profile()
        for incoming in ([{"jsonrpc": "2.0", "id": 99, "result": {}}], []):
            session = FakeJsonRpcSession(list(incoming))
            runner = AppServerCodexRunner(
                configured,
                session_factory=SessionFactory(session),
                auth_environment=lambda: {"HOME": "/private/operator"},
            )
            with self.subTest(incoming=bool(incoming)), self.assertRaises(CodexExecutionError):
                runner.run(
                    argv=app_server_argv(configured),
                    cwd=Path("/private/writer/app"),
                    environment={},
                    stdin=b"prompt",
                    timeout_seconds=30,
                    max_output_bytes=65_536,
                )


if __name__ == "__main__":
    unittest.main()
