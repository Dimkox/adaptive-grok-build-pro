from __future__ import annotations

import hashlib
from pathlib import Path

EXCLUDED_PARTS = {
    '.git', '__pycache__', '.pytest_cache', 'node_modules', 'vendor', '.venv', 'dist', '.idea', '.vscode',
}
EXCLUDED_FILES = {'MANIFEST.sha256', '.coverage'}


def included_files(root: Path) -> list[Path]:
    result: list[Path] = []
    for path in root.rglob('*'):
        if not path.is_file() or path.name in EXCLUDED_FILES or any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        rel = path.relative_to(root).as_posix()
        if rel.startswith('.grok-stack/runtime/') and rel != '.grok-stack/runtime/.gitkeep':
            continue
        if rel.endswith(('.pyc', '.pyo', '.zip', '.sha256')):
            continue
        result.append(path)
    return sorted(result, key=lambda item: item.relative_to(root).as_posix())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def generate_manifest(root: Path) -> Path:
    lines = [f'{sha256(path)}  {path.relative_to(root).as_posix()}' for path in included_files(root)]
    target = root / 'MANIFEST.sha256'
    target.write_text('\n'.join(lines) + '\n', encoding='utf-8')
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
    actual_paths = {item.relative_to(root).as_posix(): item for item in included_files(root)}
    for rel, digest in expected.items():
        file = actual_paths.get(rel)
        if file is None:
            errors.append(f'missing: {rel}')
        elif sha256(file) != digest:
            errors.append(f'checksum mismatch: {rel}')
    for rel in sorted(set(actual_paths) - set(expected)):
        errors.append(f'untracked by manifest: {rel}')
    return errors
