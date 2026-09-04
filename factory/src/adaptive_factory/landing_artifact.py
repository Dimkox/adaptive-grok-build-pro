from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
import errno
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile

from .contracts import canonical_json
from .landing_contracts import (
    LandingAttemptV1,
    LandingEvaluationV1,
    SiteArtifactV1,
)
from .landing_renderer import (
    FIXED_COMMIT_EMAIL,
    FIXED_COMMIT_NAME,
    FIXED_COMMIT_TIME,
    LANDING_WRITE_PATHS,
    TARGET_DEFAULT_BRANCH,
    TARGET_REPOSITORY_ID,
    GitTreeMember,
    LandingCandidateSnapshot,
)


CONTROL_REPOSITORY_ID = "github.com/Dimkox/adaptive-grok-build-pro"
DEPLOY_MEMBERS = tuple(
    sorted(
        (
            ".htaccess",
            "index.html",
            "content.css",
            "zh-cn/index.html",
            "ko/index.html",
            "nl/index.html",
            "lv/index.html",
            "km/index.html",
            "roadmap.html",
            "privacy.html",
            "cookies.html",
            "california-privacy.html",
            "terms.html",
            "favicon.png",
            "og-image-automatic.jpg",
            "robots.txt",
            "sitemap.xml",
            "google4175cca555a80a32.html",
            "yandex_15bd00519dc47ca1.html",
        )
    )
)
ARCHIVE_TIMESTAMP = (2000, 1, 1, 0, 0, 0)
ARCHIVE_MODE = 0o100644
MAX_MEMBER_BYTES = 25 * 1_048_576
MAX_ARCHIVE_BYTES = 100 * 1_048_576
_HEX40 = re.compile(r"^[0-9a-f]{40}$")


class LandingArtifactError(RuntimeError):
    pass


@dataclass(frozen=True)
class LandingArtifactResult:
    artifact: SiteArtifactV1
    zip_path: Path
    sidecar_path: Path
    sidecar_bytes: bytes
    manifest_bytes: bytes
    member_names: tuple[str, ...]


class ExactGitLandingArtifactSource:
    """Read-only exact-Git source boundary for the site-only packager."""

    def __init__(self, source_repository: Path) -> None:
        source = Path(source_repository)
        if not source.is_absolute():
            raise LandingArtifactError("source_path")
        self._source = source.resolve()
        git = shutil.which("git")
        upload_pack = shutil.which("git-upload-pack")
        if not git or not upload_pack:
            raise LandingArtifactError("git_unavailable")
        self._git_executable = str(Path(git).resolve())
        # Preserve the multicall symlink name; resolving it changes argv[0].
        self._upload_pack = str(Path(upload_pack).absolute())

    @contextmanager
    def materialize(
        self, snapshot: LandingCandidateSnapshot
    ) -> Iterator[tuple[Path, Mapping[str, str]]]:
        guard = self._source_guard(snapshot)
        workspace = self._private_directory()
        repository = workspace / "candidate"
        failure: BaseException | None = None
        try:
            environment = self._environment(workspace)
            self._git(
                (
                    "-c",
                    "protocol.allow=never",
                    "-c",
                    "protocol.file.allow=always",
                    "clone",
                    "--no-local",
                    "--no-hardlinks",
                    "--no-tags",
                    "--no-checkout",
                    "--single-branch",
                    f"--branch={TARGET_DEFAULT_BRANCH}",
                    f"--upload-pack={self._upload_pack}",
                    str(self._source),
                    str(repository),
                ),
                cwd=workspace,
                env=environment,
            )
            self._git(
                (
                    "-c",
                    "advice.detachedHead=false",
                    "checkout",
                    "--detach",
                    "--force",
                    snapshot.source_sha,
                ),
                cwd=repository,
                env=environment,
            )
            self._git(("remote", "remove", "origin"), cwd=repository, env=environment)
            tree = self._git(
                ("rev-parse", "HEAD^{tree}"), cwd=repository, env=environment
            ).strip()
            if tree != snapshot.source_tree.encode("ascii"):
                raise LandingArtifactError("source_tree")
            if not self._objects_are_independent(repository):
                raise LandingArtifactError("hardlinked_objects")
            yield repository, environment
        except BaseException as exc:
            failure = exc
            raise
        finally:
            cleanup_error: LandingArtifactError | None = None
            try:
                shutil.rmtree(workspace)
            except OSError as exc:
                cleanup_error = LandingArtifactError("workspace_cleanup")
                cleanup_error.__cause__ = exc
            guard_error: LandingArtifactError | None = None
            try:
                if self._source_guard(snapshot) != guard:
                    guard_error = LandingArtifactError("source_mutation")
            except LandingArtifactError as exc:
                guard_error = exc
            if failure is None and (cleanup_error is not None or guard_error is not None):
                raise cleanup_error or guard_error  # type: ignore[misc]

    def _source_guard(self, snapshot: LandingCandidateSnapshot) -> tuple[bytes, bytes, bytes]:
        if not self._source.is_dir() or not (self._source / ".git").is_dir():
            raise LandingArtifactError("source_identity")
        environment = self._environment(self._source)
        head = self._git(("rev-parse", "HEAD"), cwd=self._source, env=environment).strip()
        tree = self._git(
            ("rev-parse", "HEAD^{tree}"), cwd=self._source, env=environment
        ).strip()
        if head != snapshot.source_sha.encode() or tree != snapshot.source_tree.encode():
            raise LandingArtifactError("source_identity")
        status = self._git(
            ("status", "--porcelain=v1", "-z", "--untracked-files=no"),
            cwd=self._source,
            env=environment,
        )
        if status:
            raise LandingArtifactError("source_worktree")
        for relative in DEPLOY_MEMBERS:
            path = self._source.joinpath(*PurePosixPath(relative).parts)
            try:
                metadata = path.lstat()
            except OSError as exc:
                raise LandingArtifactError("source_file") from exc
            if (
                not stat.S_ISREG(metadata.st_mode)
                or stat.S_ISLNK(metadata.st_mode)
                or metadata.st_nlink != 1
                or metadata.st_mode & 0o111
            ):
                raise LandingArtifactError("source_file_type")
        refs = self._git(
            ("for-each-ref", "--format=%(refname)%00%(objectname)"),
            cwd=self._source,
            env=environment,
        )
        return head, tree, refs

    @staticmethod
    def _private_directory() -> Path:
        previous = os.umask(0o077)
        try:
            path = Path(tempfile.mkdtemp(prefix="adaptive-landing-artifact-"))
        finally:
            os.umask(previous)
        path.chmod(0o700)
        return path

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

    def _objects_are_independent(self, repository: Path) -> bool:
        candidate_objects = repository / ".git" / "objects"
        source_objects = self._source / ".git" / "objects"
        if (candidate_objects / "info" / "alternates").exists():
            return False

        def inodes(root: Path) -> set[tuple[int, int]]:
            result: set[tuple[int, int]] = set()
            for path in root.rglob("*"):
                try:
                    metadata = path.stat(follow_symlinks=False)
                except OSError:
                    continue
                if stat.S_ISREG(metadata.st_mode):
                    result.add((metadata.st_dev, metadata.st_ino))
            return result

        return not (inodes(candidate_objects) & inodes(source_objects))

    def _git(
        self,
        arguments: tuple[str, ...],
        *,
        cwd: Path,
        env: Mapping[str, str],
        input_bytes: bytes | None = None,
    ) -> bytes:
        try:
            completed = subprocess.run(
                (self._git_executable, *arguments),
                cwd=cwd,
                env=dict(env),
                input=input_bytes,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise LandingArtifactError("git_command") from exc
        if (
            completed.returncode != 0
            or len(completed.stdout) > 64 * 1_048_576
            or len(completed.stderr) > 1_048_576
        ):
            raise LandingArtifactError("git_command")
        return completed.stdout


class LandingArtifactPackager:
    def __init__(self, source: ExactGitLandingArtifactSource) -> None:
        if not isinstance(source, ExactGitLandingArtifactSource):
            raise LandingArtifactError("source_type")
        self._source = source

    def seal(
        self,
        snapshot: LandingCandidateSnapshot,
        attempt: LandingAttemptV1,
        evaluation: LandingEvaluationV1,
        output_directory: Path,
    ) -> LandingArtifactResult:
        self._validate_binding(snapshot, attempt, evaluation)
        source_inventory = _validated_inventory(snapshot.source_members, "source")
        candidate_inventory = _validated_inventory(snapshot.candidate_members, "candidate")
        self._validate_delta(snapshot, source_inventory, candidate_inventory)

        with self._source.materialize(snapshot) as (repository, environment):
            actual_source = _tree_members(
                self._source, repository, snapshot.source_sha, environment
            )
            if actual_source != snapshot.source_members:
                raise LandingArtifactError("source_inventory")
            if _read_regular(repository / "index.html") != snapshot.source_index_html:
                raise LandingArtifactError("source_index")
            if _read_regular(repository / "content.css") != snapshot.source_content_css:
                raise LandingArtifactError("source_css")
            _write_regular(repository / "index.html", snapshot.index_html)
            _write_regular(repository / "content.css", snapshot.content_css)
            self._source._git(
                ("add", "--", "index.html", "content.css"),
                cwd=repository,
                env=environment,
            )
            staged = tuple(
                sorted(
                    path
                    for path in self._source._git(
                        ("diff", "--cached", "--name-only", "-z"),
                        cwd=repository,
                        env=environment,
                    )
                    .decode("utf-8")
                    .split("\x00")
                    if path
                )
            )
            if staged != tuple(sorted(LANDING_WRITE_PATHS)):
                raise LandingArtifactError("changed_paths")
            tree = self._source._git(
                ("write-tree",), cwd=repository, env=environment
            ).strip().decode("ascii")
            if tree != snapshot.candidate_tree:
                raise LandingArtifactError("candidate_tree")
            commit_environment = {
                **environment,
                "GIT_AUTHOR_NAME": FIXED_COMMIT_NAME,
                "GIT_AUTHOR_EMAIL": FIXED_COMMIT_EMAIL,
                "GIT_COMMITTER_NAME": FIXED_COMMIT_NAME,
                "GIT_COMMITTER_EMAIL": FIXED_COMMIT_EMAIL,
                "GIT_AUTHOR_DATE": FIXED_COMMIT_TIME,
                "GIT_COMMITTER_DATE": FIXED_COMMIT_TIME,
            }
            commit = self._source._git(
                (
                    "-c",
                    "commit.gpgSign=false",
                    "commit-tree",
                    tree,
                    "-p",
                    snapshot.source_sha,
                ),
                cwd=repository,
                env=commit_environment,
                input_bytes=b"L5 landing candidate\n",
            ).strip().decode("ascii")
            if commit != snapshot.candidate_sha:
                raise LandingArtifactError("candidate_commit")
            actual_candidate = _tree_members(
                self._source, repository, commit, environment
            )
            if actual_candidate != snapshot.candidate_members:
                raise LandingArtifactError("candidate_inventory")
            contents = {
                path: _read_regular(repository.joinpath(*PurePosixPath(path).parts))
                for path in DEPLOY_MEMBERS
            }

        member_records = []
        for path in DEPLOY_MEMBERS:
            body = contents[path]
            source_member = source_inventory[path]
            candidate_member = candidate_inventory[path]
            if _git_blob_id(body) != candidate_member.object_id:
                raise LandingArtifactError("member_object")
            member_records.append(
                {
                    "archive_mode": "0644",
                    "candidate_object_id": candidate_member.object_id,
                    "path": path,
                    "provenance": (
                        "candidate" if path in LANDING_WRITE_PATHS else "source"
                    ),
                    "sha256": hashlib.sha256(body).hexdigest(),
                    "size_bytes": len(body),
                    "source_object_id": source_member.object_id,
                }
            )
        manifest = {
            "schema_version": 1,
            "artifact_kind": "static-deploy-root",
            "control_repository_id": CONTROL_REPOSITORY_ID,
            "target_repository_id": snapshot.repository_id,
            "source_sha": snapshot.source_sha,
            "source_tree": snapshot.source_tree,
            "candidate_sha": snapshot.candidate_sha,
            "candidate_tree": snapshot.candidate_tree,
            "changed_paths": list(sorted(LANDING_WRITE_PATHS)),
            "attempt_digest": attempt.attempt_digest,
            "evaluation_digest": evaluation.evaluation_digest,
            "archive": {
                "compression": "deflate-9",
                "dos_timestamp": "2000-01-01T00:00:00Z",
                "member_count": len(DEPLOY_MEMBERS),
                "member_mode": "0644",
                "members_sorted": True,
            },
            "members": member_records,
        }
        manifest_bytes = canonical_json(manifest)
        manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
        return self._write_pair(
            snapshot,
            attempt,
            evaluation,
            Path(output_directory),
            contents,
            manifest_bytes,
            manifest_digest,
        )

    @staticmethod
    def _validate_binding(
        snapshot: LandingCandidateSnapshot,
        attempt: LandingAttemptV1,
        evaluation: LandingEvaluationV1,
    ) -> None:
        if not isinstance(snapshot, LandingCandidateSnapshot):
            raise LandingArtifactError("snapshot_type")
        if not isinstance(attempt, LandingAttemptV1):
            raise LandingArtifactError("attempt_type")
        if not isinstance(evaluation, LandingEvaluationV1):
            raise LandingArtifactError("evaluation_type")
        if (
            snapshot.repository_id != TARGET_REPOSITORY_ID
            or not _HEX40.fullmatch(snapshot.source_sha)
            or not _HEX40.fullmatch(snapshot.source_tree)
            or not _HEX40.fullmatch(snapshot.candidate_sha)
            or not _HEX40.fullmatch(snapshot.candidate_tree)
            or snapshot.commit_time != FIXED_COMMIT_TIME
            or snapshot.clone_strategy != "no-local-no-hardlinks"
            or not snapshot.head_detached
            or not snapshot.object_storage_independent
            or snapshot.workspace_mode != 0o700
        ):
            raise LandingArtifactError("snapshot_identity")
        if (
            attempt.ordinal != snapshot.ordinal
            or attempt.exact_base_sha != snapshot.source_sha
            or attempt.exact_head_sha != snapshot.candidate_sha
            or attempt.workspace_result_digest != snapshot.workspace_result_digest
            or attempt.renderer_digest != snapshot.renderer_digest
        ):
            raise LandingArtifactError("attempt_binding")
        if (
            evaluation.attempt_digest != attempt.attempt_digest
            or evaluation.candidate_head_sha != snapshot.candidate_sha
            or evaluation.decision != "pass"
            or evaluation.reason_codes
            or evaluation.finding_digests
        ):
            raise LandingArtifactError("evaluation_binding")

    @staticmethod
    def _validate_delta(
        snapshot: LandingCandidateSnapshot,
        source: dict[str, GitTreeMember],
        candidate: dict[str, GitTreeMember],
    ) -> None:
        if set(source) != set(candidate):
            raise LandingArtifactError("tree_shape")
        calculated = tuple(
            sorted(path for path in source if source[path] != candidate[path])
        )
        if (
            tuple(snapshot.changed_paths) != tuple(sorted(LANDING_WRITE_PATHS))
            or calculated != tuple(sorted(LANDING_WRITE_PATHS))
        ):
            raise LandingArtifactError("changed_paths")
        for path in source:
            if source[path].mode != candidate[path].mode:
                raise LandingArtifactError("mode_drift")
        if any(path not in candidate for path in DEPLOY_MEMBERS):
            raise LandingArtifactError("deploy_inventory")
        if _git_blob_id(snapshot.source_index_html) != source["index.html"].object_id:
            raise LandingArtifactError("source_index")
        if _git_blob_id(snapshot.source_content_css) != source["content.css"].object_id:
            raise LandingArtifactError("source_css")
        if _git_blob_id(snapshot.index_html) != candidate["index.html"].object_id:
            raise LandingArtifactError("candidate_index")
        if _git_blob_id(snapshot.content_css) != candidate["content.css"].object_id:
            raise LandingArtifactError("candidate_css")

    def _write_pair(
        self,
        snapshot: LandingCandidateSnapshot,
        attempt: LandingAttemptV1,
        evaluation: LandingEvaluationV1,
        output_directory: Path,
        contents: dict[str, bytes],
        manifest_bytes: bytes,
        manifest_digest: str,
    ) -> LandingArtifactResult:
        output = _private_output_directory(output_directory)
        temporary_zip = _temporary_file(output, ".landing-zip-")
        installed_zip: Path | None = None
        temporary_sidecar: Path | None = None
        installed_sidecar: Path | None = None
        try:
            _write_zip(temporary_zip, contents)
            zip_digest = _sha256_file(temporary_zip)
            byte_length = temporary_zip.stat().st_size
            zip_name = f"therealaidarkfactory.online-{zip_digest}.zip"
            zip_path = output / zip_name
            sidecar_path = output / f"{zip_name}.sha256"
            sidecar_bytes = f"{zip_digest.upper()}  {zip_name}\n".encode("ascii")
            temporary_sidecar = _temporary_file(output, ".landing-sidecar-")
            _write_fsync(temporary_sidecar, sidecar_bytes)
            zip_present = _existing_exact_file(
                zip_path, digest=zip_digest, maximum=MAX_ARCHIVE_BYTES
            )
            sidecar_present = _existing_exact_file(
                sidecar_path, value=sidecar_bytes, maximum=1_024
            )
            if not zip_present:
                _install_noreplace(temporary_zip, zip_path)
                installed_zip = zip_path
                _fsync_directory(output)
            if not sidecar_present:
                _install_noreplace(temporary_sidecar, sidecar_path)
                installed_sidecar = sidecar_path
                _fsync_directory(output)
            artifact = SiteArtifactV1.from_facts(
                {
                    "schema_version": 1,
                    "site_id": "therealaidarkfactory.online",
                    "canonical_origin": "https://therealaidarkfactory.online/",
                    "source_sha": snapshot.source_sha,
                    "source_tree": snapshot.source_tree,
                    "candidate_sha": snapshot.candidate_sha,
                    "candidate_tree": snapshot.candidate_tree,
                    "input_digest": attempt.input_digest,
                    "spec_digest": attempt.spec_digest,
                    "profile_digest": attempt.profile_digest,
                    "attempt_digest": attempt.attempt_digest,
                    "evaluation_digest": evaluation.evaluation_digest,
                    "manifest_digest": manifest_digest,
                    "zip_sha256": zip_digest,
                    "sidecar_sha256": hashlib.sha256(sidecar_bytes).hexdigest(),
                    "member_count": len(DEPLOY_MEMBERS),
                    "byte_length": byte_length,
                    "disposition": "artifact_ready",
                }
            )
            return LandingArtifactResult(
                artifact,
                zip_path,
                sidecar_path,
                sidecar_bytes,
                manifest_bytes,
                DEPLOY_MEMBERS,
            )
        except BaseException as failure:
            cleanup_error: OSError | None = None
            for installed in (installed_sidecar, installed_zip):
                if installed is None:
                    continue
                try:
                    installed.unlink(missing_ok=True)
                except OSError as exc:
                    cleanup_error = cleanup_error or exc
            try:
                _fsync_directory(output)
            except LandingArtifactError as exc:
                if cleanup_error is None:
                    cleanup_error = OSError(str(exc))
            if cleanup_error is not None:
                raise LandingArtifactError("artifact_cleanup") from failure
            raise
        finally:
            temporary_zip.unlink(missing_ok=True)
            if temporary_sidecar is not None:
                temporary_sidecar.unlink(missing_ok=True)


def _validated_inventory(
    members: tuple[GitTreeMember, ...], name: str
) -> dict[str, GitTreeMember]:
    if not isinstance(members, tuple) or not members:
        raise LandingArtifactError(f"{name}_inventory")
    result: dict[str, GitTreeMember] = {}
    casefolded: set[str] = set()
    for member in members:
        if not isinstance(member, GitTreeMember):
            raise LandingArtifactError(f"{name}_inventory")
        _validate_path(member.path)
        folded = member.path.casefold()
        if member.path in result:
            raise LandingArtifactError("duplicate_path")
        if folded in casefolded:
            raise LandingArtifactError("case_collision")
        if member.mode != "100644":
            raise LandingArtifactError("member_type")
        if not _HEX40.fullmatch(member.object_id):
            raise LandingArtifactError("member_object")
        result[member.path] = member
        casefolded.add(folded)
    if tuple(result) != tuple(sorted(result)):
        raise LandingArtifactError(f"{name}_inventory_order")
    return result


def _validate_path(path: str) -> None:
    if not isinstance(path, str) or not path or "\\" in path or "\x00" in path:
        raise LandingArtifactError("invalid_path")
    try:
        path.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise LandingArtifactError("invalid_path") from exc
    candidate = PurePosixPath(path)
    if (
        candidate.is_absolute()
        or str(candidate) != path
        or any(part in {"", ".", ".."} for part in candidate.parts)
    ):
        raise LandingArtifactError("invalid_path")


def _tree_members(
    source: ExactGitLandingArtifactSource,
    repository: Path,
    revision: str,
    environment: Mapping[str, str],
) -> tuple[GitTreeMember, ...]:
    raw = source._git(
        ("ls-tree", "-r", "-z", "--full-tree", revision),
        cwd=repository,
        env=environment,
    )
    members: list[GitTreeMember] = []
    for entry in raw.split(b"\x00"):
        if not entry:
            continue
        try:
            metadata, encoded_path = entry.split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split(" ")
            path = encoded_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as exc:
            raise LandingArtifactError("tree_inventory") from exc
        if object_type != "blob":
            raise LandingArtifactError("member_type")
        members.append(GitTreeMember(path, mode, object_id))
    result = tuple(sorted(members, key=lambda item: item.path))
    _validated_inventory(result, "git")
    return result


def _git_blob_id(value: bytes) -> str:
    if not isinstance(value, bytes):
        raise LandingArtifactError("member_bytes")
    header = f"blob {len(value)}\0".encode("ascii")
    return hashlib.sha1(header + value, usedforsecurity=False).hexdigest()


def _read_regular(path: Path) -> bytes:
    try:
        metadata = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_mode & 0o111
            or not 0 < metadata.st_size <= MAX_MEMBER_BYTES
        ):
            raise LandingArtifactError("member_file")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            chunks: list[bytes] = []
            remaining = metadata.st_size
            while remaining:
                chunk = os.read(descriptor, min(remaining, 1_048_576))
                if not chunk:
                    raise LandingArtifactError("member_read")
                chunks.append(chunk)
                remaining -= len(chunk)
            value = b"".join(chunks)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise LandingArtifactError("member_read") from exc
    return value


def _write_regular(path: Path, value: bytes) -> None:
    if not isinstance(value, bytes) or not 0 < len(value) <= MAX_MEMBER_BYTES:
        raise LandingArtifactError("member_write")
    try:
        metadata = path.lstat()
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or metadata.st_nlink != 1
            or metadata.st_mode & 0o111
        ):
            raise LandingArtifactError("member_file")
        descriptor = os.open(path, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
        try:
            view = memoryview(value)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise LandingArtifactError("member_write")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise LandingArtifactError("member_write") from exc


def _private_output_directory(path: Path) -> Path:
    if not path.is_absolute():
        raise LandingArtifactError("output_path")
    previous = os.umask(0o077)
    try:
        path.mkdir(parents=True, mode=0o700, exist_ok=True)
    finally:
        os.umask(previous)
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise LandingArtifactError("output_path") from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or stat.S_IMODE(metadata.st_mode) & 0o077
    ):
        raise LandingArtifactError("output_boundary")
    return path


def _temporary_file(directory: Path, prefix: str) -> Path:
    previous = os.umask(0o077)
    try:
        descriptor, name = tempfile.mkstemp(prefix=prefix, dir=directory)
    finally:
        os.umask(previous)
    os.close(descriptor)
    return Path(name)


def _write_zip(path: Path, contents: dict[str, bytes]) -> None:
    try:
        with path.open("w+b") as stream:
            with zipfile.ZipFile(
                stream,
                "w",
                compression=zipfile.ZIP_DEFLATED,
                compresslevel=9,
                strict_timestamps=True,
            ) as archive:
                archive.comment = b""
                for name in DEPLOY_MEMBERS:
                    info = zipfile.ZipInfo(name, ARCHIVE_TIMESTAMP)
                    info.create_system = 3
                    info.external_attr = ARCHIVE_MODE << 16
                    info.internal_attr = 0
                    info.extra = b""
                    info.comment = b""
                    info.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(
                        info,
                        contents[name],
                        compress_type=zipfile.ZIP_DEFLATED,
                        compresslevel=9,
                    )
            stream.flush()
            os.fsync(stream.fileno())
    except (OSError, ValueError, zipfile.BadZipFile) as exc:
        raise LandingArtifactError("zip_write") from exc
    if not 0 < path.stat().st_size <= MAX_ARCHIVE_BYTES:
        raise LandingArtifactError("zip_size")


def _write_fsync(path: Path, value: bytes) -> None:
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_TRUNC | os.O_NOFOLLOW)
        try:
            view = memoryview(value)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise LandingArtifactError("sidecar_write")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise LandingArtifactError("sidecar_write") from exc


def _install_noreplace(source: Path, destination: Path) -> None:
    try:
        os.link(source, destination, follow_symlinks=False)
        source.unlink()
    except FileExistsError as exc:
        raise LandingArtifactError("artifact_exists") from exc
    except OSError as exc:
        if exc.errno == errno.EEXIST:
            raise LandingArtifactError("artifact_exists") from exc
        raise LandingArtifactError("artifact_install") from exc


def _existing_exact_file(
    path: Path,
    *,
    digest: str | None = None,
    value: bytes | None = None,
    maximum: int,
) -> bool:
    if (digest is None) == (value is None):
        raise LandingArtifactError("artifact_recovery")
    try:
        metadata = path.lstat()
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise LandingArtifactError("artifact_exists") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or metadata.st_uid != os.geteuid()
        or metadata.st_nlink != 1
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or not 0 < metadata.st_size <= maximum
    ):
        raise LandingArtifactError("artifact_exists")
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            body = bytearray()
            while chunk := os.read(descriptor, min(1_048_576, maximum + 1)):
                body.extend(chunk)
                if len(body) > maximum:
                    raise LandingArtifactError("artifact_exists")
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise LandingArtifactError("artifact_exists") from exc
    if value is not None:
        matches = bytes(body) == value
    else:
        matches = hashlib.sha256(body).hexdigest() == digest
    if not matches:
        raise LandingArtifactError("artifact_exists")
    return True


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            while chunk := stream.read(1_048_576):
                digest.update(chunk)
    except OSError as exc:
        raise LandingArtifactError("artifact_hash") from exc
    return digest.hexdigest()


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
    except OSError as exc:
        raise LandingArtifactError("output_fsync") from exc
