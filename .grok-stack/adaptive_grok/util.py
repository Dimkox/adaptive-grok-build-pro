from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

RUNTIME_REL = Path('.grok-stack/runtime')


def now_utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def find_root(start: str | Path | None = None) -> Path:
    current = Path(start or os.getcwd()).resolve()
    if current.is_file():
        current = current.parent
    for candidate in [current, *current.parents]:
        if (candidate / '.grok-stack').is_dir():
            return candidate
    try:
        proc = subprocess.run(
            ['git', 'rev-parse', '--show-toplevel'],
            cwd=current,
            text=True,
            capture_output=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return Path(proc.stdout.strip()).resolve()
    except OSError:
        pass
    return current


def runtime_dir(root: Path) -> Path:
    path = root / RUNTIME_REL
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return default


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f'.{path.name}.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    finally:
        try:
            os.unlink(tmp_name)
        except FileNotFoundError:
            pass


def dump_json(path: Path, data: Any) -> None:
    atomic_write_text(path, json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + '\n')


def run(
    args: list[str],
    *,
    cwd: Path,
    timeout: int = 120,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=merged,
            check=False,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(args, 127, '', f'command not found: {args[0]}')
    except subprocess.TimeoutExpired as exc:
        return subprocess.CompletedProcess(args, 124, exc.stdout or '', exc.stderr or 'timeout')


def command_exists(name: str) -> bool:
    return shutil.which(name) is not None


def git_output(root: Path, *args: str) -> str | None:
    if not command_exists('git'):
        return None
    proc = run(['git', *args], cwd=root, timeout=30)
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def git_head(root: Path) -> str | None:
    return git_output(root, 'rev-parse', 'HEAD')


def git_default_base(root: Path) -> str | None:
    for ref in ('origin/main', 'origin/master', 'main', 'master', 'HEAD'):
        value = git_output(root, 'rev-parse', '--verify', ref)
        if value:
            return value
    return None




def _fingerprint_noise(rel: str) -> bool:
    normalized = rel.replace('\\', '/')
    while normalized.startswith('./'):
        normalized = normalized[2:]
    parts = normalized.split('/')
    if normalized.startswith('.grok-stack/runtime/'):
        return True
    if '__pycache__' in parts or '.pytest_cache' in parts or 'node_modules' in parts or 'vendor' in parts:
        return True
    if normalized.endswith(('.pyc', '.pyo')):
        return True
    if normalized in {'.coverage'} or normalized.startswith('coverage/'):
        return True
    return False


def changed_files(root: Path, base: str | None = None) -> list[str]:
    paths: set[str] = set()
    if git_head(root):
        commands: list[list[str]] = [
            ['git', 'diff', '--name-only', '--cached'],
            ['git', 'diff', '--name-only'],
            ['git', 'ls-files', '--others', '--exclude-standard'],
        ]
        if base:
            commands.insert(0, ['git', 'diff', '--name-only', f'{base}...HEAD'])
        for command in commands:
            proc = run(command, cwd=root, timeout=60)
            if proc.returncode == 0:
                for line in proc.stdout.splitlines():
                    line = line.strip().replace('\\', '/')
                    if line and not _fingerprint_noise(line):
                        paths.add(line)
        return sorted(paths)

    ignored = {'.git', '.grok-stack/runtime', 'vendor', 'node_modules', '.venv', '__pycache__'}
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if any(rel == item or rel.startswith(item + '/') for item in ignored) or _fingerprint_noise(rel):
            continue
        paths.add(rel)
    return sorted(paths)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def tree_fingerprint(root: Path) -> str:
    digest = hashlib.sha256()
    head = git_head(root) or 'NO_HEAD'
    digest.update(head.encode())
    for rel in changed_files(root):
        digest.update(rel.encode())
        path = root / rel
        try:
            if path.is_symlink():
                digest.update(os.readlink(path).encode())
            elif path.is_file():
                digest.update(file_sha256(path).encode())
            else:
                digest.update(b'MISSING')
        except OSError:
            digest.update(b'ERROR')
    return digest.hexdigest()


def slugify(value: str, max_length: int = 48) -> str:
    value = value.lower().strip()
    value = re.sub(r'[^a-zа-яё0-9]+', '-', value, flags=re.IGNORECASE)
    value = value.strip('-') or 'change'
    return value[:max_length].rstrip('-')


def unique_ordered(items: Iterable[str]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def safe_relative_path(root: Path, raw: str | Path) -> str | None:
    try:
        path = Path(raw)
        absolute = path.resolve() if path.is_absolute() else (root / path).resolve()
        rel = absolute.relative_to(root.resolve())
        return rel.as_posix()
    except (ValueError, OSError):
        return None


def read_text_limited(path: Path, limit: int = 2_000_000) -> str:
    try:
        data = path.read_bytes()
    except OSError:
        return ''
    if len(data) > limit or b'\x00' in data:
        return ''
    return data.decode('utf-8', errors='replace')
