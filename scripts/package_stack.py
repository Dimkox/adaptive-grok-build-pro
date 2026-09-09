from __future__ import annotations

import argparse
import hashlib
import os
import secrets
import stat
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import BinaryIO, NamedTuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.manifest import (
    READ_CHUNK_BYTES,
    ManifestEntry,
    is_included_relative_path,
    render_manifest,
    snapshot_files,
    stream_entry,
)
FIXED_ZIP_TIME = (2026, 8, 14, 0, 0, 0)
TEMP_CREATE_ATTEMPTS = 32


class PackageError(RuntimeError):
    pass


def _temporary_flags() -> int:
    try:
        return os.O_RDWR | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC
    except AttributeError as exc:
        raise PackageError('secure temporary archive creation is unsupported on this platform') from exc


def _directory_flags() -> int:
    try:
        return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    except AttributeError as exc:
        raise PackageError('secure output directory binding is unsupported on this platform') from exc


def _path_directory_flags() -> int:
    try:
        return os.O_PATH | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    except AttributeError as exc:
        raise PackageError('secure output directory creation is unsupported on this platform') from exc


class _OutputDirectory(NamedTuple):
    requested_path: Path
    canonical_path: Path
    descriptor: int
    device: int
    inode: int


class _TemporaryArchive(NamedTuple):
    name: str
    file: BinaryIO
    device: int
    inode: int


class _TrackedHeadFile(NamedTuple):
    path: Path
    relative_path: str
    object_id: str
    mode: int


class _ReleaseHead(NamedTuple):
    commit_oid: str
    tree_oid: str


class ReleaseSnapshot(NamedTuple):
    head_oid: str
    tree_oid: str
    entries: tuple[ManifestEntry, ...]
    included_paths: tuple[Path, ...]
    member_modes: tuple[tuple[str, int], ...]


class _PublicationBackup(NamedTuple):
    target_name: str
    backup_name: str | None
    device: int | None
    inode: int | None


def _path_chain(path: Path) -> list[Path]:
    chain = [path]
    while chain[-1].parent != chain[-1]:
        chain.append(chain[-1].parent)
    return list(reversed(chain))


def _validate_ancestor_authority(canonical_path: Path, effective_uid: int) -> None:
    chain = _path_chain(canonical_path)
    try:
        metadata = [path.lstat() for path in chain]
    except OSError as exc:
        raise PackageError('cannot inspect archive output ancestor authority') from exc
    for ancestor, child in zip(metadata, metadata[1:]):
        if not stat.S_ISDIR(ancestor.st_mode):
            raise PackageError('archive output ancestor is not a directory')
        if ancestor.st_uid not in {0, effective_uid}:
            raise PackageError('archive output ancestor owner is outside the trusted boundary')
        if not stat.S_IMODE(ancestor.st_mode) & 0o022:
            continue
        sticky = bool(ancestor.st_mode & stat.S_ISVTX)
        if not sticky or child.st_uid != effective_uid:
            raise PackageError('archive output ancestor grants untrusted rename authority')


def _validate_child_creation_authority(canonical_parent: Path, effective_uid: int) -> None:
    try:
        metadata = canonical_parent.lstat()
    except OSError as exc:
        raise PackageError('cannot inspect archive output creation parent') from exc
    if not stat.S_ISDIR(metadata.st_mode):
        raise PackageError('archive output creation parent is not a directory')
    if metadata.st_uid not in {0, effective_uid}:
        raise PackageError('archive output creation parent owner is outside the trusted boundary')
    if not stat.S_IMODE(metadata.st_mode) & 0o022:
        return
    if not metadata.st_mode & stat.S_ISVTX or metadata.st_uid not in {0, effective_uid}:
        raise PackageError('archive output creation parent grants untrusted rename authority')


def _cleanup_created_output_parents(
    created: list[Path],
    primary_error: BaseException,
) -> None:
    for path in reversed(created):
        try:
            path.rmdir()
        except FileNotFoundError:
            continue
        except OSError as cleanup_error:
            primary_error.add_note(f'created output parent cleanup failed: {cleanup_error}')


def _ensure_output_parent(output: Path) -> list[Path]:
    requested_path = output.parent.absolute()
    missing: list[Path] = []
    cursor = requested_path
    while True:
        try:
            cursor.lstat()
        except FileNotFoundError:
            if cursor.parent == cursor:
                raise PackageError('archive output path has no existing ancestor')
            missing.append(cursor)
            cursor = cursor.parent
            continue
        except OSError as exc:
            raise PackageError('cannot inspect archive output path safely') from exc
        break
    try:
        effective_uid = os.geteuid()
        canonical_parent = cursor.resolve(strict=True)
    except (AttributeError, OSError) as exc:
        raise PackageError('cannot resolve archive output creation boundary') from exc
    _validate_ancestor_authority(cursor, effective_uid)
    _validate_ancestor_authority(canonical_parent, effective_uid)
    _validate_child_creation_authority(canonical_parent, effective_uid)
    created: list[Path] = []
    parent_descriptor: int | None = None
    try:
        parent_descriptor = os.open(canonical_parent, _directory_flags())
        for path in reversed(missing):
            name = path.name
            os.mkdir(name, mode=0o700, dir_fd=parent_descriptor)
            created.append(path)
            binding_descriptor: int | None = None
            child_descriptor: int | None = None
            try:
                binding_descriptor = os.open(
                    name,
                    _path_directory_flags(),
                    dir_fd=parent_descriptor,
                )
                binding = os.fstat(binding_descriptor)
                named = os.stat(name, dir_fd=parent_descriptor, follow_symlinks=False)
                if (
                    not stat.S_ISDIR(binding.st_mode)
                    or binding.st_uid != effective_uid
                    or binding.st_dev != named.st_dev
                    or binding.st_ino != named.st_ino
                ):
                    raise PackageError('created archive output parent identity changed')
                os.chmod(
                    name,
                    0o700,
                    dir_fd=parent_descriptor,
                    follow_symlinks=False,
                )
                child_descriptor = os.open(
                    name,
                    _directory_flags(),
                    dir_fd=parent_descriptor,
                )
                os.fchmod(child_descriptor, 0o700)
                metadata = os.fstat(child_descriptor)
                if (
                    not stat.S_ISDIR(metadata.st_mode)
                    or metadata.st_uid != effective_uid
                    or metadata.st_dev != binding.st_dev
                    or metadata.st_ino != binding.st_ino
                    or stat.S_IMODE(metadata.st_mode) != 0o700
                ):
                    raise PackageError('created archive output parent is not private')
                previous_descriptor = parent_descriptor
                parent_descriptor = child_descriptor
                child_descriptor = None
                os.close(previous_descriptor)
            finally:
                if child_descriptor is not None:
                    os.close(child_descriptor)
                if binding_descriptor is not None:
                    os.close(binding_descriptor)
    except BaseException as exc:
        _cleanup_created_output_parents(created, exc)
        if isinstance(exc, PackageError):
            raise
        raise PackageError('cannot create private archive output parent') from exc
    finally:
        if parent_descriptor is not None:
            os.close(parent_descriptor)
    return created


def _open_output_directory(output: Path) -> _OutputDirectory:
    requested_path = output.parent.absolute()
    try:
        canonical_path = requested_path.resolve(strict=True)
        descriptor = os.open(canonical_path, _directory_flags())
    except OSError as exc:
        raise PackageError('cannot bind archive output directory safely') from exc
    try:
        metadata = os.fstat(descriptor)
        effective_uid = os.geteuid()
    except (AttributeError, OSError) as exc:
        os.close(descriptor)
        raise PackageError('cannot inspect archive output directory safely') from exc
    if not stat.S_ISDIR(metadata.st_mode):
        os.close(descriptor)
        raise PackageError('archive output parent is not a directory')
    if metadata.st_uid != effective_uid or stat.S_IMODE(metadata.st_mode) & 0o022:
        os.close(descriptor)
        raise PackageError('archive output parent must be owned by the effective user and private')
    try:
        _validate_ancestor_authority(requested_path, effective_uid)
        _validate_ancestor_authority(canonical_path, effective_uid)
    except BaseException:
        os.close(descriptor)
        raise
    directory = _OutputDirectory(
        requested_path,
        canonical_path,
        descriptor,
        metadata.st_dev,
        metadata.st_ino,
    )
    try:
        _validate_output_directory_binding(directory)
    except BaseException:
        os.close(descriptor)
        raise
    return directory


def _validate_output_directory_binding(directory: _OutputDirectory) -> None:
    try:
        metadata = directory.requested_path.stat()
    except OSError as exc:
        raise PackageError('archive output directory binding changed') from exc
    if (
        not stat.S_ISDIR(metadata.st_mode)
        or metadata.st_dev != directory.device
        or metadata.st_ino != directory.inode
    ):
        raise PackageError('archive output directory binding changed')


def _existing_output_mode(directory: _OutputDirectory, output_name: str) -> int | None:
    try:
        metadata = os.stat(
            output_name,
            dir_fd=directory.descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise PackageError('cannot inspect archive output safely') from exc
    if not stat.S_ISREG(metadata.st_mode):
        raise PackageError('archive output must be a regular non-symlink file')
    return stat.S_IMODE(metadata.st_mode)


def _create_temporary_archive(
    directory: _OutputDirectory,
    output_name: str,
) -> _TemporaryArchive:
    existing_mode = _existing_output_mode(directory, output_name)
    return _create_temporary_file(directory, output_name, existing_mode)


def _create_temporary_file(
    directory: _OutputDirectory,
    target_name: str,
    existing_mode: int | None,
) -> _TemporaryArchive:
    for _attempt in range(TEMP_CREATE_ATTEMPTS):
        name = f'.{target_name}.{secrets.token_hex(16)}.tmp'
        try:
            descriptor = os.open(
                name,
                _temporary_flags(),
                0o666,
                dir_fd=directory.descriptor,
            )
        except FileExistsError:
            continue
        except OSError as exc:
            raise PackageError('cannot create temporary archive safely') from exc
        try:
            if existing_mode is not None:
                os.fchmod(descriptor, existing_mode)
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise PackageError('temporary archive is not a regular file')
            file = os.fdopen(descriptor, 'w+b')
        except BaseException:
            os.close(descriptor)
            _unlink_directory_entry(directory, name)
            raise
        return _TemporaryArchive(name, file, metadata.st_dev, metadata.st_ino)
    raise PackageError('cannot allocate a unique temporary archive name')


def _unlink_directory_entry(directory: _OutputDirectory, name: str) -> None:
    try:
        os.unlink(name, dir_fd=directory.descriptor)
    except FileNotFoundError:
        return
    except OSError as exc:
        raise PackageError(f'cannot remove archive output entry safely: {name}') from exc


def _validate_temporary_name(
    directory: _OutputDirectory,
    temporary: _TemporaryArchive,
) -> None:
    try:
        metadata = os.stat(
            temporary.name,
            dir_fd=directory.descriptor,
            follow_symlinks=False,
        )
    except OSError as exc:
        raise PackageError('temporary archive name changed before publication') from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or metadata.st_dev != temporary.device
        or metadata.st_ino != temporary.inode
    ):
        raise PackageError('temporary archive identity changed before publication')


def _digest_temporary_archive(temporary: _TemporaryArchive) -> str:
    temporary.file.flush()
    temporary.file.seek(0)
    digest = hashlib.sha256()
    while chunk := temporary.file.read(READ_CHUNK_BYTES):
        digest.update(chunk)
    return digest.hexdigest()


def _cleanup_temporary(
    directory: _OutputDirectory,
    temporary: _TemporaryArchive,
) -> list[BaseException]:
    errors: list[BaseException] = []
    try:
        temporary.file.close()
    except BaseException as exc:
        errors.append(exc)
    try:
        _unlink_directory_entry(directory, temporary.name)
    except BaseException as exc:
        errors.append(exc)
    return errors


def _validate_published_output(
    directory: _OutputDirectory,
    output_name: str,
    temporary: _TemporaryArchive,
) -> None:
    try:
        metadata = os.stat(
            output_name,
            dir_fd=directory.descriptor,
            follow_symlinks=False,
        )
    except OSError as exc:
        raise PackageError('published archive name is unavailable') from exc
    if (
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_dev == temporary.device
        and metadata.st_ino == temporary.inode
    ):
        return
    try:
        _unlink_directory_entry(directory, output_name)
    except PackageError as exc:
        raise PackageError('published archive identity mismatch could not be removed') from exc
    raise PackageError('published archive identity does not match the verified descriptor')


def _stage_sidecar(
    directory: _OutputDirectory,
    output_name: str,
    digest: str,
) -> _TemporaryArchive:
    sidecar_name = f'{output_name}.sha256'
    payload = f'{digest}  {output_name}\n'.encode('utf-8')
    existing_mode = _existing_sidecar_mode(directory, sidecar_name)
    temporary = _create_temporary_file(directory, sidecar_name, existing_mode)
    try:
        temporary.file.write(payload)
        temporary.file.flush()
        metadata = os.fstat(temporary.file.fileno())
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_dev != temporary.device
            or metadata.st_ino != temporary.inode
        ):
            raise PackageError('temporary checksum descriptor identity changed')
        _validate_temporary_name(directory, temporary)
        return temporary
    except BaseException as exc:
        for cleanup_error in _cleanup_temporary(directory, temporary):
            exc.add_note(f'temporary checksum cleanup failed: {cleanup_error}')
        raise


def _write_sidecar(directory: _OutputDirectory, output_name: str, digest: str) -> None:
    sidecar_name = f'{output_name}.sha256'
    temporary = _stage_sidecar(directory, output_name, digest)
    try:
        os.replace(
            temporary.name,
            sidecar_name,
            src_dir_fd=directory.descriptor,
            dst_dir_fd=directory.descriptor,
        )
        _validate_published_entry(directory, sidecar_name, temporary, 'checksum')
        temporary.file.close()
    except BaseException as exc:
        for cleanup_error in _cleanup_temporary(directory, temporary):
            exc.add_note(f'temporary checksum cleanup failed: {cleanup_error}')
        raise


def _existing_sidecar_mode(directory: _OutputDirectory, sidecar_name: str) -> int | None:
    try:
        metadata = os.stat(
            sidecar_name,
            dir_fd=directory.descriptor,
            follow_symlinks=False,
        )
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise PackageError('cannot inspect archive checksum entry safely') from exc
    if stat.S_ISDIR(metadata.st_mode):
        raise PackageError('archive checksum entry must not be a directory')
    if stat.S_ISREG(metadata.st_mode):
        return stat.S_IMODE(metadata.st_mode)
    return None


def _validate_published_entry(
    directory: _OutputDirectory,
    name: str,
    temporary: _TemporaryArchive,
    label: str,
) -> None:
    try:
        metadata = os.stat(name, dir_fd=directory.descriptor, follow_symlinks=False)
    except OSError as exc:
        raise PackageError(f'published archive {label} is unavailable') from exc
    if (
        stat.S_ISREG(metadata.st_mode)
        and metadata.st_dev == temporary.device
        and metadata.st_ino == temporary.inode
    ):
        return
    try:
        _unlink_directory_entry(directory, name)
    except PackageError as exc:
        raise PackageError(f'published archive {label} mismatch could not be removed') from exc
    raise PackageError(f'published archive {label} does not match the verified descriptor')


def _git_invocation(root: Path, arguments: list[str]) -> tuple[list[str], dict[str, str]]:
    try:
        canonical_root = root.resolve(strict=True)
    except OSError as exc:
        raise PackageError('cannot resolve tracked HEAD for release packaging') from exc
    environment = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith('GIT_')
    }
    environment.update(
        {
            'GIT_CONFIG_COUNT': '0',
            'GIT_CONFIG_GLOBAL': os.devnull,
            'GIT_CONFIG_NOSYSTEM': '1',
            'GIT_CONFIG_SYSTEM': os.devnull,
            'GIT_GRAFT_FILE': os.devnull,
            'GIT_NO_REPLACE_OBJECTS': '1',
            'GIT_OPTIONAL_LOCKS': '0',
        }
    )
    command = [
        'git',
        '--no-replace-objects',
        '-c',
        f'safe.directory={canonical_root}',
        '-c',
        'core.useReplaceRefs=false',
        '-c',
        f'core.worktree={canonical_root}',
        '-c',
        'core.bare=false',
        '-c',
        'core.fsmonitor=false',
        '-C',
        str(canonical_root),
        *arguments,
    ]
    return command, environment


def _git_command(root: Path, arguments: list[str]) -> subprocess.CompletedProcess[bytes]:
    command, environment = _git_invocation(root, arguments)
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            env=environment,
        )
    except OSError as exc:
        raise PackageError('cannot inspect tracked HEAD for release packaging') from exc


def _git_oid(root: Path, revision: str) -> str:
    result = _git_command(root, ['rev-parse', '--verify', revision])
    encoded = result.stdout.strip()
    if (
        result.returncode != 0
        or len(encoded) not in {40, 64}
        or any(character not in b'0123456789abcdef' for character in encoded)
    ):
        raise PackageError('cannot resolve immutable tracked HEAD for release packaging')
    return encoded.decode('ascii')


def _release_repository_root(root: Path) -> Path:
    canonical_root = root.resolve(strict=True)
    top_level = _git_command(canonical_root, ['rev-parse', '--show-toplevel'])
    if top_level.returncode != 0:
        raise PackageError('release packaging requires a Git repository at tracked HEAD')
    try:
        repository_root = Path(os.fsdecode(top_level.stdout).strip()).resolve(strict=True)
    except OSError as exc:
        raise PackageError('cannot resolve the tracked HEAD repository root') from exc
    if repository_root != canonical_root:
        raise PackageError('release packaging root must be the tracked HEAD repository root')
    return canonical_root


def _capture_release_head(root: Path) -> _ReleaseHead:
    commit_oid = _git_oid(root, 'HEAD^{commit}')
    tree_oid = _git_oid(root, f'{commit_oid}^{{tree}}')
    return _ReleaseHead(commit_oid, tree_oid)


def _git_diff_records(
    root: Path,
    head: _ReleaseHead,
    *,
    cached: bool,
) -> list[tuple[bytes, bytes]]:
    arguments = ['diff']
    if cached:
        arguments.append('--cached')
    arguments.extend(
        [
            '--name-status',
            '-z',
            '--no-renames',
            '--no-ext-diff',
            '--ignore-submodules=none',
            head.commit_oid,
            '--',
        ]
    )
    result = _git_command(root, arguments)
    if result.returncode != 0:
        raise PackageError('cannot verify the clean tracked HEAD for release packaging')
    fields = result.stdout.split(b'\0')
    if fields[-1:] == [b'']:
        fields.pop()
    if len(fields) % 2:
        raise PackageError('tracked HEAD change inventory is malformed')
    return list(zip(fields[::2], fields[1::2]))


def _require_release_head(
    root: Path,
    head: _ReleaseHead,
    *,
    allowed_worktree_paths: frozenset[bytes] = frozenset(),
) -> None:
    current_oid = _git_oid(root, 'HEAD^{commit}')
    if current_oid != head.commit_oid:
        raise PackageError('tracked HEAD changed during release packaging')
    current_tree_oid = _git_oid(root, f'{current_oid}^{{tree}}')
    if current_tree_oid != head.tree_oid:
        raise PackageError('tracked HEAD tree changed during release packaging')
    if _git_diff_records(root, head, cached=True):
        raise PackageError('tracked HEAD source changed during release packaging')
    worktree_changes = _git_diff_records(root, head, cached=False)
    if any(
        status != b'M' or path not in allowed_worktree_paths
        for status, path in worktree_changes
    ):
        raise PackageError('tracked HEAD source changed during release packaging')


def _tracked_head_files(root: Path, tree_oid: str) -> list[_TrackedHeadFile]:
    result = _git_command(root, ['ls-tree', '-r', '-z', tree_oid])
    if result.returncode != 0:
        raise PackageError('cannot read tracked HEAD inventory for release packaging')
    files: list[_TrackedHeadFile] = []
    for record in result.stdout.rstrip(b'\0').split(b'\0') if result.stdout else []:
        try:
            metadata, encoded_path = record.split(b'\t', 1)
            mode, kind, object_id = metadata.decode('ascii').split(' ')
            relative_path = os.fsdecode(encoded_path)
            parsed_mode = int(mode, 8)
        except (ValueError, UnicodeDecodeError) as exc:
            raise PackageError('tracked HEAD inventory is malformed') from exc
        if kind != 'blob' or mode not in {'100644', '100755'}:
            continue
        if not is_included_relative_path(relative_path):
            continue
        files.append(_TrackedHeadFile(root / relative_path, relative_path, object_id, parsed_mode))
    return sorted(files, key=lambda item: item.relative_path)


def _head_blob_digests(
    root: Path,
    files: list[_TrackedHeadFile],
) -> dict[str, tuple[int, str]]:
    command, environment = _git_invocation(root, ['cat-file', '--batch'])
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            env=environment,
        )
    except OSError as exc:
        raise PackageError('cannot read tracked HEAD content for release packaging') from exc
    digests: dict[str, tuple[int, str]] = {}
    try:
        if process.stdin is None or process.stdout is None:
            raise PackageError('cannot bind tracked HEAD content for release packaging')
        for file in files:
            process.stdin.write(f'{file.object_id}\n'.encode('ascii'))
            process.stdin.flush()
            header = process.stdout.readline()
            try:
                object_id, kind, encoded_size = header.decode('ascii').rstrip('\n').split(' ')
                size = int(encoded_size)
            except (ValueError, UnicodeDecodeError) as exc:
                raise PackageError('tracked HEAD content response is malformed') from exc
            if object_id != file.object_id or kind != 'blob' or size < 0:
                raise PackageError('tracked HEAD content identity is inconsistent')
            digest = hashlib.sha256()
            remaining = size
            while remaining:
                chunk = process.stdout.read(min(READ_CHUNK_BYTES, remaining))
                if not chunk:
                    raise PackageError('tracked HEAD content ended unexpectedly')
                digest.update(chunk)
                remaining -= len(chunk)
            if process.stdout.read(1) != b'\n':
                raise PackageError('tracked HEAD content boundary is malformed')
            digests[file.relative_path] = (size, digest.hexdigest())
    except (BrokenPipeError, OSError) as exc:
        raise PackageError('cannot read tracked HEAD content for release packaging') from exc
    finally:
        if process.stdin is not None:
            try:
                process.stdin.close()
            except BrokenPipeError:
                pass
        returncode = process.wait()
        if process.stdout is not None:
            process.stdout.close()
    if returncode != 0:
        raise PackageError('cannot read tracked HEAD content for release packaging')
    return digests


def _release_snapshot_from_tracked_head(root: Path) -> ReleaseSnapshot:
    canonical_root = _release_repository_root(root)
    head = _capture_release_head(canonical_root)
    _require_release_head(canonical_root, head)
    files = _tracked_head_files(canonical_root, head.tree_oid)
    entries = snapshot_files(canonical_root, files=[file.path for file in files])
    head_digests = _head_blob_digests(canonical_root, files)
    tracked_by_path = {file.relative_path: file for file in files}
    for entry in entries:
        tracked = tracked_by_path[entry.relative_path]
        size, digest = head_digests[entry.relative_path]
        if entry.identity.size != size or entry.digest != digest:
            raise PackageError(f'release source differs from tracked HEAD: {entry.relative_path}')
        if bool(entry.identity.mode & 0o111) != bool(tracked.mode & 0o111):
            raise PackageError(f'release source mode differs from tracked HEAD: {entry.relative_path}')
    snapshot = ReleaseSnapshot(
        head.commit_oid,
        head.tree_oid,
        tuple(entries),
        tuple(file.path.resolve(strict=True) for file in files),
        tuple((file.relative_path, file.mode) for file in files),
    )
    _require_release_head(canonical_root, head)
    return snapshot


def _paths_overlap(left: Path, right: Path) -> bool:
    return left == right or left in right.parents or right in left.parents


def _validate_release_output(output: Path, snapshot: ReleaseSnapshot) -> None:
    try:
        canonical_output = output.resolve(strict=False)
        canonical_sidecar = output.with_name(f'{output.name}.sha256').resolve(strict=False)
    except OSError as exc:
        raise PackageError('cannot resolve release output path safely') from exc
    for label, target in (('archive', canonical_output), ('checksum', canonical_sidecar)):
        for source in snapshot.included_paths:
            if _paths_overlap(target, source):
                raise PackageError(
                    f'release {label} output overlaps included tracked source: '
                    f'{source}'
                )


def _release_output_git_paths(root: Path, output: Path) -> frozenset[bytes]:
    canonical_root = root.resolve(strict=True)
    paths: set[bytes] = set()
    for target in (output, output.with_name(f'{output.name}.sha256')):
        try:
            relative = target.resolve(strict=False).relative_to(canonical_root)
        except ValueError:
            continue
        paths.add(os.fsencode(relative.as_posix()))
    return frozenset(paths)


def _stage_archive(
    root: Path,
    directory: _OutputDirectory,
    output_name: str,
    entries: list[ManifestEntry] | tuple[ManifestEntry, ...],
    *,
    member_modes: dict[str, int] | None = None,
) -> tuple[_TemporaryArchive, str]:
    manifest = render_manifest(root, entries=list(entries))
    members = [
        (
            entry.relative_path,
            entry.identity.mode
            if member_modes is None
            else member_modes[entry.relative_path],
            entry,
        )
        for entry in entries
    ]
    members.append(('MANIFEST.sha256', 0o100644, manifest))
    temporary = _create_temporary_archive(directory, output_name)
    try:
        _validate_output_directory_binding(directory)
        with zipfile.ZipFile(
            temporary.file,
            'w',
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for rel, mode, source in sorted(members, key=lambda member: member[0]):
                info = zipfile.ZipInfo(f'adaptive-grok-build-pro/{rel}', FIXED_ZIP_TIME)
                info.external_attr = (mode & 0xFFFF) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                if isinstance(source, bytes):
                    archive.writestr(info, source)
                else:
                    with archive.open(info, 'w') as archive_file:
                        stream_entry(root, source, archive_file)
        temporary.file.flush()
        held_metadata = os.fstat(temporary.file.fileno())
        if (
            not stat.S_ISREG(held_metadata.st_mode)
            or held_metadata.st_dev != temporary.device
            or held_metadata.st_ino != temporary.inode
        ):
            raise PackageError('temporary archive descriptor identity changed')
        _validate_temporary_name(directory, temporary)
        digest = _digest_temporary_archive(temporary)
        _validate_temporary_name(directory, temporary)
        return temporary, digest
    except BaseException as exc:
        for cleanup_error in _cleanup_temporary(directory, temporary):
            exc.add_note(f'temporary archive cleanup failed: {cleanup_error}')
        raise


def _prepare_publication_backup(
    directory: _OutputDirectory,
    target_name: str,
) -> _PublicationBackup:
    try:
        original = os.stat(target_name, dir_fd=directory.descriptor, follow_symlinks=False)
    except FileNotFoundError:
        return _PublicationBackup(target_name, None, None, None)
    except OSError as exc:
        raise PackageError(f'cannot inspect preexisting release output: {target_name}') from exc
    for _attempt in range(TEMP_CREATE_ATTEMPTS):
        backup_name = f'.{target_name}.{secrets.token_hex(16)}.rollback'
        try:
            os.link(
                target_name,
                backup_name,
                src_dir_fd=directory.descriptor,
                dst_dir_fd=directory.descriptor,
                follow_symlinks=False,
            )
        except FileExistsError:
            continue
        except OSError as exc:
            raise PackageError(f'cannot preserve preexisting release output: {target_name}') from exc
        try:
            backup = os.stat(backup_name, dir_fd=directory.descriptor, follow_symlinks=False)
            current = os.stat(target_name, dir_fd=directory.descriptor, follow_symlinks=False)
        except OSError as exc:
            _unlink_directory_entry(directory, backup_name)
            raise PackageError(f'preexisting release output changed: {target_name}') from exc
        if (
            backup.st_dev != original.st_dev
            or backup.st_ino != original.st_ino
            or current.st_dev != original.st_dev
            or current.st_ino != original.st_ino
        ):
            _unlink_directory_entry(directory, backup_name)
            raise PackageError(f'preexisting release output changed: {target_name}')
        return _PublicationBackup(target_name, backup_name, original.st_dev, original.st_ino)
    raise PackageError(f'cannot allocate release rollback name: {target_name}')


def _validate_named_identity(
    directory: _OutputDirectory,
    name: str,
    device: int,
    inode: int,
    label: str,
) -> None:
    try:
        metadata = os.stat(name, dir_fd=directory.descriptor, follow_symlinks=False)
    except OSError as exc:
        raise PackageError(f'{label} is unavailable') from exc
    if metadata.st_dev != device or metadata.st_ino != inode:
        raise PackageError(f'{label} identity changed')


def _discard_publication_backup(
    directory: _OutputDirectory,
    backup: _PublicationBackup,
) -> None:
    if backup.backup_name is None:
        return
    if backup.device is None or backup.inode is None:
        raise PackageError('release rollback identity is incomplete')
    _validate_named_identity(
        directory,
        backup.backup_name,
        backup.device,
        backup.inode,
        'release rollback entry',
    )
    _unlink_directory_entry(directory, backup.backup_name)


def _rollback_release_publication(
    directory: _OutputDirectory,
    backups: list[_PublicationBackup],
    published: dict[str, _TemporaryArchive],
) -> list[BaseException]:
    errors: list[BaseException] = []
    for backup in reversed(backups):
        temporary = published.get(backup.target_name)
        try:
            if temporary is None:
                _discard_publication_backup(directory, backup)
                continue
            _validate_named_identity(
                directory,
                backup.target_name,
                temporary.device,
                temporary.inode,
                'published release output',
            )
            if backup.backup_name is None:
                _unlink_directory_entry(directory, backup.target_name)
                continue
            if backup.device is None or backup.inode is None:
                raise PackageError('release rollback identity is incomplete')
            _validate_named_identity(
                directory,
                backup.backup_name,
                backup.device,
                backup.inode,
                'release rollback entry',
            )
            os.replace(
                backup.backup_name,
                backup.target_name,
                src_dir_fd=directory.descriptor,
                dst_dir_fd=directory.descriptor,
            )
            _validate_named_identity(
                directory,
                backup.target_name,
                backup.device,
                backup.inode,
                'restored release output',
            )
        except BaseException as exc:
            errors.append(exc)
    return errors


def write_archive(
    root: Path,
    output: Path,
    *,
    entries: list[ManifestEntry] | None = None,
) -> str:
    if entries is None:
        entries = snapshot_files(root)
    created_parents = _ensure_output_parent(output)
    try:
        directory = _open_output_directory(output)
        try:
            _existing_sidecar_mode(directory, f'{output.name}.sha256')
            temporary, digest = _stage_archive(root, directory, output.name, entries)
            try:
                _validate_output_directory_binding(directory)
                os.replace(
                    temporary.name,
                    output.name,
                    src_dir_fd=directory.descriptor,
                    dst_dir_fd=directory.descriptor,
                )
                _validate_published_output(directory, output.name, temporary)
                temporary.file.close()
            except BaseException as exc:
                for cleanup_error in _cleanup_temporary(directory, temporary):
                    exc.add_note(f'temporary archive cleanup failed: {cleanup_error}')
                raise
            _write_sidecar(directory, output.name, digest)
            return digest
        finally:
            os.close(directory.descriptor)
    except BaseException as exc:
        _cleanup_created_output_parents(created_parents, exc)
        raise


def write_release_archive(
    root: Path,
    output: Path,
    snapshot: ReleaseSnapshot,
) -> str:
    _validate_release_output(output, snapshot)
    published_git_paths = _release_output_git_paths(root, output)
    created_parents = _ensure_output_parent(output)
    try:
        directory = _open_output_directory(output)
        backups: list[_PublicationBackup] = []
        temporaries: list[_TemporaryArchive] = []
        published: dict[str, _TemporaryArchive] = {}
        try:
            _existing_output_mode(directory, output.name)
            _existing_sidecar_mode(directory, f'{output.name}.sha256')
            temporary, digest = _stage_archive(
                root,
                directory,
                output.name,
                snapshot.entries,
                member_modes=dict(snapshot.member_modes),
            )
            temporaries.append(temporary)
            sidecar = _stage_sidecar(directory, output.name, digest)
            temporaries.append(sidecar)
            backups.append(_prepare_publication_backup(directory, output.name))
            backups.append(_prepare_publication_backup(directory, f'{output.name}.sha256'))
            _validate_output_directory_binding(directory)
            _require_release_head(root, _ReleaseHead(snapshot.head_oid, snapshot.tree_oid))
            os.replace(
                temporary.name,
                output.name,
                src_dir_fd=directory.descriptor,
                dst_dir_fd=directory.descriptor,
            )
            published[output.name] = temporary
            _validate_named_identity(
                directory,
                output.name,
                temporary.device,
                temporary.inode,
                'published release archive',
            )
            sidecar_name = f'{output.name}.sha256'
            os.replace(
                sidecar.name,
                sidecar_name,
                src_dir_fd=directory.descriptor,
                dst_dir_fd=directory.descriptor,
            )
            published[sidecar_name] = sidecar
            _validate_named_identity(
                directory,
                sidecar_name,
                sidecar.device,
                sidecar.inode,
                'published release checksum',
            )
            _require_release_head(
                root,
                _ReleaseHead(snapshot.head_oid, snapshot.tree_oid),
                allowed_worktree_paths=published_git_paths,
            )
            temporary.file.close()
            sidecar.file.close()
            for backup in backups:
                _discard_publication_backup(directory, backup)
            return digest
        except BaseException as exc:
            for rollback_error in _rollback_release_publication(directory, backups, published):
                exc.add_note(f'release publication rollback failed: {rollback_error}')
            for temporary in temporaries:
                for cleanup_error in _cleanup_temporary(directory, temporary):
                    exc.add_note(f'release temporary cleanup failed: {cleanup_error}')
            raise
        finally:
            os.close(directory.descriptor)
    except BaseException as exc:
        _cleanup_created_output_parents(created_parents, exc)
        raise


def _default_output(root: Path) -> str:
    version = (root / 'VERSION').read_text(encoding='utf-8').strip() or '0.0.0'
    return f'dist/adaptive-grok-build-pro-v{version}.zip'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default=None)
    args = parser.parse_args()
    root = Path(ROOT).resolve(strict=True)
    output = Path(args.output) if args.output else root / _default_output(root)
    output = output.resolve()
    snapshot = _release_snapshot_from_tracked_head(root)
    digest = write_release_archive(root, output, snapshot)
    print(output)
    print(digest)


if __name__ == '__main__':
    main()
