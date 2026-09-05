"""Pinned, closed GitHub command transport for the exact landing pilot."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
from typing import Any, Protocol

from .contracts import ContractError, contract_digest
from .github import (
    BranchPushRequestV1,
    ExactGitPushCommand,
    GhDraftProposalCommand,
    ProposalCreateRequestV1,
    ProposalObservation,
    PublicationError,
    PublicationObservation,
)
from .issue_source import BaseObservation, IssueObservation, issue_observation_from_github
from .profile import TARGET_GITHUB_NAME
from .workspace import PreparedWorkspace


_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_ALLOWED_AUTH_ENV = {"HOME", "GH_CONFIG_DIR", "XDG_CONFIG_HOME"}


@dataclass(frozen=True)
class CommandResult:
    returncode: int
    stdout: bytes
    stderr: bytes


class CommandRunner(Protocol):
    def run(
        self,
        *,
        argv: tuple[str, ...],
        cwd: Path,
        environment: Mapping[str, str],
        stdin: bytes,
        timeout_seconds: int,
        max_output_bytes: int,
    ) -> CommandResult: ...


class SubprocessCommandRunner:
    def run(
        self,
        *,
        argv: tuple[str, ...],
        cwd: Path,
        environment: Mapping[str, str],
        stdin: bytes,
        timeout_seconds: int,
        max_output_bytes: int,
    ) -> CommandResult:
        if len(argv) > 64 or len(stdin) > 131_072:
            raise PublicationError("command_limit")
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            try:
                completed = subprocess.run(
                    argv,
                    cwd=cwd,
                    env=dict(environment),
                    input=stdin,
                    stdout=stdout_file,
                    stderr=stderr_file,
                    timeout=timeout_seconds,
                    check=False,
                    shell=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise PublicationError("github_command") from exc
            size = stdout_file.tell() + stderr_file.tell()
            if size > max_output_bytes:
                raise PublicationError("github_output_limit")
            stdout_file.seek(0)
            stderr_file.seek(0)
            return CommandResult(completed.returncode, stdout_file.read(), stderr_file.read())


class PinnedGitHubTransport:
    """Expose only the reads and two writes needed by the exact pilot."""

    def __init__(
        self,
        *,
        gh_executable: str,
        gh_sha256: str,
        git_executable: str,
        git_sha256: str,
        auth_environment: Callable[[], Mapping[str, str]],
        runner: CommandRunner | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._gh = _pinned_path(gh_executable, gh_sha256)
        self._gh_sha256 = gh_sha256
        self._git = _pinned_path(git_executable, git_sha256)
        self._git_sha256 = git_sha256
        self._auth_environment = auth_environment
        self._runner = runner or SubprocessCommandRunner()
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    @property
    def source_adapter_digest(self) -> str:
        return contract_digest(
            "github-source-adapter",
            {
                "host": "github.com",
                "repository": TARGET_GITHUB_NAME,
                "gh_sha256": self._gh_sha256,
            },
        )

    @property
    def auth_principal_digest(self) -> str:
        return contract_digest(
            "github-auth-principal",
            {"host": "github.com", "capability": "gh-host-auth"},
        )

    def fetch_issue(self, repository: str, issue_number: int) -> IssueObservation:
        self._exact_target(repository)
        if issue_number != 1:
            raise ContractError("target_mismatch", "issue_number")
        repo = self._get_json(f"repos/{TARGET_GITHUB_NAME}")
        issue = self._get_json(f"repos/{TARGET_GITHUB_NAME}/issues/1")
        if (
            not isinstance(repo, dict)
            or repo.get("full_name") != TARGET_GITHUB_NAME
            or repo.get("default_branch") != "main"
        ):
            raise ContractError("target_mismatch", "repository")
        if not isinstance(issue, dict):
            raise ContractError("invalid_issue_observation")
        return issue_observation_from_github(
            {
                **issue,
                "repository_full_name": repo.get("full_name"),
                "repository_node_id": repo.get("node_id"),
                "author": issue.get("user"),
            }
        )

    def fetch_ref(self, repository: str, base_ref: str) -> BaseObservation:
        self._exact_target(repository)
        if base_ref != "refs/heads/main":
            raise ContractError("target_mismatch", "base_ref")
        ref = self._get_json(f"repos/{TARGET_GITHUB_NAME}/git/ref/heads/main")
        try:
            sha = str(ref["object"]["sha"])
        except (KeyError, TypeError) as exc:
            raise ContractError("invalid_base_observation") from exc
        if _HEX40.fullmatch(sha) is None:
            raise ContractError("invalid_base_observation")
        commit = self._get_json(f"repos/{TARGET_GITHUB_NAME}/git/commits/{sha}")
        try:
            tree = str(commit["tree"]["sha"])
        except (KeyError, TypeError) as exc:
            raise ContractError("invalid_base_observation") from exc
        if _HEX40.fullmatch(tree) is None:
            raise ContractError("invalid_base_observation")
        return BaseObservation(sha, tree)

    def observe(
        self, request: BranchPushRequestV1 | ProposalCreateRequestV1
    ) -> PublicationObservation:
        if request.github_name != TARGET_GITHUB_NAME:
            raise PublicationError("request_binding")
        issue = self.fetch_issue(TARGET_GITHUB_NAME, 1)
        base = self.fetch_ref(TARGET_GITHUB_NAME, "refs/heads/main")
        branch = (
            request.branch_ref.removeprefix("refs/heads/")
            if isinstance(request, BranchPushRequestV1)
            else request.head_ref
        )
        value = self._get_json(
            f"repos/{TARGET_GITHUB_NAME}/git/ref/heads/{branch}", optional=True
        )
        branch_sha = None
        if value is not None:
            try:
                branch_sha = str(value["object"]["sha"])
            except (KeyError, TypeError) as exc:
                raise PublicationError("github_observation") from exc
            if _HEX40.fullmatch(branch_sha) is None:
                raise PublicationError("github_observation")
        return PublicationObservation(
            base.sha,
            issue.issue_node_id,
            issue.updated_at,
            branch_sha,
            _utc(self._clock()),
        )

    def push_exact(self, request: BranchPushRequestV1, writer: PreparedWorkspace) -> None:
        argv, _unused = ExactGitPushCommand(
            self._git, gh_executable=self._gh
        ).invocation(request, writer)
        result = self._run(argv, cwd=writer.worktree, stdin=b"", executable="git")
        if result.returncode != 0:
            raise PublicationError("push_failed")

    def find_proposals(
        self, request: ProposalCreateRequestV1
    ) -> tuple[ProposalObservation, ...]:
        if request.github_name != TARGET_GITHUB_NAME:
            raise PublicationError("request_binding")
        value = self._get_json(
            f"repos/{TARGET_GITHUB_NAME}/pulls",
            fields=(
                "state=open",
                f"head=Dimkox:{request.head_ref}",
                f"base={request.base_ref}",
                "per_page=100",
            ),
        )
        if not isinstance(value, list) or len(value) > 100:
            raise PublicationError("proposal_observation")
        observations: list[ProposalObservation] = []
        try:
            for item in value:
                body = str(item.get("body") or "")
                observations.append(
                    ProposalObservation(
                        int(item["number"]),
                        str(item["node_id"]),
                        str(item["html_url"]),
                        str(item["head"]["ref"]),
                        str(item["head"]["sha"]),
                        str(item["base"]["ref"]),
                        bool(item["draft"]),
                        request.marker if request.marker in body else "",
                        str(item["state"]),
                        str(item["created_at"]),
                    )
                )
        except (KeyError, TypeError, ValueError) as exc:
            raise PublicationError("proposal_observation") from exc
        return tuple(observations)

    def create_draft(self, request: ProposalCreateRequestV1) -> None:
        argv, payload = GhDraftProposalCommand(self._gh).invocation(request)
        result = self._run(
            argv,
            cwd=Path("/"),
            stdin=json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8"),
            executable="gh",
        )
        if result.returncode != 0:
            raise PublicationError("proposal_create_failed")
        value = _json(result.stdout, "proposal_create_failed")
        if not isinstance(value, dict) or value.get("draft") is not True:
            raise PublicationError("proposal_create_failed")

    def _get_json(
        self,
        endpoint: str,
        *,
        fields: tuple[str, ...] = (),
        optional: bool = False,
    ) -> Any:
        argv = (
            self._gh,
            "api",
            "--hostname",
            "github.com",
            "--method",
            "GET",
            endpoint,
            *(item for field in fields for item in ("-f", field)),
        )
        result = self._run(argv, cwd=Path("/"), stdin=b"", executable="gh")
        if result.returncode != 0:
            if optional and result.stdout == b"" and re.fullmatch(
                br"gh: Not Found \(HTTP 404\)\r?\n", result.stderr
            ):
                return None
            raise PublicationError("github_read_failed")
        return _json(result.stdout, "github_response")

    def _run(
        self,
        argv: tuple[str, ...],
        *,
        cwd: Path,
        stdin: bytes,
        executable: str,
    ) -> CommandResult:
        if executable == "gh":
            _verify_pinned(self._gh, self._gh_sha256)
        elif executable == "git":
            _verify_pinned(self._git, self._git_sha256)
            _verify_pinned(self._gh, self._gh_sha256)
        else:
            raise PublicationError("command_binding")
        result = self._runner.run(
            argv=argv,
            cwd=cwd,
            environment=_github_environment(self._auth_environment()),
            stdin=stdin,
            timeout_seconds=30,
            max_output_bytes=1_048_576,
        )
        if (
            not isinstance(result, CommandResult)
            or type(result.returncode) is not int
            or not isinstance(result.stdout, bytes)
            or not isinstance(result.stderr, bytes)
        ):
            raise PublicationError("github_command")
        return result

    @staticmethod
    def _exact_target(repository: str) -> None:
        if repository != TARGET_GITHUB_NAME:
            raise ContractError("target_mismatch", "repository")


def _pinned_path(path: str, digest: str) -> str:
    target = Path(path)
    if not target.is_absolute() or not re.fullmatch(r"/[A-Za-z0-9._/+@-]+", path):
        raise PublicationError("executable_binding")
    _verify_pinned(path, digest)
    return path


def _verify_pinned(path: str, digest: str) -> None:
    target = Path(path)
    try:
        metadata = target.lstat()
        body = target.read_bytes()
    except OSError as exc:
        raise PublicationError("executable_binding") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or metadata.st_mode & 0o111 == 0
        or hashlib.sha256(body).hexdigest() != digest
    ):
        raise PublicationError("executable_binding")


def verify_pinned_executable(path: str, digest: str) -> None:
    _verify_pinned(path, digest)


def _github_environment(value: Mapping[str, str]) -> dict[str, str]:
    environment = dict(value)
    if set(environment) - _ALLOWED_AUTH_ENV or "HOME" not in environment:
        raise PublicationError("github_auth_capability")
    if any(
        not isinstance(item, str)
        or not item
        or not Path(item).is_absolute()
        or "\x00" in item
        for item in environment.values()
    ):
        raise PublicationError("github_auth_capability")
    return {
        **environment,
        "PATH": "/usr/bin:/bin",
        "LC_ALL": "C.UTF-8",
        "TZ": "UTC",
        "GH_HOST": "github.com",
        "GH_PROMPT_DISABLED": "1",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": "/dev/null",
        "GIT_TERMINAL_PROMPT": "0",
    }


def _json(raw: bytes, code: str) -> Any:
    if len(raw) > 1_048_576:
        raise PublicationError(code)
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise PublicationError(code) from exc


def _utc(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise PublicationError("clock")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
