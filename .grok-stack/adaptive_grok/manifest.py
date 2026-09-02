from __future__ import annotations

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import BinaryIO

EXCLUDED_PARTS = {
    '.git', '__pycache__', '.pytest_cache', 'node_modules', 'vendor', '.venv', 'dist', 'build', '.idea', '.vscode',
    'htmlcov', '.ruff_cache',
}
EXCLUDED_FILES = {'MANIFEST.sha256', '.coverage', '.env', 'err.log'}
SECRET_SUFFIXES = ('.pem', '.key', '.p12', '.pfx')
READ_CHUNK_BYTES = 1024 * 1024


class ManifestError(RuntimeError):
    pass


def _descriptor_flags() -> tuple[int, int]:
    try:
        directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
        file_flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC
    except AttributeError as exc:
        raise ManifestError('secure package source descriptors are unsupported on this platform') from exc
    if os.open not in getattr(os, 'supports_dir_fd', set()):
        raise ManifestError('descriptor-relative package source opens are unsupported on this platform')
    return directory_flags, file_flags


@dataclass(frozen=True)
class FileIdentity:
    device: int
    inode: int
    mode: int
    size: int
    mtime_ns: int
    ctime_ns: int


@dataclass(frozen=True)
class ManifestEntry:
    relative_path: str
    identity: FileIdentity
    digest: str


def _is_secret_path(rel: str, name: str) -> bool:
    if name == '.env' or name.startswith('.env.'):
        return name != '.env.example'
    return name.endswith(SECRET_SUFFIXES)


def is_included_relative_path(relative: str | PurePosixPath) -> bool:
    path = PurePosixPath(relative)
    if path.is_absolute() or not path.parts or any(part in {'', '.', '..'} for part in path.parts):
        return False
    rel = path.as_posix()
    if path.name in EXCLUDED_FILES or any(part in EXCLUDED_PARTS for part in path.parts):
        return False
    if _is_secret_path(rel, path.name):
        return False
    if rel.startswith('.grok-stack/runtime/') and rel != '.grok-stack/runtime/.gitkeep':
        return False
    if '20260817-' in rel or path.name.endswith('-pin.env'):
        return False
    if path.name == '.coverage' or path.name.startswith('.coverage.'):
        return False
    return not rel.endswith(('.pyc', '.pyo', '.zip', '.sha256'))


def included_files(root: Path) -> list[Path]:
    canonical_root = root.resolve(strict=True)
    result: list[Path] = []
    for path in canonical_root.rglob('*'):
        try:
            metadata = path.lstat()
        except OSError as exc:
            raise ManifestError(f'cannot inspect package source path: {path.relative_to(canonical_root)}') from exc
        if not stat.S_ISREG(metadata.st_mode):
            continue
        rel = path.relative_to(canonical_root).as_posix()
        if not is_included_relative_path(rel):
            continue
        result.append(path)
    return sorted(result, key=lambda item: item.relative_to(canonical_root).as_posix())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(READ_CHUNK_BYTES), b''):
            digest.update(chunk)
    return digest.hexdigest()


def _identity(metadata: os.stat_result) -> FileIdentity:
    return FileIdentity(
        device=metadata.st_dev,
        inode=metadata.st_ino,
        mode=metadata.st_mode,
        size=metadata.st_size,
        mtime_ns=metadata.st_mtime_ns,
        ctime_ns=metadata.st_ctime_ns,
    )


def _open_root(root: Path) -> tuple[Path, int]:
    canonical_root = root.resolve(strict=True)
    directory_flags, _file_flags = _descriptor_flags()
    try:
        descriptor = os.open(canonical_root, directory_flags)
    except OSError as exc:
        raise ManifestError('cannot open package source root safely') from exc
    try:
        metadata = os.fstat(descriptor)
    except OSError as exc:
        os.close(descriptor)
        raise ManifestError('cannot inspect package source root safely') from exc
    if not stat.S_ISDIR(metadata.st_mode):
        os.close(descriptor)
        raise ManifestError('package source root is not a directory')
    return canonical_root, descriptor


def _relative_parts(root: Path, path: Path) -> tuple[str, tuple[str, ...]]:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise ManifestError('package source path escapes the repository root') from exc
    if not relative.parts or any(part in {'', '.', '..'} for part in relative.parts):
        raise ManifestError('package source path is invalid')
    return relative.as_posix(), relative.parts


def _open_regular_at(root_descriptor: int, parts: tuple[str, ...], relative_path: str) -> int:
    directory_flags, file_flags = _descriptor_flags()
    directory_descriptor = os.dup(root_descriptor)
    try:
        for component in parts[:-1]:
            next_descriptor = os.open(
                component,
                directory_flags,
                dir_fd=directory_descriptor,
            )
            os.close(directory_descriptor)
            directory_descriptor = next_descriptor
        descriptor = os.open(parts[-1], file_flags, dir_fd=directory_descriptor)
    except OSError as exc:
        raise ManifestError(f'cannot open package source safely: {relative_path}') from exc
    finally:
        os.close(directory_descriptor)
    try:
        metadata = os.fstat(descriptor)
    except OSError as exc:
        os.close(descriptor)
        raise ManifestError(f'cannot inspect package source safely: {relative_path}') from exc
    if not stat.S_ISREG(metadata.st_mode):
        os.close(descriptor)
        raise ManifestError(f'package source is not a regular file: {relative_path}')
    return descriptor


def _stable_digest(descriptor: int, relative_path: str) -> tuple[FileIdentity, str]:
    before = _identity(os.fstat(descriptor))
    digest = hashlib.sha256()
    while chunk := os.read(descriptor, READ_CHUNK_BYTES):
        digest.update(chunk)
    after = _identity(os.fstat(descriptor))
    if after != before:
        raise ManifestError(f'package source changed while hashing: {relative_path}')
    return before, digest.hexdigest()


def snapshot_files(root: Path, files: list[Path] | None = None) -> list[ManifestEntry]:
    canonical_root, root_descriptor = _open_root(root)
    try:
        source_files = included_files(canonical_root) if files is None else files
        entries: list[ManifestEntry] = []
        for path in source_files:
            relative_path, parts = _relative_parts(canonical_root, path)
            descriptor = _open_regular_at(root_descriptor, parts, relative_path)
            try:
                identity, digest = _stable_digest(descriptor, relative_path)
            finally:
                os.close(descriptor)
            entries.append(ManifestEntry(relative_path, identity, digest))
    finally:
        os.close(root_descriptor)
    return sorted(entries, key=lambda entry: entry.relative_path)


def render_manifest(
    root: Path,
    files: list[Path] | None = None,
    *,
    entries: list[ManifestEntry] | None = None,
) -> bytes:
    if entries is not None and files is not None:
        raise ManifestError('manifest accepts files or entries, not both')
    if entries is None:
        canonical_root = root.resolve(strict=True)
        source_files = included_files(canonical_root) if files is None else files
        lines = [
            f'{sha256(path)}  {path.relative_to(canonical_root).as_posix()}'
            for path in source_files
        ]
    else:
        lines = [f'{entry.digest}  {entry.relative_path}' for entry in entries]
    return ('\n'.join(lines) + '\n').encode('utf-8')


def stream_entry(root: Path, entry: ManifestEntry, destination: BinaryIO) -> None:
    canonical_root, root_descriptor = _open_root(root)
    try:
        _relative_path, parts = _relative_parts(canonical_root, canonical_root / entry.relative_path)
        descriptor = _open_regular_at(root_descriptor, parts, entry.relative_path)
        try:
            before = _identity(os.fstat(descriptor))
            if before != entry.identity:
                raise ManifestError(f'package source was replaced: {entry.relative_path}')
            digest = hashlib.sha256()
            while chunk := os.read(descriptor, READ_CHUNK_BYTES):
                digest.update(chunk)
                destination.write(chunk)
            after = _identity(os.fstat(descriptor))
        finally:
            os.close(descriptor)
    finally:
        os.close(root_descriptor)
    if after != before or digest.hexdigest() != entry.digest:
        raise ManifestError(f'package source changed while archiving: {entry.relative_path}')


def generate_manifest(root: Path) -> Path:
    target = root / 'MANIFEST.sha256'
    target.write_bytes(render_manifest(root))
    return target


def verify_manifest(root: Path) -> list[str]:
    path = root / 'MANIFEST.sha256'
    if not path.is_file():
        return ['MANIFEST.sha256 is missing']
    expected: dict[str, str] = {}
    errors: list[str] = []
    for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), start=1):
        if not line.strip():
            continue
        try:
            digest, rel = line.split('  ', 1)
        except ValueError:
            errors.append(f'line {number}: invalid manifest format')
            continue
        expected[rel] = digest
    canonical_root = root.resolve(strict=True)
    actual_paths = {
        item.relative_to(canonical_root).as_posix(): item
        for item in included_files(canonical_root)
    }
    for rel, digest in expected.items():
        file = actual_paths.get(rel)
        if file is None:
            errors.append(f'missing: {rel}')
        elif sha256(file) != digest:
            errors.append(f'checksum mismatch: {rel}')
    for rel in sorted(set(actual_paths) - set(expected)):
        errors.append(f'untracked by manifest: {rel}')
    return errors
