from __future__ import annotations

import hashlib
import stat
from pathlib import Path


class HoldoutError(ValueError):
    pass


def bundle_digest(root: Path) -> str:
    """Hash an immutable holdout tree including paths, executable bits, and contents."""
    resolved = root.resolve()
    if not resolved.is_dir():
        raise HoldoutError(f'holdout directory does not exist: {resolved}')
    digest = hashlib.sha256()
    count = 0
    for path in sorted(resolved.rglob('*'), key=lambda item: item.relative_to(resolved).as_posix()):
        if path.is_symlink():
            raise HoldoutError(f'holdout symlinks are forbidden: {path}')
        if not path.is_file():
            continue
        rel = path.relative_to(resolved).as_posix()
        mode = stat.S_IMODE(path.stat().st_mode) & 0o111
        content_digest = hashlib.sha256(path.read_bytes()).hexdigest()
        digest.update(rel.encode('utf-8'))
        digest.update(b'\0')
        digest.update(f'{mode:o}'.encode('ascii'))
        digest.update(b'\0')
        digest.update(content_digest.encode('ascii'))
        digest.update(b'\n')
        count += 1
    if count == 0:
        raise HoldoutError('holdout directory must contain at least one regular file')
    return digest.hexdigest()


def verify_bundle(root: Path, expected_digest: str) -> str:
    normalized = expected_digest.strip().lower()
    if len(normalized) != 64 or any(char not in '0123456789abcdef' for char in normalized):
        raise HoldoutError('expected holdout digest must be lowercase SHA-256')
    actual = bundle_digest(root)
    if actual != normalized:
        raise HoldoutError(f'holdout digest mismatch: expected {normalized}, got {actual}')
    return actual
