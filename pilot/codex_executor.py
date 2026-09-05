"""Pinned one-start Codex supervisor; GitHub authority never enters this port."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import selectors
import signal
import socket
import stat
import subprocess
import tempfile
import time
from typing import Any, Protocol

from .contracts import CandidateChangeV1, ContractError, IssueSnapshotV1, canonical_json, contract_digest
from .profile import CODEX_OUTPUT_SCHEMA, CODEX_PERMISSION_PROFILE, CODEX_PROMPT, PilotProfileV1
from .store import PilotStore, PilotStoreError
from .workspace import PreparedWorkspace


class CodexExecutionError(RuntimeError):
    pass


def confined_configuration(executable: str) -> tuple[str, ...]:
    # Replace the complete profile map rather than inheriting operator entries.
    # The exact binary exception permits sandbox re-exec, not its parent directory.
    config = (
        'permissions={pilot_confined={extends=":workspace",filesystem={'
        '":root"="deny",":minimal"="read",":tmpdir"="deny",":slash_tmp"="deny",'
        + json.dumps(executable) + '="read"},network={enabled=false}}}'
    )
    return ('-c', config, '-c', 'default_permissions="pilot_confined"')


@dataclass(frozen=True)
class ProcessResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    started_at: str
    completed_at: str


@dataclass(frozen=True)
class SandboxProof:
    profile_digest: str
    workspace_digest: str
    launcher_digest: str
    inside_write: bool
    outside_write_denied: bool
    outside_read_denied: bool
    network_denied: bool
    unix_socket_denied: bool
    git_write_denied: bool
    credentials_absent: bool
    status: str
    reason_code: str | None
    observed_at: str
    evidence_digest: str

    @classmethod
    def passed(cls, *, profile_digest: str, workspace_digest: str, launcher_digest: str, observed_at: str) -> "SandboxProof":
        return cls._build(
            profile_digest=profile_digest,
            workspace_digest=workspace_digest,
            launcher_digest=launcher_digest,
            inside_write=True,
            outside_write_denied=True,
            outside_read_denied=True,
            network_denied=True,
            unix_socket_denied=True,
            git_write_denied=True,
            credentials_absent=True,
            status="pass",
            reason_code=None,
            observed_at=observed_at,
        )

    @classmethod
    def failed(cls, *, profile_digest: str, workspace_digest: str, launcher_digest: str, reason_code: str, observed_at: str) -> "SandboxProof":
        return cls._build(
            profile_digest=profile_digest,
            workspace_digest=workspace_digest,
            launcher_digest=launcher_digest,
            inside_write=False,
            outside_write_denied=False,
            outside_read_denied=False,
            network_denied=False,
            unix_socket_denied=False,
            git_write_denied=False,
            credentials_absent=False,
            status="fail",
            reason_code=reason_code,
            observed_at=observed_at,
        )

    @classmethod
    def _build(cls, **facts) -> "SandboxProof":
        digest = contract_digest("sandbox-proof", facts)
        return cls(**facts, evidence_digest=digest)

    def validate(self) -> None:
        facts = {
            key: value
            for key, value in self.__dict__.items()
            if key != "evidence_digest"
        }
        if contract_digest("sandbox-proof", facts) != self.evidence_digest:
            raise CodexExecutionError("sandbox_proof_digest")
        checks = (
            self.inside_write,
            self.outside_write_denied,
            self.outside_read_denied,
            self.network_denied,
            self.unix_socket_denied,
            self.git_write_denied,
            self.credentials_absent,
        )
        if self.status == "pass" and (not all(checks) or self.reason_code is not None):
            raise CodexExecutionError("sandbox_proof_invalid")
        if self.status == "fail" and not self.reason_code:
            raise CodexExecutionError("sandbox_proof_invalid")


class SandboxProbe(Protocol):
    def prove(self, workspace: PreparedWorkspace) -> SandboxProof: ...


class ProcessRunner(Protocol):
    def run(
        self,
        *,
        argv: tuple[str, ...],
        cwd: Path,
        environment: Mapping[str, str],
        stdin: bytes,
        timeout_seconds: int,
        max_output_bytes: int,
    ) -> ProcessResult: ...


class CandidateWorkspace(Protocol):
    def seal(self, workspace: PreparedWorkspace, issue: IssueSnapshotV1, **facts) -> CandidateChangeV1: ...


class CodexExecutor:
    def __init__(
        self,
        profile: PilotProfileV1,
        store: PilotStore,
        workspaces: CandidateWorkspace,
        *,
        probe: SandboxProbe,
        runner: ProcessRunner,
        output_schema_path: Path,
    ) -> None:
        self._profile = profile
        self._store = store
        self._workspaces = workspaces
        self._probe = probe
        self._runner = runner
        self._output_schema_path = Path(output_schema_path)

    def run(self, issue: IssueSnapshotV1, workspace: PreparedWorkspace, *, command_key: str) -> CandidateChangeV1:
        current = self._store.get(issue.job_id)
        if current.state != "workspace_ready" or current.snapshot != issue:
            raise CodexExecutionError("invalid_state")
        if (
            issue.profile_digest != self._profile.profile_digest
            or workspace.base_sha != issue.base_sha
            or workspace.base_tree != issue.base_tree
            or workspace.workspace_digest != current.workspace_digest
            or not workspace.remote_removed
            or not workspace.object_storage_independent
        ):
            raise CodexExecutionError("binding_mismatch")
        proof = self._probe.prove(workspace)
        proof.validate()
        if (
            proof.profile_digest != self._profile.profile_digest
            or proof.workspace_digest != workspace.workspace_digest
            or proof.status != "pass"
        ):
            self._terminal(issue.job_id, "sandbox_unavailable")
            raise CodexExecutionError("sandbox_unavailable")
        self._verify_executable(self._profile.codex_executable, self._profile.codex_sha256)
        self._verify_output_schema()
        supervisor_home = workspace.root / "supervisor-home"
        codex_home = workspace.root / "codex-home"
        for directory in (supervisor_home, codex_home):
            directory.mkdir(mode=0o700, exist_ok=False)
        argv = self._argv(workspace)
        environment = {
            "HOME": str(supervisor_home),
            "CODEX_HOME": str(codex_home),
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C.UTF-8",
            "TZ": "UTC",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "/bin/false",
            "SSH_ASKPASS": "/bin/false",
        }
        stdin = CODEX_PROMPT.encode("utf-8") + b"\n\nUntrusted issue snapshot JSON:\n" + canonical_json(issue.to_dict()) + b"\n"
        try:
            self._store.begin_invocation(issue.job_id, command_key=command_key)
        except PilotStoreError as exc:
            raise CodexExecutionError("attempt_consumed") from exc
        try:
            result = self._runner.run(
                argv=argv,
                cwd=workspace.worktree,
                environment=environment,
                stdin=stdin,
                timeout_seconds=self._profile.codex_timeout_seconds,
                max_output_bytes=self._profile.max_output_bytes,
            )
            self._validate_result(result)
            candidate = self._workspaces.seal(
                workspace,
                issue,
                sandbox_evidence_digest=proof.evidence_digest,
                model_id=self._profile.model_id,
                executable_version=self._profile.codex_version,
                executable_sha256=self._profile.codex_sha256,
                prompt_digest=self._profile.prompt_digest,
                tool_policy_digest=self._profile.tool_policy_digest,
                output_schema_digest=self._profile.output_schema_digest,
                started_at=result.started_at,
                completed_at=result.completed_at,
            )
            self._validate_candidate(candidate, issue, workspace, proof)
            self._store.store_candidate(issue.job_id, candidate)
            return candidate
        except BaseException as exc:
            self._terminal(issue.job_id, "model_outcome_ambiguous")
            if isinstance(exc, CodexExecutionError):
                raise
            raise CodexExecutionError("model_outcome_ambiguous") from exc

    def _argv(self, workspace: PreparedWorkspace) -> tuple[str, ...]:
        if self._profile.provider_mode == "app_server_chatgpt":
            return (
                self._profile.codex_executable,
                *confined_configuration(self._profile.codex_executable),
                "-c", "mcp_servers={}",
                "-c", 'web_search="disabled"',
                "-c", 'shell_environment_policy.inherit="none"',
                "-c", "shell_environment_policy.ignore_default_excludes=false",
                "app-server",
                "--stdio",
                "--strict-config",
            )
        return (
            self._profile.codex_executable,
            "-a", "never",
            *confined_configuration(self._profile.codex_executable),
            "-P", CODEX_PERMISSION_PROFILE,
            "exec",
            "--strict-config",
            "--ignore-user-config",
            "--ignore-rules",
            "--ephemeral",
            "-C", str(workspace.worktree),
            "--model", self._profile.model_id,
            "-c", "sandbox_workspace_write.network_access=false",
            "-c", "sandbox_workspace_write.exclude_slash_tmp=true",
            "-c", "sandbox_workspace_write.exclude_tmpdir_env_var=true",
            "-c", 'web_search="disabled"',
            "-c", 'shell_environment_policy.inherit="none"',
            "-c", "shell_environment_policy.ignore_default_excludes=false",
            "--json",
            "--output-schema", str(self._output_schema_path),
            "-",
        )

    def _verify_output_schema(self) -> None:
        expected = canonical_json(CODEX_OUTPUT_SCHEMA)
        try:
            metadata = self._output_schema_path.lstat()
            body = self._output_schema_path.read_bytes()
        except OSError as exc:
            raise CodexExecutionError("output_schema_unavailable") from exc
        if (
            not self._output_schema_path.is_absolute()
            or not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or body != expected
            or hashlib.sha256(body).hexdigest() != self._profile.output_schema_digest
        ):
            raise CodexExecutionError("output_schema_mismatch")

    @staticmethod
    def _verify_executable(path: str, digest: str) -> None:
        target = Path(path)
        try:
            metadata = target.lstat()
            body_digest = _sha256_file(target)
        except OSError as exc:
            raise CodexExecutionError("executable_unavailable") from exc
        if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode) or metadata.st_mode & 0o111 == 0 or body_digest != digest:
            raise CodexExecutionError("executable_mismatch")

    def _validate_result(self, result: ProcessResult) -> None:
        if type(result.returncode) is not int or not isinstance(result.stdout, bytes) or not isinstance(result.stderr, bytes):
            raise CodexExecutionError("provider_result")
        if len(result.stdout) + len(result.stderr) > self._profile.max_output_bytes:
            raise CodexExecutionError("provider_output_limit")
        if result.returncode != 0:
            raise CodexExecutionError("provider_nonzero")
        terminals = 0
        try:
            for raw in result.stdout.splitlines():
                event = json.loads(raw)
                if not isinstance(event, dict) or not isinstance(event.get("type"), str):
                    raise ValueError
                if event["type"] == "turn.completed":
                    terminals += 1
                if event["type"] in {"error", "turn.failed"}:
                    raise CodexExecutionError("provider_failed")
        except (UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise CodexExecutionError("provider_stream") from exc
        if terminals != 1:
            raise CodexExecutionError("provider_terminal")

    def _validate_candidate(self, candidate: CandidateChangeV1, issue: IssueSnapshotV1, workspace: PreparedWorkspace, proof: SandboxProof) -> None:
        try:
            candidate = CandidateChangeV1.from_dict(candidate.to_dict())
        except ContractError as exc:
            raise CodexExecutionError("candidate_contract") from exc
        if (
            candidate.job_id != issue.job_id
            or candidate.profile_digest != self._profile.profile_digest
            or candidate.issue_snapshot_digest != issue.issue_snapshot_digest
            or (candidate.base_sha, candidate.base_tree) != (issue.base_sha, issue.base_tree)
            or candidate.workspace_digest != workspace.workspace_digest
            or candidate.sandbox_evidence_digest != proof.evidence_digest
            or candidate.model_id != self._profile.model_id
            or candidate.executable_version != self._profile.codex_version
            or candidate.executable_sha256 != self._profile.codex_sha256
            or candidate.prompt_digest != self._profile.prompt_digest
            or candidate.tool_policy_digest != self._profile.tool_policy_digest
            or candidate.output_schema_digest != self._profile.output_schema_digest
            or any(item.path not in self._profile.allowed_write_paths for item in candidate.changed_files)
            or candidate.diff_bytes > self._profile.max_diff_bytes
        ):
            raise CodexExecutionError("candidate_binding")

    def _terminal(self, job_id: str, reason_code: str) -> None:
        try:
            if self._store.get(job_id).state not in {"needs_human", "rejected"}:
                self._store.mark_terminal(job_id, reason_code=reason_code)
        except PilotStoreError:
            pass


class SubprocessCodexRunner:
    """Process adapter; credential bytes are provided only at effect time."""

    def __init__(self, credential_environment: Callable[[], Mapping[str, str]] | None = None, *, clock=None) -> None:
        self._credential_environment = credential_environment or (lambda: {})
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def run(self, *, argv: tuple[str, ...], cwd: Path, environment: Mapping[str, str], stdin: bytes, timeout_seconds: int, max_output_bytes: int) -> ProcessResult:
        credentials = dict(self._credential_environment())
        if set(credentials) - {"CODEX_API_KEY"} or any(not isinstance(value, str) or not value for value in credentials.values()):
            raise CodexExecutionError("credential_handle")
        started = _utc(self._clock())
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            try:
                process = subprocess.Popen(
                    argv,
                    cwd=cwd,
                    env={**dict(environment), **credentials},
                    stdin=subprocess.PIPE,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    shell=False,
                    close_fds=True,
                    start_new_session=True,
                )
                process.communicate(input=stdin, timeout=timeout_seconds)
            except subprocess.TimeoutExpired as exc:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except OSError:
                    pass
                process.wait()
                raise CodexExecutionError("provider_timeout") from exc
            except OSError as exc:
                raise CodexExecutionError("provider_start") from exc
            completed = _utc(self._clock())
            if stdout_file.tell() + stderr_file.tell() > max_output_bytes:
                raise CodexExecutionError("provider_output_limit")
            stdout_file.seek(0)
            stderr_file.seek(0)
            return ProcessResult(process.returncode, stdout_file.read(), stderr_file.read(), started, completed)


class JsonRpcSession(Protocol):
    def send(self, message: dict[str, Any]) -> None: ...

    def receive(self, timeout_seconds: float) -> dict[str, Any]: ...

    def close(self) -> None: ...


class StdioJsonRpcSession:
    """Bounded JSON-lines session for one local Codex app-server process."""

    def __init__(
        self,
        *,
        argv: tuple[str, ...],
        cwd: Path,
        environment: Mapping[str, str],
        max_output_bytes: int,
    ) -> None:
        self._stderr = tempfile.TemporaryFile()
        try:
            self._process = subprocess.Popen(
                argv,
                cwd=cwd,
                env=dict(environment),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=self._stderr,
                shell=False,
                close_fds=True,
                start_new_session=True,
                bufsize=0,
            )
        except OSError as exc:
            self._stderr.close()
            raise CodexExecutionError("provider_start") from exc
        if self._process.stdin is None or self._process.stdout is None:
            self.close()
            raise CodexExecutionError("provider_start")
        self._selector = selectors.DefaultSelector()
        self._selector.register(self._process.stdout, selectors.EVENT_READ)
        self._buffer = bytearray()
        self._observed_bytes = 0
        self._max_output_bytes = max_output_bytes
        self._closed = False

    def send(self, message: dict[str, Any]) -> None:
        raw = canonical_json(message) + b"\n"
        if len(raw) > 262_144:
            raise CodexExecutionError("provider_protocol")
        try:
            assert self._process.stdin is not None
            self._process.stdin.write(raw)
            self._process.stdin.flush()
        except (OSError, BrokenPipeError) as exc:
            raise CodexExecutionError("provider_protocol") from exc

    def receive(self, timeout_seconds: float) -> dict[str, Any]:
        deadline = time.monotonic() + max(timeout_seconds, 0.0)
        while b"\n" not in self._buffer:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            events = self._selector.select(remaining)
            if not events:
                raise TimeoutError
            assert self._process.stdout is not None
            chunk = os.read(self._process.stdout.fileno(), 65_536)
            if not chunk:
                raise CodexExecutionError("provider_protocol")
            self._observed_bytes += len(chunk)
            self._stderr.flush()
            if self._observed_bytes + self._stderr.tell() > self._max_output_bytes:
                raise CodexExecutionError("provider_output_limit")
            self._buffer.extend(chunk)
        raw, _, remainder = self._buffer.partition(b"\n")
        self._buffer = bytearray(remainder)
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise CodexExecutionError("provider_protocol") from exc
        if not isinstance(value, dict):
            raise CodexExecutionError("provider_protocol")
        return value

    def close(self) -> None:
        if getattr(self, "_closed", False):
            return
        self._closed = True
        process = getattr(self, "_process", None)
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except OSError:
                pass
            try:
                process.wait(timeout=5)
            except (OSError, subprocess.TimeoutExpired):
                pass
        selector = getattr(self, "_selector", None)
        if selector is not None:
            selector.close()
        if process is not None:
            if process.stdin is not None:
                process.stdin.close()
            if process.stdout is not None:
                process.stdout.close()
        stderr = getattr(self, "_stderr", None)
        if stderr is not None:
            stderr.close()


class AppServerCodexRunner:
    """Run one ephemeral, no-request Codex app-server thread and turn."""

    def __init__(
        self,
        profile: PilotProfileV1,
        *,
        session_factory: Callable[..., JsonRpcSession] | None = None,
        auth_environment: Callable[[], Mapping[str, str]] | None = None,
        clock=None,
    ) -> None:
        if profile.provider_mode != "app_server_chatgpt":
            raise CodexExecutionError("provider_mode")
        self._profile = profile
        self._session_factory = session_factory or (
            lambda **values: StdioJsonRpcSession(**values)
        )
        self._auth_environment = auth_environment or (lambda: {})
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def run(
        self,
        *,
        argv: tuple[str, ...],
        cwd: Path,
        environment: Mapping[str, str],
        stdin: bytes,
        timeout_seconds: int,
        max_output_bytes: int,
    ) -> ProcessResult:
        expected_argv = (
            self._profile.codex_executable,
            *confined_configuration(self._profile.codex_executable),
            "-c", "mcp_servers={}",
            "-c", 'web_search="disabled"',
            "-c", 'shell_environment_policy.inherit="none"',
            "-c", "shell_environment_policy.ignore_default_excludes=false",
            "app-server",
            "--stdio",
            "--strict-config",
        )
        if argv != expected_argv or not cwd.is_absolute() or len(stdin) > max_output_bytes:
            raise CodexExecutionError("provider_binding")
        try:
            prompt = stdin.decode("utf-8")
        except UnicodeError as exc:
            raise CodexExecutionError("provider_input") from exc
        auth = _chatgpt_auth_environment(self._auth_environment())
        child_environment = {
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C.UTF-8",
            "TZ": "UTC",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "/bin/false",
            "SSH_ASKPASS": "/bin/false",
            **auth,
        }
        started_at = _utc(self._clock())
        deadline = time.monotonic() + timeout_seconds
        session = self._session_factory(
            argv=argv,
            cwd=cwd,
            environment=child_environment,
            max_output_bytes=max_output_bytes,
        )
        try:
            session.send(
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "clientInfo": {"name": "adaptive-pilot", "version": "2.0.15"},
                        "capabilities": {"experimentalApi": True},
                    },
                }
            )
            _response(session, 1, deadline)
            session.send({"jsonrpc": "2.0", "method": "initialized", "params": {}})
            session.send(
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "thread/start",
                    "params": {
                        "cwd": str(cwd),
                        "model": self._profile.model_id,
                        "approvalPolicy": "never",
                        "permissions": CODEX_PERMISSION_PROFILE,
                        "ephemeral": True,
                        "dynamicTools": [],
                        "runtimeWorkspaceRoots": [str(cwd)],
                    },
                }
            )
            thread_result = _response(session, 2, deadline)
            thread = thread_result.get("thread")
            thread_id = thread.get("id") if isinstance(thread, dict) else None
            permission = thread_result.get("activePermissionProfile")
            sandbox = thread_result.get("sandbox")
            if (
                not isinstance(thread_id, str)
                or not thread_id
                or thread_result.get("model") != self._profile.model_id
                or thread_result.get("modelProvider") != "openai"
                or thread_result.get("cwd") != str(cwd)
                or thread_result.get("runtimeWorkspaceRoots") != [str(cwd)]
                or thread_result.get("approvalPolicy") != "never"
                or not isinstance(permission, dict)
                or permission.get("id") != CODEX_PERMISSION_PROFILE
                or permission.get("extends") != ":workspace"
                or not isinstance(sandbox, dict)
                or sandbox.get("type") != "workspaceWrite"
                or sandbox.get("networkAccess") is not False
                or sandbox.get("writableRoots") != []
                or sandbox.get("excludeTmpdirEnvVar") is not True
                or sandbox.get("excludeSlashTmp") is not True
                or thread_result.get("instructionSources") != []
            ):
                raise CodexExecutionError("provider_confinement")
            session.send(
                {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "turn/start",
                    "params": {
                        "threadId": thread_id,
                        "input": [{"type": "text", "text": prompt}],
                        "outputSchema": CODEX_OUTPUT_SCHEMA,
                    },
                }
            )
            turn_result = _response(session, 3, deadline)
            turn = turn_result.get("turn")
            turn_id = turn.get("id") if isinstance(turn, dict) else None
            if not isinstance(turn_id, str) or not turn_id:
                raise CodexExecutionError("provider_protocol")
            _terminal(session, thread_id, turn_id, deadline)
            return ProcessResult(
                0,
                b'{"type":"turn.completed"}\n',
                b"",
                started_at,
                _utc(self._clock()),
            )
        except TimeoutError as exc:
            raise CodexExecutionError("provider_timeout") from exc
        finally:
            session.close()


def _response(session: JsonRpcSession, request_id: int, deadline: float) -> dict[str, Any]:
    for _ in range(4096):
        message = session.receive(deadline - time.monotonic())
        if "id" not in message:
            continue
        if "method" in message:
            raise CodexExecutionError("provider_request_denied")
        if message.get("jsonrpc") != "2.0" or message.get("id") != request_id:
            raise CodexExecutionError("provider_protocol")
        if message.get("error") is not None or not isinstance(message.get("result"), dict):
            raise CodexExecutionError("provider_failed")
        return message["result"]
    raise CodexExecutionError("provider_message_limit")


def _terminal(
    session: JsonRpcSession, thread_id: str, turn_id: str, deadline: float
) -> None:
    for _ in range(4096):
        message = session.receive(deadline - time.monotonic())
        if "id" in message:
            raise CodexExecutionError("provider_request_denied")
        method = message.get("method")
        if method in {"turn/failed", "error"}:
            raise CodexExecutionError("provider_failed")
        if method != "turn/completed":
            continue
        params = message.get("params")
        turn = params.get("turn") if isinstance(params, dict) else None
        if (
            not isinstance(turn, dict)
            or message.get("jsonrpc") != "2.0"
            or params.get("threadId") != thread_id
            or turn.get("id") != turn_id
            or turn.get("status") != "completed"
            or turn.get("error") is not None
            or not isinstance(turn.get("items"), list)
        ):
            raise CodexExecutionError("provider_terminal")
        return
    raise CodexExecutionError("provider_message_limit")


def _chatgpt_auth_environment(value: Mapping[str, str]) -> dict[str, str]:
    environment = dict(value)
    if set(environment) - {"HOME", "CODEX_HOME"} or "HOME" not in environment:
        raise CodexExecutionError("provider_credential_unavailable")
    if any(
        not isinstance(item, str)
        or not item
        or not Path(item).is_absolute()
        or "\x00" in item
        for item in environment.values()
    ):
        raise CodexExecutionError("provider_credential_unavailable")
    return environment


class CodexSandboxProbe:
    """No-model confinement probe using the installed Codex sandbox helper."""

    _SCRIPT = r'''import os, socket, sys
inside, outside, git_head, socket_path, abstract_name, *read_paths = sys.argv[1:]
with open(inside, "xb") as stream:
    stream.write(b"inside")
os.unlink(inside)
outside_denied = False
try:
    with open(outside, "xb") as stream:
        stream.write(b"escape")
except OSError:
    outside_denied = not os.path.exists(outside)
git_denied = False
try:
    descriptor = os.open(git_head, os.O_WRONLY)
except OSError:
    git_denied = True
else:
    os.close(descriptor)
network_denied = False
try:
    candidate = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
except OSError:
    network_denied = True
else:
    candidate.close()
credentials_absent = not any(key in os.environ for key in ("CODEX_API_KEY", "GH_TOKEN", "GITHUB_TOKEN"))
def read_denied(path):
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return True
    else:
        os.close(descriptor)
        return False
def socket_denied(address):
    candidate = None
    try:
        candidate = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        candidate.settimeout(1)
        candidate.connect(address)
    except OSError:
        return True
    else:
        return False
    finally:
        if candidate is not None:
            candidate.close()
outside_reads_denied = all(read_denied(path) for path in (git_head, *read_paths))
unix_denied = all(socket_denied(address) for address in (socket_path, '\0' + abstract_name))
if all((outside_denied, git_denied, network_denied, credentials_absent, outside_reads_denied, unix_denied)):
    print("adaptive-pilot-sandbox-proof-v2")
else:
    raise SystemExit(91)
'''

    def __init__(self, profile: PilotProfileV1, *, clock=None) -> None:
        self._profile = profile
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def prove(self, workspace: PreparedWorkspace) -> SandboxProof:
        configuration = confined_configuration(self._profile.codex_executable)
        launcher_digest = hashlib.sha256(canonical_json({
            'script': self._SCRIPT,
            'configuration': list(configuration),
            'permission_profile': CODEX_PERMISSION_PROFILE,
            'codex_sha256': self._profile.codex_sha256,
            'python_sha256': self._profile.python_sha256,
        })).hexdigest()
        outside = workspace.root / "outside-sentinel"
        inside = workspace.worktree / ".pilot-sandbox-probe"
        if outside.exists() or inside.exists():
            return SandboxProof.failed(profile_digest=self._profile.profile_digest, workspace_digest=workspace.workspace_digest, launcher_digest=launcher_digest, reason_code="sentinel_exists", observed_at=_utc(self._clock()))
        completed = None
        try:
            CodexExecutor._verify_executable(self._profile.codex_executable, self._profile.codex_sha256)
            CodexExecutor._verify_executable(self._profile.python_executable, self._profile.python_sha256)
            with tempfile.TemporaryDirectory(prefix='pilot-proof-') as raw:
                probe_root = Path(raw)
                environment = {
                    "HOME": str(probe_root / 'operator-home'),
                    "CODEX_HOME": str(probe_root / 'provider-home'),
                    "PATH": "/usr/bin:/bin", "LC_ALL": "C.UTF-8", "TZ": "UTC",
                }
                read_paths = []
                for name in ('operator-home', 'provider-home', 'publisher-home', 'sibling-repo'):
                    directory = probe_root / name
                    directory.mkdir(mode=0o700)
                    sentinel = directory / 'benign-sentinel'
                    sentinel.write_bytes(b'public synthetic sandbox probe')
                    read_paths.append(str(sentinel))
                control_marker = Path(__file__).resolve().parents[1] / 'AGENTS.md'
                if control_marker.is_file():
                    read_paths.append(str(control_marker))
                socket_path = str(probe_root / 'daemon.sock')
                abstract_name = probe_root.name
                with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as filesystem_socket, socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as abstract_socket:
                    filesystem_socket.bind(socket_path)
                    filesystem_socket.listen(1)
                    abstract_socket.bind('\0' + abstract_name)
                    abstract_socket.listen(1)
                    argv = (
                        self._profile.codex_executable, "sandbox", *configuration,
                        "-P", CODEX_PERMISSION_PROFILE, "-C", str(workspace.worktree), "--",
                        self._profile.python_executable, "-c", self._SCRIPT,
                        str(inside), str(outside), str(workspace.git_dir / "HEAD"),
                        socket_path, abstract_name, *read_paths,
                    )
                    completed = subprocess.run(argv, cwd=workspace.worktree, env=environment, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired, CodexExecutionError):
            pass
        passed = (
            completed is not None
            and completed.returncode == 0
            and completed.stdout == b"adaptive-pilot-sandbox-proof-v2\n"
            and len(completed.stderr) <= 4096
            and not outside.exists()
            and not inside.exists()
        )
        observed = _utc(self._clock())
        if passed:
            return SandboxProof.passed(profile_digest=self._profile.profile_digest, workspace_digest=workspace.workspace_digest, launcher_digest=launcher_digest, observed_at=observed)
        return SandboxProof.failed(profile_digest=self._profile.profile_digest, workspace_digest=workspace.workspace_digest, launcher_digest=launcher_digest, reason_code="sandbox_probe_failed", observed_at=observed)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65_536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _utc(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise CodexExecutionError("clock")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
