from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .policy import DEFAULT_CONTROL_PLANE, DEFAULT_SECRET_READ, _configured_patterns, _matches_any
from .state import has_valid_approval
from .util import file_sha256, load_json, safe_relative_path

SCHEMA_VERSION = 1
EXPECTED_MISSING = 'MISSING'
MAX_OPERATIONS = 100
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_BATCH_BYTES = 32 * 1024 * 1024
_SHA256_RE = re.compile(r'^[0-9a-f]{64}$')


class ProtectedWriteError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProtectedWriteOperation:
    path: str
    expected_sha256: str
    content: bytes


@dataclass(frozen=True)
class _PreparedWrite:
    operation: ProtectedWriteOperation
    target: Path
    existed: bool
    original: bytes | None
    mode: int


def load_manifest(path: Path) -> list[ProtectedWriteOperation]:
    try:
        raw = json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError as exc:
        raise ProtectedWriteError(f'manifest does not exist: {path}') from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ProtectedWriteError(f'cannot read protected-write manifest {path}: {exc}') from exc
    if not isinstance(raw, Mapping) or raw.get('schema_version') != SCHEMA_VERSION:
        raise ProtectedWriteError(f'manifest schema_version must be {SCHEMA_VERSION}')
    items = raw.get('operations')
    if not isinstance(items, list) or not items:
        raise ProtectedWriteError('manifest operations must be a non-empty list')
    if len(items) > MAX_OPERATIONS:
        raise ProtectedWriteError(f'manifest contains more than {MAX_OPERATIONS} operations')

    operations: list[ProtectedWriteOperation] = []
    seen: set[str] = set()
    total = 0
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            raise ProtectedWriteError(f'operation {index} must be an object')
        path_value = item.get('path')
        if not isinstance(path_value, str) or not path_value.strip():
            raise ProtectedWriteError(f'operation {index} requires a non-empty path')
        normalized_path = path_value.replace('\\', '/').strip()
        if normalized_path in seen:
            raise ProtectedWriteError(f'duplicate operation path: {normalized_path}')
        seen.add(normalized_path)

        expected = str(item.get('expected_sha256', '')).strip()
        if expected != EXPECTED_MISSING:
            expected = expected.lower()
            if not _SHA256_RE.fullmatch(expected):
                raise ProtectedWriteError(
                    f'operation {index} expected_sha256 must be {EXPECTED_MISSING} or 64 lowercase hex characters'
                )

        has_text = 'content' in item
        has_base64 = 'content_base64' in item
        if has_text == has_base64:
            raise ProtectedWriteError(
                f'operation {index} must contain exactly one of content or content_base64'
            )
        if has_text:
            value = item['content']
            if not isinstance(value, str):
                raise ProtectedWriteError(f'operation {index} content must be a string')
            content = value.encode('utf-8')
        else:
            value = item['content_base64']
            if not isinstance(value, str):
                raise ProtectedWriteError(f'operation {index} content_base64 must be a string')
            try:
                content = base64.b64decode(value, validate=True)
            except (binascii.Error, ValueError) as exc:
                raise ProtectedWriteError(f'operation {index} content_base64 is invalid') from exc

        if len(content) > MAX_FILE_BYTES:
            raise ProtectedWriteError(f'operation {index} exceeds {MAX_FILE_BYTES} bytes')
        total += len(content)
        if total > MAX_BATCH_BYTES:
            raise ProtectedWriteError(f'manifest exceeds {MAX_BATCH_BYTES} bytes in total')
        operations.append(ProtectedWriteOperation(normalized_path, expected, content))
    return operations


def apply_manifest(root: Path, manifest_path: Path, *, dry_run: bool = False) -> dict[str, Any]:
    resolved_root = root.resolve()
    resolved_manifest = manifest_path.resolve()
    try:
        resolved_manifest.relative_to(resolved_root)
    except ValueError:
        pass
    else:
        raise ProtectedWriteError('protected-write manifest must live outside the repository')

    operations = load_manifest(resolved_manifest)
    config = load_json(resolved_root / '.grok-stack/config/policy.json', {}) or {}
    if not isinstance(config, dict):
        config = {}
    control_plane = _configured_patterns(config, 'control_plane_paths', DEFAULT_CONTROL_PLANE)
    secret_read = _configured_patterns(config, 'secret_read_paths', DEFAULT_SECRET_READ)
    prepared: list[_PreparedWrite] = []
    canonical_paths: set[str] = set()

    # Validate the complete batch before the first mutation. This preserves one
    # exact tree-bound grant across a multi-file control-plane edit.
    for operation in operations:
        rel = safe_relative_path(resolved_root, operation.path)
        if rel is None:
            raise ProtectedWriteError(f'path escapes repository root: {operation.path}')
        if rel in canonical_paths:
            raise ProtectedWriteError(f'duplicate canonical operation path: {rel}')
        canonical_paths.add(rel)
        if not _matches_any(rel, control_plane):
            raise ProtectedWriteError(f'path is not part of the repository control plane: {rel}')
        if _matches_any(rel, secret_read) or rel == '.git' or rel.startswith('.git/'):
            raise ProtectedWriteError(f'secret or Git metadata path cannot be batch-written: {rel}')

        target = resolved_root / rel
        if not target.parent.is_dir():
            raise ProtectedWriteError(f'target parent directory does not exist: {rel}')
        if target.is_symlink():
            raise ProtectedWriteError(f'symlink targets are forbidden: {rel}')
        if target.exists() and not target.is_file():
            raise ProtectedWriteError(f'target is not a regular file: {rel}')

        existed = target.exists()
        current = file_sha256(target) if existed else EXPECTED_MISSING
        if current != operation.expected_sha256:
            raise ProtectedWriteError(
                f'optimistic-lock mismatch for {rel}: expected {operation.expected_sha256}, found {current}'
            )
        if not has_valid_approval(
            resolved_root,
            'protected-path',
            action='protected-path-write',
            resource=rel,
        ):
            raise ProtectedWriteError(f'no exact protected-path grant for {rel}')
        prepared.append(
            _PreparedWrite(
                operation=ProtectedWriteOperation(rel, operation.expected_sha256, operation.content),
                target=target,
                existed=existed,
                original=target.read_bytes() if existed else None,
                mode=(target.stat().st_mode & 0o777) if existed else 0o644,
            )
        )

    planned = [
        {
            'path': item.operation.path,
            'previous_sha256': item.operation.expected_sha256,
            'new_sha256': hashlib.sha256(item.operation.content).hexdigest(),
            'bytes': len(item.operation.content),
        }
        for item in prepared
    ]
    if dry_run:
        return {'ok': True, 'dry_run': True, 'operations': planned}

    staged: dict[Path, Path] = {}
    replaced: list[_PreparedWrite] = []
    try:
        for item in prepared:
            staged[item.target] = _stage(item.target, item.operation.content, item.mode)
        for item in prepared:
            current = file_sha256(item.target) if item.target.exists() else EXPECTED_MISSING
            if current != item.operation.expected_sha256:
                raise ProtectedWriteError(
                    f'optimistic lock changed during batch for {item.operation.path}: '
                    f'expected {item.operation.expected_sha256}, found {current}'
                )
            os.replace(staged.pop(item.target), item.target)
            _fsync_directory(item.target.parent)
            replaced.append(item)
    except Exception as exc:
        rollback_errors: list[str] = []
        for item in reversed(replaced):
            try:
                if item.existed:
                    assert item.original is not None
                    restore = _stage(item.target, item.original, item.mode)
                    os.replace(restore, item.target)
                    _fsync_directory(item.target.parent)
                else:
                    item.target.unlink(missing_ok=True)
                    _fsync_directory(item.target.parent)
            except Exception as rollback_exc:  # pragma: no cover - catastrophic filesystem failure
                rollback_errors.append(f'{item.operation.path}: {rollback_exc}')
        suffix = f'; rollback errors: {rollback_errors}' if rollback_errors else ''
        if isinstance(exc, ProtectedWriteError):
            raise ProtectedWriteError(f'{exc}{suffix}') from exc
        raise ProtectedWriteError(f'protected batch write failed: {exc}{suffix}') from exc
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)

    return {'ok': True, 'dry_run': False, 'operations': planned}


def _stage(target: Path, content: bytes, mode: int) -> Path:
    descriptor, temporary_name = tempfile.mkstemp(prefix=f'.{target.name}.grok-write-', dir=target.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise
    return temporary


def _fsync_directory(path: Path) -> None:
    try:
        descriptor = os.open(path, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(descriptor)
    except OSError:
        pass
    finally:
        os.close(descriptor)
