from __future__ import annotations

import argparse
import hashlib
import os
import secrets
import stat
import sys
import zipfile
from pathlib import Path
from typing import BinaryIO, NamedTuple

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / '.grok-stack'))

from adaptive_grok.manifest import READ_CHUNK_BYTES, render_manifest, snapshot_files, stream_entry
from adaptive_grok.util import find_root

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


def _write_sidecar(directory: _OutputDirectory, output_name: str, digest: str) -> None:
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


def write_archive(root: Path, output: Path) -> str:
    entries = snapshot_files(root)
    manifest = render_manifest(root, entries=entries)
    members = [
        (entry.relative_path, entry.identity.mode, entry)
        for entry in entries
    ]
    members.append(('MANIFEST.sha256', 0o100644, manifest))
    created_parents = _ensure_output_parent(output)
    try:
        directory = _open_output_directory(output)
        try:
            _existing_sidecar_mode(directory, f'{output.name}.sha256')
            temporary = _create_temporary_archive(directory, output.name)
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


def _default_output(root: Path) -> str:
    version = (root / 'VERSION').read_text(encoding='utf-8').strip() or '0.0.0'
    return f'dist/adaptive-grok-build-pro-v{version}.zip'


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default=None)
    args = parser.parse_args()
    root = find_root(ROOT)
    output = Path(args.output) if args.output else root / _default_output(root)
    output = output.resolve()
    digest = write_archive(root, output)
    print(output)
    print(digest)


if __name__ == '__main__':
    main()
