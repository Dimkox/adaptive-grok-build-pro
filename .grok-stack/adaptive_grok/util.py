from __future__ import annotations

import hashlib
import json
import locale
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
    # Escapes preserve filesystem surrogate code points in valid UTF-8 JSON.
    atomic_write_text(path, json.dumps(data, ensure_ascii=True, indent=2, sort_keys=True) + '\n')


def run(
    args: list[str],
    *,
    cwd: Path,
    timeout: int = 120,
    env: dict[str, str] | None = None,
    encoding: str | None = None,
    errors: str = 'strict',
) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    if env:
        merged.update(env)
    try:
        options: dict[str, str] = {}
        if encoding is not None:
            options['encoding'] = encoding
        if errors != 'strict':
            options['errors'] = errors
        return subprocess.run(
            args,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            env=merged,
            check=False,
            **options,
        )
    except FileNotFoundError:
        return subprocess.CompletedProcess(args, 127, '', f'command not found: {args[0]}')
    except subprocess.TimeoutExpired as exc:
        stdout = exc.stdout or ''
        stderr = exc.stderr or 'timeout'
        if encoding is not None or errors != 'strict':
            output_encoding = encoding or locale.getpreferredencoding(False)
            if isinstance(stdout, bytes):
                stdout = stdout.decode(output_encoding, errors)
            if isinstance(stderr, bytes):
                stderr = stderr.decode(output_encoding, errors)
        return subprocess.CompletedProcess(args, 124, stdout, stderr)


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
    # Git -z and relative_to(...).as_posix() already use directory slashes.
    # Backslashes in these paths are literal filename data on POSIX.
    parts = rel.split('/')
    if rel.startswith('.grok-stack/runtime/'):
        return True
    if '__pycache__' in parts or '.pytest_cache' in parts or 'node_modules' in parts or 'vendor' in parts:
        return True
    if rel.endswith(('.pyc', '.pyo')):
        return True
    if rel in {'.coverage'} or rel.startswith('coverage/'):
        return True
    return False


def _git_paths(root: Path, *args: str) -> set[str] | None:
    try:
        # -z emits filesystem bytes, not quoted text. Binary mode also avoids
        # newline translation changing legal carriage returns in filenames.
        proc = subprocess.run(
            ['git', *args], cwd=root, capture_output=True, timeout=60, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    # An unsuccessful or malformed inventory cannot establish untracked ownership.
    if proc.returncode != 0 or (proc.stdout and not proc.stdout.endswith(b'\0')):
        return None
    return {os.fsdecode(path) for path in proc.stdout.split(b'\0') if path}


def _git_name_status(root: Path, *args: str) -> list[dict[str, str]] | None:
    try:
        # Name-status records use one NUL-delimited field per status/path.  A
        # rename or copy has an additional original-path field.
        proc = subprocess.run(
            ['git', *args], cwd=root, capture_output=True, timeout=60, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0 or (proc.stdout and not proc.stdout.endswith(b'\0')):
        return None

    fields = proc.stdout.split(b'\0')
    if fields and fields[-1] == b'':
        fields.pop()
    records: list[dict[str, str]] = []
    index = 0
    while index < len(fields):
        status = os.fsdecode(fields[index])
        index += 1
        if not status:
            return None
        if status[:1] in {'R', 'C'}:
            if index + 1 >= len(fields):
                return None
            original_path = os.fsdecode(fields[index])
            path = os.fsdecode(fields[index + 1])
            index += 2
            records.append({
                'status': status,
                'original_path': original_path,
                'path': path,
            })
        else:
            if index >= len(fields):
                return None
            records.append({
                'status': status,
                'path': os.fsdecode(fields[index]),
            })
            index += 1
    return records


def changed_file_statuses(
    root: Path,
    base: str | None = None,
    *,
    include_worktree: bool = True,
    include_untracked: bool = True,
) -> list[dict[str, str]] | None:
    """Return focused-only Git status records without changing ``changed_files``.

    The ordinary changed-file inventory intentionally returns names for the
    repository fingerprint.  Focused verification additionally needs Git's
    status and rename/copy provenance so it can reject unsafe landing/test
    changes instead of treating them as ordinary modifications.
    """
    if not command_exists('git') or not git_head(root):
        return None

    records: list[dict[str, str]] = []

    def add_diff(source: str, *arguments: str) -> bool:
        parsed = _git_name_status(root, *arguments)
        if parsed is None:
            return False
        for item in parsed:
            item['source'] = source
            records.append(item)
        return True

    if base is not None and not add_diff(
        f'range:{base}',
        'diff', '--name-status', '--find-renames', '--find-copies',
        '--find-copies-harder', '-z', f'{base}...HEAD',
    ):
        return None
    if include_worktree:
        if not add_diff(
            'index', 'diff', '--name-status', '--find-renames', '--find-copies',
            '--find-copies-harder', '-z', '--cached',
        ):
            return None
        if not add_diff(
            'worktree', 'diff', '--name-status', '--find-renames', '--find-copies',
            '--find-copies-harder', '-z',
        ):
            return None
    if include_untracked:
        untracked = _git_paths(root, 'ls-files', '--others', '--exclude-standard', '-z')
        if untracked is None:
            return None
        records.extend(
            {
                'status': '??',
                'path': path,
                'source': 'untracked',
            }
            for path in sorted(untracked)
            if not (_fingerprint_noise(path) or path.startswith('.qwen/tmp/'))
        )
    return records


def changed_files(root: Path, base: str | None = None) -> list[str]:
    paths: set[str] = set()
    indexed = _git_paths(root, 'ls-files', '--cached', '-z')
    if git_head(root):
        commands = [
            ['diff', '--name-only', '--no-renames', '-z', '--cached'],
            ['diff', '--name-only', '--no-renames', '-z'],
        ]
        if base:
            commands.insert(0, ['diff', '--name-only', '--no-renames', '-z', f'{base}...HEAD'])
        tracking_known = indexed is not None
        for command in commands:
            changed = _git_paths(root, *command)
            if changed is None:
                tracking_known = False
            else:
                # Diff provenance also protects staged deletions, absent from the index.
                paths.update(changed)
        for rel in _git_paths(root, 'ls-files', '--others', '--exclude-standard', '-z') or ():
            if (rel in paths or rel in (indexed or ()) or not tracking_known
                    or not (_fingerprint_noise(rel) or rel.startswith('.qwen/tmp/'))):
                paths.add(rel)
        return sorted(paths)

    # No HEAD is not proof of untracked ownership: retain scratch and every index
    # entry, including staged files subsequently removed from the worktree.
    paths.update(indexed or ())
    for path in root.rglob('*'):
        if not path.is_file():
            continue
        rel = path.relative_to(root).as_posix()
        if rel == '.git' or rel.startswith('.git/'):
            continue
        if (indexed is not None and rel not in indexed
                and (_fingerprint_noise(rel) or rel.startswith('.venv/'))):
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
        digest.update(os.fsencode(rel))
        path = root / rel
        try:
            if path.is_symlink():
                digest.update(os.fsencode(os.readlink(path)))
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
