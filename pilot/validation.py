"""Exact-candidate test runner and deterministic landing semantic gate."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile
from typing import Protocol

from .contracts import CandidateChangeV1, CandidateValidationV1, contract_digest
from .profile import PilotProfileV1
from .store import PilotStore, PilotStoreError
from .workspace import PreparedWorkspace


class ValidationError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProtectedFileObservation:
    blob_sha: str
    sha256: str


@dataclass(frozen=True)
class SemanticDecision:
    decision: str
    acceptance_ids: tuple[str, ...]
    reason_codes: tuple[str, ...]


@dataclass(frozen=True)
class TestProcessResult:
    status: str
    exit_code: int
    stdout: bytes
    stderr: bytes
    elapsed_ms: int
    completed_at: str


@dataclass(frozen=True)
class ValidationWorkspace:
    root: Path
    worktree: Path
    git_dir: Path
    candidate_sha: str
    candidate_tree: str
    workspace_digest: str


class ValidationWorkspaces(Protocol):
    def materialize(self, writer: PreparedWorkspace, candidate: CandidateChangeV1) -> ValidationWorkspace: ...

    def tree(self, workspace: ValidationWorkspace) -> str: ...

    def protected_file(self, workspace: ValidationWorkspace, path: str) -> ProtectedFileObservation: ...


class TestRunner(Protocol):
    def run(self, *, command: tuple[str, ...], workspace: ValidationWorkspace, timeout_seconds: int, max_output_bytes: int) -> TestProcessResult: ...


class LandingSemanticGate:
    _JSON_LD = re.compile(br'<script\s+type=["\']application/ld\+json["\']\s*>(.*?)</script\s*>', re.DOTALL | re.IGNORECASE)
    _FORBIDDEN = (
        "enterprise-ready",
        "enterprise ready",
        "production autonomy",
        "fully autonomous production",
        "m8 active",
        "m9 active",
        "live provider",
        "live publisher",
        "hosting active",
        "deployed to production",
    )

    def __init__(self, profile: PilotProfileV1) -> None:
        self._profile = profile

    def evaluate(self, root: Path, candidate: CandidateChangeV1, protected: ProtectedFileObservation, acceptance_ids: tuple[str, ...]) -> SemanticDecision:
        findings: list[str] = []
        if tuple(item.path for item in candidate.changed_files) != self._profile.allowed_write_paths:
            findings.append("changed_path_set")
        if (protected.blob_sha, protected.sha256) != (
            self._profile.protected_index_css_blob,
            self._profile.protected_index_css_sha256,
        ):
            findings.append("protected_index_css")
        try:
            root_html_bytes = _read(root / "index.html")
            root_html = root_html_bytes.decode("utf-8")
            if root_html.count(self._profile.expected_visible_version) < 2 or "v2.0.12" in root_html:
                findings.append("root_version")
            if self._profile.expected_honest_label not in root_html:
                findings.append("honest_label")
            if self._profile.expected_version_label not in root_html:
                findings.append("version_label")
            folded = root_html.casefold()
            if any(claim in folded for claim in self._FORBIDDEN):
                findings.append("forbidden_claim")
            scripts = self._JSON_LD.findall(root_html_bytes)
            if len(scripts) != 1:
                findings.append("jsonld_count")
                script = b""
            else:
                script = scripts[0]
                document = json.loads(script.decode("utf-8"))
                if not isinstance(document, dict) or document.get("version") != self._profile.expected_jsonld_version:
                    findings.append("jsonld_version")
            csp = _read(root / ".htaccess").decode("utf-8")
            token = "'sha256-" + base64.b64encode(hashlib.sha256(script).digest()).decode("ascii") + "'"
            if not self._csp_matches(csp, token):
                findings.append("csp")
            for locale in ("km", "ko", "lv", "nl", "zh-cn"):
                text = _read(root / locale / "index.html").decode("utf-8")
                if self._profile.expected_visible_version not in text or "v2.0.12" in text:
                    findings.append(f"locale_{locale}")
            tests = _read(root / "tests/test_landing.py").decode("utf-8")
            for value in (
                self._profile.expected_jsonld_version,
                self._profile.expected_visible_version,
                self._profile.expected_honest_label,
                self._profile.expected_version_label,
            ):
                if value not in tests:
                    findings.append("test_expectation")
                    break
        except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
            findings.append("semantic_input")
        return SemanticDecision(
            "pass" if not findings else "rejected",
            tuple(acceptance_ids),
            () if not findings else ("semantic_non_pass",),
        )

    @staticmethod
    def _csp_matches(htaccess: str, script_token: str) -> bool:
        # The pinned landing allows changing only its JSON-LD hash, not policy.
        # Count all mentions so another Header unset/set cannot override this one.
        if htaccess.casefold().count("content-security-policy") != 1:
            return False
        match = re.search(
            r'^\s*Header[ \t]+always[ \t]+set[ \t]+Content-Security-Policy[ \t]+"([^"\r\n]*)"[ \t]*$',
            htaccess, re.MULTILINE,
        )
        if match is None:
            return False
        directives: dict[str, tuple[str, ...]] = {}
        for raw in match.group(1).split(';'):
            parts = raw.split()
            if not parts:
                continue
            name, *sources = parts
            if name in directives:
                return False
            directives[name] = tuple(sources)
        expected = {
            'default-src': ("'self'",),
            'script-src': ("'self'", script_token),
            'style-src': ("'self'",),
            'img-src': ("'self'",),
            'font-src': ("'self'",),
            'connect-src': ("'none'",),
            'media-src': ("'none'",),
            'frame-src': ("'none'",),
            'worker-src': ("'none'",),
            'object-src': ("'none'",),
            'base-uri': ("'self'",),
            'form-action': ("'self'",),
            'frame-ancestors': ("'none'",),
            'upgrade-insecure-requests': (),
        }
        return directives == expected


class CandidateValidator:
    EVALUATOR_ID = "landing-semantic-gate-v1"

    def __init__(self, profile: PilotProfileV1, store: PilotStore, workspaces: ValidationWorkspaces, *, runner: TestRunner, gate: LandingSemanticGate) -> None:
        self._profile = profile
        self._store = store
        self._workspaces = workspaces
        self._runner = runner
        self._gate = gate

    def validate(self, candidate: CandidateChangeV1, writer: PreparedWorkspace, *, command_key: str) -> CandidateValidationV1:
        job = self._store.get(candidate.job_id)
        if job.state != "candidate_sealed" or job.candidate != candidate:
            raise ValidationError("candidate_state")
        if (
            candidate.profile_digest != self._profile.profile_digest
            or candidate.candidate_sha == candidate.base_sha
            or writer.workspace_digest != candidate.workspace_digest
            or writer.base_sha != candidate.base_sha
            or writer.base_tree != candidate.base_tree
            or candidate.writer_id == self.EVALUATOR_ID
        ):
            raise ValidationError("identity_mismatch")
        workspace = self._workspaces.materialize(writer, candidate)
        if (workspace.candidate_sha, workspace.candidate_tree) != (candidate.candidate_sha, candidate.candidate_tree):
            raise ValidationError("identity_mismatch")
        pre_tree = self._workspaces.tree(workspace)
        if pre_tree != candidate.candidate_tree:
            raise ValidationError("identity_mismatch")
        self._store.begin_validation(candidate.job_id, command_key=command_key)
        try:
            result = self._runner.run(
                command=self._profile.test_argv,
                workspace=workspace,
                timeout_seconds=self._profile.test_timeout_seconds,
                max_output_bytes=self._profile.max_output_bytes,
            )
            post_tree = self._workspaces.tree(workspace)
            reasons: set[str] = set()
            exit_code = result.exit_code
            if result.status == "timeout":
                reasons.add("test_timeout")
                exit_code = 124
            elif result.status == "overflow":
                reasons.add("test_overflow")
                exit_code = 125
            elif result.status != "completed":
                reasons.add("test_failed")
                exit_code = 126
            if not 0 <= exit_code <= 255:
                reasons.add("test_failed")
                exit_code = 126
            if result.status == "completed" and result.exit_code != 0:
                reasons.add("test_failed")
            if len(result.stdout) + len(result.stderr) > self._profile.max_output_bytes:
                reasons.add("test_overflow")
            if post_tree != pre_tree:
                reasons.add("test_mutation")
            if not reasons:
                semantic = self._gate.evaluate(
                    workspace.worktree,
                    candidate,
                    self._workspaces.protected_file(workspace, "index.css"),
                    job.snapshot.acceptance_ids,
                )
                reasons.update(semantic.reason_codes)
            decision = "pass" if not reasons else "rejected"
            validation = CandidateValidationV1.from_facts(
                {
                    "schema_version": 1,
                    "job_id": candidate.job_id,
                    "profile_digest": candidate.profile_digest,
                    "candidate_digest": candidate.candidate_digest,
                    "candidate_sha": candidate.candidate_sha,
                    "candidate_tree": candidate.candidate_tree,
                    "test_profile_digest": self._profile.test_profile_digest,
                    "command_digest": self._profile.test_command_digest,
                    "exit_code": exit_code,
                    "elapsed_ms": min(max(result.elapsed_ms, 0), 900_000),
                    "stdout_sha256": hashlib.sha256(result.stdout).hexdigest(),
                    "stderr_sha256": hashlib.sha256(result.stderr).hexdigest(),
                    "pre_test_tree": pre_tree,
                    "post_test_tree": post_tree,
                    "writer_id": candidate.writer_id,
                    "evaluator_id": self.EVALUATOR_ID,
                    "semantic_profile_digest": self._profile.semantic_profile_digest,
                    "acceptance_ids": list(job.snapshot.acceptance_ids),
                    "decision": decision,
                    "reason_codes": sorted(reasons),
                    "completed_at": result.completed_at,
                }
            )
            self._store.store_validation(candidate.job_id, validation)
            return validation
        except BaseException as exc:
            try:
                if self._store.get(candidate.job_id).state == "validation_intent":
                    self._store.mark_terminal(candidate.job_id, reason_code="gate_outcome_ambiguous")
            except PilotStoreError:
                pass
            if isinstance(exc, ValidationError):
                raise
            raise ValidationError("gate_outcome_ambiguous") from exc
        finally:
            cleanup = getattr(self._workspaces, "cleanup", None)
            if cleanup is not None:
                cleanup(workspace)


class ExactValidationWorkspace:
    def __init__(self, root: Path, *, control_repository: Path, git_executable: str = "/usr/bin/git") -> None:
        if not Path(root).is_absolute():
            raise ValidationError("validation_root_absolute")
        absolute = Path(os.path.abspath(root))
        control = Path(control_repository).resolve(strict=True)
        if absolute == control or control in absolute.parents:
            raise ValidationError("validation_root_repository")
        previous = os.umask(0o077)
        try:
            absolute.mkdir(mode=0o700, parents=False, exist_ok=True)
        finally:
            os.umask(previous)
        metadata = absolute.lstat()
        if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode) or metadata.st_mode & 0o777 != 0o700:
            raise ValidationError("validation_root_mode")
        self._root = absolute.resolve(strict=True)
        self._git = git_executable

    def materialize(self, writer: PreparedWorkspace, candidate: CandidateChangeV1) -> ValidationWorkspace:
        previous = os.umask(0o077)
        try:
            root = Path(tempfile.mkdtemp(prefix="validation-", dir=self._root))
        finally:
            os.umask(previous)
        root.chmod(0o700)
        git_dir = root / "control.git"
        worktree = root / "app"
        worktree.mkdir(mode=0o700)
        try:
            self._run(("clone", "--bare", "--no-local", "--no-hardlinks", "--no-tags", str(writer.git_dir), str(git_dir)), root)
            self._repo(git_dir, worktree, ("-c", "advice.detachedHead=false", "checkout", "--detach", "--force", candidate.candidate_sha))
            self._repo(git_dir, worktree, ("remote", "remove", "origin"))
            if self._repo(git_dir, worktree, ("remote",)) or (worktree / ".git").exists():
                raise ValidationError("validation_remote")
            if (git_dir / "objects/info/alternates").exists() or _inodes(git_dir / "objects") & _inodes(writer.git_dir / "objects"):
                raise ValidationError("validation_objects")
            workspace = ValidationWorkspace(
                root,
                worktree,
                git_dir,
                candidate.candidate_sha,
                candidate.candidate_tree,
                contract_digest("validation-workspace", {"candidate_digest": candidate.candidate_digest, "candidate_sha": candidate.candidate_sha, "candidate_tree": candidate.candidate_tree, "independent": True, "remote_removed": True}),
            )
            if self.tree(workspace) != candidate.candidate_tree:
                raise ValidationError("validation_identity")
            return workspace
        except BaseException:
            shutil.rmtree(root, ignore_errors=True)
            raise

    def tree(self, workspace: ValidationWorkspace) -> str:
        if self._repo(workspace.git_dir, workspace.worktree, ("status", "--porcelain=v1", "-z", "--untracked-files=all")):
            return "0" * 40
        return self._repo(workspace.git_dir, workspace.worktree, ("rev-parse", "HEAD^{tree}")).decode().strip()

    def protected_file(self, workspace: ValidationWorkspace, path: str) -> ProtectedFileObservation:
        raw = self._repo(workspace.git_dir, workspace.worktree, ("ls-tree", "-z", workspace.candidate_sha, "--", path))
        try:
            metadata, listed = raw.rstrip(b"\0").split(b"\t", 1)
            mode, kind, blob = metadata.decode("ascii").split(" ")
        except (ValueError, UnicodeError) as exc:
            raise ValidationError("protected_file") from exc
        if (mode, kind, listed.decode("utf-8")) != ("100644", "blob", path):
            raise ValidationError("protected_file")
        body = _read(workspace.worktree.joinpath(*PurePosixPath(path).parts))
        return ProtectedFileObservation(blob, hashlib.sha256(body).hexdigest())

    @staticmethod
    def cleanup(workspace: ValidationWorkspace) -> None:
        shutil.rmtree(workspace.root)

    def _repo(self, git_dir: Path, worktree: Path, args: tuple[str, ...]) -> bytes:
        return self._run((f"--git-dir={git_dir}", f"--work-tree={worktree}", *args), worktree)

    def _run(self, args: tuple[str, ...], cwd: Path) -> bytes:
        try:
            completed = subprocess.run((self._git, *args), cwd=cwd, env=_git_env(cwd), stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValidationError("git_command") from exc
        if completed.returncode != 0 or len(completed.stdout) > 64 * 1_048_576 or len(completed.stderr) > 1_048_576:
            raise ValidationError("git_command")
        return completed.stdout


class BubblewrapTestRunner:
    def __init__(self, profile: PilotProfileV1, *, executable: str = "/usr/bin/bwrap") -> None:
        self._profile = profile
        self._executable = executable

    def invocation(self, command: tuple[str, ...], workspace: ValidationWorkspace) -> tuple[tuple[str, ...], dict[str, str]]:
        if command != self._profile.test_argv:
            raise ValidationError("test_command")
        argv = (
            self._executable,
            "--unshare-all", "--die-with-parent", "--new-session", "--clearenv",
            "--ro-bind", "/usr", "/usr",
            "--symlink", "usr/bin", "/bin",
            "--symlink", "usr/lib", "/lib",
            "--proc", "/proc", "--dev", "/dev",
            "--tmpfs", "/tmp", "--dir", "/tmp/home",  # nosec B108: private sandbox tmpfs, not host paths
            "--ro-bind", str(workspace.worktree), "/workspace",
            "--chdir", "/workspace",
            "--setenv", "HOME", "/tmp/home",  # nosec B108: private sandbox tmpfs
            "--setenv", "TMPDIR", "/tmp",  # nosec B108: private sandbox tmpfs
            "--setenv", "PATH", "/usr/bin:/bin",
            "--setenv", "LC_ALL", "C.UTF-8",
            "--setenv", "TZ", "UTC",
            "--setenv", "PYTHONDONTWRITEBYTECODE", "1",
            "--",
            *command,
        )
        return argv, {}

    def run(self, *, command: tuple[str, ...], workspace: ValidationWorkspace, timeout_seconds: int, max_output_bytes: int) -> TestProcessResult:
        argv, environment = self.invocation(command, workspace)
        started = datetime.now(timezone.utc)
        with tempfile.TemporaryFile() as stdout_file, tempfile.TemporaryFile() as stderr_file:
            try:
                completed = subprocess.run(argv, cwd=workspace.worktree, env=environment, stdin=subprocess.DEVNULL, stdout=stdout_file, stderr=stderr_file, timeout=timeout_seconds, check=False)
                status = "completed"
                exit_code = completed.returncode
            except subprocess.TimeoutExpired:
                status, exit_code = "timeout", 124
            except OSError as exc:
                raise ValidationError("test_start") from exc
            elapsed = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
            size = stdout_file.tell() + stderr_file.tell()
            if size > max_output_bytes:
                status, exit_code = "overflow", 125
            stdout_file.seek(0)
            stderr_file.seek(0)
            return TestProcessResult(status, exit_code, stdout_file.read(max_output_bytes), stderr_file.read(max_output_bytes), elapsed, datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"))


def _read(path: Path) -> bytes:
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode) or metadata.st_size > 1_048_576:
        raise ValidationError("semantic_file")
    return path.read_bytes()


def _git_env(home: Path) -> dict[str, str]:
    return {"HOME": str(home), "PATH": "/usr/bin:/bin", "LC_ALL": "C", "TZ": "UTC", "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_TERMINAL_PROMPT": "0", "GIT_ASKPASS": "/bin/false"}


def _inodes(root: Path) -> set[tuple[int, int]]:
    result = set()
    for path in root.rglob("*"):
        try:
            metadata = path.lstat()
        except OSError:
            continue
        if stat.S_ISREG(metadata.st_mode):
            result.add((metadata.st_dev, metadata.st_ino))
    return result
