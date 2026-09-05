"""Private exact-base Git workspace with a detached model-visible worktree."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile
from typing import Mapping

from .contracts import CandidateChangeV1, ChangedFileV1, IssueSnapshotV1, canonical_json


_HEX40 = re.compile(r"^[0-9a-f]{40}$")
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


class WorkspaceError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkspacePolicy:
    profile_digest: str
    base_sha: str
    base_tree: str
    allowed_write_paths: tuple[str, ...]
    max_diff_bytes: int

    def __post_init__(self) -> None:
        if _HEX64.fullmatch(self.profile_digest) is None:
            raise WorkspaceError("profile_digest")
        if _HEX40.fullmatch(self.base_sha) is None or _HEX40.fullmatch(self.base_tree) is None:
            raise WorkspaceError("base_identity")
        if (
            not self.allowed_write_paths
            or self.allowed_write_paths != tuple(sorted(set(self.allowed_write_paths)))
            or len(self.allowed_write_paths) > 16
        ):
            raise WorkspaceError("allowed_paths")
        for path in self.allowed_write_paths:
            _safe_path(path)
        if type(self.max_diff_bytes) is not int or not 1 <= self.max_diff_bytes <= 4_194_304:
            raise WorkspaceError("diff_limit")


@dataclass(frozen=True)
class PreparedWorkspace:
    root: Path
    worktree: Path
    git_dir: Path
    base_sha: str
    base_tree: str
    workspace_digest: str
    object_storage_independent: bool
    remote_removed: bool


class ExactGitWorkspace:
    def __init__(
        self,
        source_repository: Path,
        root: Path,
        *,
        control_repository: Path,
        policy: WorkspacePolicy,
        git_executable: str = "/usr/bin/git",
    ) -> None:
        source = Path(source_repository)
        if not source.is_absolute():
            raise WorkspaceError("source_absolute")
        self._source = source.resolve(strict=True)
        self._control = Path(control_repository).resolve(strict=True)
        self._root = _private_root(Path(root), (self._source, self._control))
        self._policy = policy
        executable = Path(git_executable)
        if not executable.is_absolute():
            raise WorkspaceError("git_executable")
        try:
            metadata = executable.lstat()
        except OSError as exc:
            raise WorkspaceError("git_executable") from exc
        if not stat.S_ISREG(metadata.st_mode) or metadata.st_mode & 0o111 == 0:
            raise WorkspaceError("git_executable")
        self._git_executable = str(executable)

    def prepare(self, job_id: str) -> PreparedWorkspace:
        if not isinstance(job_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._+-]{0,127}", job_id):
            raise WorkspaceError("job_id")
        source_guard = self._source_guard()
        previous = os.umask(0o077)
        try:
            workspace_root = Path(
                tempfile.mkdtemp(
                    prefix=f"job-{hashlib.sha256(job_id.encode()).hexdigest()[:16]}-",
                    dir=self._root,
                )
            )
        finally:
            os.umask(previous)
        workspace_root.chmod(0o700)
        git_dir = workspace_root / "control.git"
        worktree = workspace_root / "app"
        worktree.mkdir(mode=0o700)
        environment = self._environment(workspace_root)
        try:
            self._git(
                (
                    "-c", "protocol.allow=never",
                    "-c", "protocol.file.allow=always",
                    "clone", "--bare", "--no-local", "--no-hardlinks",
                    "--no-tags", str(self._source), str(git_dir),
                ),
                cwd=workspace_root,
                env=environment,
            )
            self._git_repo(
                git_dir,
                worktree,
                ("-c", "advice.detachedHead=false", "checkout", "--detach", "--force", self._policy.base_sha),
                env=environment,
            )
            self._git_repo(git_dir, worktree, ("remote", "remove", "origin"), env=environment)
            hooks = git_dir / "hooks"
            if hooks.exists():
                shutil.rmtree(hooks)
            hooks.mkdir(mode=0o700)
            head, tree = self._head_tree(git_dir, worktree, environment)
            if (head, tree) != (self._policy.base_sha, self._policy.base_tree):
                raise WorkspaceError("base_identity")
            if self._git_repo(git_dir, worktree, ("status", "--porcelain=v1", "-z", "--untracked-files=all"), env=environment):
                raise WorkspaceError("base_worktree")
            if self._git_repo(git_dir, worktree, ("remote",), env=environment):
                raise WorkspaceError("remote_present")
            independent = self._objects_are_independent(git_dir)
            if not independent:
                raise WorkspaceError("object_storage_shared")
            if (worktree / ".git").exists() or self._source_guard() != source_guard:
                raise WorkspaceError("source_mutation")
            digest = hashlib.sha256(
                canonical_json(
                    {
                        "contract": "adaptive-pilot.workspace/v1",
                        "profile_digest": self._policy.profile_digest,
                        "base_sha": head,
                        "base_tree": tree,
                        "remote_removed": True,
                        "object_storage_independent": True,
                    }
                )
            ).hexdigest()
            return PreparedWorkspace(
                workspace_root,
                worktree,
                git_dir,
                head,
                tree,
                digest,
                True,
                True,
            )
        except BaseException:
            shutil.rmtree(workspace_root, ignore_errors=True)
            raise

    def seal(
        self,
        workspace: PreparedWorkspace,
        issue: IssueSnapshotV1,
        *,
        sandbox_evidence_digest: str,
        model_id: str,
        executable_version: str,
        executable_sha256: str,
        prompt_digest: str,
        tool_policy_digest: str,
        output_schema_digest: str,
        started_at: str,
        completed_at: str,
    ) -> CandidateChangeV1:
        self._validate_prepared(workspace, issue)
        environment = self._environment(workspace.root)
        source_guard = self._source_guard()
        head, tree = self._head_tree(workspace.git_dir, workspace.worktree, environment)
        if (head, tree) != (self._policy.base_sha, self._policy.base_tree):
            raise WorkspaceError("base_identity")
        if (workspace.worktree / ".git").exists():
            raise WorkspaceError("git_visible")
        staged = self._git_repo(workspace.git_dir, workspace.worktree, ("diff", "--cached", "--name-only", "-z"), env=environment)
        if staged:
            raise WorkspaceError("model_staged_change")
        tracked = _nul_paths(
            self._git_repo(workspace.git_dir, workspace.worktree, ("diff", "--name-only", "-z", "--no-renames", self._policy.base_sha, "--"), env=environment)
        )
        untracked = _nul_paths(
            self._git_repo(workspace.git_dir, workspace.worktree, ("ls-files", "--others", "--exclude-standard", "-z"), env=environment)
        )
        paths = tuple(sorted(set((*tracked, *untracked))))
        if not paths:
            raise WorkspaceError("empty_diff")
        if any(path not in self._policy.allowed_write_paths for path in paths):
            raise WorkspaceError("changed_paths")
        for relative in paths:
            target = workspace.worktree.joinpath(*PurePosixPath(relative).parts)
            try:
                metadata = target.lstat()
            except OSError as exc:
                raise WorkspaceError("changed_file_type") from exc
            if (
                not stat.S_ISREG(metadata.st_mode)
                or stat.S_ISLNK(metadata.st_mode)
                or metadata.st_nlink != 1
                or metadata.st_mode & 0o111
            ):
                raise WorkspaceError("changed_file_type")
        self._git_repo(workspace.git_dir, workspace.worktree, ("add", "--", *paths), env=environment)
        staged_paths = _nul_paths(
            self._git_repo(workspace.git_dir, workspace.worktree, ("diff", "--cached", "--name-only", "-z", "--no-renames", self._policy.base_sha, "--"), env=environment)
        )
        if tuple(sorted(staged_paths)) != paths:
            raise WorkspaceError("changed_paths")
        diff = self._git_repo(
            workspace.git_dir,
            workspace.worktree,
            ("diff", "--cached", "--binary", "--full-index", "--no-ext-diff", self._policy.base_sha, "--"),
            env=environment,
            max_stdout=self._policy.max_diff_bytes,
        )
        if not diff or len(diff) > self._policy.max_diff_bytes:
            raise WorkspaceError("diff_limit")
        candidate_tree = self._git_repo(workspace.git_dir, workspace.worktree, ("write-tree",), env=environment).decode().strip()
        commit_environment = {
            **environment,
            "GIT_AUTHOR_NAME": "Adaptive Pilot",
            "GIT_AUTHOR_EMAIL": "pilot@example.invalid",
            "GIT_COMMITTER_NAME": "Adaptive Pilot",
            "GIT_COMMITTER_EMAIL": "pilot@example.invalid",
            "GIT_AUTHOR_DATE": "2000-01-01T00:00:00Z",
            "GIT_COMMITTER_DATE": "2000-01-01T00:00:00Z",
        }
        candidate_sha = self._git_repo(
            workspace.git_dir,
            workspace.worktree,
            ("-c", "commit.gpgSign=false", "commit-tree", candidate_tree, "-p", self._policy.base_sha),
            env=commit_environment,
            input_bytes=f"Adaptive pilot candidate for {issue.job_id}\n".encode("utf-8"),
        ).decode().strip()
        self._git_repo(workspace.git_dir, workspace.worktree, ("update-ref", "--no-deref", "HEAD", candidate_sha, self._policy.base_sha), env=environment)
        self._git_repo(workspace.git_dir, workspace.worktree, ("reset", "--hard", candidate_sha), env=environment)
        if self._head_tree(workspace.git_dir, workspace.worktree, environment) != (candidate_sha, candidate_tree):
            raise WorkspaceError("candidate_identity")
        if self._git_repo(workspace.git_dir, workspace.worktree, ("status", "--porcelain=v1", "-z", "--untracked-files=all"), env=environment):
            raise WorkspaceError("candidate_worktree")
        if self._git_repo(workspace.git_dir, workspace.worktree, ("remote",), env=environment):
            raise WorkspaceError("remote_present")
        if not self._objects_are_independent(workspace.git_dir) or self._source_guard() != source_guard:
            raise WorkspaceError("source_mutation")
        changed_files = [self._changed_file(workspace, path, candidate_sha, environment) for path in paths]
        return CandidateChangeV1.from_facts(
            {
                "schema_version": 1,
                "job_id": issue.job_id,
                "profile_digest": issue.profile_digest,
                "issue_snapshot_digest": issue.issue_snapshot_digest,
                "run_id": f"{issue.job_id}-run-1",
                "attempt": 1,
                "provider_id": "openai-codex-cli",
                "model_id": model_id,
                "writer_id": "codex-writer",
                "executable_version": executable_version,
                "executable_sha256": executable_sha256,
                "prompt_digest": prompt_digest,
                "tool_policy_digest": tool_policy_digest,
                "output_schema_digest": output_schema_digest,
                "sandbox_evidence_digest": sandbox_evidence_digest,
                "workspace_digest": workspace.workspace_digest,
                "base_sha": self._policy.base_sha,
                "base_tree": self._policy.base_tree,
                "candidate_sha": candidate_sha,
                "candidate_tree": candidate_tree,
                "changed_files": [item.__dict__ for item in changed_files],
                "diff_sha256": hashlib.sha256(diff).hexdigest(),
                "diff_bytes": len(diff),
                "remote_removed": True,
                "object_storage_independent": True,
                "started_at": started_at,
                "completed_at": completed_at,
                "outcome": "candidate",
            }
        )

    @staticmethod
    def cleanup(workspace: PreparedWorkspace) -> None:
        try:
            metadata = workspace.root.lstat()
        except FileNotFoundError:
            return
        if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
            raise WorkspaceError("cleanup_target")
        shutil.rmtree(workspace.root)

    def _validate_prepared(self, workspace: PreparedWorkspace, issue: IssueSnapshotV1) -> None:
        if (
            workspace.base_sha != self._policy.base_sha
            or workspace.base_tree != self._policy.base_tree
            or issue.base_sha != self._policy.base_sha
            or issue.base_tree != self._policy.base_tree
            or issue.profile_digest != self._policy.profile_digest
            or not workspace.remote_removed
            or not workspace.object_storage_independent
            or workspace.root.parent != self._root
        ):
            raise WorkspaceError("workspace_binding")

    def _changed_file(self, workspace: PreparedWorkspace, path: str, candidate_sha: str, environment: Mapping[str, str]) -> ChangedFileV1:
        raw = self._git_repo(workspace.git_dir, workspace.worktree, ("ls-tree", "-z", candidate_sha, "--", path), env=environment)
        try:
            metadata, listed = raw.rstrip(b"\0").split(b"\t", 1)
            mode, kind, object_id = metadata.decode("ascii").split(" ")
            listed_path = listed.decode("utf-8")
        except (ValueError, UnicodeError) as exc:
            raise WorkspaceError("candidate_inventory") from exc
        if (mode, kind, listed_path) != ("100644", "blob", path):
            raise WorkspaceError("candidate_inventory")
        body = workspace.worktree.joinpath(*PurePosixPath(path).parts).read_bytes()
        expected_object = hashlib.sha1(b"blob " + str(len(body)).encode("ascii") + b"\0" + body).hexdigest()  # nosec B324
        if expected_object != object_id:
            raise WorkspaceError("candidate_inventory")
        return ChangedFileV1(path, mode, object_id, hashlib.sha256(body).hexdigest())

    def _source_guard(self) -> tuple[bytes, bytes, bytes]:
        environment = self._environment(self._source)
        head = self._git(("rev-parse", "HEAD"), cwd=self._source, env=environment)
        tree = self._git(("rev-parse", "HEAD^{tree}"), cwd=self._source, env=environment)
        status = self._git(("status", "--porcelain=v1", "-z", "--untracked-files=all"), cwd=self._source, env=environment)
        if status:
            raise WorkspaceError("source_worktree")
        refs = self._git(("for-each-ref", "--format=%(refname)%00%(objectname)"), cwd=self._source, env=environment)
        if (head.decode().strip(), tree.decode().strip()) != (self._policy.base_sha, self._policy.base_tree):
            raise WorkspaceError("source_identity")
        return head, tree, refs

    def _head_tree(self, git_dir: Path, worktree: Path, environment: Mapping[str, str]) -> tuple[str, str]:
        head = self._git_repo(git_dir, worktree, ("rev-parse", "HEAD"), env=environment).decode().strip()
        tree = self._git_repo(git_dir, worktree, ("rev-parse", "HEAD^{tree}"), env=environment).decode().strip()
        return head, tree

    def _objects_are_independent(self, git_dir: Path) -> bool:
        candidate_objects = git_dir / "objects"
        source_objects = self._source / ".git" / "objects"
        if not source_objects.is_dir():
            source_objects = self._source / "objects"
        if (candidate_objects / "info" / "alternates").exists():
            return False
        return not (_regular_inodes(candidate_objects) & _regular_inodes(source_objects))

    def _git_repo(self, git_dir: Path, worktree: Path, arguments: tuple[str, ...], *, env: Mapping[str, str], input_bytes: bytes | None = None, max_stdout: int = 64 * 1_048_576) -> bytes:
        return self._git((f"--git-dir={git_dir}", f"--work-tree={worktree}", *arguments), cwd=worktree, env=env, input_bytes=input_bytes, max_stdout=max_stdout)

    def _git(self, arguments: tuple[str, ...], *, cwd: Path, env: Mapping[str, str], input_bytes: bytes | None = None, max_stdout: int = 64 * 1_048_576) -> bytes:
        try:
            completed = subprocess.run((self._git_executable, *arguments), cwd=cwd, env=dict(env), input=input_bytes, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise WorkspaceError("git_command") from exc
        if completed.returncode != 0 or len(completed.stdout) > max_stdout or len(completed.stderr) > 1_048_576:
            raise WorkspaceError("git_command")
        return completed.stdout

    @staticmethod
    def _environment(home: Path) -> dict[str, str]:
        return {
            "HOME": str(home),
            "PATH": "/usr/bin:/bin",
            "LC_ALL": "C",
            "TZ": "UTC",
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": "/dev/null",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_ASKPASS": "/bin/false",
            "SSH_ASKPASS": "/bin/false",
        }


def _private_root(root: Path, forbidden: tuple[Path, ...]) -> Path:
    if not root.is_absolute():
        raise WorkspaceError("workspace_root_absolute")
    absolute = Path(os.path.abspath(root))
    for boundary in forbidden:
        if absolute == boundary or boundary in absolute.parents or absolute in boundary.parents:
            raise WorkspaceError("workspace_root_boundary")
    previous = os.umask(0o077)
    try:
        absolute.mkdir(mode=0o700, parents=False, exist_ok=True)
    except OSError as exc:
        raise WorkspaceError("workspace_root") from exc
    finally:
        os.umask(previous)
    metadata = absolute.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode) or metadata.st_uid != os.getuid() or metadata.st_mode & 0o777 != 0o700:
        raise WorkspaceError("workspace_root_mode")
    return absolute.resolve(strict=True)


def _safe_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value or value.startswith("/"):
        raise WorkspaceError("path")
    parts = PurePosixPath(value).parts
    if any(part in {"", ".", "..", ".git"} for part in parts):
        raise WorkspaceError("path")
    return value


def _nul_paths(raw: bytes) -> tuple[str, ...]:
    try:
        paths = tuple(item.decode("utf-8") for item in raw.split(b"\0") if item)
    except UnicodeDecodeError as exc:
        raise WorkspaceError("path_encoding") from exc
    for path in paths:
        _safe_path(path)
    return paths


def _regular_inodes(root: Path) -> set[tuple[int, int]]:
    result: set[tuple[int, int]] = set()
    for path in root.rglob("*"):
        try:
            metadata = path.lstat()
        except OSError:
            continue
        if stat.S_ISREG(metadata.st_mode):
            result.add((metadata.st_dev, metadata.st_ino))
    return result
